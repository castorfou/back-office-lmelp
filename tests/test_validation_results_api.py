"""Tests TDD pour l'API de réception des résultats de validation biblio du frontend."""

from unittest.mock import patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestValidationResultsAPI:
    """Tests TDD pour recevoir les résultats de validation du frontend."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_set_validation_results_should_accept_frontend_results(self):
        """Test TDD: L'API doit accepter les résultats de validation du frontend."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        # Résultats de validation du frontend (BiblioValidationService.js)
        validation_results = {
            "episode_oid": episode_oid,
            "avis_critique_id": str(avis_critique_id),
            "books": [
                {
                    "auteur": "Laurent Mauvignier",
                    "titre": "La Maison Vide",
                    "editeur": "Éditions de Minuit",
                    "programme": True,
                    "validation_status": "suggestion",  # Du frontend
                    "suggested_author": "Laurent Mauvignier",
                    "suggested_title": "La Maison vide",
                },
                {
                    "auteur": "Maria Pourchet",
                    "titre": "Tressaillir",
                    "editeur": "Stock",
                    "programme": True,
                    "validation_status": "verified",  # Du frontend
                },
            ],
        }

        with patch(
            "back_office_lmelp.app.livres_auteurs_cache_service"
        ) as mock_cache_service:
            # Mock: création des entrées cache avec les bons statuts
            cache_entry_id1 = ObjectId(
                "68d3eb092f32bb8c43063f91"  # pragma: allowlist secret
            )  # pragma: allowlist secret
            cache_entry_id2 = ObjectId(
                "68d3eb092f32bb8c43063f92"  # pragma: allowlist secret
            )  # pragma: allowlist secret
            mock_cache_service.create_cache_entry.side_effect = [
                cache_entry_id1,
                cache_entry_id2,
            ]

            # Act
            response = self.client.post(
                "/api/set-validation-results", json=validation_results
            )

            # Assert
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["books_processed"] == 2

            # Vérifier que les livres ont été créés dans le cache avec les statuts du frontend
            assert mock_cache_service.create_cache_entry.call_count == 2

            # Premier appel - Laurent Mauvignier (suggested)
            first_call = mock_cache_service.create_cache_entry.call_args_list[0]
            laurent_data = first_call[0][1]  # book_data
            assert laurent_data["auteur"] == "Laurent Mauvignier"
            assert laurent_data["status"] == "suggested"  # Status du frontend
            assert laurent_data["suggested_author"] == "Laurent Mauvignier"
            assert laurent_data["suggested_title"] == "La Maison vide"

            # Deuxième appel - Maria Pourchet (verified)
            second_call = mock_cache_service.create_cache_entry.call_args_list[1]
            maria_data = second_call[0][1]  # book_data
            assert maria_data["auteur"] == "Maria Pourchet"
            assert maria_data["status"] == "verified"  # Status du frontend

    def test_set_validation_results_should_trigger_auto_processing_for_verified(self):
        """Test TDD: L'auto-processing doit être déclenché pour les livres verified du frontend."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        validation_results = {
            "episode_oid": episode_oid,
            "avis_critique_id": str(avis_critique_id),
            "books": [
                {
                    "auteur": "Maria Pourchet",
                    "titre": "Tressaillir",
                    "editeur": "Stock",
                    "programme": True,
                    "validation_status": "verified",  # Du frontend → doit déclencher auto-processing
                }
            ],
        }

        with (
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
        ):
            # Mock: cache et auto-processing
            cache_entry_id = ObjectId(
                "68d3eb092f32bb8c43063f91"  # pragma: allowlist secret
            )  # pragma: allowlist secret
            mock_cache_service.create_cache_entry.return_value = cache_entry_id
            author_id = ObjectId("67a79b615b03b52d8c51db29")  # pragma: allowlist secret
            book_id = ObjectId("68d3eb092f32bb8c43063f76")  # pragma: allowlist secret
            mock_mongodb.create_author_if_not_exists.return_value = author_id
            mock_mongodb.create_book_if_not_exists.return_value = book_id

            # Act
            response = self.client.post(
                "/api/set-validation-results", json=validation_results
            )

            # Assert
            assert response.status_code == 200

            # Vérifier que l'auto-processing a été déclenché pour le livre verified
            mock_mongodb.create_author_if_not_exists.assert_called_once_with(
                "Maria Pourchet"
            )
            mock_mongodb.create_book_if_not_exists.assert_called_once()

            # Vérifier que le livre a été marqué comme traité (mongo)
            mock_cache_service.mark_as_processed.assert_called_once_with(
                cache_entry_id, author_id, book_id
            )

    def test_set_validation_results_should_not_auto_process_suggested_books(self):
        """Test TDD: L'auto-processing ne doit PAS être déclenché pour les livres suggested."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        validation_results = {
            "episode_oid": episode_oid,
            "avis_critique_id": str(avis_critique_id),
            "books": [
                {
                    "auteur": "Laurent Mauvignier",
                    "titre": "La Maison Vide",
                    "editeur": "Éditions de Minuit",
                    "programme": True,
                    "validation_status": "suggestion",  # Du frontend → PAS d'auto-processing
                    "suggested_author": "Laurent Mauvignier",
                    "suggested_title": "La Maison vide",
                }
            ],
        }

        with (
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
        ):
            cache_entry_id = ObjectId(
                "68d3eb092f32bb8c43063f91"  # pragma: allowlist secret
            )  # pragma: allowlist secret
            mock_cache_service.create_cache_entry.return_value = cache_entry_id

            # Act
            response = self.client.post(
                "/api/set-validation-results", json=validation_results
            )

            # Assert
            assert response.status_code == 200

            # Vérifier qu'AUCUN auto-processing n'a été déclenché
            mock_mongodb.create_author_if_not_exists.assert_not_called()
            mock_mongodb.create_book_if_not_exists.assert_not_called()
            mock_cache_service.mark_as_processed.assert_not_called()

            # Vérifier que le livre reste suggested dans le cache
            cache_call = mock_cache_service.create_cache_entry.call_args
            book_data = cache_call[0][1]
            assert book_data["status"] == "suggested"
