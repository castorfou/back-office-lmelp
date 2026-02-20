"""Tests for Calibre enrichment on livre detail page (Issue #214).

Tests that GET /api/livre/{id} includes:
- calibre_in_library: whether the book is in the Calibre library
- calibre_read: whether the book has been read
- calibre_rating: the Calibre rating if available
- calibre_current_tags: the actual tags from Calibre (for delta display)
"""

from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def make_livre_data(livre_id: str, titre: str = "Test Book") -> dict:
    """Build a minimal livre_data dict."""
    return {
        "livre_id": livre_id,
        "titre": titre,
        "auteur_id": str(ObjectId()),
        "auteur_nom": "Test Author",
        "editeur": "Test Publisher",
        "url_babelio": None,
        "note_moyenne": None,
        "nombre_emissions": 0,
        "emissions": [],
        "calibre_tags": ["lmelp_240324"],
    }


class TestLivreDetailCalibreEnrichment:
    """Tests pour l'enrichissement Calibre dans GET /api/livre/{livre_id}."""

    @patch("back_office_lmelp.app.calibre_matching_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_livre_detail_includes_calibre_in_library_true(
        self, mock_mongodb_service, mock_calibre_service, client
    ):
        """Test that calibre_in_library=True when book is in Calibre index."""
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = make_livre_data(
            livre_id, titre="L'Adversaire"
        )

        # Simulate calibre enrich_palmares_item setting calibre_in_library=True
        def mock_enrich(item, calibre_index):
            item["calibre_in_library"] = True
            item["calibre_read"] = False
            item["calibre_rating"] = None
            item["calibre_current_tags"] = ["lmelp_240324"]

        mock_calibre_service.get_calibre_index.return_value = {}
        mock_calibre_service.enrich_palmares_item.side_effect = mock_enrich

        response = client.get(f"/api/livre/{livre_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["calibre_in_library"] is True

    @patch("back_office_lmelp.app.calibre_matching_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_livre_detail_includes_calibre_in_library_false(
        self, mock_mongodb_service, mock_calibre_service, client
    ):
        """Test that calibre_in_library=False when book is NOT in Calibre index."""
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = make_livre_data(
            livre_id, titre="Livre Inconnu"
        )

        def mock_enrich(item, calibre_index):
            item["calibre_in_library"] = False
            item["calibre_read"] = None
            item["calibre_rating"] = None
            item["calibre_current_tags"] = None

        mock_calibre_service.get_calibre_index.return_value = {}
        mock_calibre_service.enrich_palmares_item.side_effect = mock_enrich

        response = client.get(f"/api/livre/{livre_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["calibre_in_library"] is False

    @patch("back_office_lmelp.app.calibre_matching_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_livre_detail_includes_calibre_read_and_rating(
        self, mock_mongodb_service, mock_calibre_service, client
    ):
        """Test that calibre_read=True and calibre_rating are included when book is read."""
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = make_livre_data(
            livre_id, titre="La Deuxième Vie"
        )

        def mock_enrich(item, calibre_index):
            item["calibre_in_library"] = True
            item["calibre_read"] = True
            item["calibre_rating"] = 8
            item["calibre_current_tags"] = ["lmelp_240324"]

        mock_calibre_service.get_calibre_index.return_value = {}
        mock_calibre_service.enrich_palmares_item.side_effect = mock_enrich

        response = client.get(f"/api/livre/{livre_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["calibre_in_library"] is True
        assert data["calibre_read"] is True
        assert data["calibre_rating"] == 8

    @patch("back_office_lmelp.app.calibre_matching_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_livre_detail_includes_calibre_current_tags(
        self, mock_mongodb_service, mock_calibre_service, client
    ):
        """Test that calibre_current_tags from Calibre are returned for tag delta."""
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = {
            **make_livre_data(livre_id, titre="Test Book"),
            "calibre_tags": ["lmelp_240101", "lmelp_240324", "lmelp_arnaud_viviant"],
        }

        def mock_enrich(item, calibre_index):
            item["calibre_in_library"] = True
            item["calibre_read"] = True
            item["calibre_rating"] = 7
            # Only lmelp_240101 is already in Calibre
            item["calibre_current_tags"] = ["lmelp_240101", "babelio"]

        mock_calibre_service.get_calibre_index.return_value = {}
        mock_calibre_service.enrich_palmares_item.side_effect = mock_enrich

        response = client.get(f"/api/livre/{livre_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["calibre_current_tags"] == ["lmelp_240101", "babelio"]

    @patch("back_office_lmelp.app.calibre_matching_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_livre_detail_calibre_unavailable_fallback(
        self, mock_mongodb_service, mock_calibre_service, client
    ):
        """Test graceful fallback when Calibre is unavailable."""
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = make_livre_data(
            livre_id
        )

        # Simulate Calibre unavailable: get_calibre_index raises
        mock_calibre_service.get_calibre_index.side_effect = RuntimeError(
            "Calibre non disponible"
        )

        response = client.get(f"/api/livre/{livre_id}")

        # Should still return 200 with livre data, just no calibre enrichment
        assert response.status_code == 200
        data = response.json()
        assert data["calibre_in_library"] is False
        assert data["calibre_read"] is None
        assert data["calibre_rating"] is None
        assert data["calibre_current_tags"] is None

    @patch("back_office_lmelp.app.calibre_matching_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_livre_detail_enrich_called_with_calibre_index(
        self, mock_mongodb_service, mock_calibre_service, client
    ):
        """Test that enrich_palmares_item is called with the calibre index."""
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = make_livre_data(
            livre_id
        )

        calibre_index = {"test book": {"id": 1, "read": False, "rating": None}}
        mock_calibre_service.get_calibre_index.return_value = calibre_index

        def mock_enrich(item, index):
            item["calibre_in_library"] = False
            item["calibre_read"] = None
            item["calibre_rating"] = None
            item["calibre_current_tags"] = None

        mock_calibre_service.enrich_palmares_item.side_effect = mock_enrich

        response = client.get(f"/api/livre/{livre_id}")

        assert response.status_code == 200
        mock_calibre_service.enrich_palmares_item.assert_called_once()
        call_args = mock_calibre_service.enrich_palmares_item.call_args
        assert call_args[0][1] == calibre_index
