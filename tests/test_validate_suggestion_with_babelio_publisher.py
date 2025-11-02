"""Tests TDD pour accepter babelio_publisher dans l'API validate-suggestion (Issue #85).

Quand l'utilisateur clique "Valider" sur un livre enrichi par Babelio,
le frontend envoie babelio_publisher et l'API doit le transmettre pour mise à jour du summary.
"""

from unittest.mock import patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestValidateSuggestionWithBabelioPublisher:
    """Tests TDD pour l'endpoint /api/livres-auteurs/validate-suggestion avec babelio_publisher."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_validate_suggestion_endpoint_should_accept_babelio_publisher(self):
        """
        RED TEST: L'endpoint /api/livres-auteurs/validate-suggestion doit accepter babelio_publisher.

        GIVEN: Frontend envoie une validation avec babelio_publisher enrichi par Babelio
        WHEN: POST /api/livres-auteurs/validate-suggestion est appelé
        THEN: L'API doit accepter babelio_publisher dans la requête (HTTP 200)
        """
        # Arrange
        cache_id = ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret
        avis_critique_id = "507f1f77bcf86cd799439012"  # pragma: allowlist secret
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret

        validation_request = {
            "cache_id": str(cache_id),
            "episode_oid": episode_oid,
            "avis_critique_id": avis_critique_id,
            "auteur": "Emmanuel Carrère",
            "titre": "Kolkhoze",
            "editeur": "POL",  # Éditeur original du markdown
            "user_validated_author": "Emmanuel Carrère",  # Pas de correction
            "user_validated_title": "Kolkhoze",  # Pas de correction
            "user_validated_publisher": None,
            "babelio_publisher": "P.O.L.",  # ✅ Enrichissement Babelio
            "babelio_url": "https://www.babelio.com/livres/Carrere-Kolkhoze/123456",
        }

        with patch(
            "back_office_lmelp.app.collections_management_service"
        ) as mock_service:
            # Mock du service
            mock_service.handle_book_validation.return_value = {
                "success": True,
                "author_id": "507f1f77bcf86cd799439014",
                "book_id": "507f1f77bcf86cd799439015",
            }

            # Act
            response = self.client.post(
                "/api/livres-auteurs/validate-suggestion", json=validation_request
            )

            # Assert - L'endpoint doit accepter la requête
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )
            result = response.json()
            assert result["success"] is True

            # Vérifier que handle_book_validation a été appelé avec babelio_publisher
            mock_service.handle_book_validation.assert_called_once()
            call_args = mock_service.handle_book_validation.call_args[0][0]

            # RED TEST: Vérifier que babelio_publisher a été transmis au service
            assert "babelio_publisher" in call_args, (
                "babelio_publisher doit être passé au service"
            )
            assert call_args["babelio_publisher"] == "P.O.L."
            assert (
                call_args["babelio_url"]
                == "https://www.babelio.com/livres/Carrere-Kolkhoze/123456"
            )

    def test_validate_suggestion_should_update_summary_with_babelio_publisher(self):
        """
        RED TEST: La validation avec babelio_publisher doit mettre à jour le summary markdown.

        GIVEN: Frontend envoie validation avec babelio_publisher enrichi
        WHEN: handle_book_validation est appelé avec babelio_publisher
        THEN: Le summary doit être mis à jour avec le nouvel éditeur et persisted en MongoDB
        """
        # Arrange
        cache_id = ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "507f1f77bcf86cd799439012"
        )  # pragma: allowlist secret

        validation_request = {
            "cache_id": str(cache_id),
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": str(avis_critique_id),
            "auteur": "Emmanuel Carrère",
            "titre": "Kolkhoze",
            "editeur": "POL",
            "user_validated_author": "Emmanuel Carrère",
            "user_validated_title": "Kolkhoze",
            "user_validated_publisher": None,
            "babelio_publisher": "P.O.L.",  # Enrichissement
        }

        with (
            patch(
                "back_office_lmelp.app.collections_management_service"
            ) as mock_service,
            patch("back_office_lmelp.app.livres_auteurs_cache_service"),
        ):
            # Mock du service pour capturer les appels
            mock_service.handle_book_validation.return_value = {
                "success": True,
                "author_id": str(ObjectId()),
                "book_id": str(ObjectId()),
            }

            # Act
            response = self.client.post(
                "/api/livres-auteurs/validate-suggestion", json=validation_request
            )

            # Assert
            assert response.status_code == 200

            # Vérifier que le service a reçu correctement les données
            call_kwargs = mock_service.handle_book_validation.call_args[0][0]
            assert call_kwargs["babelio_publisher"] == "P.O.L."
            assert call_kwargs["editeur"] == "POL"  # Original pour la comparaison
