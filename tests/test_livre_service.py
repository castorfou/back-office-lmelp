"""Tests for get_livre_with_episodes() service method (Issue #96 - Phase 2)."""

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
    return service


class TestGetLivreWithEpisodes:
    """Tests pour la méthode get_livre_with_episodes()."""

    def test_get_livre_with_episodes_returns_book_with_episodes_sorted_by_date(
        self, mongodb_service
    ):
        """Test que get_livre_with_episodes retourne un livre avec ses épisodes triés par date."""
        # GIVEN: Un livre avec plusieurs épisodes en base
        livre_id = ObjectId()
        auteur_id = ObjectId()
        episode1_id = ObjectId()
        episode2_id = ObjectId()
        episode3_id = ObjectId()

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

        # WHEN: On appelle get_livre_with_episodes
        result = mongodb_service.get_livre_with_episodes(str(livre_id))

        # THEN: On reçoit le livre avec ses épisodes triés par date (plus récent d'abord)
        assert result is not None
        assert result["livre_id"] == str(livre_id)
        assert result["titre"] == "L'Adversaire"
        assert result["auteur_nom"] == "Emmanuel Carrère"
        assert result["auteur_id"] == str(auteur_id)
        assert result["editeur"] == "Gallimard"
        assert result["nombre_episodes"] == 3

        # Vérifier que les épisodes sont triés par date (plus récent d'abord)
        assert len(result["episodes"]) == 3
        assert result["episodes"][0]["date"] == "2000-12-20"
        assert result["episodes"][1]["date"] == "2000-09-15"
        assert result["episodes"][2]["date"] == "2000-03-12"

        # Vérifier que chaque épisode a les bons champs
        for episode in result["episodes"]:
            assert "episode_id" in episode
            assert "titre" in episode
            assert "date" in episode
            assert "programme" in episode

    def test_get_livre_with_episodes_returns_none_when_not_found(self, mongodb_service):
        """Test que get_livre_with_episodes retourne None si le livre n'existe pas."""
        # GIVEN: Un livre inexistant
        livre_id = str(ObjectId())
        mongodb_service.livres_collection.aggregate.return_value = []

        # WHEN: On appelle get_livre_with_episodes
        result = mongodb_service.get_livre_with_episodes(livre_id)

        # THEN: On reçoit None
        assert result is None

    def test_get_livre_with_episodes_returns_book_with_empty_episodes_list(
        self, mongodb_service
    ):
        """Test qu'un livre sans épisodes retourne une liste d'épisodes vide."""
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

        # WHEN: On appelle get_livre_with_episodes
        result = mongodb_service.get_livre_with_episodes(str(livre_id))

        # THEN: On reçoit le livre avec une liste d'épisodes vide
        assert result is not None
        assert result["nombre_episodes"] == 0
        assert result["episodes"] == []

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
