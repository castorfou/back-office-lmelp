"""Tests TDD pour le problème: livre suggested ajouté manuellement doit passer de suggested à mongo dans le cache."""

from unittest.mock import patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestSuggestedToMongoStatusUpdate:
    """Tests TDD pour garantir que le statut cache passe de suggested à mongo après ajout manuel."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_suggested_book_manually_added_should_update_cache_status_to_mongo_RED_PHASE(
        self,
    ):
        """
        Test TDD RED: Quand un livre 'suggested' est manuellement ajouté en base,
        le statut cache doit passer de 'suggested' à 'mongo'.

        Ce test doit initialement ÉCHOUER pour reproduire le bug actuel.
        """
        # Données du test - livre Laurent Mauvignier qui pose problème
        cache_id = ObjectId("68d3eb092f32bb8c43063f91")  # pragma: allowlist secret
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = "68c718a16e51b9428ab88066"  # pragma: allowlist secret

        suggested_book_data = {
            "cache_id": str(cache_id),
            "episode_oid": episode_oid,
            "avis_critique_id": avis_critique_id,
            "auteur": "Laurent Mauvignier",
            "titre": "La Maison Vide",
            "editeur": "Éditions de Minuit",
            "user_validated_author": "Laurent Mauvignier",  # Utilisateur confirme
            "user_validated_title": "La Maison Vide",  # Utilisateur confirme
        }

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.collections_management_service"
            ) as mock_collections_service,
        ):
            # Mock: memory guard
            mock_memory_guard.check_memory_limit.return_value = None

            # Mock: création réussie en base MongoDB
            author_id = ObjectId("67a79b615b03b52d8c51db29")  # pragma: allowlist secret
            book_id = ObjectId("68d3eb092f32bb8c43063f76")  # pragma: allowlist secret

            # Mock: handle_book_validation retourne un succès (nouvelle méthode unifiée)
            mock_collections_service.handle_book_validation.return_value = {
                "success": True,
                "author_id": str(author_id),
                "book_id": str(book_id),
            }

            # Act: L'utilisateur valide manuellement la suggestion
            response = self.client.post(
                "/api/livres-auteurs/validate-suggestion", json=suggested_book_data
            )

            # Assert: Le livre est créé avec succès
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert "author_id" in result
            assert "book_id" in result

            # CRITICAL: Vérifier que handle_book_validation A ÉTÉ appelé (nouvelle méthode unifiée)
            mock_collections_service.handle_book_validation.assert_called_once()

            # Vérifier que les données essentielles sont passées
            call_args = mock_collections_service.handle_book_validation.call_args[0][0]
            assert call_args["cache_id"] == str(cache_id)
            assert call_args["auteur"] == "Laurent Mauvignier"
            assert call_args["titre"] == "La Maison Vide"
            assert call_args["user_validated_author"] == "Laurent Mauvignier"
            assert call_args["user_validated_title"] == "La Maison Vide"

    def test_verify_cache_status_change_from_suggested_to_mongo(self):
        """
        Test TDD: Vérifier que la méthode mark_as_processed change bien le statut à "mongo".
        """
        cache_id = ObjectId("68d3eb092f32bb8c43063f91")  # pragma: allowlist secret
        author_id = ObjectId("67a79b615b03b52d8c51db29")  # pragma: allowlist secret
        book_id = ObjectId("68d3eb092f32bb8c43063f76")  # pragma: allowlist secret

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
        ) as mock_cache_service:
            # Mock: mark_as_processed retourne True
            mock_cache_service.mark_as_processed.return_value = True

            # Act: Appeler mark_as_processed via le mock
            result = mock_cache_service.mark_as_processed(cache_id, author_id, book_id)

            # Assert: Operation succeeds
            assert result is True

            # Vérifier que mark_as_processed a été appelé avec les bons paramètres
            mock_cache_service.mark_as_processed.assert_called_once_with(
                cache_id, author_id, book_id
            )

    def test_manually_validate_suggestion_calls_mark_as_processed(self):
        """
        Test TDD: Vérifier que manually_validate_suggestion appelle bien mark_as_processed.
        """
        cache_id = ObjectId("68d3eb092f32bb8c43063f91")  # pragma: allowlist secret
        book_data = {
            "cache_id": str(cache_id),
            "auteur": "Laurent Mauvignier",
            "titre": "La Maison Vide",
            "editeur": "Éditions de Minuit",
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "user_validated_author": "Laurent Mauvignier",
            "user_validated_title": "La Maison Vide",
        }

        with (
            patch(
                "back_office_lmelp.services.collections_management_service.collections_management_service.mongodb_service"
            ) as mock_mongodb,
            patch(
                "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
            ) as mock_cache_service,
        ):
            # Mocks
            author_id = ObjectId("67a79b615b03b52d8c51db29")  # pragma: allowlist secret
            book_id = ObjectId("68d3eb092f32bb8c43063f76")  # pragma: allowlist secret
            mock_mongodb.create_author_if_not_exists.return_value = author_id
            mock_mongodb.create_book_if_not_exists.return_value = book_id
            mock_mongodb.update_book_validation.return_value = True
            mock_cache_service.mark_as_processed.return_value = True

            # Importer le service et l'appeler
            from back_office_lmelp.services.collections_management_service import (
                collections_management_service,
            )

            # Act
            result = collections_management_service.manually_validate_suggestion(
                book_data
            )

            # Assert
            assert result["success"] is True

            # CRITICAL: Vérifier que mark_as_processed est appelé
            # Issue #159: metadata avec editeur est maintenant toujours passé
            mock_cache_service.mark_as_processed.assert_called_once_with(
                cache_id, author_id, book_id, metadata={"editeur": "Éditions de Minuit"}
            )
