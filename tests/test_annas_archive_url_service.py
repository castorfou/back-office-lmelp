"""Tests pour le service de récupération d'URL d'Anna's Archive.

Ce module teste AnnasArchiveUrlService qui scrape Wikipedia pour trouver
l'URL officielle actuelle d'Anna's Archive.

Architecture testée:
- Priority 1: Environment variable (ANNAS_ARCHIVE_URL) avec health check
- Priority 2: Wikipedia scraping with caching (24h TTL) avec health check
- Priority 3: Hardcoded default fallback

Tests basés sur des captures HTML RÉELLES de Wikipedia (Issue #85 lesson).
"""

import pathlib
from unittest.mock import AsyncMock, Mock, patch

import pytest

from back_office_lmelp.services.annas_archive_url_service import (
    AnnasArchiveUrlService,
)
from back_office_lmelp.services.babelio_cache_service import BabelioCacheService
from back_office_lmelp.settings import Settings


FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures" / "annas_archive"


class TestUrlNormalization:
    """Tests for URL normalization with French subdomain."""

    @pytest.fixture
    def mock_settings(self):
        """Mock Settings object."""
        settings = Mock(spec=Settings)
        settings.annas_archive_url = None
        return settings

    @pytest.fixture
    def cache_service(self, tmp_path):
        """Create a temporary cache service."""
        return BabelioCacheService(cache_dir=tmp_path / "cache", ttl_hours=24.0)

    @pytest.fixture
    def service(self, mock_settings, cache_service):
        """Create AnnasArchiveUrlService instance."""
        return AnnasArchiveUrlService(mock_settings, cache_service)

    def test_normalize_url_should_add_fr_subdomain_when_missing(self, service):
        """Should add 'fr.' subdomain to domains without language prefix."""
        # GIVEN: URL without language subdomain
        url = "https://annas-archive.li/search?q=test"

        # WHEN: Normalizing URL
        result = service._normalize_url(url)

        # THEN: Should add 'fr.' prefix
        assert result == "https://fr.annas-archive.li"

    def test_normalize_url_should_preserve_existing_fr_subdomain(self, service):
        """Should not duplicate 'fr.' if already present."""
        # GIVEN: URL with 'fr.' subdomain
        url = "https://fr.annas-archive.se/about"

        # WHEN: Normalizing URL
        result = service._normalize_url(url)

        # THEN: Should preserve existing prefix
        assert result == "https://fr.annas-archive.se"

    def test_normalize_url_should_strip_path_and_query(self, service):
        """Should remove path and query parameters."""
        # GIVEN: URL with path and query
        url = "https://annas-archive.org/search?q=book&page=2"

        # WHEN: Normalizing URL
        result = service._normalize_url(url)

        # THEN: Should keep only scheme + netloc with fr prefix
        assert result == "https://fr.annas-archive.org"


class TestAnnasArchiveUrlService:
    """Tests du service de récupération d'URL d'Anna's Archive."""

    @pytest.fixture
    def mock_settings(self):
        """Mock Settings object."""
        settings = Mock(spec=Settings)
        settings.annas_archive_url = None  # Default: not set
        return settings

    @pytest.fixture
    def cache_service(self, tmp_path):
        """Create a temporary cache service."""
        return BabelioCacheService(cache_dir=tmp_path / "cache", ttl_hours=24.0)

    @pytest.fixture
    def service(self, mock_settings, cache_service):
        """Create AnnasArchiveUrlService instance."""
        return AnnasArchiveUrlService(mock_settings, cache_service)

    # ========== Priority 1: Environment Variable with Health Check ==========

    @pytest.mark.asyncio
    async def test_get_url_should_use_env_var_when_set_and_healthy(
        self, service, mock_settings
    ):
        """Test que l'env var est utilisée quand définie ET accessible."""
        # GIVEN: Env var configurée
        mock_settings.annas_archive_url = "https://fr.annas-archive.se"

        # Mock health check → URL accessible
        with patch.object(service, "_health_check_url", return_value=True):
            # WHEN: On récupère l'URL
            url = await service.get_url()

            # THEN: L'env var est retournée (pas de scraping)
            assert url == "https://fr.annas-archive.se"

    @pytest.mark.asyncio
    async def test_get_url_should_fallback_to_wikipedia_when_env_var_timeout(
        self, service, mock_settings
    ):
        """Test que Wikipedia est scrapée si env var URL ne répond pas (timeout)."""
        # GIVEN: Env var configurée MAIS URL inaccessible
        mock_settings.annas_archive_url = "https://dead-domain.org"

        # Mock health check → URL morte
        # Mock Wikipedia scraping → URL valide trouvée
        with (
            patch.object(service, "_health_check_url", return_value=False),
            patch.object(
                service,
                "_scrape_wikipedia_url",
                return_value="https://annas-archive.se",
            ),
        ):
            # WHEN: On récupère l'URL
            url = await service.get_url()

            # THEN: Wikipedia est scrapée et retourne une nouvelle URL
            assert url == "https://annas-archive.se"
            assert url != mock_settings.annas_archive_url  # Fallback utilisé

    # ========== Priority 2: Wikipedia Scraping with Cache and Health Check ==========

    @pytest.mark.asyncio
    async def test_get_url_should_use_cached_url_when_available_and_healthy(
        self, service, cache_service
    ):
        """Test que l'URL cachée est utilisée si accessible (health check OK)."""
        # GIVEN: URL en cache (simulé par un précédent scraping)
        cache_service.set_cached(
            "wikipedia_url", "https://annas-archive.se", "annas_archive"
        )

        # Mock health check → URL accessible
        with patch.object(service, "_health_check_url", return_value=True):
            # WHEN: On récupère l'URL
            url = await service.get_url()

            # THEN: L'URL cachée est retournée (pas de re-scraping)
            assert url == "https://annas-archive.se"

    @pytest.mark.asyncio
    async def test_get_url_should_rescrape_when_cached_url_timeout(
        self, service, cache_service
    ):
        """Test que Wikipedia est re-scrapée si URL cachée ne répond plus."""
        # GIVEN: URL en cache MAIS morte
        cache_service.set_cached(
            "wikipedia_url", "https://dead-domain.org", "annas_archive"
        )

        # Mock health check → URL morte
        # Mock Wikipedia scraping → URL valide trouvée
        with (
            patch.object(service, "_health_check_url", return_value=False),
            patch.object(
                service,
                "_scrape_wikipedia_url",
                return_value="https://annas-archive.li",
            ),
        ):
            # WHEN: On récupère l'URL
            url = await service.get_url()

            # THEN: Wikipedia est re-scrapée
            assert url == "https://annas-archive.li"

    @pytest.mark.asyncio
    async def test_get_url_should_scrape_wikipedia_when_cache_expired(self, service):
        """Test que Wikipedia est scrapée si cache expiré."""
        # GIVEN: Pas de cache, pas d'env var

        # Mock Wikipedia scraping → succès
        with patch.object(
            service, "_scrape_wikipedia_url", return_value="https://annas-archive.se"
        ):
            # WHEN: On scrape Wikipedia
            url = await service.get_url()

            # THEN: Une URL annas-archive est retournée
            assert url == "https://annas-archive.se"

    # ========== Priority 3: Hardcoded Fallback ==========

    @pytest.mark.asyncio
    async def test_get_url_should_return_hardcoded_default_when_wikipedia_fails(
        self, service
    ):
        """Test que le fallback hardcodé est utilisé si Wikipedia échoue."""
        # GIVEN: Wikipedia retourne None (échec)

        # Mock Wikipedia scraping → échec
        with patch.object(service, "_scrape_wikipedia_url", return_value=None):
            # WHEN: On tente de récupérer l'URL
            url = await service.get_url()

            # THEN: Le hardcoded default est retourné
            assert url == "https://fr.annas-archive.org"

    # ========== Health Check Tests ==========

    @pytest.mark.asyncio
    async def test_health_check_should_return_true_when_url_accessible(self, service):
        """Test que health check retourne True si URL accessible (200)."""
        # Mock aiohttp session → 200 OK
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.head = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # WHEN: On teste une URL
        with patch("aiohttp.ClientSession", return_value=mock_session):
            is_healthy = await service._health_check_url("https://annas-archive.se")

        # THEN: Health check retourne True
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_should_return_false_when_url_timeout(self, service):
        """Test que health check retourne False si timeout."""
        # Mock aiohttp session → timeout
        mock_session = Mock()
        mock_session.head = Mock(side_effect=TimeoutError())
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # WHEN: On teste une URL
        with patch("aiohttp.ClientSession", return_value=mock_session):
            is_healthy = await service._health_check_url("https://dead-domain.org")

        # THEN: Health check retourne False
        assert is_healthy is False

    # ========== Parsing Strategy Tests ==========

    def test_parse_infobox_should_extract_url_from_wikipedia_infobox(self, service):
        """Test d'extraction d'URL depuis l'infobox Wikipedia."""
        # GIVEN: HTML d'infobox Wikipedia (structure réelle)
        from bs4 import BeautifulSoup

        html = """
        <table class="infobox">
          <tr><th>Type</th><td>Digital library</td></tr>
          <tr><th>Website</th><td><a href="https://annas-archive.se">annas-archive.se</a></td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")

        # WHEN: On parse l'infobox
        url = service._parse_infobox(soup)

        # THEN: L'URL est correctement extraite et normalisée avec préfixe fr
        assert url == "https://fr.annas-archive.se"

    def test_normalize_url_should_strip_path_and_query(self, service):
        """Test de normalisation d'URL (base domain seulement avec préfixe fr)."""
        # GIVEN: URLs avec path, query, fragment
        test_cases = [
            ("https://annas-archive.se/search?q=test", "https://fr.annas-archive.se"),
            (
                "https://fr.annas-archive.org/about#section",
                "https://fr.annas-archive.org",
            ),
            ("https://annas-archive.li/", "https://fr.annas-archive.li"),
        ]

        for input_url, expected in test_cases:
            # WHEN: On normalise l'URL
            result = service._normalize_url(input_url)

            # THEN: Seul le base domain est retourné
            assert result == expected


# Imports requis pour le test asyncio
