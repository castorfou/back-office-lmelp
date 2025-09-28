"""Tests TDD pour corriger les valeurs de statuts autorisées."""

from unittest.mock import patch

import pytest
from bson import ObjectId

from back_office_lmelp.services.livres_auteurs_cache_service import (
    LivresAuteursCacheService,
)


class TestCorrectStatusValues:
    """Tests TDD pour s'assurer que seuls les 4 statuts corrects sont autorisés."""

    def test_only_four_status_values_allowed(self):
        """Test TDD: Seuls not_found, suggested, verified, mongo sont autorisés."""
        # Les 4 statuts AUTORISÉS (selon specification utilisateur)
        allowed_statuses = ["not_found", "suggested", "verified", "mongo"]

        # Statuts INTERDITS (y compris l'ancien 'processed')
        forbidden_statuses = ["processed", "pending", "rejected", "error", "active"]

        avis_critique_id = ObjectId("68c718a16e51b9428ab88066")

        # Test avec chaque statut autorisé
        for status in allowed_statuses:
            book_data = {
                "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
                "auteur": "Test Author",
                "titre": "Test Title",
                "editeur": "Test Publisher",
                "programme": False,
                "status": status,
            }

            with patch(
                "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
            ) as mock_mongodb:
                mock_mongodb.get_collection.return_value.find_one.return_value = None
                mock_mongodb.get_collection.return_value.replace_one.return_value.upserted_id = ObjectId()

                service = LivresAuteursCacheService()
                # Doit réussir sans lever d'erreur
                result = service.create_cache_entry(avis_critique_id, book_data)
                assert result is not None

        # Test avec chaque statut interdit
        for status in forbidden_statuses:
            book_data = {
                "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
                "auteur": "Test Author",
                "titre": "Test Title",
                "editeur": "Test Publisher",
                "programme": False,
                "status": status,
            }

            with patch(
                "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
            ) as mock_mongodb:
                service = LivresAuteursCacheService()
                # Doit lever une erreur pour les statuts interdits
                with pytest.raises(ValueError, match=f"Statut invalide: {status}"):
                    service.create_cache_entry(avis_critique_id, book_data)

    def test_auto_processing_should_mark_as_mongo(self):
        """Test TDD: L'auto-processing doit marquer les livres comme 'mongo'."""
        cache_id = ObjectId("68d4c4859265d804e509db57")
        author_id = ObjectId("67a79b615b03b52d8c51db29")
        book_id = ObjectId("68d3ed1fad794a968c14f921")

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.update_one.return_value.modified_count = 1

            service = LivresAuteursCacheService()
            result = service.mark_as_processed(cache_id, author_id, book_id)

            # Vérifier que le statut est mis à 'mongo' (pas 'processed')
            update_call = mock_mongodb.get_collection.return_value.update_one.call_args
            update_fields = update_call[0][1]["$set"]

            assert (
                update_fields["status"] == "mongo"
            )  # CORRECTION : mongo au lieu de processed
            assert update_fields["author_id"] == author_id
            assert update_fields["book_id"] == book_id
            assert "processed_at" in update_fields
            assert result is True

    def test_statistics_should_count_mongo_as_couples_en_base(self):
        """Test TDD: Les statistiques doivent compter 'mongo' comme couples_en_base."""
        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            # Mock des données de cache avec différents statuts
            mock_mongodb.get_collection.return_value.aggregate.return_value = [
                {"_id": "mongo", "count": 5},  # Livres en base
                {"_id": "verified", "count": 3},  # Livres vérifiés
                {"_id": "suggested", "count": 2},  # Livres suggérés
                {"_id": "not_found", "count": 1},  # Livres non trouvés
            ]

            # Mock pour untreated count
            mock_mongodb.get_collection.return_value.count_documents.return_value = 100
            mock_mongodb.get_collection.return_value.distinct.return_value = [
                "id1",
                "id2",
            ]

            service = LivresAuteursCacheService()
            stats = service.get_statistics_from_cache()

            # Vérifier que 'mongo' est compté comme couples_en_base
            assert stats["couples_en_base"] == 5  # Statut 'mongo'
            assert stats["couples_verified_pas_en_base"] == 3
            assert stats["couples_suggested_pas_en_base"] == 2
            assert stats["couples_not_found_pas_en_base"] == 1

    def test_update_validation_status_should_accept_mongo(self):
        """Test TDD: update_validation_status doit accepter le statut 'mongo'."""
        cache_id = ObjectId("68d4c4859265d804e509db57")

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.update_one.return_value.modified_count = 1

            service = LivresAuteursCacheService()
            metadata = {"author_id": ObjectId(), "book_id": ObjectId()}

            # Doit réussir avec le statut 'mongo'
            result = service.update_validation_status(cache_id, "mongo", metadata)

            assert result is True
            update_call = mock_mongodb.get_collection.return_value.update_one.call_args
            update_fields = update_call[0][1]["$set"]
            assert update_fields["status"] == "mongo"
