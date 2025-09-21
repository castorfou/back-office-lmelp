"""Tests TDD pour le service de gestion des collections auteurs/livres (Issue #66)."""

from unittest.mock import patch

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


class TestCollectionsManagementService:
    """Tests pour le service de gestion automatique des collections auteurs/livres."""

    def test_service_exists_and_can_be_imported(self):
        """Test que le service existe et peut être importé."""
        # Ce test échouera initialement - nous devons créer le service
        assert CollectionsManagementService is not None

    def test_get_statistics_for_livres_auteurs_page(self):
        """Test récupération des statistiques pour la page livres-auteurs."""
        service = CollectionsManagementService()

        # Mock des données de test
        with patch.object(service, "mongodb_service") as mock_mongodb:
            # Setup mock responses
            mock_mongodb.get_verified_books_not_in_collections.return_value = 15
            mock_mongodb.get_suggested_books_not_in_collections.return_value = 8
            mock_mongodb.get_not_found_books_not_in_collections.return_value = 12
            mock_mongodb.get_books_in_collections_count.return_value = 45
            mock_mongodb.get_untreated_episodes_count.return_value = 3

            stats = service.get_statistics()

            # Vérifier la structure des statistiques retournées
            assert isinstance(stats, dict)
            assert "episodes_non_traites" in stats
            assert "couples_en_base" in stats
            assert "couples_verified_pas_en_base" in stats
            assert "couples_suggested_pas_en_base" in stats
            assert "couples_not_found_pas_en_base" in stats

            # Vérifier les valeurs
            assert stats["episodes_non_traites"] == 3
            assert stats["couples_en_base"] == 45
            assert stats["couples_verified_pas_en_base"] == 15
            assert stats["couples_suggested_pas_en_base"] == 8
            assert stats["couples_not_found_pas_en_base"] == 12

    def test_auto_process_verified_books(self):
        """Test traitement automatique des livres 'verified'."""
        service = CollectionsManagementService()

        # Mock des livres verified à traiter
        verified_books = [
            {
                "auteur": "Michel Houellebecq",
                "titre": "Les Particules élémentaires",
                "editeur": "Flammarion",
                "episode_id": "64f1234567890abcdef12345",  # pragma: allowlist secret
                "validation_status": "verified",
            },
            {
                "auteur": "Emmanuel Carrère",
                "titre": "Kolkhoze",
                "editeur": "POL",
                "episode_id": "64f1234567890abcdef12346",
                "validation_status": "verified",
            },
        ]

        with patch.object(service, "mongodb_service") as mock_mongodb:
            mock_mongodb.get_verified_books_not_in_collections.return_value = (
                verified_books
            )
            mock_mongodb.create_author_if_not_exists.return_value = ObjectId(
                "64f1234567890abcdef11111"  # pragma: allowlist secret
            )
            mock_mongodb.create_book_if_not_exists.return_value = ObjectId(
                "64f1234567890abcdef22222"  # pragma: allowlist secret
            )

            result = service.auto_process_verified_books()

            # Vérifier que le service a traité les livres
            assert isinstance(result, dict)
            assert "processed_count" in result
            assert "created_authors" in result
            assert "created_books" in result
            assert result["processed_count"] == 2

            # Vérifier que les méthodes de création ont été appelées
            assert mock_mongodb.create_author_if_not_exists.call_count == 2
            assert mock_mongodb.create_book_if_not_exists.call_count == 2

    def test_get_books_by_validation_status(self):
        """Test récupération des livres par statut de validation."""
        service = CollectionsManagementService()

        with patch.object(service, "mongodb_service") as mock_mongodb:
            mock_books = [
                {
                    "auteur": "Test Author",
                    "titre": "Test Book",
                    "validation_status": "suggested",
                    "suggested_author": "Corrected Author",
                    "suggested_title": "Corrected Title",
                }
            ]
            mock_mongodb.get_books_by_validation_status.return_value = mock_books

            # Test récupération des livres 'suggested'
            suggested_books = service.get_books_by_validation_status("suggested")

            assert isinstance(suggested_books, list)
            assert len(suggested_books) == 1
            assert suggested_books[0]["validation_status"] == "suggested"
            mock_mongodb.get_books_by_validation_status.assert_called_with("suggested")

    def test_manually_validate_suggestion(self):
        """Test validation manuelle d'une suggestion."""
        service = CollectionsManagementService()

        book_data = {
            "id": "64f1234567890abcdef12345",  # pragma: allowlist secret
            "auteur": "Test Author",
            "titre": "Test Book",
            "user_validated_author": "Corrected Author",
            "user_validated_title": "Corrected Title",
        }

        with patch.object(service, "mongodb_service") as mock_mongodb:
            mock_mongodb.update_book_validation.return_value = True
            mock_mongodb.create_author_if_not_exists.return_value = ObjectId(
                "64f1234567890abcdef11111"  # pragma: allowlist secret
            )
            mock_mongodb.create_book_if_not_exists.return_value = ObjectId(
                "64f1234567890abcdef22222"  # pragma: allowlist secret
            )

            result = service.manually_validate_suggestion(book_data)

            assert isinstance(result, dict)
            assert "success" in result
            assert result["success"] is True
            assert "author_id" in result
            assert "book_id" in result

    def test_manually_add_not_found_book(self):
        """Test ajout manuel d'un livre 'not_found'."""
        service = CollectionsManagementService()

        book_data = {
            "id": "64f1234567890abcdef12345",  # pragma: allowlist secret
            "user_entered_author": "New Author",
            "user_entered_title": "New Title",
            "user_entered_publisher": "New Publisher",
        }

        with patch.object(service, "mongodb_service") as mock_mongodb:
            mock_mongodb.create_author_if_not_exists.return_value = ObjectId(
                "64f1234567890abcdef11111"  # pragma: allowlist secret
            )
            mock_mongodb.create_book_if_not_exists.return_value = ObjectId(
                "64f1234567890abcdef22222"  # pragma: allowlist secret
            )
            mock_mongodb.update_book_validation.return_value = True

            result = service.manually_add_not_found_book(book_data)

            assert isinstance(result, dict)
            assert "success" in result
            assert result["success"] is True
            assert "author_id" in result
            assert "book_id" in result
