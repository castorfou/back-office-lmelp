"""Tests pour l'enrichissement de l'éditeur depuis Babelio (Issue #85).

Ce module teste la nouvelle fonctionnalité de scraping de l'éditeur depuis les pages
Babelio pour enrichir automatiquement les réponses de l'API verify_book.

Fonctionnalités testées :
1. fetch_publisher_from_url() - Scraping éditeur depuis URL Babelio
2. verify_book() enrichi avec babelio_publisher (confiance >= 0.90)
3. Priorité éditeur dans handle_book_validation()
4. Frontend: transmission de babelio_publisher au modal

Architecture :
- Sélecteur CSS: a.tiny_links.dark[href*="/editeur/"]
- Seuil confiance: >= 0.90 pour activer le scraping
- Rate limiting: Respecte les 0.8s existants (pas de requête supplémentaire en parallèle)
"""

from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from back_office_lmelp.services.babelio_service import BabelioService


class TestPublisherScraping:
    """Tests du scraping de l'éditeur depuis les pages Babelio."""

    @pytest.fixture
    def babelio_service(self):
        """Fixture pour créer une instance BabelioService."""
        return BabelioService()

    @pytest.mark.asyncio
    async def test_fetch_publisher_from_url_should_return_publisher(
        self, babelio_service
    ):
        """GIVEN: URL Babelio valide avec éditeur Herscher
        WHEN: fetch_publisher_from_url() est appelé
        THEN: Retourne "Herscher"
        """
        url = "https://www.babelio.com/livres/Assouline-Des-visages-et-des-mains-150-portraits-decrivain/1635414"

        # Mock HTTP response avec HTML contenant l'éditeur
        mock_html = """
        <html>
            <div class="livre_refs grey_light">
                EAN : 9782733504642 <br />
                <a href="/editeur/2306/Herscher" class="tiny_links dark">Herscher</a>
                (27/03/2024)
            </div>
        </html>
        """

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_html)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(babelio_service, "_get_session", return_value=mock_session):
            publisher = await babelio_service.fetch_publisher_from_url(url)

            assert publisher == "Herscher"

    @pytest.mark.asyncio
    async def test_fetch_publisher_from_url_should_return_none_when_not_found(
        self, babelio_service
    ):
        """GIVEN: URL Babelio sans éditeur dans le HTML
        WHEN: fetch_publisher_from_url() est appelé
        THEN: Retourne None
        """
        url = "https://www.babelio.com/livres/Unknown/999999"

        # Mock HTTP response sans éditeur
        mock_html = "<html><body>Pas d'éditeur ici</body></html>"

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_html)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(babelio_service, "_get_session", return_value=mock_session):
            publisher = await babelio_service.fetch_publisher_from_url(url)

            assert publisher is None

    @pytest.mark.asyncio
    async def test_fetch_publisher_from_url_should_handle_http_error(
        self, babelio_service
    ):
        """GIVEN: URL Babelio qui retourne une erreur HTTP
        WHEN: fetch_publisher_from_url() est appelé
        THEN: Retourne None (gestion d'erreur gracieuse)
        """
        url = "https://www.babelio.com/livres/NotFound/404"

        mock_response = Mock()
        mock_response.status = 404

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(babelio_service, "_get_session", return_value=mock_session):
            publisher = await babelio_service.fetch_publisher_from_url(url)

            assert publisher is None

    @pytest.mark.asyncio
    async def test_fetch_publisher_from_url_should_handle_timeout(
        self, babelio_service
    ):
        """GIVEN: URL Babelio qui timeout
        WHEN: fetch_publisher_from_url() est appelé
        THEN: Retourne None et log l'erreur
        """
        url = "https://www.babelio.com/livres/Timeout/999"

        mock_session = Mock()
        mock_session.get = Mock(side_effect=aiohttp.ClientError("Timeout"))

        with patch.object(babelio_service, "_get_session", return_value=mock_session):
            publisher = await babelio_service.fetch_publisher_from_url(url)

            assert publisher is None


class TestVerifyBookEnrichment:
    """Tests de l'enrichissement verify_book() avec babelio_publisher."""

    @pytest.fixture
    def babelio_service(self):
        """Fixture pour créer une instance BabelioService."""
        return BabelioService()

    @pytest.mark.asyncio
    async def test_verify_book_should_include_publisher_when_confidence_high(
        self, babelio_service
    ):
        """GIVEN: verify_book() retourne confiance >= 0.90 avec babelio_url
        WHEN: verify_book() est appelé
        THEN: babelio_publisher est enrichi automatiquement
        """
        # Mock search() pour retourner un livre avec confiance élevée
        mock_book_data = {
            "id_oeuvre": "1635414",
            "titre": "Des visages et des mains: 150 portraits d'écrivain...",
            "prenoms": "Hannah",
            "nom": "Assouline",
            "ca_copies": "6",
            "type": "livres",
            "url": "/livres/Assouline-Des-visages-et-des-mains-150-portraits-decrivain/1635414",
        }

        with (
            patch.object(babelio_service, "search", return_value=[mock_book_data]),
            patch.object(
                babelio_service,
                "fetch_publisher_from_url",
                return_value="Herscher",
            ),
        ):
            result = await babelio_service.verify_book(
                "Des visages et des mains: 150 portraits d'écrivain...",
                "Hannah Assouline",
            )

            # Status peut être verified ou corrected selon score exact
            assert result["status"] in ["verified", "corrected"]
            assert result["confidence_score"] >= 0.90
            assert "babelio_publisher" in result
            assert result["babelio_publisher"] == "Herscher"
            assert (
                "https://www.babelio.com/livres/Assouline-Des-visages-et-des-mains-150-portraits-decrivain/1635414"
                in result["babelio_url"]
            )

    @pytest.mark.asyncio
    async def test_verify_book_should_NOT_scrape_publisher_when_confidence_low(
        self, babelio_service
    ):
        """GIVEN: verify_book() retourne confiance < 0.90
        WHEN: verify_book() est appelé
        THEN: babelio_publisher n'est pas enrichi (gain de performance)
        """
        # Mock search() pour retourner un livre avec confiance faible
        mock_book_data = {
            "id_oeuvre": "999",
            "titre": "Titre vague",
            "prenoms": "Auteur",
            "nom": "Inconnu",
            "ca_copies": "1",
            "type": "livres",
            "url": "/livres/Inconnu-Titre-vague/999",
        }

        with (
            patch.object(babelio_service, "search", return_value=[mock_book_data]),
            patch.object(babelio_service, "fetch_publisher_from_url") as mock_fetch,
        ):
            result = await babelio_service.verify_book(
                "Titre vague incomplet", "Auteur Inconnu Totalement"
            )

            # Vérifier que fetch_publisher_from_url n'a PAS été appelé
            mock_fetch.assert_not_called()

            # babelio_publisher devrait être None ou absent
            assert result.get("babelio_publisher") is None

    @pytest.mark.asyncio
    async def test_verify_book_should_handle_scraping_error_gracefully(
        self, babelio_service
    ):
        """GIVEN: verify_book() avec confiance >= 0.90 mais scraping échoue
        WHEN: verify_book() est appelé
        THEN: Retourne résultat sans babelio_publisher (pas d'erreur fatale)
        """
        mock_book_data = {
            "id_oeuvre": "1635414",
            "titre": "Des visages et des mains",
            "prenoms": "Hannah",
            "nom": "Assouline",
            "ca_copies": "6",
            "type": "livres",
            "url": "/livres/Assouline-Des-visages-et-des-mains/1635414",
        }

        with (
            patch.object(babelio_service, "search", return_value=[mock_book_data]),
            patch.object(
                babelio_service,
                "fetch_publisher_from_url",
                side_effect=Exception("Scraping failed"),
            ),
        ):
            result = await babelio_service.verify_book(
                "Des visages et des mains", "Hannah Assouline"
            )

            # Le résultat principal devrait être OK
            assert result["status"] in ["verified", "corrected"]
            assert result["confidence_score"] >= 0.90

            # babelio_publisher devrait être None (erreur gérée)
            assert result.get("babelio_publisher") is None
