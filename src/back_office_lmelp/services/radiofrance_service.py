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
from datetime import datetime
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
        self.http_headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

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
        self,
        episode_title: str,
        episode_date: str | datetime | None = None,
        min_duration_seconds: int | None = None,
    ) -> str | None:
        """Recherche l'URL de la page d'un épisode par son titre et optionnellement sa date.

        Args:
            episode_title: Titre de l'épisode à rechercher
            episode_date: Date de l'épisode au format YYYY-MM-DD (optionnel).
                         Si fournie, seules les URLs dont la date correspondent seront retournées.
                         Accepte aussi un datetime object (comme retourné par MongoDB).
            min_duration_seconds: Durée minimale en secondes (optionnel).
                         Si fournie, les URLs avec une durée inférieure sont ignorées.
                         Permet de filtrer les clips courts (livres) vs émissions complètes.
                         Si la durée n'est pas disponible dans le JSON-LD, l'URL n'est pas exclue.

        Returns:
            URL complète de la page de l'épisode, ou None si non trouvé
        """
        try:
            # Convertir datetime en string si nécessaire (MongoDB retourne des datetime)
            if episode_date is not None and not isinstance(episode_date, str):
                # Assume it's a datetime object
                episode_date = episode_date.strftime("%Y-%m-%d")
            # Construire l'URL de recherche
            search_query = quote_plus(episode_title)
            search_url = f"{self.base_url}{self.podcast_search_base}?q={search_query}"

            logger.info(f"Searching RadioFrance for episode: {episode_title[:50]}...")

            # Faire la requête HTTP
            async with (
                aiohttp.ClientSession(headers=self.http_headers) as session,
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

                # PAGINATION: Essayer plusieurs pages de résultats
                # Garde-fou 1: Limiter à 10 pages max pour éviter boucle infinie
                max_pages = 10
                page = 1

                while page <= max_pages:
                    # Construire l'URL avec pagination (?p=2, ?p=3, etc.)
                    if page == 1:
                        paginated_url = search_url  # Première page (pas de &p=1)
                        paginated_soup = soup  # Réutiliser soup déjà chargé
                    else:
                        paginated_url = f"{search_url}&p={page}"
                        logger.warning(f"🔍 Trying page {page}: {paginated_url}")

                        # Charger la page suivante
                        async with (
                            aiohttp.ClientSession(headers=self.http_headers) as session,
                            session.get(
                                paginated_url, timeout=aiohttp.ClientTimeout(total=10)
                            ) as response,
                        ):
                            if response.status != 200:
                                logger.warning(
                                    f"Page {page} returned status {response.status}, stopping pagination"
                                )
                                break

                            paginated_html = await response.text()
                            paginated_soup = BeautifulSoup(
                                paginated_html, "html.parser"
                            )

                    # Extraire les URLs candidates de cette page
                    candidate_urls = self._extract_all_candidate_urls(paginated_soup)
                    logger.warning(
                        f"🔍 Page {page}: Found {len(candidate_urls)} candidate URLs"
                    )

                    # Garde-fou 2: Si aucun résultat, on a atteint la fin
                    if not candidate_urls:
                        logger.warning(
                            f"🔍 Page {page} has no results, stopping pagination"
                        )
                        break

                    # Parcourir chaque URL et vérifier sa date (et durée si applicable)
                    target_date = datetime.strptime(episode_date, "%Y-%m-%d")
                    for url in candidate_urls:
                        logger.warning(f"🔍 Checking URL: {url}")
                        (
                            episode_date_from_page,
                            duration_from_page,
                        ) = await self._extract_episode_date_and_duration(url)
                        logger.warning(
                            f"🔍   → Date: {episode_date_from_page}, Duration: {duration_from_page}s"
                        )
                        if not episode_date_from_page:
                            continue

                        # Vérifier que la date est dans une fenêtre de ±7 jours
                        # (RadioFrance publie parfois l'émission 2 jours après la diffusion)
                        try:
                            page_date = datetime.strptime(
                                episode_date_from_page, "%Y-%m-%d"
                            )
                            date_diff = abs((page_date - target_date).days)
                        except ValueError:
                            continue

                        if date_diff > 7:
                            logger.warning(
                                f"⏱ Skipping {url}: date diff {date_diff} days > 7"
                            )
                            continue

                        # Filtrer par durée minimale si spécifiée
                        if (
                            min_duration_seconds
                            and duration_from_page is not None
                            and duration_from_page < min_duration_seconds
                        ):
                            logger.warning(
                                f"⏱ Skipping {url}: duration {duration_from_page}s < min {min_duration_seconds}s"
                            )
                            continue

                        logger.warning(
                            f"✅ Found matching episode URL by date on page {page}: {url} (date: {episode_date_from_page}, duration: {duration_from_page}s)"
                        )
                        return url

                    # Passer à la page suivante
                    page += 1

                logger.warning(
                    f"❌ Search (?q=) found nothing for date {episode_date}, trying chronological fallback..."
                )

                # FALLBACK: Pagination chronologique (?p=N sans filtre de titre)
                # Utilisé quand le moteur de recherche ne retourne pas l'épisode
                # (ex: épisodes anciens avec titre générique non indexés par ?q=)
                result = await self._search_chronological_pages(
                    episode_title, episode_date, min_duration_seconds
                )
                if result:
                    return result

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

    async def _get_page_links_and_median_date(
        self, page: int
    ) -> tuple[list[str], datetime | None]:
        """Retourne la liste des liens et la date médiane d'une page chronologique.

        Retourne ([], None) si la page n'existe pas ou est un fallback RadioFrance.
        RadioFrance retourne une page de fallback (mêmes liens récents) pour les pages
        invalides — on détecte ça en comparant le nombre de liens attendus.
        """
        url = f"{self.base_url}{self.podcast_search_base}?p={page}"
        try:
            async with (
                aiohttp.ClientSession(headers=self.http_headers) as session,
                session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response,
            ):
                if response.status != 200:
                    return [], None
                html = await response.text()
        except Exception:
            return [], None

        soup = BeautifulSoup(html, "html.parser")
        candidate_urls = self._extract_all_candidate_urls(soup)

        if not candidate_urls:
            return [], None

        mid_url = candidate_urls[len(candidate_urls) // 2]
        episode_date_str, _ = await self._extract_episode_date_and_duration(mid_url)
        if not episode_date_str:
            return candidate_urls, None

        try:
            return candidate_urls, datetime.strptime(episode_date_str, "%Y-%m-%d")
        except ValueError:
            return candidate_urls, None

    async def _get_page_median_date(self, page: int) -> datetime | None:
        """Retourne la date médiane des épisodes d'une page chronologique.

        Utilisé par la recherche dichotomique pour orienter la recherche.
        Retourne None si la page est vide ou invalide.
        """
        _, date = await self._get_page_links_and_median_date(page)
        return date

    async def _search_chronological_pages(
        self,
        episode_title: str,
        episode_date: str,
        min_duration_seconds: int | None = None,
    ) -> str | None:
        """Fallback: cherche dans la pagination chronologique (?p=N) via dichotomie.

        Utilisé quand la recherche textuelle (?q=) ne retourne pas l'épisode.
        Utilise une recherche binaire pour converger rapidement vers la bonne page
        (max ~8 étapes pour 200 pages), puis vérifie une fenêtre autour du résultat.

        Pages récentes = petits numéros (page 1), pages anciennes = grands numéros.
        La date médiane d'une page sert de comparateur pour orienter la dichotomie.
        """
        target_date = datetime.strptime(episode_date, "%Y-%m-%d")

        logger.warning(
            f"🔍 Chronological fallback (dichotomy): searching for '{episode_title[:40]}' on {episode_date}"
        )

        # Phase 0: Récupérer la signature de la page 1 (premiers liens = épisodes récents).
        # Les pages invalides retournent le même contenu que la page 1 (fallback RadioFrance).
        page1_links, _ = await self._get_page_links_and_median_date(1)
        page1_signature = set(page1_links[:3]) if page1_links else set()

        # Phase 1: Dichotomie sur [1, 500]
        lo, hi = 1, 500
        best_page = 1

        for _ in range(10):  # max 10 itérations = log2(500) ≈ 9
            if lo > hi:
                break
            mid = (lo + hi) // 2
            mid_links, mid_date = await self._get_page_links_and_median_date(mid)

            # Détecter fallback : page invalide → même contenu que page 1
            if page1_signature and set(mid_links[:3]) == page1_signature and mid > 1:
                logger.warning(
                    f"🔍 Dichotomy: page {mid} is fallback (same as p=1), hi={mid - 1}"
                )
                hi = mid - 1
                continue

            logger.warning(
                f"🔍 Dichotomy: [{lo},{hi}] → page {mid}, "
                f"date={mid_date.strftime('%Y-%m-%d') if mid_date else 'None'}"
            )

            if mid_date is None:
                hi = mid - 1
                continue

            best_page = mid
            date_diff_days = (mid_date - target_date).days

            if abs(date_diff_days) <= 30:
                # Assez proche pour la phase 2
                break
            if date_diff_days > 0:
                # mid_date plus récente que cible → cible est plus ancienne → pages élevées
                lo = mid + 1
            else:
                # mid_date plus ancienne que cible → cible est plus récente → pages basses
                hi = mid - 1

        logger.warning(f"🔍 Dichotomy converged to page {best_page}")

        # Phase 2: Vérifier les pages dans une fenêtre autour de best_page
        # Chercher le meilleur candidat (diff de date minimale) dans la fenêtre
        window = 5
        best_url: str | None = None
        best_diff = 999

        for page in range(max(1, best_page - window), best_page + window + 1):
            chrono_url = f"{self.base_url}{self.podcast_search_base}?p={page}"

            try:
                async with (
                    aiohttp.ClientSession(headers=self.http_headers) as session,
                    session.get(
                        chrono_url, timeout=aiohttp.ClientTimeout(total=10)
                    ) as response,
                ):
                    if response.status != 200:
                        continue
                    html_content = await response.text()
            except Exception:
                continue

            chrono_soup = BeautifulSoup(html_content, "html.parser")
            candidate_urls = self._extract_all_candidate_urls(chrono_soup)

            logger.warning(f"🔍 Chrono page {page}: {len(candidate_urls)} candidates")

            if not candidate_urls:
                continue

            for url in candidate_urls:
                (
                    episode_date_from_page,
                    duration_from_page,
                ) = await self._extract_episode_date_and_duration(url)

                if not episode_date_from_page:
                    continue

                try:
                    page_date = datetime.strptime(episode_date_from_page, "%Y-%m-%d")
                    diff = abs((page_date - target_date).days)
                except ValueError:
                    continue

                # Tolérance de 3 jours (délai de publication RadioFrance)
                if diff > 3:
                    continue

                if (
                    min_duration_seconds
                    and duration_from_page is not None
                    and duration_from_page < min_duration_seconds
                ):
                    continue

                if diff < best_diff:
                    best_diff = diff
                    best_url = url
                    logger.warning(f"🔍 Candidate page {page}: diff={diff}j → {url}")

                if diff == 0:
                    # Correspondance exacte, on arrête immédiatement
                    logger.warning(
                        f"✅ Found exact match via chronological fallback page {page}: {url}"
                    )
                    return url

        if best_url:
            logger.warning(
                f"✅ Found best match (diff={best_diff}j) via chronological fallback: {best_url}"
            )
        return best_url

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
                aiohttp.ClientSession(headers=self.http_headers) as session,
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

    def _parse_iso_duration(self, duration_str: str) -> int | None:
        """Parse une durée ISO 8601 en secondes.

        Formats supportés:
        - PT47M25S (format court)
        - PT1H30M (avec heures)
        - P0Y0M0DT0H47M40S (format complet RadioFrance réel, mainEntity.duration)

        Args:
            duration_str: Durée au format ISO 8601

        Returns:
            Durée en secondes, ou None si le format est invalide
        """
        import re

        if not duration_str:
            return None

        # Format court: PT47M25S, PT9M, PT1H30M
        match = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", duration_str)
        if not match:
            # Format complet ISO 8601: P0Y0M0DT0H47M40S (format réel RadioFrance)
            match = re.match(
                r"^P\d+Y\d+M\d+DT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", duration_str
            )
        if not match:
            return None

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        total = hours * 3600 + minutes * 60 + seconds
        # Return None if all components are 0 (invalid "PT" with no values)
        return total if total > 0 else None

    async def _extract_episode_date_and_duration(
        self, episode_url: str
    ) -> tuple[str | None, int | None]:
        """Extrait la date et la durée de publication d'un épisode depuis son URL.

        Fait une requête GET sur l'URL de l'épisode et extrait la date (datePublished)
        et la durée (timeRequired) depuis le JSON-LD.

        Args:
            episode_url: URL complète de la page de l'épisode

        Returns:
            Tuple (date au format YYYY-MM-DD, durée en secondes).
            Les deux peuvent être None si non trouvés.
        """
        try:
            async with (
                aiohttp.ClientSession(headers=self.http_headers) as session,
                session.get(
                    episode_url, timeout=aiohttp.ClientTimeout(total=10)
                ) as response,
            ):
                if response.status != 200:
                    logger.debug(
                        f"Failed to fetch episode page {episode_url}: status {response.status}"
                    )
                    return None, None

                html_content = await response.text()
                soup = BeautifulSoup(html_content, "html.parser")

                # Chercher le JSON-LD avec date et durée
                json_ld_scripts = soup.find_all("script", type="application/ld+json")
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)

                        items = []
                        if isinstance(data, dict) and "@graph" in data:
                            items = data["@graph"]
                        elif isinstance(data, dict):
                            items = [data]

                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            # Priorité à RadioEpisode avec dateCreated + mainEntity.duration
                            if item.get("@type") == "RadioEpisode":
                                date_raw = item.get("dateCreated") or item.get(
                                    "datePublished"
                                )
                                if date_raw:
                                    date = str(date_raw).split("T")[0]
                                    # Durée dans mainEntity.duration (format réel RadioFrance)
                                    main_entity = item.get("mainEntity", {})
                                    duration_str = main_entity.get("duration", "")
                                    # Fallback sur timeRequired (ancien format)
                                    if not duration_str:
                                        duration_str = item.get("timeRequired", "")
                                    duration = self._parse_iso_duration(duration_str)
                                    return date, duration

                    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
                        continue

                # Fallback: chercher n'importe quelle date dans les scripts JSON-LD
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        items = []
                        if isinstance(data, dict) and "@graph" in data:
                            items = data["@graph"]
                        elif isinstance(data, dict):
                            items = [data]
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            date_raw = item.get("datePublished") or item.get(
                                "dateCreated"
                            )
                            if date_raw:
                                return str(date_raw).split("T")[0], None
                    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
                        continue

                return None, None

        except Exception as e:
            logger.debug(f"Error extracting date/duration from {episode_url}: {e}")
            return None, None

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
                aiohttp.ClientSession(headers=self.http_headers) as session,
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
