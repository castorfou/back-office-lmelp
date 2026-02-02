"""Tests for enhanced /api/auteur/{auteur_id} with emissions and avis (Issue #190).

The author detail endpoint should return books with average ratings and emission dates,
sorted by most recent emission date.
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


class TestAuteurWithEmissionsAndAvis:
    """Tests for get_auteur_with_livres returning books with avis and emissions."""

    def test_auteur_response_includes_note_moyenne_per_book(
        self, mongodb_service_instance
    ):
        """Test that each book includes note_moyenne."""
        auteur_id = ObjectId()
        livre1_id = ObjectId()
        livre2_id = ObjectId()
        ep1_id = ObjectId()
        ep2_id = ObjectId()
        ep3_id = ObjectId()

        mongodb_service_instance.auteurs_collection.aggregate.return_value = [
            {
                "_id": auteur_id,
                "nom": "Constance Debré",
                "url_babelio": "https://www.babelio.com/auteur/test",
                "livres": [
                    {
                        "_id": livre1_id,
                        "titre": "Love me tender",
                        "editeur": "Flammarion",
                        "episodes": [str(ep1_id), str(ep2_id)],
                    },
                    {
                        "_id": livre2_id,
                        "titre": "Nom",
                        "editeur": "Flammarion",
                        "episodes": [str(ep3_id)],
                    },
                ],
            }
        ]

        # Mock avis for livre1: notes [9, 7], for livre2: notes [5]
        def avis_find_side_effect(query):
            livre_oid = query.get("livre_oid")
            if livre_oid == str(livre1_id):
                return [
                    {"note": 9, "emission_oid": "em1", "livre_oid": str(livre1_id)},
                    {"note": 7, "emission_oid": "em1", "livre_oid": str(livre1_id)},
                ]
            elif livre_oid == str(livre2_id):
                return [
                    {"note": 5, "emission_oid": "em2", "livre_oid": str(livre2_id)},
                ]
            return []

        mongodb_service_instance.avis_collection.find.side_effect = (
            avis_find_side_effect
        )

        # Mock emissions (no emissions needed for note_moyenne test)
        mongodb_service_instance.emissions_collection.find.return_value = []

        # WHEN
        result = mongodb_service_instance.get_auteur_with_livres(str(auteur_id))

        # THEN: Each book has note_moyenne
        assert result is not None
        livres = result["livres"]
        assert len(livres) == 2

        for livre in livres:
            assert "note_moyenne" in livre

    def test_auteur_books_include_emission_dates(self, mongodb_service_instance):
        """Test that each book includes its emission dates."""
        auteur_id = ObjectId()
        livre_id = ObjectId()
        episode_id = ObjectId()
        emission_id = ObjectId()

        mongodb_service_instance.auteurs_collection.aggregate.return_value = [
            {
                "_id": auteur_id,
                "nom": "Constance Debré",
                "livres": [
                    {
                        "_id": livre_id,
                        "titre": "Love me tender",
                        "editeur": "Flammarion",
                        "episodes": [str(episode_id)],
                    },
                ],
            }
        ]

        # Mock avis
        mongodb_service_instance.avis_collection.find.return_value = [
            {"note": 8, "emission_oid": str(emission_id), "livre_oid": str(livre_id)},
        ]

        # Mock emissions collection directly
        mongodb_service_instance.emissions_collection.find.return_value = [
            {
                "_id": emission_id,
                "episode_id": episode_id,
                "date": "2020-01-26T00:00:00.000Z",
            }
        ]

        # WHEN
        result = mongodb_service_instance.get_auteur_with_livres(str(auteur_id))

        # THEN: Each book includes emissions with dates
        assert result is not None
        livre = result["livres"][0]
        assert "emissions" in livre
        assert len(livre["emissions"]) == 1
        assert livre["emissions"][0]["date"] == "2020-01-26"

    def test_auteur_books_sorted_by_most_recent_emission(
        self, mongodb_service_instance
    ):
        """Test that books are sorted by most recent emission date (desc)."""
        auteur_id = ObjectId()
        livre_old_id = ObjectId()
        livre_recent_id = ObjectId()
        ep_old_id = ObjectId()
        ep_recent_id = ObjectId()
        em_old_id = ObjectId()
        em_recent_id = ObjectId()

        mongodb_service_instance.auteurs_collection.aggregate.return_value = [
            {
                "_id": auteur_id,
                "nom": "Test Auteur",
                "livres": [
                    # Order in DB: old book first
                    {
                        "_id": livre_old_id,
                        "titre": "Ancien Livre",
                        "editeur": "Ed1",
                        "episodes": [str(ep_old_id)],
                    },
                    {
                        "_id": livre_recent_id,
                        "titre": "Récent Livre",
                        "editeur": "Ed2",
                        "episodes": [str(ep_recent_id)],
                    },
                ],
            }
        ]

        # Mock avis (no notes needed for this test)
        mongodb_service_instance.avis_collection.find.return_value = []

        # Mock emissions: need to return correct results based on query
        def emissions_find_side_effect(query):
            episode_ids = query.get("episode_id", {}).get("$in", [])
            results = []
            for ep_id in episode_ids:
                if ep_id == ep_old_id:
                    results.append(
                        {
                            "_id": em_old_id,
                            "episode_id": ep_old_id,
                            "date": "2018-05-10T00:00:00.000Z",
                        }
                    )
                elif ep_id == ep_recent_id:
                    results.append(
                        {
                            "_id": em_recent_id,
                            "episode_id": ep_recent_id,
                            "date": "2024-11-15T00:00:00.000Z",
                        }
                    )
            return results

        mongodb_service_instance.emissions_collection.find.side_effect = (
            emissions_find_side_effect
        )

        # WHEN
        result = mongodb_service_instance.get_auteur_with_livres(str(auteur_id))

        # THEN: Books sorted by most recent emission (desc)
        assert result is not None
        livres = result["livres"]
        assert len(livres) == 2
        # Recent book should be first
        assert livres[0]["titre"] == "Récent Livre"
        assert livres[1]["titre"] == "Ancien Livre"


class TestAuteurDetailEndpointWithEmissions:
    """Tests for the GET /api/auteur/{auteur_id} endpoint with emissions data."""

    @patch("back_office_lmelp.app.mongodb_service")
    def test_endpoint_returns_books_with_emissions_and_notes(
        self, mock_mongodb_service, client
    ):
        """Test that the endpoint returns books with emissions and notes."""
        auteur_id = str(ObjectId())
        livre_id = str(ObjectId())
        emission_id = str(ObjectId())

        mock_mongodb_service.get_auteur_with_livres.return_value = {
            "auteur_id": auteur_id,
            "nom": "Constance Debré",
            "url_babelio": "https://www.babelio.com/auteur/test",
            "nombre_oeuvres": 1,
            "livres": [
                {
                    "livre_id": livre_id,
                    "titre": "Love me tender",
                    "editeur": "Flammarion",
                    "note_moyenne": 7.5,
                    "emissions": [
                        {"emission_id": emission_id, "date": "2020-01-26"},
                    ],
                }
            ],
        }

        response = client.get(f"/api/auteur/{auteur_id}")
        assert response.status_code == 200
        data = response.json()

        livre = data["livres"][0]
        assert livre["note_moyenne"] == 7.5
        assert "emissions" in livre
        assert livre["emissions"][0]["date"] == "2020-01-26"
