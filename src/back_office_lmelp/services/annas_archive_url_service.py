"""Service pour récupérer l'URL d'Anna's Archive depuis Wikipedia.

Ce service scrape la page Wikipedia d'Anna's Archive pour extraire l'URL
officielle actuelle. Les résultats sont mis en cache pour 24h.

Stratégie hybride (Issue #188):
1. Priority 1: Variable d'environnement (ANNAS_ARCHIVE_URL) + health check
2. Priority 2: Wikipedia scraping (avec cache 24h) + health check
3. Priority 3: Hardcoded default fallback

Stratégie de parsing Wikipedia:
1. Chercher dans l'infobox (balise <table class="infobox">)
2. Fallback: Premier lien externe dans le contenu principal
3. Ultimate fallback: Hardcoded default
"""

import logging
import os
from typing import TYPE_CHECKING

import aiohttp
from bs4 import BeautifulSoup, NavigableString, Tag

from .babelio_cache_service import BabelioCacheService


if TYPE_CHECKING:
    from ..settings import Settings


logger = logging.getLogger(__name__)


class AnnasArchiveUrlService:
    """Service pour récupérer l'URL d'Anna's Archive."""

    def __init__(self, settings: "Settings", cache_service: BabelioCacheService):
        """Initialize service.

        Args:
            settings: Settings object with annas_archive_url property
            cache_service: Cache service for storing scraped URLs (24h TTL)
        """
        self.settings = settings
        self.cache_service = cache_service
        self.wikipedia_url = "https://en.wikipedia.org/wiki/Anna%27s_Archive"
        self.hardcoded_default = "https://fr.annas-archive.org"
        self._debug_log_enabled = os.getenv("ANNAS_ARCHIVE_DEBUG_LOG", "0").lower() in (
            "1",
            "true",
        )

    async def get_url(self) -> str:
        """Get Anna's Archive URL with fallback strategy.

        Priority:
        1. Environment variable (ANNAS_ARCHIVE_URL) + health check
        2. Wikipedia scraping (cached 24h) + health check
        3. Hardcoded default

        Returns:
            Base URL for Anna's Archive (e.g., "https://fr.annas-archive.se")
        """
        # Priority 1: Environment variable avec health check
        if self.settings.annas_archive_url:
            if self._debug_log_enabled:
                logger.info(
                    f"🔧 Testing env var ANNAS_ARCHIVE_URL: {self.settings.annas_archive_url}"
                )

            # Health check: vérifier si l'URL est accessible
            is_healthy = await self._health_check_url(self.settings.annas_archive_url)
            if is_healthy:
                if self._debug_log_enabled:
                    logger.info(
                        f"✅ Env var URL accessible: {self.settings.annas_archive_url}"
                    )
                return self.settings.annas_archive_url
            else:
                logger.warning(
                    f"⚠️ Env var URL non accessible (timeout): {self.settings.annas_archive_url}, "
                    f"fallback sur Wikipedia"
                )

        # Priority 2: Wikipedia scraping (with cache) + health check
        cached = self.cache_service.get_cached("wikipedia_url", "annas_archive")
        if cached:
            cached_url: str | None = cached.get("data")
            if cached_url and self._debug_log_enabled:
                logger.info(f"💾 Testing cached Wikipedia URL: {cached_url}")

            # Health check: vérifier si l'URL cachée est encore accessible
            if cached_url:
                is_healthy = await self._health_check_url(cached_url)
                if is_healthy:
                    if self._debug_log_enabled:
                        logger.info(f"✅ Cached URL accessible: {cached_url}")
                    return cached_url
                else:
                    logger.warning(
                        f"⚠️ Cached URL non accessible (timeout): {cached_url}, re-scraping Wikipedia"
                    )

        # Scrape Wikipedia (cache expiré ou URL morte)
        scraped_url = await self._scrape_wikipedia_url()
        if scraped_url:
            # Cache for 24h
            self.cache_service.set_cached("wikipedia_url", scraped_url, "annas_archive")
            if self._debug_log_enabled:
                logger.info(f"🌐 Scraped Wikipedia URL: {scraped_url}")
            return scraped_url

        # Priority 3: Hardcoded default
        logger.warning(
            f"⚠️ Wikipedia scraping failed, using hardcoded default: {self.hardcoded_default}"
        )
        return self.hardcoded_default

    async def _health_check_url(self, url: str) -> bool:
        """Vérifie si une URL Anna's Archive répond (timeout 2s).

        Args:
            url: URL à tester

        Returns:
            True si l'URL est accessible (200/301/302), False sinon
        """
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.head(
                    url,
                    timeout=aiohttp.ClientTimeout(total=2.0),  # Timeout court
                    allow_redirects=True,
                ) as response,
            ):
                return response.status in (200, 301, 302)
        except (aiohttp.ClientError, TimeoutError):
            return False

    async def _scrape_wikipedia_url(self) -> str | None:
        """Scrape Wikipedia page for official Anna's Archive URL.

        Returns:
            Base URL if found, None otherwise
        """
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    self.wikipedia_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; BackOfficeLMELP/1.0)"
                    },
                ) as response,
            ):
                if response.status != 200:
                    logger.warning(f"Wikipedia returned status {response.status}")
                    return None

                html = await response.text()

            soup = BeautifulSoup(html, "html.parser")

            # Strategy 1: Parse infobox
            url = self._parse_infobox(soup)
            if url:
                return url

            # Strategy 2: Find first external link in content
            url = self._parse_external_links(soup)
            if url:
                return url

            return None

        except Exception as e:
            logger.error(f"Error scraping Wikipedia: {e}")
            return None

    def _parse_infobox(self, soup: BeautifulSoup) -> str | None:
        """Parse Wikipedia infobox for official URL.

        Wikipedia infoboxes typically have:
        <table class="infobox">
          <tr><th>Website</th><td><a href="...">annas-archive.se</a></td></tr>
        </table>

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Normalized URL or None
        """
        infobox = soup.find("table", class_="infobox")
        if not infobox or isinstance(infobox, NavigableString):
            return None

        # Find row with "Website" or "URL"
        for row in infobox.find_all("tr"):
            header = row.find("th")
            if not header or isinstance(header, NavigableString):
                continue

            header_text = header.get_text(strip=True).lower()
            if "website" in header_text or "url" in header_text:
                link = row.find("a", href=True)
                if link and isinstance(link, Tag):
                    href_value = link.get("href")
                    if (
                        isinstance(href_value, str)
                        and href_value.startswith("http")
                        and "annas-archive" in href_value
                    ):
                        return self._normalize_url(href_value)

        return None

    def _parse_external_links(self, soup: BeautifulSoup) -> str | None:
        """Parse external links section for official URL.

        Look for links in the main content that point to annas-archive domains.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Normalized URL or None
        """
        # Find all links in main content
        content = soup.find("div", id="mw-content-text")
        if not content or isinstance(content, NavigableString):
            return None

        for link in content.find_all("a", href=True):
            if isinstance(link, Tag):
                href = str(link["href"])
                if href.startswith("http") and "annas-archive" in href:
                    return self._normalize_url(href)

        return None

    def _normalize_url(self, url: str) -> str:
        """Normalize URL to base domain (strip path, query, fragment).

        Automatically adds 'fr.' subdomain for French interface if not present.

        Examples:
        - https://annas-archive.se/search?q=test → https://fr.annas-archive.se
        - https://fr.annas-archive.org/about → https://fr.annas-archive.org
        - https://annas-archive.li → https://fr.annas-archive.li

        Args:
            url: URL to normalize

        Returns:
            Base URL (scheme + netloc) with 'fr.' subdomain
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        netloc = parsed.netloc

        # Add 'fr.' prefix if not already present for French interface
        if not netloc.startswith("fr."):
            netloc = f"fr.{netloc}"

        return f"{parsed.scheme}://{netloc}"
