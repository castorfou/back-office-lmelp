"""Tests TDD pour la méthode unifiée de validation des livres (suggested et not_found)."""

from unittest.mock import patch

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


class TestUnifiedBookValidation:
    """Tests TDD pour la méthode unifiée handle_book_validation."""

    def test_handle_book_validation_with_suggested_book_should_preserve_suggested_fields(
        self,
    ):
        """
        Test TDD: La méthode unifiée doit gérer les livres suggested avec champs suggested.

        Cas d'usage: Livre suggested (Maria Pourchet) avec corrections utilisateur
        → Doit préserver suggested_author/suggested_title
        """
        # ARRANGE
        service = CollectionsManagementService()
        cache_id = ObjectId("64a1b2c3d4e5f6789abcdef0")  # pragma: allowlist secret
        author_id = ObjectId("64a1b2c3d4e5f6789abcdef1")  # pragma: allowlist secret
        book_id = ObjectId("64a1b2c3d4e5f6789abcdef2")  # pragma: allowlist secret

        # Données pour livre suggested avec corrections utilisateur
        book_data = {
            "cache_id": str(cache_id),
            "auteur": "Maria Pourchet",  # Données originales du cache
            "titre": "Tressaillir",
            "editeur": "Stock",
            "user_validated_author": "Maria Pourchet",  # Corrections utilisateur
            "user_validated_title": "Tressaillir",
            "suggested_author": "Maria Pourchet",  # Champs suggested à préserver
            "suggested_title": "Tressaillir",
        }

        # ACT & ASSERT
        with (
            patch.object(service, "mongodb_service") as mock_mongodb,
            patch(
                "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
            ) as mock_cache_service,
        ):
            # Setup mocks
            mock_mongodb.create_author_if_not_exists.return_value = author_id
            mock_mongodb.create_book_if_not_exists.return_value = book_id
            mock_mongodb.update_book_validation.return_value = True
            mock_cache_service.mark_as_processed.return_value = True

            # Act: Appeler la méthode unifiée (qui n'existe pas encore - RED phase)
            result = service.handle_book_validation(book_data)

            # Assert: Comportement attendu
            assert result["success"] is True
            assert result["author_id"] == str(author_id)
            assert result["book_id"] == str(book_id)

            # Vérifier que les champs suggested sont préservés
            call_args = mock_mongodb.update_book_validation.call_args[0]
            metadata = call_args[2]  # 3ème argument
            assert metadata["suggested_author"] == "Maria Pourchet"
            assert metadata["suggested_title"] == "Tressaillir"

            # Vérifier que le cache est marqué comme traité
            mock_cache_service.mark_as_processed.assert_called_once_with(
                cache_id, author_id, book_id
            )

    def test_handle_book_validation_with_not_found_book_should_work_like_suggested(
        self,
    ):
        """
        Test TDD: La méthode unifiée doit gérer les livres not_found comme les suggested.

        Cas d'usage: Livre not_found (Nin Antico) saisi manuellement par utilisateur
        → Doit utiliser la même logique que suggested
        """
        # ARRANGE
        service = CollectionsManagementService()
        cache_id = ObjectId("68d7f65892d24efb2c41ab11")  # pragma: allowlist secret
        author_id = ObjectId("68d152157e4140105a6977c2")  # pragma: allowlist secret
        book_id = ObjectId("68d7f68383ac9ac399ec8cfb")  # pragma: allowlist secret

        # Données pour livre not_found avec saisie utilisateur
        book_data = {
            "cache_id": str(cache_id),
            "auteur": "Nin Antico",  # Données originales du cache
            "titre": "Une Obsession",
            "editeur": "Dargaud",
            # Pour not_found, l'utilisateur SAISIT les données (pas de correction)
            "user_validated_author": "Nin Antico",  # Saisie utilisateur
            "user_validated_title": "Une Obsession",
            # Les champs suggested doivent être remplis avec la saisie utilisateur
            "suggested_author": "Nin Antico",
            "suggested_title": "Une Obsession",
        }

        # ACT & ASSERT
        with (
            patch.object(service, "mongodb_service") as mock_mongodb,
            patch(
                "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
            ) as mock_cache_service,
        ):
            # Setup mocks
            mock_mongodb.create_author_if_not_exists.return_value = author_id
            mock_mongodb.create_book_if_not_exists.return_value = book_id
            mock_mongodb.update_book_validation.return_value = True
            mock_cache_service.mark_as_processed.return_value = True

            # Act: Appeler la méthode unifiée
            result = service.handle_book_validation(book_data)

            # Assert: Même comportement que suggested
            assert result["success"] is True
            assert result["author_id"] == str(author_id)
            assert result["book_id"] == str(book_id)

            # Vérifier que les champs suggested sont remplis avec la saisie utilisateur
            call_args = mock_mongodb.update_book_validation.call_args[0]
            metadata = call_args[2]
            assert metadata["suggested_author"] == "Nin Antico"
            assert metadata["suggested_title"] == "Une Obsession"

            # Vérifier que le cache est marqué comme traité (statut mongo)
            mock_cache_service.mark_as_processed.assert_called_once_with(
                cache_id, author_id, book_id
            )

    def test_handle_book_validation_should_handle_cache_id_lookup_for_both_cases(self):
        """
        Test TDD: La méthode unifiée doit gérer le lookup de cache_id pour les deux cas.

        Vérifie que si cache_id est manquant, la méthode peut le retrouver.
        """
        # ARRANGE
        service = CollectionsManagementService()
        author_id = ObjectId("64a1b2c3d4e5f6789abcdef1")  # pragma: allowlist secret
        book_id = ObjectId("64a1b2c3d4e5f6789abcdef2")  # pragma: allowlist secret

        # Données sans cache_id (cas problématique actuel)
        book_data = {
            # Pas de cache_id fourni
            "auteur": "Test Auteur",
            "titre": "Test Titre",
            "editeur": "Test Éditeur",
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "user_validated_author": "Test Auteur Corrigé",
            "user_validated_title": "Test Titre Corrigé",
            "suggested_author": "Test Auteur Corrigé",
            "suggested_title": "Test Titre Corrigé",
        }

        # ACT & ASSERT
        with (
            patch.object(service, "mongodb_service") as mock_mongodb,
            patch(
                "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
            ) as mock_cache_service,
        ):
            # Setup mocks
            mock_mongodb.create_author_if_not_exists.return_value = author_id
            mock_mongodb.create_book_if_not_exists.return_value = book_id
            mock_mongodb.update_book_validation.return_value = True
            mock_cache_service.mark_as_processed.return_value = True

            # Mock du lookup de cache_id
            mock_cache_service.get_books_by_episode_oid.return_value = [
                {
                    "_id": ObjectId(
                        "64a1b2c3d4e5f6789abcdef0"  # pragma: allowlist secret
                    ),  # pragma: allowlist secret
                    "auteur": "Test Auteur",
                    "titre": "Test Titre",
                }
            ]

            # Act: La méthode doit fonctionner même sans cache_id
            result = service.handle_book_validation(book_data)

            # Assert: Doit réussir et retrouver le cache_id
            assert result["success"] is True

            # Vérifier que le lookup a été tenté
            mock_cache_service.get_books_by_episode_oid.assert_called_once_with(
                "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
            )
