"""Tests pour l'extraction d'URL auteur depuis verify_book() (Issue #124).

Ce module teste que verify_book() retourne maintenant babelio_author_url
en plus de babelio_url, permettant de créer des auteurs avec leur URL Babelio.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from back_office_lmelp.services.babelio_service import BabelioService


class TestBabelioAuthorUrlExtraction:
    """Tests pour l'extraction d'URL auteur depuis les données livre."""

    @pytest.fixture
    def babelio_service(self):
        """Fixture pour créer une instance du service Babelio."""
        return BabelioService()

    @pytest.mark.asyncio
    async def test_fetch_author_url_from_page_scrapes_correctly(self, babelio_service):
        """Test que fetch_author_url_from_page() scrape correctement l'URL auteur (Issue #124).

        Vérifie que BeautifulSoup extrait bien le lien auteur depuis le HTML.
        """
        # HTML réel simplifié d'une page livre Babelio
        mock_html = """
        <html>
            <body>
                <h1>Sphinx</h1>
                <a href="/auteur/Anne-F-Garreta/20464">Anne F. Garréta</a>
                <a href="/editeur/Grasset/123">Grasset</a>
            </body>
        </html>
        """

        # Mock de la session HTTP
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with patch.object(babelio_service, "_get_session", return_value=mock_session):
            url = await babelio_service.fetch_author_url_from_page(
                "https://www.babelio.com/livres/Garreta-Sphinx/149981"
            )

        # Vérifications: BeautifulSoup doit avoir extrait le bon lien
        assert url == "https://www.babelio.com/auteur/Anne-F-Garreta/20464"

    @pytest.mark.asyncio
    async def test_verify_book_includes_author_url(self, babelio_service):
        """Test que verify_book() retourne l'URL auteur scrapée (Issue #124)."""
        # Mock de la vraie réponse Babelio pour un livre
        mock_search_results = [
            {
                "id_oeuvre": "1870367",
                "titre": "Simone Émonet",
                "couverture": "/couv/cvt_Simone-monet_42.jpg",
                "id_auteur": "7743",
                "prenoms": "Catherine",
                "nom": "Millet",
                "ca_copies": "158",
                "tri": "158",
                "ca_note": "3.23",
                "type": "livres",
                "url": "/livres/Millet-Simone-monet/1870367",
            }
        ]

        # HTML de la page du livre avec le lien auteur
        mock_html = """
        <html>
            <body>
                <a href="/auteur/Catherine-Millet/7743">Catherine Millet</a>
            </body>
        </html>
        """

        # Mock de la session HTTP
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with (
            patch.object(babelio_service, "search", return_value=mock_search_results),
            patch.object(babelio_service, "_get_session", return_value=mock_session),
        ):
            result = await babelio_service.verify_book(
                "Simone Émonet", "Catherine Millet"
            )

        # Vérifications
        assert result["status"] == "verified"
        assert (
            result["babelio_url"]
            == "https://www.babelio.com/livres/Millet-Simone-monet/1870367"
        )

        # Issue #124: Vérifier que l'URL auteur est bien scrapée
        assert "babelio_author_url" in result
        assert (
            result["babelio_author_url"]
            == "https://www.babelio.com/auteur/Catherine-Millet/7743"
        )

    @pytest.mark.asyncio
    async def test_fetch_author_url_no_author_link_in_page(self, babelio_service):
        """Test que fetch_author_url_from_page() retourne None si aucun lien auteur."""
        # HTML sans lien auteur
        mock_html = """
        <html>
            <body>
                <h1>Livre anonyme</h1>
                <a href="/editeur/Grasset/123">Grasset</a>
            </body>
        </html>
        """

        # Mock de la session HTTP
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with patch.object(babelio_service, "_get_session", return_value=mock_session):
            url = await babelio_service.fetch_author_url_from_page(
                "https://www.babelio.com/livres/Anonyme-Livre/1234"
            )

        # Vérifications: doit retourner None
        assert url is None

    @pytest.mark.asyncio
    async def test_verify_book_not_found_no_author_url(self, babelio_service):
        """Test que babelio_author_url est None si livre non trouvé."""
        with patch.object(babelio_service, "search", return_value=[]):
            result = await babelio_service.verify_book(
                "Livre Inexistant", "Auteur Inconnu"
            )

        assert result["status"] == "not_found"
        assert "babelio_author_url" in result
        assert result["babelio_author_url"] is None
