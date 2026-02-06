"""Tests for enriched GET /api/avis/by-livre/{livre_id} endpoint (Issue #201).

The endpoint should return critic reviews for a book, enriched with
critic names and emission dates for display on the livre detail page.
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestAvisByLivreEnriched:
    """Tests for enriched avis data in GET /api/avis/by-livre/{livre_id}."""

    @patch("back_office_lmelp.app.mongodb_service")
    def test_enriched_response_includes_critique_nom(
        self, mock_mongodb_service, client
    ):
        """Test that response includes official critic name when resolved."""
        livre_id = str(ObjectId())
        critique_id = ObjectId()
        emission_id = ObjectId()

        # Mock the service method (not the collection directly)
        mock_mongodb_service.avis_collection = MagicMock()
        mock_mongodb_service.get_avis_by_livre.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "livre_oid": livre_id,
                "critique_oid": str(critique_id),
                "critique_nom_extrait": "Arnaud Viviant",
                "commentaire": "Impressionnant",
                "note": 8,
                "section": "programme",
            }
        ]

        # Mock critiques collection for enrichment
        mock_mongodb_service.critiques_collection = MagicMock()
        mock_mongodb_service.critiques_collection.find_one.return_value = {
            "_id": critique_id,
            "nom": "Arnaud Viviant",
        }

        # Mock emissions collection for enrichment
        mock_mongodb_service.emissions_collection = MagicMock()
        mock_mongodb_service.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "date": "2025-01-26T00:00:00.000Z",
        }

        response = client.get(f"/api/avis/by-livre/{livre_id}")
        assert response.status_code == 200
        data = response.json()

        assert len(data["avis"]) == 1
        avis = data["avis"][0]
        assert avis["critique_nom"] == "Arnaud Viviant"
        assert avis["emission_date"] is not None

    @patch("back_office_lmelp.app.mongodb_service")
    def test_enriched_response_includes_emission_date(
        self, mock_mongodb_service, client
    ):
        """Test that response includes emission date for grouping."""
        livre_id = str(ObjectId())
        emission_id = ObjectId()

        mock_mongodb_service.avis_collection = MagicMock()
        mock_mongodb_service.get_avis_by_livre.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "livre_oid": livre_id,
                "critique_oid": None,
                "critique_nom_extrait": "Test Critique",
                "commentaire": "Bon livre",
                "note": 7,
                "section": "programme",
            }
        ]

        mock_mongodb_service.critiques_collection = MagicMock()

        # Mock emissions lookup
        mock_mongodb_service.emissions_collection = MagicMock()
        mock_mongodb_service.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "date": "2024-12-15T00:00:00.000Z",
        }

        response = client.get(f"/api/avis/by-livre/{livre_id}")
        assert response.status_code == 200
        data = response.json()

        avis = data["avis"][0]
        assert "emission_date" in avis
        assert "2024-12-15" in avis["emission_date"]

    @patch("back_office_lmelp.app.mongodb_service")
    def test_response_with_no_avis_returns_empty_list(
        self, mock_mongodb_service, client
    ):
        """Test that a book with no avis returns empty list."""
        livre_id = str(ObjectId())

        mock_mongodb_service.avis_collection = MagicMock()
        mock_mongodb_service.get_avis_by_livre.return_value = []
        mock_mongodb_service.critiques_collection = MagicMock()
        mock_mongodb_service.emissions_collection = MagicMock()

        response = client.get(f"/api/avis/by-livre/{livre_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["avis"] == []

    @patch("back_office_lmelp.app.mongodb_service")
    def test_unresolved_critique_has_no_critique_nom(
        self, mock_mongodb_service, client
    ):
        """Test that avis with no critique_oid has no critique_nom field."""
        livre_id = str(ObjectId())
        emission_id = ObjectId()

        mock_mongodb_service.avis_collection = MagicMock()
        mock_mongodb_service.get_avis_by_livre.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "livre_oid": livre_id,
                "critique_oid": None,
                "critique_nom_extrait": "Critique Inconnu",
                "commentaire": "Pas mal",
                "note": 6,
                "section": "programme",
            }
        ]

        mock_mongodb_service.critiques_collection = MagicMock()
        mock_mongodb_service.emissions_collection = MagicMock()
        mock_mongodb_service.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "date": "2025-03-01T00:00:00.000Z",
        }

        response = client.get(f"/api/avis/by-livre/{livre_id}")
        assert response.status_code == 200
        data = response.json()

        avis = data["avis"][0]
        assert "critique_nom" not in avis
        assert avis["critique_nom_extrait"] == "Critique Inconnu"
