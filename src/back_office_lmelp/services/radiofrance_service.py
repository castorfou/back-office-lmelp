"""Service de recherche d'URL de page RadioFrance.

Ce service scrape la page de recherche RadioFrance pour trouver l'URL
de la page d'un épisode de podcast à partir de son titre.

Le service utilise deux stratégies de parsing :
1. JSON-LD (Schema.org ItemList) - plus robuste et structuré
2. Fallback sur parsing HTML des liens <a href> si JSON-LD absent
"""

import json
import logging
from urllib.parse import quote_plus

import aiohttp
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


class RadioFranceService:
    """Service pour rechercher l'URL de page d'un épisode sur RadioFrance."""

    def __init__(self):
        """Initialise le service RadioFrance."""
        self.base_url = "https://www.radiofrance.fr"
        self.podcast_search_base = "/franceinter/podcasts/le-masque-et-la-plume"

    async def search_episode_page_url(self, episode_title: str) -> str | None:
        """Recherche l'URL de la page d'un épisode par son titre.

        Args:
            episode_title: Titre de l'épisode à rechercher

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

        # Les épisodes valides contiennent généralement :
        # - "du-dimanche" ou "du-lundi" etc. (jour de diffusion)
        # - Une date dans l'URL
        # - Un ID numérique à la fin
        # Exemple: /le-masque-et-la-plume-du-dimanche-10-decembre-2023-5870209
        return "-du-" in url or any(
            month in url
            for month in [
                "janvier",
                "fevrier",
                "mars",
                "avril",
                "mai",
                "juin",
                "juillet",
                "aout",
                "septembre",
                "octobre",
                "novembre",
                "decembre",
            ]
        )

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
