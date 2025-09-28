"""Tests TDD pour garantir l'unicité dans le cache livres/auteurs."""

from datetime import datetime
from unittest.mock import patch

from bson import ObjectId

from back_office_lmelp.services.livres_auteurs_cache_service import (
    LivresAuteursCacheService,
)


class TestCacheUniquenessConstraint:
    """Tests TDD pour l'unicité dans le cache."""

    def test_create_cache_entry_should_not_create_duplicates(self):
        """Test TDD: create_cache_entry ne doit pas créer de doublons."""
        avis_critique_id = ObjectId("686d794675251909f6024300")
        book_data = {
            "episode_oid": "678cce7aa414f229887780d3",  # pragma: allowlist secret
            "auteur": "Philippe Solers",
            "titre": "La deuxième vie",
            "editeur": "Gallimard",
            "programme": False,
            "status": "suggested",
        }

        existing_entry = {
            "_id": ObjectId("68d4bfe7bccfe76bb00681ea"),
            "avis_critique_id": avis_critique_id,
            "auteur": "Philippe Solers",
            "titre": "La deuxième vie",
            "status": "suggested",
        }

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            # Simuler qu'un document existe déjà
            mock_mongodb.get_collection.return_value.find_one.return_value = (
                existing_entry
            )
            mock_mongodb.get_collection.return_value.replace_one.return_value.upserted_id = None
            mock_mongodb.get_collection.return_value.replace_one.return_value.modified_count = 1

            # Act
            cache_service = LivresAuteursCacheService()
            result_id = cache_service.create_cache_entry(avis_critique_id, book_data)

            # Assert - Doit faire un upsert au lieu d'un insert
            mock_mongodb.get_collection.return_value.find_one.assert_called_once()
            mock_mongodb.get_collection.return_value.replace_one.assert_called_once()
            # Ne doit PAS appeler insert_one
            mock_mongodb.get_collection.return_value.insert_one.assert_not_called()

            # Doit retourner l'ID existant
            assert result_id == existing_entry["_id"]

    def test_create_cache_entry_should_insert_new_unique_entry(self):
        """Test TDD: create_cache_entry doit insérer une nouvelle entrée si elle n'existe pas."""
        avis_critique_id = ObjectId("686d794675251909f6024300")
        book_data = {
            "episode_oid": "678cce7aa414f229887780d3",  # pragma: allowlist secret
            "auteur": "Denis Infante",
            "titre": "Rousse",
            "editeur": "Tristram",
            "programme": False,
            "status": "verified",
        }

        new_id = ObjectId("68d4bfe7bccfe76bb00681eb")

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            # Simuler qu'aucun document n'existe
            mock_mongodb.get_collection.return_value.find_one.return_value = None
            mock_mongodb.get_collection.return_value.replace_one.return_value.upserted_id = new_id
            mock_mongodb.get_collection.return_value.replace_one.return_value.modified_count = 0

            # Act
            cache_service = LivresAuteursCacheService()
            result_id = cache_service.create_cache_entry(avis_critique_id, book_data)

            # Assert - Doit faire un upsert qui crée un nouveau document
            mock_mongodb.get_collection.return_value.find_one.assert_called_once()
            mock_mongodb.get_collection.return_value.replace_one.assert_called_once()

            # Doit retourner le nouvel ID
            assert result_id == new_id

    def test_create_cache_entry_should_use_correct_uniqueness_filter(self):
        """Test TDD: create_cache_entry doit utiliser le bon filtre d'unicité."""
        avis_critique_id = ObjectId("686d794675251909f6024300")
        book_data = {
            "episode_oid": "678cce7aa414f229887780d3",  # pragma: allowlist secret
            "auteur": "Philippe Solers",
            "titre": "La deuxième vie",
            "editeur": "Gallimard",
            "programme": False,
            "status": "not_found",
        }

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.find_one.return_value = None
            mock_mongodb.get_collection.return_value.replace_one.return_value.upserted_id = ObjectId()

            # Act
            cache_service = LivresAuteursCacheService()
            cache_service.create_cache_entry(avis_critique_id, book_data)

            # Assert - Doit chercher avec le bon filtre d'unicité
            expected_filter = {
                "avis_critique_id": avis_critique_id,
                "auteur": "Philippe Solers",
                "titre": "La deuxième vie",
            }
            mock_mongodb.get_collection.return_value.find_one.assert_called_with(
                expected_filter
            )

            # Le replace_one doit utiliser le même filtre
            replace_call = (
                mock_mongodb.get_collection.return_value.replace_one.call_args
            )
            assert replace_call[0][0] == expected_filter  # Premier argument = filtre

    def test_create_cache_entry_should_preserve_important_fields_on_update(self):
        """Test TDD: create_cache_entry doit préserver les champs importants lors d'une mise à jour."""
        avis_critique_id = ObjectId("686d794675251909f6024300")
        book_data = {
            "episode_oid": "678cce7aa414f229887780d3",  # pragma: allowlist secret
            "auteur": "Philippe Solers",
            "titre": "La deuxième vie",
            "editeur": "Gallimard",
            "programme": False,
            "status": "verified",  # Nouveau statut
        }

        existing_entry = {
            "_id": ObjectId("68d4bfe7bccfe76bb00681ea"),
            "avis_critique_id": avis_critique_id,
            "auteur": "Philippe Solers",
            "titre": "La deuxième vie",
            "status": "mongo",  # Statut existant important à préserver
            "author_id": "123",  # ID existant à préserver
            "book_id": "456",  # ID existant à préserver
            "created_at": datetime(2025, 9, 24, 10, 0, 0),  # Date existante à préserver
        }

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.find_one.return_value = (
                existing_entry
            )
            mock_mongodb.get_collection.return_value.replace_one.return_value.modified_count = 1

            # Act
            cache_service = LivresAuteursCacheService()
            cache_service.create_cache_entry(avis_critique_id, book_data)

            # Assert - Vérifier que les champs importants sont préservés
            replace_call = (
                mock_mongodb.get_collection.return_value.replace_one.call_args
            )
            updated_document = replace_call[0][
                1
            ]  # Deuxième argument = document de remplacement

            # Champs qui DOIVENT être préservés quand le statut est déjà "mongo"
            # Si l'entrée existante a déjà le statut "mongo", elle ne doit pas changer
            # Sinon, le nouveau statut doit être appliqué
            if existing_entry["status"] == "mongo":
                assert updated_document["status"] == "mongo"  # Préserver mongo
            else:
                assert updated_document["status"] == "verified"  # Nouveau statut

            assert updated_document["author_id"] == "123"
            assert updated_document["book_id"] == "456"
            assert updated_document["created_at"] == existing_entry["created_at"]

            # Champs qui PEUVENT être mis à jour
            assert "updated_at" in updated_document

    def test_get_books_by_avis_critique_id_should_return_unique_books(self):
        """Test TDD: get_books_by_avis_critique_id ne doit retourner que des livres uniques."""
        avis_critique_id = ObjectId("686d794675251909f6024300")

        # Simuler des doublons dans la base (ne devrait pas arriver avec notre fix)
        mock_books = [
            {
                "_id": ObjectId("68d4bfe7bccfe76bb00681ea"),
                "avis_critique_id": avis_critique_id,
                "auteur": "Philippe Solers",
                "titre": "La deuxième vie",
            }
        ]

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.find.return_value = mock_books

            # Act
            cache_service = LivresAuteursCacheService()
            result = cache_service.get_books_by_avis_critique_id(avis_critique_id)

            # Assert - Doit retourner des livres uniques
            assert len(result) == 1
            assert result[0]["auteur"] == "Philippe Solers"
