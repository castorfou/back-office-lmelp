"""Tests for auteur service in mongodb_service (Issue #96 - Phase 1)."""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


@pytest.fixture
def mongodb_service():
    """Create a MongoDBService instance with mocked collections."""
    service = MongoDBService()
    service.auteurs_collection = MagicMock()
    service.livres_collection = MagicMock()
    return service


class TestGetAuteurWithLivres:
    """Tests pour la méthode get_auteur_with_livres."""

    def test_get_auteur_with_livres_returns_author_with_books_sorted_alphabetically(
        self, mongodb_service
    ):
        """Test que get_auteur_with_livres retourne un auteur avec ses livres triés alphabétiquement."""
        # GIVEN: Un auteur avec plusieurs livres dans MongoDB
        auteur_id = ObjectId()
        livre1_id = ObjectId()
        livre2_id = ObjectId()
        livre3_id = ObjectId()

        # Mock de l'agrégation MongoDB
        mongodb_service.auteurs_collection.aggregate.return_value = [
            {
                "_id": auteur_id,
                "nom": "Emmanuel Carrère",
                "livres": [
                    {
                        "_id": livre2_id,
                        "titre": "Yoga",
                        "editeur": "P.O.L",
                    },
                    {
                        "_id": livre1_id,
                        "titre": "L'Adversaire",
                        "editeur": "Gallimard",
                    },
                    {
                        "_id": livre3_id,
                        "titre": "Limonov",
                        "editeur": "P.O.L",
                    },
                ],
            }
        ]

        # WHEN: On appelle get_auteur_with_livres
        result = mongodb_service.get_auteur_with_livres(str(auteur_id))

        # THEN: On reçoit l'auteur avec ses livres triés alphabétiquement
        assert result is not None
        assert result["auteur_id"] == str(auteur_id)
        assert result["nom"] == "Emmanuel Carrère"
        assert result["nombre_oeuvres"] == 3
        assert len(result["livres"]) == 3

        # Vérifier le tri alphabétique
        assert result["livres"][0]["titre"] == "L'Adversaire"
        assert result["livres"][1]["titre"] == "Limonov"
        assert result["livres"][2]["titre"] == "Yoga"

        # Vérifier que chaque livre a les bons champs
        for livre in result["livres"]:
            assert "livre_id" in livre
            assert "titre" in livre
            assert "editeur" in livre

    def test_get_auteur_with_livres_returns_none_when_not_found(self, mongodb_service):
        """Test que get_auteur_with_livres retourne None si l'auteur n'existe pas."""
        # GIVEN: Un auteur inexistant
        auteur_id = str(ObjectId())
        mongodb_service.auteurs_collection.aggregate.return_value = []

        # WHEN: On appelle get_auteur_with_livres
        result = mongodb_service.get_auteur_with_livres(auteur_id)

        # THEN: On reçoit None
        assert result is None

    def test_get_auteur_with_livres_returns_author_with_empty_books_list(
        self, mongodb_service
    ):
        """Test qu'un auteur sans livres retourne une liste vide."""
        # GIVEN: Un auteur sans livres
        auteur_id = ObjectId()
        mongodb_service.auteurs_collection.aggregate.return_value = [
            {
                "_id": auteur_id,
                "nom": "Nouvel Auteur",
                "livres": [],
            }
        ]

        # WHEN: On appelle get_auteur_with_livres
        result = mongodb_service.get_auteur_with_livres(str(auteur_id))

        # THEN: On reçoit l'auteur avec une liste de livres vide
        assert result is not None
        assert result["auteur_id"] == str(auteur_id)
        assert result["nom"] == "Nouvel Auteur"
        assert result["nombre_oeuvres"] == 0
        assert result["livres"] == []

    def test_get_auteur_with_livres_uses_lookup_aggregation(self, mongodb_service):
        """Test que get_auteur_with_livres utilise une agrégation $lookup correcte."""
        # GIVEN: Un auteur_id valide
        auteur_id = ObjectId()
        mongodb_service.auteurs_collection.aggregate.return_value = []

        # WHEN: On appelle get_auteur_with_livres
        mongodb_service.get_auteur_with_livres(str(auteur_id))

        # THEN: L'agrégation doit être appelée avec $match et $lookup
        mongodb_service.auteurs_collection.aggregate.assert_called_once()
        pipeline = mongodb_service.auteurs_collection.aggregate.call_args[0][0]

        # Vérifier que le pipeline contient $match, $lookup, et $project
        assert any("$match" in stage for stage in pipeline)
        assert any("$lookup" in stage for stage in pipeline)
        assert any("$project" in stage for stage in pipeline)
