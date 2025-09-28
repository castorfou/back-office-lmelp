"""Tests TDD pour la méthode get_books_by_validation_status."""

from unittest.mock import patch

from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


class TestMongoDBGetBooksByValidationStatus:
    """Tests TDD pour la méthode get_books_by_validation_status."""

    def test_get_books_by_validation_status_should_return_mongo_books(self):
        """Test TDD: La méthode doit retourner les livres avec validation_status=mongo."""
        mock_mongo_books = [
            {
                "_id": ObjectId("64f440010000000000000001"),
                "auteur": "Albert Camus",
                "titre": "L'Étranger",
                "validation_status": "mongo",
                "biblio_verification_status": "verified",
                "author_id": "123",
                "book_id": "456",
            },
            {
                "_id": ObjectId("64f440010000000000000002"),
                "auteur": "Victor Hugo",
                "titre": "Les Misérables",
                "validation_status": "mongo",
                "biblio_verification_status": "verified",
                "author_id": "789",
                "book_id": "101",
            },
        ]

        with patch.object(MongoDBService, "get_collection") as mock_get_collection:
            mock_get_collection.return_value.find.return_value = mock_mongo_books

            # Act
            mongodb_service = MongoDBService()
            result = mongodb_service.get_books_by_validation_status("mongo")

            # Assert
            assert result == mock_mongo_books
            mock_get_collection.assert_called_once_with("livresauteurs_cache")
            mock_get_collection.return_value.find.assert_called_once_with(
                {"validation_status": "mongo"}
            )

    def test_get_books_by_validation_status_should_return_pending_books(self):
        """Test TDD: La méthode doit retourner les livres avec validation_status=pending."""
        mock_pending_books = [
            {
                "_id": ObjectId("64f440010000000000000003"),
                "auteur": "Laurent Mauvignier",
                "titre": "La Maison Vide",
                "validation_status": "pending",
                "biblio_verification_status": "verified",
            },
            {
                "_id": ObjectId("64f440010000000000000004"),
                "auteur": "Yakuta Ali Kavazovic",
                "titre": "Au Grand Jamais",
                "validation_status": "pending",
                "biblio_verification_status": "not_found",
            },
        ]

        with patch.object(MongoDBService, "get_collection") as mock_get_collection:
            mock_get_collection.return_value.find.return_value = mock_pending_books

            # Act
            mongodb_service = MongoDBService()
            result = mongodb_service.get_books_by_validation_status("pending")

            # Assert
            assert result == mock_pending_books
            mock_get_collection.assert_called_once_with("livresauteurs_cache")
            mock_get_collection.return_value.find.assert_called_once_with(
                {"validation_status": "pending"}
            )

    def test_get_books_by_validation_status_should_return_verified_books(self):
        """Test TDD: La méthode doit retourner les livres pending avec biblio_verification_status=verified."""
        mock_verified_books = [
            {
                "_id": ObjectId("64f440010000000000000005"),
                "auteur": "Laurent Mauvignier",
                "titre": "La Maison Vide",
                "validation_status": "pending",
                "biblio_verification_status": "verified",
            }
        ]

        with patch.object(MongoDBService, "get_collection") as mock_get_collection:
            mock_get_collection.return_value.find.return_value = mock_verified_books

            # Act
            mongodb_service = MongoDBService()
            result = mongodb_service.get_books_by_validation_status("verified")

            # Assert
            assert result == mock_verified_books
            mock_get_collection.assert_called_once_with("livresauteurs_cache")
            mock_get_collection.return_value.find.assert_called_once_with(
                {
                    "validation_status": "pending",
                    "biblio_verification_status": "verified",
                }
            )

    def test_get_books_by_validation_status_should_return_suggested_books(self):
        """Test TDD: La méthode doit retourner les livres pending avec biblio_verification_status=suggested."""
        mock_suggested_books = [
            {
                "_id": ObjectId("64f440010000000000000006"),
                "auteur": "Marguerite Duras",
                "titre": "L'Amant",
                "validation_status": "pending",
                "biblio_verification_status": "suggested",
            }
        ]

        with patch.object(MongoDBService, "get_collection") as mock_get_collection:
            mock_get_collection.return_value.find.return_value = mock_suggested_books

            # Act
            mongodb_service = MongoDBService()
            result = mongodb_service.get_books_by_validation_status("suggested")

            # Assert
            assert result == mock_suggested_books
            mock_get_collection.assert_called_once_with("livresauteurs_cache")
            mock_get_collection.return_value.find.assert_called_once_with(
                {
                    "validation_status": "pending",
                    "biblio_verification_status": "suggested",
                }
            )

    def test_get_books_by_validation_status_should_return_not_found_books(self):
        """Test TDD: La méthode doit retourner les livres pending avec biblio_verification_status=not_found."""
        mock_not_found_books = [
            {
                "_id": ObjectId("64f440010000000000000007"),
                "auteur": "Yakuta Ali Kavazovic",
                "titre": "Au Grand Jamais",
                "validation_status": "pending",
                "biblio_verification_status": "not_found",
            }
        ]

        with patch.object(MongoDBService, "get_collection") as mock_get_collection:
            mock_get_collection.return_value.find.return_value = mock_not_found_books

            # Act
            mongodb_service = MongoDBService()
            result = mongodb_service.get_books_by_validation_status("not_found")

            # Assert
            assert result == mock_not_found_books
            mock_get_collection.assert_called_once_with("livresauteurs_cache")
            mock_get_collection.return_value.find.assert_called_once_with(
                {
                    "validation_status": "pending",
                    "biblio_verification_status": "not_found",
                }
            )

    def test_get_books_by_validation_status_should_return_rejected_books(self):
        """Test TDD: La méthode doit retourner les livres avec validation_status=rejected."""
        mock_rejected_books = []

        with patch.object(MongoDBService, "get_collection") as mock_get_collection:
            mock_get_collection.return_value.find.return_value = mock_rejected_books

            # Act
            mongodb_service = MongoDBService()
            result = mongodb_service.get_books_by_validation_status("rejected")

            # Assert
            assert result == mock_rejected_books
            mock_get_collection.assert_called_once_with("livresauteurs_cache")
            mock_get_collection.return_value.find.assert_called_once_with(
                {"validation_status": "rejected"}
            )

    def test_get_books_by_validation_status_should_handle_unknown_status(self):
        """Test TDD: La méthode doit gérer les statuts inconnus en retournant une liste vide."""
        with patch.object(MongoDBService, "get_collection") as mock_get_collection:
            mock_get_collection.return_value.find.return_value = []

            # Act
            mongodb_service = MongoDBService()
            result = mongodb_service.get_books_by_validation_status("unknown_status")

            # Assert
            assert result == []
            mock_get_collection.assert_called_once_with("livresauteurs_cache")
            mock_get_collection.return_value.find.assert_called_once_with(
                {"validation_status": "unknown_status"}
            )

    def test_get_books_by_validation_status_should_convert_objectid_to_string(self):
        """Test TDD: La méthode doit convertir les ObjectId en string pour la sérialisation."""
        mock_books_with_objectid = [
            {
                "_id": ObjectId("64f440010000000000000008"),
                "auteur": "Test Author",
                "titre": "Test Book",
                "validation_status": "mongo",
                "episode_oid": ObjectId("64f440010000000000000009"),
            }
        ]

        expected_books = [
            {
                "_id": "64f440010000000000000008",
                "auteur": "Test Author",
                "titre": "Test Book",
                "validation_status": "mongo",
                "episode_oid": "64f440010000000000000009",
            }
        ]

        with patch.object(MongoDBService, "get_collection") as mock_get_collection:
            mock_get_collection.return_value.find.return_value = (
                mock_books_with_objectid
            )

            # Act
            mongodb_service = MongoDBService()
            result = mongodb_service.get_books_by_validation_status("mongo")

            # Assert
            assert result == expected_books
