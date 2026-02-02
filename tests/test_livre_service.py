"""Tests for get_livre_with_episodes() service method (Issue #96 - Phase 2, updated Issue #190)."""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


@pytest.fixture
def mongodb_service():
    """Create a MongoDB service with mocked collections."""
    service = MongoDBService()
    service.livres_collection = MagicMock()
    service.episodes_collection = MagicMock()
    service.auteurs_collection = MagicMock()
    service.emissions_collection = MagicMock()
    service.avis_collection = MagicMock()
    return service


class TestGetLivreWithEpisodes:
    """Tests pour la méthode get_livre_with_episodes()."""

    def test_get_livre_with_episodes_returns_book_with_emissions_sorted_by_date(
        self, mongodb_service
    ):
        """Test que get_livre_with_episodes retourne un livre avec ses émissions triées par date."""
        # GIVEN: Un livre avec plusieurs épisodes en base
        livre_id = ObjectId()
        auteur_id = ObjectId()
        episode1_id = ObjectId()
        episode2_id = ObjectId()
        episode3_id = ObjectId()
        emission1_id = ObjectId()
        emission2_id = ObjectId()
        emission3_id = ObjectId()

        mongodb_service.livres_collection.aggregate.return_value = [
            {
                "_id": livre_id,
                "titre": "L'Adversaire",
                "auteur_id": auteur_id,
                "editeur": "Gallimard",
                "auteur": [{"nom": "Emmanuel Carrère"}],
                "episodes_data": [
                    {
                        "_id": episode2_id,
                        "titre": "Émission du 15 septembre 2000",
                        "date": "2000-09-15T00:00:00.000Z",
                        "programme": True,
                    },
                    {
                        "_id": episode1_id,
                        "titre": "Émission du 12 mars 2000",
                        "date": "2000-03-12T00:00:00.000Z",
                        "programme": False,
                    },
                    {
                        "_id": episode3_id,
                        "titre": "Émission du 20 décembre 2000",
                        "date": "2000-12-20T00:00:00.000Z",
                        "programme": True,
                    },
                ],
            }
        ]

        # Mock emissions
        mongodb_service.emissions_collection.find.return_value = [
            {
                "_id": emission1_id,
                "episode_id": episode1_id,
                "date": "2000-03-12T00:00:00.000Z",
            },
            {
                "_id": emission2_id,
                "episode_id": episode2_id,
                "date": "2000-09-15T00:00:00.000Z",
            },
            {
                "_id": emission3_id,
                "episode_id": episode3_id,
                "date": "2000-12-20T00:00:00.000Z",
            },
        ]

        # Mock avis (no ratings for this test)
        mongodb_service.avis_collection.find.return_value = []

        # WHEN: On appelle get_livre_with_episodes
        result = mongodb_service.get_livre_with_episodes(str(livre_id))

        # THEN: On reçoit le livre avec ses émissions triées par date (plus récent d'abord)
        assert result is not None
        assert result["livre_id"] == str(livre_id)
        assert result["titre"] == "L'Adversaire"
        assert result["auteur_nom"] == "Emmanuel Carrère"
        assert result["auteur_id"] == str(auteur_id)
        assert result["editeur"] == "Gallimard"
        assert result["nombre_emissions"] == 3

        # Vérifier que les émissions sont triées par date (plus récent d'abord)
        assert len(result["emissions"]) == 3
        assert result["emissions"][0]["date"] == "2000-12-20"
        assert result["emissions"][1]["date"] == "2000-09-15"
        assert result["emissions"][2]["date"] == "2000-03-12"

        # Vérifier que chaque émission a les bons champs (Issue #190)
        for emission in result["emissions"]:
            assert "emission_id" in emission
            assert "date" in emission
            assert "note_moyenne" in emission
            assert "nombre_avis" in emission

    def test_get_livre_with_episodes_returns_none_when_not_found(self, mongodb_service):
        """Test que get_livre_with_episodes retourne None si le livre n'existe pas."""
        # GIVEN: Un livre inexistant
        livre_id = str(ObjectId())
        mongodb_service.livres_collection.aggregate.return_value = []

        # WHEN: On appelle get_livre_with_episodes
        result = mongodb_service.get_livre_with_episodes(livre_id)

        # THEN: On reçoit None
        assert result is None

    def test_get_livre_with_episodes_returns_book_with_empty_emissions_list(
        self, mongodb_service
    ):
        """Test qu'un livre sans épisodes retourne une liste d'émissions vide."""
        # GIVEN: Un livre sans épisodes
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mongodb_service.livres_collection.aggregate.return_value = [
            {
                "_id": livre_id,
                "titre": "Nouveau Livre",
                "auteur_id": auteur_id,
                "editeur": "Nouveau Editeur",
                "auteur": [{"nom": "Nouvel Auteur"}],
                "episodes_data": [],
            }
        ]

        # Mock avis (no ratings)
        mongodb_service.avis_collection.find.return_value = []

        # WHEN: On appelle get_livre_with_episodes
        result = mongodb_service.get_livre_with_episodes(str(livre_id))

        # THEN: On reçoit le livre avec une liste d'émissions vide
        assert result is not None
        assert result["nombre_emissions"] == 0
        assert result["emissions"] == []

    def test_get_livre_with_episodes_uses_lookup_aggregation(self, mongodb_service):
        """Test que get_livre_with_episodes utilise une agrégation avec $lookup."""
        # GIVEN: Un livre avec des épisodes
        livre_id = str(ObjectId())
        mongodb_service.livres_collection.aggregate.return_value = []

        # WHEN: On appelle get_livre_with_episodes
        mongodb_service.get_livre_with_episodes(livre_id)

        # THEN: Une agrégation a été appelée sur la collection livres
        mongodb_service.livres_collection.aggregate.assert_called_once()
        pipeline = mongodb_service.livres_collection.aggregate.call_args[0][0]

        # Vérifier que le pipeline contient $match, $lookup pour auteur, et $lookup pour episodes
        assert any(stage.get("$match") for stage in pipeline)
        # Compter les $lookup (il devrait y en avoir 2: un pour auteur, un pour episodes)
        lookup_stages = [stage for stage in pipeline if "$lookup" in stage]
        assert len(lookup_stages) >= 2
