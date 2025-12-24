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
            # Issue #159: metadata avec editeur est maintenant toujours passé
            mock_cache_service.mark_as_processed.assert_called_once_with(
                cache_id, author_id, book_id, metadata={"editeur": "Stock"}
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
            # Issue #159: metadata avec editeur est maintenant toujours passé
            mock_cache_service.mark_as_processed.assert_called_once_with(
                cache_id, author_id, book_id, metadata={"editeur": "Dargaud"}
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

    def test_handle_book_validation_should_update_publisher_in_cache_when_validated(
        self,
    ):
        """
        RED Test TDD: La validation doit mettre à jour l'éditeur dans le cache (Issue #159).

        Bug: Quand l'utilisateur change l'éditeur lors de la validation,
        le nouveau éditeur est bien enregistré dans la collection livres,
        MAIS l'ancien éditeur reste dans livresauteurs_cache.

        Exemple: "Segers" → "Editions Seghers"
        Le cache doit refléter "Editions Seghers", pas "Segers".
        """
        # ARRANGE
        service = CollectionsManagementService()
        cache_id = ObjectId("64a1b2c3d4e5f6789abcdef0")  # pragma: allowlist secret
        author_id = ObjectId("64a1b2c3d4e5f6789abcdef1")  # pragma: allowlist secret
        book_id = ObjectId("64a1b2c3d4e5f6789abcdef2")  # pragma: allowlist secret

        # Données de validation avec changement d'éditeur
        book_data = {
            "cache_id": str(cache_id),
            "auteur": "John Steinbeck",
            "titre": "Jours de travail",
            "editeur": "Segers",  # ANCIEN éditeur du cache
            "user_validated_author": "John Steinbeck",
            "user_validated_title": "Jours de travail",
            "user_validated_publisher": "Editions Seghers",  # NOUVEAU éditeur validé
            "suggested_author": "John Steinbeck",
            "suggested_title": "Jours de travail",
            "suggested_publisher": "Editions Seghers",
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

            # Act: Appeler la validation
            result = service.handle_book_validation(book_data)

            # Assert: La validation doit réussir
            assert result["success"] is True
            assert result["author_id"] == str(author_id)
            assert result["book_id"] == str(book_id)

            # Assert CRITIQUE: Le cache doit être mis à jour avec le NOUVEAU éditeur
            # ❌ ÉCHEC ATTENDU (RED): actuellement mark_as_processed ne reçoit PAS le nouvel éditeur
            mock_cache_service.mark_as_processed.assert_called_once()
            call_args = mock_cache_service.mark_as_processed.call_args

            # Vérifier les arguments de mark_as_processed
            assert call_args[0][0] == cache_id  # cache_id
            assert call_args[0][1] == author_id  # author_id
            assert call_args[0][2] == book_id  # book_id

            # ASSERTION CRITIQUE: metadata doit contenir le nouvel éditeur
            # C'est ce qui ÉCHOUE actuellement (RED phase)
            # kwargs contient les arguments nommés (metadata=...)
            if "metadata" in call_args.kwargs:
                metadata = call_args.kwargs["metadata"]
                assert "editeur" in metadata, (
                    "Le metadata doit contenir le champ 'editeur'"
                )
                assert metadata["editeur"] == "Editions Seghers", (
                    f"Le cache doit être mis à jour avec le NOUVEAU éditeur 'Editions Seghers', pas '{metadata.get('editeur', 'ABSENT')}'"
                )
            else:
                # ❌ ÉCHEC ATTENDU (RED): metadata n'est pas passé du tout
                raise AssertionError(
                    "Le metadata doit être passé à mark_as_processed pour mettre à jour l'éditeur dans le cache"
                )
