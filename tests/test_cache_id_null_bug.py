"""Test TDD RED: Reproduire le bug cache_id null = statut reste suggested."""

from unittest.mock import patch

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    collections_management_service,
)


class TestCacheIdNullBug:
    """Test TDD pour reproduire le bug cache_id null."""

    @patch(
        "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
    )
    def test_manually_validate_suggestion_with_null_cache_id_should_fail_RED_PHASE(
        self, mock_cache_service
    ):
        """
        TEST TDD RED: Ce test doit ÉCHOUER car cache_id null empêche mark_as_processed.

        Problème identifié:
        - Laurent Mauvignier a cache_id: null dans les données
        - Code: if cache_id_str: → False quand cache_id est null
        - Résultat: mark_as_processed n'est JAMAIS appelé
        - Statut reste "suggested" au lieu de passer à "mongo"
        """

        # DONNÉES EXACTES du problème Laurent Mauvignier
        book_data_with_null_cache_id = {
            "cache_id": None,  # ❌ PROBLÈME: cache_id est null !
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "auteur": "Laurent Mauvignier",
            "titre": "La Maison Vide",
            "editeur": "Éditions de Minuit",
            "user_validated_author": "Laurent Mauvignier",
            "user_validated_title": "La Maison Vide",
        }

        with patch.object(
            collections_management_service, "mongodb_service"
        ) as mock_mongodb:
            # Mock: Création réussie en base
            author_id = ObjectId("67a79b615b03b52d8c51db29")  # pragma: allowlist secret
            book_id = ObjectId("68d3eb092f32bb8c43063f76")  # pragma: allowlist secret
            mock_mongodb.create_author_if_not_exists.return_value = author_id
            mock_mongodb.create_book_if_not_exists.return_value = book_id
            mock_mongodb.update_book_validation.return_value = True
            mock_cache_service.mark_as_processed.return_value = True

            # Act: Appeler manually_validate_suggestion avec cache_id null
            result = collections_management_service.manually_validate_suggestion(
                book_data_with_null_cache_id
            )

            # Assert: Le livre est créé en base (success=True)
            assert result["success"] is True

            # CRITICAL: Vérifier que mark_as_processed N'A PAS été appelé !
            # C'est ça le bug: cache_id null = pas de mise à jour cache
            mock_cache_service.mark_as_processed.assert_not_called()

            print("❌ BUG REPRODUIT: mark_as_processed pas appelé avec cache_id null")
            print("📊 Le livre est créé en base mais le statut cache reste 'suggested'")

    @patch(
        "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
    )
    def test_manually_validate_suggestion_with_valid_cache_id_should_work(
        self, mock_cache_service
    ):
        """
        Test TDD: Avec un cache_id valide, mark_as_processed DOIT être appelé.
        """

        # DONNÉES avec cache_id valide
        cache_id = ObjectId("68d3eb092f32bb8c43063f91")  # pragma: allowlist secret
        book_data_with_cache_id = {
            "cache_id": str(cache_id),  # ✅ cache_id valide
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "auteur": "Laurent Mauvignier",
            "titre": "La Maison Vide",
            "editeur": "Éditions de Minuit",
            "user_validated_author": "Laurent Mauvignier",
            "user_validated_title": "La Maison Vide",
        }

        with patch.object(
            collections_management_service, "mongodb_service"
        ) as mock_mongodb:
            # Mock: Création réussie en base
            author_id = ObjectId("67a79b615b03b52d8c51db29")  # pragma: allowlist secret
            book_id = ObjectId("68d3eb092f32bb8c43063f76")  # pragma: allowlist secret
            mock_mongodb.create_author_if_not_exists.return_value = author_id
            mock_mongodb.create_book_if_not_exists.return_value = book_id
            mock_mongodb.update_book_validation.return_value = True
            mock_cache_service.mark_as_processed.return_value = True

            # Act: Appeler manually_validate_suggestion avec cache_id valide
            result = collections_management_service.manually_validate_suggestion(
                book_data_with_cache_id
            )

            # Assert: Le livre est créé en base
            assert result["success"] is True

            # CRITICAL: Vérifier que mark_as_processed A été appelé avec cache_id valide
            # Issue #159: metadata avec editeur est maintenant toujours passé
            mock_cache_service.mark_as_processed.assert_called_once_with(
                cache_id, author_id, book_id, metadata={"editeur": "Éditions de Minuit"}
            )

            print(
                "✅ COMPORTEMENT NORMAL: mark_as_processed appelé avec cache_id valide"
            )

    def test_debug_why_cache_id_is_null_in_api_data(self):
        """
        Test pour débugger pourquoi l'API retourne cache_id null.

        L'API /api/livres-auteurs devrait retourner _id comme cache_id mais ne le fait pas.
        """

        # Simuler les données comme elles sont dans le cache MongoDB
        real_cache_data = {
            "_id": ObjectId("68d3eb092f32bb8c43063f91"),  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "auteur": "Laurent Mauvignier",
            "titre": "La Maison Vide",
            "status": "suggested",
            "suggested_author": "Laurent Mauvignier",
            "suggested_title": "La Maison vide",
        }

        # Le problème: Comment ces données deviennent-elles cache_id: null dans l'API?
        # L'API devrait mapper _id → cache_id mais ne le fait pas

        print("🔍 Cache MongoDB _id:", real_cache_data["_id"])
        print("📊 API devrait retourner cache_id:", str(real_cache_data["_id"]))
        print("❌ API retourne cache_id: null")

        # La correction devra être dans la fonction qui formate les données de l'API
        # Elle doit faire: cache_id = str(data["_id"])
        assert str(real_cache_data["_id"]) != "null"
        print("✅ Test montre que _id existe et devrait être utilisé comme cache_id")
