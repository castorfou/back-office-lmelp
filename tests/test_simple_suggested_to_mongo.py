"""Test simple pour vérifier que mark_as_processed fonctionne bien."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from bson import ObjectId

from back_office_lmelp.services.livres_auteurs_cache_service import (
    LivresAuteursCacheService,
)


class TestSimpleSuggestedToMongo:
    """Tests simples pour vérifier mark_as_processed."""

    def test_mark_as_processed_sets_status_to_mongo(self):
        """Test unitaire simple: mark_as_processed doit mettre le statut à 'mongo'."""
        # Créer une instance du service avec un mock
        cache_service = LivresAuteursCacheService()

        # Mock de la collection MongoDB
        mock_collection = MagicMock()
        mock_collection.update_one.return_value.modified_count = 1

        # Mock du service MongoDB
        with patch.object(cache_service, "mongodb_service") as mock_mongodb_service:
            mock_mongodb_service.get_collection.return_value = mock_collection

            # Test data
            cache_id = ObjectId("68d3eb092f32bb8c43063f91")  # pragma: allowlist secret
            author_id = ObjectId("67a79b615b03b52d8c51db29")  # pragma: allowlist secret
            book_id = ObjectId("68d3eb092f32bb8c43063f76")  # pragma: allowlist secret

            # Act
            result = cache_service.mark_as_processed(cache_id, author_id, book_id)

            # Assert
            assert result is True

            # Vérifier l'appel update_one
            mock_collection.update_one.assert_called_once()
            call_args = mock_collection.update_one.call_args

            # Vérifier le filtre (premier argument)
            filter_arg = call_args[0][0]
            assert filter_arg == {"_id": cache_id}

            # Vérifier les données de mise à jour (second argument)
            update_arg = call_args[0][1]
            assert "$set" in update_arg
            set_fields = update_arg["$set"]

            # CRITICAL: Le statut doit être "mongo"
            assert set_fields["status"] == "mongo"
            assert set_fields["author_id"] == author_id
            assert set_fields["book_id"] == book_id
            assert "processed_at" in set_fields
            assert "updated_at" in set_fields
            assert isinstance(set_fields["processed_at"], datetime)
            assert isinstance(set_fields["updated_at"], datetime)

    def test_update_validation_status_to_mongo(self):
        """Test unitaire: update_validation_status avec statut 'mongo'."""
        # Créer une instance du service avec un mock
        cache_service = LivresAuteursCacheService()

        # Mock de la collection MongoDB
        mock_collection = MagicMock()
        mock_collection.update_one.return_value.modified_count = 1

        # Mock du service MongoDB
        with patch.object(cache_service, "mongodb_service") as mock_mongodb_service:
            mock_mongodb_service.get_collection.return_value = mock_collection

            # Test data
            cache_id = ObjectId("68d3eb092f32bb8c43063f91")  # pragma: allowlist secret
            status = "mongo"
            metadata = {
                "author_id": ObjectId(
                    "67a79b615b03b52d8c51db29"  # pragma: allowlist secret
                ),  # pragma: allowlist secret
                "book_id": ObjectId(
                    "68d3eb092f32bb8c43063f76"  # pragma: allowlist secret
                ),  # pragma: allowlist secret
            }

            # Act
            result = cache_service.update_validation_status(cache_id, status, metadata)

            # Assert
            assert result is True

            # Vérifier l'appel update_one
            mock_collection.update_one.assert_called_once()
            call_args = mock_collection.update_one.call_args

            # Vérifier le filtre
            filter_arg = call_args[0][0]
            assert filter_arg == {"_id": cache_id}

            # Vérifier les données de mise à jour
            update_arg = call_args[0][1]
            assert "$set" in update_arg
            set_fields = update_arg["$set"]

            # CRITICAL: Le statut doit être "mongo" et processed_at ajouté
            assert set_fields["status"] == "mongo"
            assert set_fields["author_id"] == metadata["author_id"]
            assert set_fields["book_id"] == metadata["book_id"]
            assert "processed_at" in set_fields  # Ajouté quand status == "mongo"
            assert "updated_at" in set_fields

    def test_update_validation_status_not_mongo_should_not_add_processed_at(self):
        """Test: update_validation_status avec statut autre que 'mongo' ne doit pas ajouter processed_at."""
        # Créer une instance du service avec un mock
        cache_service = LivresAuteursCacheService()

        # Mock de la collection MongoDB
        mock_collection = MagicMock()
        mock_collection.update_one.return_value.modified_count = 1

        # Mock du service MongoDB
        with patch.object(cache_service, "mongodb_service") as mock_mongodb_service:
            mock_mongodb_service.get_collection.return_value = mock_collection

            # Test data
            cache_id = ObjectId("68d3eb092f32bb8c43063f91")  # pragma: allowlist secret
            status = "suggested"  # Pas "mongo"
            metadata = {}

            # Act
            result = cache_service.update_validation_status(cache_id, status, metadata)

            # Assert
            assert result is True

            # Vérifier l'appel update_one
            call_args = mock_collection.update_one.call_args
            update_arg = call_args[0][1]
            set_fields = update_arg["$set"]

            # Le statut est bien "suggested"
            assert set_fields["status"] == "suggested"
            # Mais PAS de processed_at car status != "mongo"
            assert "processed_at" not in set_fields
            # Seulement updated_at
            assert "updated_at" in set_fields
