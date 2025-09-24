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
                "episode_oid": "64f1234567890abcdef12345",  # pragma: allowlist secret
                "validation_status": "verified",
            },
            {
                "auteur": "Emmanuel Carrère",
                "titre": "Kolkhoze",
                "editeur": "POL",
                "episode_oid": "64f1234567890abcdef12346",  # pragma: allowlist secret
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

    def test_get_verified_books_not_in_collections_calls_extraction_service(self):
        """Test TDD: get_verified_books_not_in_collections doit utiliser le service d'extraction."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        # Créer une instance réelle du service MongoDB
        mongodb_service = MongoDBService()

        # Mock du service d'extraction existant
        with patch(
            "back_office_lmelp.services.books_extraction_service.books_extraction_service"
        ) as mock_extraction:
            # Mock des livres extraits (comme l'API /livres-auteurs)
            mock_extracted_books = [
                {
                    "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
                    "auteur": "Maria Pourchet",
                    "titre": "Tressaillir",
                    "editeur": "Stock",
                    "programme": True,
                }
            ]

            # Mock de la fonction async
            async def mock_async_extraction(reviews):
                return mock_extracted_books

            mock_extraction.extract_books_from_reviews = mock_async_extraction

            # Mock du service Babelio (retourne verified)
            with patch(
                "back_office_lmelp.services.babelio_service.babelio_service"
            ) as mock_babelio:
                mock_babelio.verify_author.return_value = {"status": "verified"}

                # Mock des collections MongoDB
                with patch.object(
                    mongodb_service, "get_all_critical_reviews"
                ) as mock_reviews:
                    mock_reviews.return_value = [{"summary": "test"}]

                    with patch.object(
                        mongodb_service, "auteurs_collection"
                    ) as mock_auteurs:
                        mock_auteurs.find_one.return_value = None  # Auteur pas en base

                        with patch.object(
                            mongodb_service, "livres_collection"
                        ) as mock_livres:
                            mock_livres.find_one.return_value = (
                                None  # Livre pas en base
                            )

                            # Act
                            result = (
                                mongodb_service.get_verified_books_not_in_collections()
                            )

                            # Assert - Maria Pourchet verified devrait être retournée
                            assert isinstance(result, list)
                            assert len(result) > 0
                            assert result[0]["auteur"] == "Maria Pourchet"
                            assert (
                                result[0]["babelio_verification_status"] == "verified"
                            )

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

    def test_auto_process_links_books_to_critical_reviews(self):
        """Test TDD: l'auto-processing doit lier les livres aux avis critiques correspondants."""
        service = CollectionsManagementService()

        # Mock des livres verified avec episode_oid
        verified_books = [
            {
                "auteur": "Maria Pourchet",
                "titre": "Tressaillir",
                "editeur": "Stock",
                "episode_oid": "68c707ad6e51b9428ab87e9e",  # Episode du 14/09  # pragma: allowlist secret
                "validation_status": "verified",
            }
        ]

        # Mock de l'avis critique correspondant
        mock_critical_review = {
            "_id": ObjectId("68c718a16e51b9428ab88066"),  # pragma: allowlist secret
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "summary": "...Maria Pourchet | Tressaillir | Stock...",
        }

        with patch.object(service, "mongodb_service") as mock_mongodb:
            # Mock des méthodes existantes
            mock_mongodb.get_verified_books_not_in_collections.return_value = (
                verified_books
            )
            mock_mongodb.create_author_if_not_exists.return_value = ObjectId(
                "67a79b615b03b52d8c51db29"  # ID existant de Maria Pourchet  # pragma: allowlist secret
            )
            mock_mongodb.create_book_if_not_exists.return_value = ObjectId(
                "68d3eb092f32bb8c43063f76"  # pragma: allowlist secret
            )

            # Mock pour récupérer l'avis critique correspondant
            mock_mongodb.get_critical_review_by_episode_oid.return_value = (
                mock_critical_review
            )

            # Act
            service.auto_process_verified_books()

            # Assert - vérifier que le livre est créé avec la référence à l'avis critique
            mock_mongodb.create_book_if_not_exists.assert_called_once()
            call_args = mock_mongodb.create_book_if_not_exists.call_args[0][0]

            # Le livre doit contenir la référence à l'avis critique
            assert "avis_critiques" in call_args
            assert call_args["avis_critiques"] == [
                ObjectId("68c718a16e51b9428ab88066")  # pragma: allowlist secret
            ]

            # Vérifier que l'avis critique a été recherché
            mock_mongodb.get_critical_review_by_episode_oid.assert_called_with(
                "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
            )

    def test_get_statistics_returns_consistent_types(self):
        """Test TDD: get_statistics doit retourner des types cohérents (nombres, pas listes)."""
        service = CollectionsManagementService()

        with patch.object(service, "mongodb_service") as mock_mongodb:
            # Mock des retours - tous devraient être des nombres
            mock_mongodb.get_verified_books_not_in_collections.return_value = []  # Liste vide
            mock_mongodb.get_suggested_books_not_in_collections.return_value = 5
            mock_mongodb.get_not_found_books_not_in_collections.return_value = 2
            mock_mongodb.get_books_in_collections_count.return_value = 10
            mock_mongodb.get_untreated_episodes_count.return_value = 3

            stats = service.get_statistics()

            # Tous les champs doivent être des nombres, pas des listes
            assert isinstance(stats["episodes_non_traites"], int)
            assert isinstance(stats["couples_en_base"], int)
            assert isinstance(
                stats["couples_verified_pas_en_base"], int
            )  # ❌ Actuellement liste
            assert isinstance(stats["couples_suggested_pas_en_base"], int)
            assert isinstance(stats["couples_not_found_pas_en_base"], int)

            # La liste vide doit être convertie en 0
            assert stats["couples_verified_pas_en_base"] == 0
