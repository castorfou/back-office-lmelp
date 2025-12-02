"""Tests pour l'extraction d'URL auteur depuis verify_book() (Issue #124).

Ce module teste que verify_book() retourne maintenant babelio_author_url
en plus de babelio_url, permettant de créer des auteurs avec leur URL Babelio.
"""

from unittest.mock import patch

import pytest

from back_office_lmelp.services.babelio_service import BabelioService


class TestBabelioAuthorUrlExtraction:
    """Tests pour l'extraction d'URL auteur depuis les données livre."""

    @pytest.fixture
    def babelio_service(self):
        """Fixture pour créer une instance du service Babelio."""
        return BabelioService()

    @pytest.mark.asyncio
    async def test_verify_book_includes_author_url(self, babelio_service):
        """Test que verify_book() retourne l'URL auteur (Issue #124).

        Quand on vérifie un livre, la réponse Babelio contient:
        - id_auteur: "7743"
        - prenoms: "Catherine"
        - nom: "Millet"

        verify_book() doit construire l'URL auteur:
        https://www.babelio.com/auteur/Catherine-Millet/7743
        """
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

        with patch.object(babelio_service, "search", return_value=mock_search_results):
            result = await babelio_service.verify_book(
                "Simone Émonet", "Catherine Millet"
            )

        # Vérifications
        assert result["status"] == "verified"
        assert (
            result["babelio_url"]
            == "https://www.babelio.com/livres/Millet-Simone-monet/1870367"
        )

        # Issue #124: Nouvelle assertion pour URL auteur
        assert "babelio_author_url" in result
        assert (
            result["babelio_author_url"]
            == "https://www.babelio.com/auteur/Catherine-Millet/7743"
        )

    @pytest.mark.asyncio
    async def test_verify_book_author_url_with_compound_name(self, babelio_service):
        """Test URL auteur avec nom composé (ex: Jean-Paul Sartre)."""
        mock_search_results = [
            {
                "id_oeuvre": "1234",
                "titre": "La Nausée",
                "id_auteur": "9999",
                "prenoms": "Jean-Paul",
                "nom": "Sartre",
                "type": "livres",
                "url": "/livres/Sartre-La-Nausee/1234",
            }
        ]

        with patch.object(babelio_service, "search", return_value=mock_search_results):
            result = await babelio_service.verify_book("La Nausée", "Jean-Paul Sartre")

        assert "babelio_author_url" in result
        assert (
            result["babelio_author_url"]
            == "https://www.babelio.com/auteur/Jean-Paul-Sartre/9999"
        )

    @pytest.mark.asyncio
    async def test_verify_book_author_url_missing_data(self, babelio_service):
        """Test que l'URL auteur est None si données manquantes."""
        # Cas: réponse Babelio sans id_auteur (rare mais possible)
        mock_search_results = [
            {
                "id_oeuvre": "1234",
                "titre": "Livre Sans Auteur",
                # id_auteur manquant
                "type": "livres",
                "url": "/livres/Inconnu-Livre/1234",
            }
        ]

        with patch.object(babelio_service, "search", return_value=mock_search_results):
            result = await babelio_service.verify_book("Livre Sans Auteur", None)

        assert "babelio_author_url" in result
        assert result["babelio_author_url"] is None

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
