"""Tests TDD pour le service de gestion des collections auteurs/livres (Issue #66)."""

from unittest.mock import ANY, patch

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

        # Mock des données de test avec système unifié
        with patch.object(service, "mongodb_service") as mock_mongodb:
            # Setup mock responses avec méthode unifiée
            mock_mongodb.get_books_by_validation_status.side_effect = lambda status: {
                "verified": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    10,
                    11,
                    12,
                    13,
                    14,
                    15,
                ],  # 15 livres
                "suggested": [1, 2, 3, 4, 5, 6, 7, 8],  # 8 livres
                "not_found": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],  # 12 livres
            }[status]
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

        # Mock des livres verified à traiter (Issue #282: champ `status`, schéma réel du cache)
        verified_books = [
            {
                "_id": ObjectId("64f1234567890abcdef33331"),  # pragma: allowlist secret
                "auteur": "Michel Houellebecq",
                "titre": "Les Particules élémentaires",
                "editeur": "Flammarion",
                "episode_oid": "64f1234567890abcdef12345",  # pragma: allowlist secret
                "status": "verified",
            },
            {
                "_id": ObjectId("64f1234567890abcdef33332"),  # pragma: allowlist secret
                "auteur": "Emmanuel Carrère",
                "titre": "Kolkhoze",
                "editeur": "POL",
                "episode_oid": "64f1234567890abcdef12346",  # pragma: allowlist secret
                "status": "verified",
            },
        ]

        with (
            patch.object(service, "mongodb_service") as mock_mongodb,
            patch(
                "back_office_lmelp.services.collections_management_service.livres_auteurs_cache_service"
            ) as mock_cache_service,
        ):
            mock_cache_service.get_books_by_status.return_value = verified_books
            mock_mongodb.create_author_if_not_exists.return_value = ObjectId(
                "64f1234567890abcdef11111"  # pragma: allowlist secret
            )
            mock_mongodb.create_book_if_not_exists.return_value = ObjectId(
                "64f1234567890abcdef22222"  # pragma: allowlist secret
            )
            mock_mongodb.get_critical_review_by_episode_oid.return_value = None

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

            # Issue #282: chaque livre traité doit être marqué comme traité dans le cache
            assert mock_cache_service.mark_as_processed.call_count == 2

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

    def test_handle_book_validation_for_not_found_case(self):
        """Test méthode unifiée pour le cas not_found (ancien manually_add_not_found_book)."""
        service = CollectionsManagementService()

        book_data = {
            "cache_id": "64f1234567890abcdef12345",  # pragma: allowlist secret
            "auteur": "Original Author",  # Données originales du cache
            "titre": "Original Title",
            "editeur": "Original Publisher",
            "user_entered_author": "New Author",  # Saisie utilisateur
            "user_entered_title": "New Title",
            "user_entered_publisher": "New Publisher",
        }

        with (
            patch.object(service, "mongodb_service") as mock_mongodb,
            patch(
                "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
            ) as mock_cache_service,
        ):
            mock_mongodb.create_author_if_not_exists.return_value = ObjectId(
                "64f1234567890abcdef11111"  # pragma: allowlist secret
            )
            mock_mongodb.create_book_if_not_exists.return_value = ObjectId(
                "64f1234567890abcdef22222"  # pragma: allowlist secret
            )
            mock_mongodb.update_book_validation.return_value = True
            mock_cache_service.mark_as_processed.return_value = True

            result = service.handle_book_validation(book_data)

            assert isinstance(result, dict)
            assert "success" in result
            assert result["success"] is True
            assert "author_id" in result
            assert "book_id" in result

    def test_auto_process_verified_books_should_mark_cache_entry_as_processed(self):
        """Test TDD (Issue #282): le traitement doit persister status='mongo' dans le cache.

        Bug racine: auto_process_verified_books() créait bien l'auteur/livre en base
        mais n'appelait jamais mark_as_processed(), laissant le cache figé en 'verified'
        (le bouton "Traiter" semblait ne rien faire côté UI).
        """
        service = CollectionsManagementService()

        cache_id = ObjectId("64f1234567890abcdef99999")  # pragma: allowlist secret
        verified_books = [
            {
                "_id": cache_id,
                "auteur": "Michel Houellebecq",
                "titre": "Les Particules élémentaires",
                "editeur": "Flammarion",
                "episode_oid": "64f1234567890abcdef12345",  # pragma: allowlist secret
                "status": "verified",
            }
        ]

        author_id = ObjectId("64f1234567890abcdef11111")  # pragma: allowlist secret
        book_id = ObjectId("64f1234567890abcdef22222")  # pragma: allowlist secret

        with (
            patch.object(service, "mongodb_service") as mock_mongodb,
            patch(
                "back_office_lmelp.services.collections_management_service.livres_auteurs_cache_service"
            ) as mock_cache_service,
        ):
            mock_cache_service.get_books_by_status.return_value = verified_books
            mock_mongodb.create_author_if_not_exists.return_value = author_id
            mock_mongodb.create_book_if_not_exists.return_value = book_id
            mock_mongodb.get_critical_review_by_episode_oid.return_value = None

            service.auto_process_verified_books()

            mock_cache_service.mark_as_processed.assert_called_once_with(
                cache_id, author_id, book_id, metadata=ANY
            )

    def test_auto_process_verified_books_with_cache_id_should_process_only_that_book(
        self,
    ):
        """Test TDD (Issue #282): passer cache_id doit cibler UN livre, pas tout traiter en masse.

        Bug racine: le bouton "Traiter" d'un livre précis déclenchait le traitement de
        TOUS les livres verified (l'endpoint ne prenait aucun paramètre).
        """
        service = CollectionsManagementService()

        target_id = ObjectId("64f1234567890abcdef99999")  # pragma: allowlist secret
        target_book = {
            "_id": target_id,
            "auteur": "Valérie Manteau",
            "titre": "Le Sillon",
            "editeur": "Le Tripode",
            "episode_oid": "64f1234567890abcdef12345",  # pragma: allowlist secret
            "status": "verified",
        }

        author_id = ObjectId("64f1234567890abcdef11111")  # pragma: allowlist secret
        book_id = ObjectId("64f1234567890abcdef22222")  # pragma: allowlist secret

        with (
            patch.object(service, "mongodb_service") as mock_mongodb,
            patch(
                "back_office_lmelp.services.collections_management_service.livres_auteurs_cache_service"
            ) as mock_cache_service,
        ):
            mock_cache_service.get_cache_entry_by_id.return_value = target_book
            mock_mongodb.create_author_if_not_exists.return_value = author_id
            mock_mongodb.create_book_if_not_exists.return_value = book_id
            mock_mongodb.get_critical_review_by_episode_oid.return_value = None

            result = service.auto_process_verified_books(cache_id=str(target_id))

            # Un seul livre traité, sélectionné par _id (pas par balayage global)
            mock_cache_service.get_books_by_status.assert_not_called()
            mock_cache_service.get_cache_entry_by_id.assert_called_once_with(target_id)
            assert result["processed_count"] == 1
            mock_cache_service.mark_as_processed.assert_called_once_with(
                target_id, author_id, book_id, metadata=ANY
            )

    def test_auto_process_links_books_to_critical_reviews(self):
        """Test TDD: l'auto-processing doit lier les livres aux avis critiques correspondants."""
        service = CollectionsManagementService()

        # Mock des livres verified avec episode_oid (Issue #282: champ `status`)
        verified_books = [
            {
                "_id": ObjectId("68d3eb092f32bb8c43063f91"),  # pragma: allowlist secret
                "auteur": "Maria Pourchet",
                "titre": "Tressaillir",
                "editeur": "Stock",
                "episode_oid": "68c707ad6e51b9428ab87e9e",  # Episode du 14/09  # pragma: allowlist secret
                "status": "verified",
            }
        ]

        # Mock de l'avis critique correspondant
        mock_critical_review = {
            "_id": ObjectId("68c718a16e51b9428ab88066"),  # pragma: allowlist secret
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "summary": "...Maria Pourchet | Tressaillir | Stock...",
        }

        with (
            patch.object(service, "mongodb_service") as mock_mongodb,
            patch(
                "back_office_lmelp.services.collections_management_service.livres_auteurs_cache_service"
            ) as mock_cache_service,
        ):
            # Mock des méthodes existantes avec système unifié
            mock_cache_service.get_books_by_status.return_value = verified_books
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
            # Mock des retours avec système unifié - tous devraient retourner des listes
            mock_mongodb.get_books_by_validation_status.side_effect = lambda status: {
                "verified": [],  # Liste vide = 0 livres
                "suggested": [1, 2, 3, 4, 5],  # 5 livres
                "not_found": [1, 2],  # 2 livres
            }[status]
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

            # La liste vide doit être convertie en 0, les autres listes en leur taille
            assert stats["couples_verified_pas_en_base"] == 0
            assert stats["couples_suggested_pas_en_base"] == 5
            assert stats["couples_not_found_pas_en_base"] == 2
