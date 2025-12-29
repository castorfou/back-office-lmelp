"""Service de recherche d'URL de page RadioFrance.

Ce service scrape la page de recherche RadioFrance pour trouver l'URL
de la page d'un épisode de podcast à partir de son titre.

Le service utilise deux stratégies de parsing :
1. JSON-LD (Schema.org ItemList) - plus robuste et structuré
2. Fallback sur parsing HTML des liens <a href> si JSON-LD absent
"""

import asyncio
import json
import logging
import os
from typing import Any
from urllib.parse import quote_plus

import aiohttp
import openai
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


class RadioFranceService:
    """Service pour rechercher l'URL de page d'un épisode sur RadioFrance."""

    def __init__(self):
        """Initialise le service RadioFrance."""
        self.base_url = "https://www.radiofrance.fr"
        self.podcast_search_base = "/franceinter/podcasts/le-masque-et-la-plume"

        # Configuration Azure OpenAI pour extraction de métadonnées par LLM
        self.azure_endpoint = os.getenv("AZURE_ENDPOINT")
        self.api_key = os.getenv("AZURE_API_KEY")
        self.api_version = os.getenv("AZURE_API_VERSION", "2024-09-01-preview")
        self.deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")

        # Configuration client OpenAI
        if (
            self.azure_endpoint
            and self.api_key
            and self.azure_endpoint.strip()
            and self.api_key.strip()
        ):
            try:
                self.client = openai.AzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.azure_endpoint,
                )
                logger.info("✅ Azure OpenAI client initialisé pour RadioFranceService")
            except Exception as e:
                logger.warning(
                    f"⚠️ Erreur initialisation Azure OpenAI client: {type(e).__name__}: {e}"
                )
                self.client = None
        else:
            logger.info(
                "ℹ️ Azure OpenAI client non configuré pour RadioFranceService (extraction JSON-LD uniquement)"
            )
            self.client = None

    async def search_episode_page_url(
        self, episode_title: str, episode_date: str | None = None
    ) -> str | None:
        """Recherche l'URL de la page d'un épisode par son titre et optionnellement sa date.

        Args:
            episode_title: Titre de l'épisode à rechercher
            episode_date: Date de l'épisode au format YYYY-MM-DD (optionnel).
                         Si fournie, seules les URLs dont la date correspond seront retournées.

        Returns:
            URL complète de la page de l'épisode, ou None si non trouvé
        """
        try:
            # Construire l'URL de recherche
            search_query = quote_plus(episode_title)
            search_url = (
                f"{self.base_url}{self.podcast_search_base}?search={search_query}"
            )

            logger.info(f"Searching RadioFrance for episode: {episode_title[:50]}...")

            # Faire la requête HTTP
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    search_url, timeout=aiohttp.ClientTimeout(total=10)
                ) as response,
            ):
                if response.status != 200:
                    logger.warning(
                        f"RadioFrance search returned status {response.status}"
                    )
                    return None

                html_content = await response.text()

            # Parser le HTML avec BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")

            # Si episode_date fournie, utiliser la stratégie de filtrage par date
            if episode_date:
                logger.warning(
                    f"🔍 Searching with date filter: {episode_date} for episode: {episode_title[:50]}..."
                )
                # Extraire toutes les URLs candidates
                candidate_urls = self._extract_all_candidate_urls(soup)
                logger.warning(
                    f"🔍 Found {len(candidate_urls)} candidate URLs to check"
                )

                # Parcourir chaque URL et vérifier sa date
                for url in candidate_urls:
                    logger.warning(f"🔍 Checking URL: {url}")
                    episode_date_from_page = await self._extract_episode_date(url)
                    logger.warning(f"🔍   → Date extracted: {episode_date_from_page}")
                    if episode_date_from_page and episode_date_from_page.startswith(
                        episode_date
                    ):
                        logger.warning(
                            f"✅ Found matching episode URL by date: {url} (date: {episode_date_from_page})"
                        )
                        return url

                logger.warning(
                    f"❌ No episode page URL found matching date {episode_date} for: {episode_title[:50]}..."
                )
                return None

            # Stratégie sans filtrage par date (comportement original)
            # Stratégie 1 : Parser le JSON-LD (Schema.org ItemList)
            # Plus robuste car structure standardisée
            json_ld_url = self._parse_json_ld(soup)
            if json_ld_url:
                logger.info(f"Found episode page URL via JSON-LD: {json_ld_url}")
                return json_ld_url

            # Stratégie 2 (fallback) : Parser les liens HTML <a href>
            # Utilisé si JSON-LD absent ou invalide
            html_url = self._parse_html_links(soup)
            if html_url:
                logger.info(f"Found episode page URL via HTML: {html_url}")
                return html_url

            logger.warning(f"No episode page URL found for: {episode_title[:50]}...")
            return None

        except Exception as e:
            logger.error(f"Error searching RadioFrance: {e}")
            return None

    def _is_valid_episode_url(self, url: str) -> bool:
        """Vérifie qu'une URL est bien un épisode valide et pas une page statique.

        Les épisodes ont un pattern d'URL spécifique avec un slug contenant une date.
        Les pages statiques comme /contact, /a-propos doivent être filtrées.

        Args:
            url: URL à valider

        Returns:
            True si l'URL est un épisode valide, False sinon
        """
        # Liste des pages statiques à exclure
        static_pages = ["/contact", "/a-propos", "/rss", "/feed"]

        # Vérifier que l'URL ne finit pas par une page statique
        for static_page in static_pages:
            if url.endswith(static_page):
                return False

        # Les épisodes valides se terminent par un ID numérique (4 chiffres minimum)
        # Exemples valides:
        # - /le-masque-et-la-plume-du-dimanche-10-decembre-2023-5870209
        # - /les-nouveaux-ouvrages-de-francois-truffaut-joel-dicker-...-4010930
        # Les URLs d'épisode se terminent toujours par -{ID_NUMERIQUE}
        import re

        # Pattern: se termine par un tiret suivi de 4 chiffres ou plus
        return bool(re.search(r"-\d{4,}$", url))

    def _parse_json_ld(self, soup: BeautifulSoup) -> str | None:
        """Parse JSON-LD Schema.org ItemList pour extraire l'URL du premier résultat.

        RadioFrance utilise le format JSON-LD pour décrire les résultats de recherche :
        {
          "@type": "ItemList",
          "itemListElement": [
            {"@type": "ListItem", "position": 1, "url": "https://..."}
          ]
        }

        Args:
            soup: BeautifulSoup object du HTML

        Returns:
            URL du premier résultat VALIDE (épisode), ou None si JSON-LD absent/invalide
        """
        try:
            # Chercher tous les scripts JSON-LD
            json_ld_scripts = soup.find_all("script", type="application/ld+json")

            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)

                    # Vérifier si c'est une ItemList
                    if isinstance(data, dict) and data.get("@type") == "ItemList":
                        items = data.get("itemListElement", [])

                        # Parcourir TOUS les résultats, pas seulement le premier
                        for item in items:
                            url: str = item.get("url", "")

                            # Vérifier que c'est bien un lien d'épisode
                            if (
                                self.podcast_search_base in url
                                and self._is_valid_episode_url(url)
                            ):
                                return url

                except (json.JSONDecodeError, KeyError, TypeError):
                    # JSON invalide ou structure inattendue, continuer
                    continue

            return None

        except Exception as e:
            logger.debug(f"Error parsing JSON-LD: {e}")
            return None

    def _parse_html_links(self, soup: BeautifulSoup) -> str | None:
        """Parse les liens HTML <a href> pour extraire l'URL du premier résultat VALIDE.

        Stratégie de fallback si JSON-LD absent.
        Cherche le premier lien VALIDE (épisode) contenant le chemin du podcast.
        Filtre les pages statiques comme /contact, /a-propos, etc.

        Args:
            soup: BeautifulSoup object du HTML

        Returns:
            URL du premier résultat valide, ou None si aucun lien trouvé
        """
        try:
            links = soup.find_all("a", href=True)
            for link in links:
                href = link.get("href", "")
                if (
                    self.podcast_search_base in href
                    and href != self.podcast_search_base
                    and self._is_valid_episode_url(href)
                ):
                    # Construire l'URL complète si c'est un chemin relatif
                    if href.startswith("/"):
                        full_url = f"{self.base_url}{href}"
                    else:
                        full_url = href

                    return full_url

            return None

        except Exception as e:
            logger.debug(f"Error parsing HTML links: {e}")
            return None

    def _extract_all_candidate_urls(self, soup: BeautifulSoup) -> list[str]:
        """Extrait toutes les URLs candidates depuis la page de recherche.

        Utilise d'abord le JSON-LD ItemList, puis fallback sur les liens HTML.

        Args:
            soup: BeautifulSoup object du HTML

        Returns:
            Liste des URLs complètes des épisodes candidats
        """
        candidate_urls = []

        try:
            # Stratégie 1: JSON-LD ItemList
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get("@type") == "ItemList":
                        items = data.get("itemListElement", [])
                        for item in items:
                            url = item.get("url", "")
                            if (
                                self.podcast_search_base in url
                                and self._is_valid_episode_url(url)
                            ):
                                candidate_urls.append(url)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

            # Stratégie 2 (fallback): Liens HTML
            if not candidate_urls:
                links = soup.find_all("a", href=True)
                for link in links:
                    href = link.get("href", "")
                    if (
                        self.podcast_search_base in href
                        and href != self.podcast_search_base
                        and self._is_valid_episode_url(href)
                    ):
                        if href.startswith("/"):
                            full_url = f"{self.base_url}{href}"
                        else:
                            full_url = href
                        candidate_urls.append(full_url)

        except Exception as e:
            logger.debug(f"Error extracting candidate URLs: {e}")

        return candidate_urls

    async def _extract_episode_date(self, episode_url: str) -> str | None:
        """Extrait la date de publication d'un épisode depuis son URL.

        Fait une requête GET sur l'URL de l'épisode et extrait la date
        depuis le JSON-LD (champ datePublished).

        Args:
            episode_url: URL complète de la page de l'épisode

        Returns:
            Date au format YYYY-MM-DD, ou None si non trouvée
        """
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    episode_url, timeout=aiohttp.ClientTimeout(total=10)
                ) as response,
            ):
                if response.status != 200:
                    logger.debug(
                        f"Failed to fetch episode page {episode_url}: status {response.status}"
                    )
                    return None

                html_content = await response.text()
                soup = BeautifulSoup(html_content, "html.parser")

                # Chercher le JSON-LD avec datePublished
                json_ld_scripts = soup.find_all("script", type="application/ld+json")
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)

                        # Chercher dans @graph si présent
                        if isinstance(data, dict) and "@graph" in data:
                            for item in data["@graph"]:
                                if "datePublished" in item:
                                    date_str = str(item["datePublished"])
                                    # Format: 2022-04-24T09:00:00.000Z -> 2022-04-24
                                    return date_str.split("T")[0]

                        # Chercher directement dans data
                        if isinstance(data, dict) and "datePublished" in data:
                            date_str = str(data["datePublished"])
                            return date_str.split("T")[0]

                    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
                        continue

                return None

        except Exception as e:
            logger.debug(f"Error extracting date from {episode_url}: {e}")
            return None

    async def extract_episode_metadata(self, episode_url: str) -> dict[str, Any]:
        """
        Scrape métadonnées depuis page RadioFrance épisode.

        Stratégie avec fallback LLM pour vieilles pages (2019) sans JSON-LD:
        1. Fetch HTML avec aiohttp
        2. Parse JSON-LD (PodcastEpisode @type) si disponible
        3. Si JSON-LD absent, utiliser LLM pour extraire depuis texte complet
        4. Extraire: animateur, critiques, date, image_url

        Returns:
            {
                "animateur": str,
                "critiques": list[str],
                "date": str (ISO),
                "image_url": str,
                "description": str,
                "page_text": str  # Contenu textuel complet de la page
            }
        """
        if not episode_url:
            return {}

        try:
            import aiohttp

            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    episode_url, timeout=aiohttp.ClientTimeout(total=10)
                ) as response,
            ):
                if response.status != 200:
                    logger.warning(
                        f"RadioFrance metadata extraction status {response.status}"
                    )
                    return {}

                html_content = await response.text()

            soup = BeautifulSoup(html_content, "html.parser")

            # Extraire tout le texte visible de la page (pour Phase 2)
            page_text = soup.get_text(separator="\n", strip=True)

            # Stratégie 1: Parse JSON-LD (pages récentes 2024+)
            metadata = self._parse_json_ld_podcast_episode(soup)

            if metadata:
                logger.info("✅ Métadonnées extraites via JSON-LD")
                # Ajouter le contenu textuel complet
                metadata["page_text"] = page_text
                return metadata

            # Stratégie 2 (fallback): LLM extraction pour vieilles pages (2019)
            logger.info(
                "📝 JSON-LD absent, tentative extraction LLM depuis texte complet..."
            )

            # Utiliser LLM pour extraire métadonnées
            llm_metadata = await self._extract_metadata_with_llm(page_text)

            if llm_metadata:
                logger.info("✅ Métadonnées extraites via LLM")
                # Ajouter le contenu textuel complet
                llm_metadata["page_text"] = page_text
                return llm_metadata

            logger.warning("⚠️ Aucune métadonnée extraite (JSON-LD et LLM ont échoué)")
            return {}

        except Exception as e:
            logger.error(f"Erreur extraction métadonnées RadioFrance: {e}")
            return {}

    def _parse_json_ld_podcast_episode(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Parse JSON-LD PodcastEpisode pour extraire métadonnées."""
        try:
            json_ld_scripts = soup.find_all("script", type="application/ld+json")

            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)

                    if isinstance(data, dict) and data.get("@type") == "PodcastEpisode":
                        # Extraire animateur (author[0].name)
                        animateur = ""
                        authors = data.get("author", [])
                        if authors and len(authors) > 0:
                            animateur = authors[0].get("name", "")

                        # Extraire date
                        date_published = data.get("datePublished", "")

                        # Extraire image
                        image_url = data.get("image", "")

                        # Extraire description
                        description = data.get("description", "")

                        # Parser titre pour critiques
                        episode_name = data.get("name", "")
                        critiques = self._parse_critics_from_title(episode_name)

                        # Si description disponible, essayer aussi
                        if description and not critiques:
                            critiques = self._parse_critics_from_title(description)

                        return {
                            "animateur": animateur,
                            "critiques": critiques,
                            "date": date_published,
                            "image_url": image_url,
                            "description": description,
                        }

                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

            return {}

        except Exception as e:
            logger.debug(f"Erreur parsing JSON-LD PodcastEpisode: {e}")
            return {}

    async def _extract_metadata_with_llm(self, page_text: str) -> dict[str, Any]:
        """
        Extrait métadonnées depuis texte de page RadioFrance avec LLM.

        Utilisé comme fallback pour les vieilles pages (2019) sans JSON-LD.

        Args:
            page_text: Texte complet extrait de la page HTML

        Returns:
            {
                "animateur": str,
                "critiques": list[str],
                "date": str (ISO format YYYY-MM-DD)
            }
            Retourne {} si extraction échoue
        """
        if not page_text or not page_text.strip():
            return {}

        if not self.client:
            logger.warning(
                "⚠️ Client OpenAI non configuré, impossible d'extraire métadonnées par LLM"
            )
            return {}

        try:
            # Limiter le texte pour éviter tokens excessifs (garder ~10000 premiers caractères)
            truncated_text = page_text[:10000]

            prompt = f"""Analyse cette page web de l'émission "Le Masque et la Plume" de France Inter et extrais les informations suivantes:

1. Le nom de l'animateur (généralement Jérôme Garcin)
2. Les noms complets des critiques présents dans l'émission
3. La date de l'émission au format YYYY-MM-DD

Texte de la page:
{truncated_text}

Réponds UNIQUEMENT avec un objet JSON valide au format suivant:
{{
  "animateur": "Prénom Nom",
  "critiques": ["Prénom Nom1", "Prénom Nom2", "Prénom Nom3"],
  "date": "YYYY-MM-DD"
}}

Si une information n'est pas trouvée, utilise une chaîne vide pour animateur/date ou une liste vide pour critiques.
IMPORTANT: Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

            logger.info("🤖 Envoi requête LLM pour extraction métadonnées...")

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.deployment_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "Tu es un assistant qui extrait des informations structurées depuis des pages web. Tu réponds UNIQUEMENT en JSON valide.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=500,
                    temperature=0.1,
                ),
                timeout=30,
            )

            llm_response = response.choices[0].message.content.strip()

            # Parser la réponse JSON
            # Le LLM peut parfois entourer le JSON avec ```json ... ```, on le nettoie
            import re

            llm_response = re.sub(r"```json\s*", "", llm_response)
            llm_response = re.sub(r"```\s*$", "", llm_response)

            metadata = json.loads(llm_response)

            # Validation du format
            if not isinstance(metadata, dict):
                logger.warning("⚠️ Réponse LLM n'est pas un dictionnaire")
                return {}

            # Normaliser le format de sortie
            result = {
                "animateur": metadata.get("animateur", ""),
                "critiques": metadata.get("critiques", []),
                "date": metadata.get("date", ""),
                "image_url": "",  # LLM ne peut pas extraire l'URL d'image
                "description": "",  # Pas nécessaire pour la correction Phase 2
            }

            # Vérifier qu'on a au moins l'animateur ou des critiques
            if not result["animateur"] and not result["critiques"]:
                logger.warning("⚠️ LLM n'a trouvé ni animateur ni critiques")
                return {}

            logger.info(
                f"✅ LLM extraction réussie: animateur={result['animateur']}, "
                f"{len(result['critiques'])} critiques"
            )

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Erreur parsing JSON depuis LLM: {e}")
            from contextlib import suppress

            with suppress(Exception):
                logger.debug(f"Réponse LLM invalide: {llm_response[:200]}")
            return {}
        except TimeoutError:
            logger.warning("⚠️ Timeout lors de l'extraction LLM")
            return {}
        except Exception as e:
            logger.error(
                f"❌ Erreur extraction métadonnées par LLM: {type(e).__name__}: {e}"
            )
            return {}

    def _parse_critics_from_title(self, title: str) -> list[str]:
        """
        Extrait noms critiques du titre épisode.

        Patterns RadioFrance:
        - "... avec Nom1, Nom2, Nom3"
        - "... par Nom1, Nom2"

        Returns:
            ["Nom1 Complet", "Nom2 Complet"]
        """
        import re

        if not title:
            return []

        critiques = []

        # Pattern 1: "avec Nom1, Nom2"
        match_avec = re.search(r"avec\s+([^\.]+)", title, re.IGNORECASE)
        if match_avec:
            names_part = match_avec.group(1)
            # Split par virgules ou "et"
            names = re.split(r",|\set\s", names_part)
            critiques = [name.strip() for name in names if name.strip()]

        # Pattern 2: "par Nom1, Nom2"
        if not critiques:
            match_par = re.search(r"par\s+([^\.]+)", title, re.IGNORECASE)
            if match_par:
                names_part = match_par.group(1)
                names = re.split(r",|\set\s", names_part)
                critiques = [name.strip() for name in names if name.strip()]

        # Nettoyer les noms (enlever caractères superflus)
        critiques = [
            re.sub(r"[^\w\s\-]", "", name).strip()
            for name in critiques
            if len(name.strip()) > 3  # Éviter les initiales seules
        ]

        return critiques


# Singleton instance
radiofrance_service = RadioFranceService()
