"""Tests for enhanced /api/livre/{livre_id} with emissions and avis (Issue #190).

The book detail endpoint should return emissions (not episodes) with average ratings,
and an overall average rating for the book.
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.services.mongodb_service import MongoDBService


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mongodb_service_instance():
    """Create a MongoDB service with mocked collections."""
    service = MongoDBService()
    service.livres_collection = MagicMock()
    service.episodes_collection = MagicMock()
    service.auteurs_collection = MagicMock()
    service.avis_collection = MagicMock()
    service.emissions_collection = MagicMock()
    return service


class TestLivreWithEmissionsAndAvis:
    """Tests for get_livre_with_episodes returning emissions with avis ratings."""

    def test_livre_response_includes_note_moyenne(self, mongodb_service_instance):
        """Test that the book response includes an overall note_moyenne."""
        # GIVEN: A book with avis having notes
        livre_id = ObjectId()
        auteur_id = ObjectId()
        episode1_id = ObjectId()
        emission1_id = ObjectId()

        mongodb_service_instance.livres_collection.aggregate.return_value = [
            {
                "_id": livre_id,
                "titre": "Love me tender",
                "auteur_id": auteur_id,
                "editeur": "Flammarion",
                "url_babelio": "https://www.babelio.com/livres/test/123",
                "auteur": [{"nom": "Constance Debré"}],
                "episodes_data": [
                    {
                        "_id": episode1_id,
                        "titre": "Émission du 26 janvier 2020",
                        "date": "2020-01-26T00:00:00.000Z",
                        "programme": True,
                    },
                ],
            }
        ]

        # Mock emissions collection
        mongodb_service_instance.emissions_collection.find.return_value = [
            {
                "_id": emission1_id,
                "episode_id": episode1_id,
                "date": "2020-01-26T00:00:00.000Z",
            }
        ]

        # Mock avis collection: ratings for this book
        mongodb_service_instance.avis_collection.find.return_value = [
            {
                "emission_oid": str(emission1_id),
                "livre_oid": str(livre_id),
                "note": 9,
            },
            {
                "emission_oid": str(emission1_id),
                "livre_oid": str(livre_id),
                "note": 7,
            },
            {
                "emission_oid": str(emission1_id),
                "livre_oid": str(livre_id),
                "note": 3,
            },
        ]

        # WHEN: We call get_livre_with_episodes
        result = mongodb_service_instance.get_livre_with_episodes(str(livre_id))

        # THEN: The response includes note_moyenne (average of 9, 7, 3 = 6.3)
        assert result is not None
        assert "note_moyenne" in result
        assert result["note_moyenne"] == pytest.approx(6.3, abs=0.1)

    def test_livre_response_includes_emissions_with_notes(
        self, mongodb_service_instance
    ):
        """Test that the book response includes emissions with per-emission average notes."""
        # GIVEN: A book with 2 emissions, each with different avis
        livre_id = ObjectId()
        auteur_id = ObjectId()
        episode1_id = ObjectId()
        episode2_id = ObjectId()
        emission1_id = ObjectId()
        emission2_id = ObjectId()

        mongodb_service_instance.livres_collection.aggregate.return_value = [
            {
                "_id": livre_id,
                "titre": "Love me tender",
                "auteur_id": auteur_id,
                "editeur": "Flammarion",
                "auteur": [{"nom": "Constance Debré"}],
                "episodes_data": [
                    {
                        "_id": episode1_id,
                        "titre": "Émission du 26 janvier 2020",
                        "date": "2020-01-26T00:00:00.000Z",
                        "programme": True,
                    },
                    {
                        "_id": episode2_id,
                        "titre": "Émission du 12 janvier 2020",
                        "date": "2020-01-12T00:00:00.000Z",
                        "programme": False,
                    },
                ],
            }
        ]

        # Mock emissions collection directly
        mongodb_service_instance.emissions_collection.find.return_value = [
            {
                "_id": emission1_id,
                "episode_id": episode1_id,
                "date": "2020-01-26T00:00:00.000Z",
            },
            {
                "_id": emission2_id,
                "episode_id": episode2_id,
                "date": "2020-01-12T00:00:00.000Z",
            },
        ]

        # Mock avis: emission1 has notes [9, 9, 3], emission2 has note [9]
        mongodb_service_instance.avis_collection.find.return_value = [
            {
                "emission_oid": str(emission1_id),
                "livre_oid": str(livre_id),
                "note": 9,
            },
            {
                "emission_oid": str(emission1_id),
                "livre_oid": str(livre_id),
                "note": 9,
            },
            {
                "emission_oid": str(emission1_id),
                "livre_oid": str(livre_id),
                "note": 3,
            },
            {
                "emission_oid": str(emission2_id),
                "livre_oid": str(livre_id),
                "note": 9,
            },
        ]

        # WHEN
        result = mongodb_service_instance.get_livre_with_episodes(str(livre_id))

        # THEN: The response has emissions (not episodes)
        assert result is not None
        assert "emissions" in result
        assert "nombre_emissions" in result
        assert result["nombre_emissions"] == 2

        # Each emission has date, note_moyenne, nombre_avis
        emissions = result["emissions"]
        assert len(emissions) == 2

        # Emissions should be sorted by date descending
        assert emissions[0]["date"] == "2020-01-26"
        assert emissions[1]["date"] == "2020-01-12"

        # Each emission has note_moyenne and nombre_avis
        for emission in emissions:
            assert "emission_id" in emission
            assert "date" in emission
            assert "note_moyenne" in emission
            assert "nombre_avis" in emission

        # Emission 1 (26 jan): avg of [9, 9, 3] = 7.0
        assert emissions[0]["note_moyenne"] == pytest.approx(7.0, abs=0.1)
        assert emissions[0]["nombre_avis"] == 3

        # Emission 2 (12 jan): avg of [9] = 9.0
        assert emissions[1]["note_moyenne"] == pytest.approx(9.0, abs=0.1)
        assert emissions[1]["nombre_avis"] == 1

    def test_livre_response_handles_no_avis(self, mongodb_service_instance):
        """Test that book with no avis returns null note_moyenne."""
        # GIVEN: A book with episodes but no avis
        livre_id = ObjectId()
        auteur_id = ObjectId()
        episode1_id = ObjectId()
        emission1_id = ObjectId()

        mongodb_service_instance.livres_collection.aggregate.return_value = [
            {
                "_id": livre_id,
                "titre": "Livre sans avis",
                "auteur_id": auteur_id,
                "editeur": "Éditeur",
                "auteur": [{"nom": "Auteur Test"}],
                "episodes_data": [
                    {
                        "_id": episode1_id,
                        "titre": "Émission du 1 mars 2020",
                        "date": "2020-03-01T00:00:00.000Z",
                        "programme": True,
                    },
                ],
            }
        ]

        # Mock emissions collection
        mongodb_service_instance.emissions_collection.find.return_value = [
            {
                "_id": emission1_id,
                "episode_id": episode1_id,
                "date": "2020-03-01T00:00:00.000Z",
            },
        ]

        # No avis for this book
        mongodb_service_instance.avis_collection.find.return_value = []

        # WHEN
        result = mongodb_service_instance.get_livre_with_episodes(str(livre_id))

        # THEN: note_moyenne is None, emissions exist but with null note_moyenne
        assert result is not None
        assert result["note_moyenne"] is None
        assert len(result["emissions"]) == 1
        assert result["emissions"][0]["note_moyenne"] is None
        assert result["emissions"][0]["nombre_avis"] == 0


class TestLivreDetailEndpointWithEmissions:
    """Tests for the GET /api/livre/{livre_id} endpoint with emissions data."""

    @patch("back_office_lmelp.app.mongodb_service")
    def test_endpoint_returns_emissions_and_note(self, mock_mongodb_service, client):
        """Test that the endpoint returns emissions with notes in response."""
        livre_id = str(ObjectId())
        auteur_id = str(ObjectId())
        emission_id = str(ObjectId())

        mock_mongodb_service.get_livre_with_episodes.return_value = {
            "livre_id": livre_id,
            "titre": "Love me tender",
            "auteur_id": auteur_id,
            "auteur_nom": "Constance Debré",
            "editeur": "Flammarion",
            "url_babelio": "https://www.babelio.com/test",
            "note_moyenne": 7.5,
            "nombre_emissions": 2,
            "emissions": [
                {
                    "emission_id": emission_id,
                    "date": "2020-01-26",
                    "note_moyenne": 7.0,
                    "nombre_avis": 3,
                },
            ],
        }

        response = client.get(f"/api/livre/{livre_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["note_moyenne"] == 7.5
        assert data["nombre_emissions"] == 2
        assert "emissions" in data
        assert data["emissions"][0]["note_moyenne"] == 7.0
        assert data["emissions"][0]["nombre_avis"] == 3
