"""Test pour vérifier le bug des épisodes manquants dans livres.episodes array."""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


class TestLivreEpisodesArrayBug:
    """Tests pour le bug où les épisodes ne sont pas ajoutés à livre.episodes."""

    @pytest.fixture
    def mongodb_service(self):
        """Create a MongoDBService with mocked collections."""
        service = MongoDBService()
        service.livres_collection = MagicMock()
        service.auteurs_collection = MagicMock()
        # Issue #189: editeurs_collection needed for get_or_create_editeur
        mock_editeurs = MagicMock()
        mock_editeurs.find.return_value = [
            {"_id": ObjectId(), "nom": "Gallimard"},
        ]
        service.editeurs_collection = mock_editeurs
        return service

    def test_create_book_if_not_exists_should_add_episode_to_existing_book(
        self, mongodb_service
    ):
        """Test que create_book_if_not_exists ajoute l'épisode quand le livre existe déjà."""
        # GIVEN: Un livre qui existe déjà avec un épisode
        existing_livre_id = ObjectId()
        existing_author_id = ObjectId()
        existing_episode_id = "68ab04b92dc760119d18f8ef"  # Premier épisode
        new_episode_id = "68ffdb9387a20121a7e1775b"  # Nouvel épisode

        # Mock: Le livre existe déjà avec le premier épisode
        mongodb_service.livres_collection.find.return_value = [
            {
                "_id": existing_livre_id,
                "titre": "La Collision",
                "auteur_id": existing_author_id,
                "editeur": "Gallimard",
                "episodes": [existing_episode_id],  # Un seul épisode
            }
        ]

        # Mock: Les update réussissent
        mongodb_service.livres_collection.update_one.return_value = MagicMock(
            modified_count=1
        )

        # WHEN: On appelle create_book_if_not_exists avec un nouvel épisode
        book_data = {
            "titre": "La Collision",
            "auteur_id": existing_author_id,
            "editeur": "Gallimard",
            "episodes": [new_episode_id],  # Nouvel épisode différent
            "avis_critiques": ["some_avis_id"],
        }

        book_id = mongodb_service.create_book_if_not_exists(book_data)

        # THEN: Le livre existant devrait être retourné
        assert book_id == existing_livre_id

        # PROBLÈME ATTENDU: Vérifier si update_one a été appelé pour ajouter l'épisode
        print(
            f"\n🔍 update_one appelé: {mongodb_service.livres_collection.update_one.called}"
        )
        print(
            f"🔍 Nombre d'appels à update_one: {mongodb_service.livres_collection.update_one.call_count}"
        )

        if mongodb_service.livres_collection.update_one.called:
            # Si update_one a été appelé, vérifier les arguments
            for (
                call_args
            ) in mongodb_service.livres_collection.update_one.call_args_list:
                filter_arg = call_args[0][0]
                update_arg = call_args[0][1]
                print(f"🔍 Filter: {filter_arg}")
                print(f"🔍 Update: {update_arg}")

                # Vérifier si $addToSet est utilisé pour les épisodes
                if "$addToSet" in update_arg and "episodes" in update_arg["$addToSet"]:
                    print(
                        f"✅ $addToSet utilisé pour episodes: {update_arg['$addToSet']['episodes']}"
                    )
                    episodes_update = update_arg["$addToSet"]["episodes"]
                    # Vérifier le format $each
                    assert "$each" in episodes_update, (
                        "Le format devrait utiliser $each"
                    )
                    assert new_episode_id in episodes_update["$each"], (
                        f"L'épisode {new_episode_id} devrait être dans la liste $each"
                    )
                    return  # Test passé

        # Si on arrive ici, le bug existe: l'épisode n'est pas ajouté
        print(
            f"❌ BUG CONFIRMÉ: L'épisode {new_episode_id} n'est PAS ajouté à episodes array!"
        )
        print(
            "   Le livre existant est retourné SANS ajouter le nouvel épisode à son array."
        )

        # Faire échouer le test pour confirmer le bug
        raise AssertionError(
            "BUG: create_book_if_not_exists ne met pas à jour episodes array pour un livre existant!"
        )

    def test_create_book_if_not_exists_should_not_create_duplicate_episodes(
        self, mongodb_service
    ):
        """Test que create_book_if_not_exists n'ajoute pas de doublon si l'épisode existe déjà."""
        # GIVEN: Un livre qui existe déjà avec 2 épisodes
        existing_livre_id = ObjectId()
        existing_author_id = ObjectId()
        episode1_id = "68ab04b92dc760119d18f8ef"
        episode2_id = "68ffdb9387a20121a7e1775b"

        # Mock: Le livre existe déjà avec 2 épisodes
        mongodb_service.livres_collection.find.return_value = [
            {
                "_id": existing_livre_id,
                "titre": "La Collision",
                "auteur_id": existing_author_id,
                "editeur": "Gallimard",
                "episodes": [episode1_id, episode2_id],  # 2 épisodes
            }
        ]

        # Mock: Les update réussissent
        mongodb_service.livres_collection.update_one.return_value = MagicMock(
            modified_count=1
        )

        # WHEN: On revalide le livre dans un épisode déjà existant
        book_data = {
            "titre": "La Collision",
            "auteur_id": existing_author_id,
            "editeur": "Gallimard",
            "episodes": [episode1_id],  # Même épisode que celui déjà présent
            "avis_critiques": ["some_avis_id"],
        }

        book_id = mongodb_service.create_book_if_not_exists(book_data)

        # THEN: Le livre existant devrait être retourné
        assert book_id == existing_livre_id

        # Vérifier que update_one a été appelé
        assert mongodb_service.livres_collection.update_one.called

        # Récupérer l'appel pour vérifier le $addToSet
        update_call = mongodb_service.livres_collection.update_one.call_args
        update_arg = update_call[0][1]

        print(f"\n🔍 Update argument: {update_arg}")

        # Vérifier que $addToSet est utilisé (pas $push qui créerait un doublon)
        assert "$addToSet" in update_arg, (
            "$addToSet devrait être utilisé pour éviter les doublons"
        )

        # Vérifier que $each est utilisé pour ajouter plusieurs éléments
        if "episodes" in update_arg.get("$addToSet", {}):
            episodes_update = update_arg["$addToSet"]["episodes"]
            assert "$each" in episodes_update, (
                "$each devrait être utilisé avec $addToSet"
            )
            assert episode1_id in episodes_update["$each"], (
                "L'épisode devrait être dans la liste $each"
            )
            print(
                "✅ $addToSet avec $each utilisé - MongoDB évitera automatiquement le doublon"
            )
