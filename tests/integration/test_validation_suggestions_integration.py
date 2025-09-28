"""Tests d'intégration TDD pour la validation des suggestions (Frontend + Backend)."""

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestValidationSuggestionsIntegration:
    """Tests TDD d'intégration pour le flow complet de validation des suggestions."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_validate_suggestion_with_undefined_fields_should_fail_422(self):
        """Test TDD: Reproduire l'erreur 422 avec cache_id et avis_critique_id undefined."""
        # Arrange: Données exactement comme le frontend les envoie (avec undefined)
        validation_data = {
            "cache_id": None,  # undefined devient None en Python
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": None,  # undefined devient None en Python
            "auteur": "Alain Mabancou",
            "titre": "Ramsès de Paris",
            "editeur": "Seuil",
            "user_validated_author": "Alain Mabanckou",
            "user_validated_title": "Ramsès de Paris",
            "user_validated_publisher": "Seuil",
        }

        # Act
        response = self.client.post(
            "/api/livres-auteurs/validate-suggestion", json=validation_data
        )

        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        # L'erreur doit mentionner les champs manquants
        assert "cache_id" in str(error_detail) or "avis_critique_id" in str(
            error_detail
        )

    def test_validate_suggestion_with_valid_data_should_succeed(self):
        """Test TDD: Validation avec données valides doit réussir (422 → 200)."""
        # Skip si pas de connexion MongoDB
        from back_office_lmelp.services.mongodb_service import mongodb_service

        try:
            if not mongodb_service.is_connected():
                pytest.skip("MongoDB not connected - skipping integration test")
        except Exception:
            pytest.skip("MongoDB service not available - skipping integration test")

        # Arrange: Données exactement comme le frontend les envoie
        cache_id = "68d5b9099265d804e509dbcb"  # pragma: allowlist secret
        validation_data = {
            "cache_id": cache_id,
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "auteur": "Alain Mabancou",
            "titre": "Ramsès de Paris",
            "editeur": "Seuil",
            "user_validated_author": "Alain Mabanckou",  # Correction de l'orthographe
            "user_validated_title": "Ramsès de Paris",
            "user_validated_publisher": "Seuil",
        }

        # Act
        response = self.client.post(
            "/api/livres-auteurs/validate-suggestion", json=validation_data
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        result = response.json()
        assert result["success"] is True
        assert "author_id" in result
        assert "book_id" in result

    def test_validate_suggestion_with_missing_cache_id_should_fail_422(self):
        """Test TDD: Validation sans cache_id doit échouer avec 422."""
        # Skip si pas de connexion MongoDB
        from back_office_lmelp.services.mongodb_service import mongodb_service

        try:
            if not mongodb_service.is_connected():
                pytest.skip("MongoDB not connected - skipping integration test")
        except Exception:
            pytest.skip("MongoDB service not available - skipping integration test")

        # Arrange: Données manquantes (pas de cache_id)
        validation_data = {
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "auteur": "Test Auteur",
            "titre": "Test Titre",
            "user_validated_author": "Test Auteur",
            "user_validated_title": "Test Titre",
        }

        # Act
        response = self.client.post(
            "/api/livres-auteurs/validate-suggestion", json=validation_data
        )

        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert "cache_id" in str(error_detail).lower()

    def test_validate_suggestion_with_invalid_objectid_should_fail_422(self):
        """Test TDD: Validation avec ObjectId invalide doit échouer avec 422."""
        # Skip si pas de connexion MongoDB
        from back_office_lmelp.services.mongodb_service import mongodb_service

        try:
            if not mongodb_service.is_connected():
                pytest.skip("MongoDB not connected - skipping integration test")
        except Exception:
            pytest.skip("MongoDB service not available - skipping integration test")

        # Arrange: cache_id avec format invalide
        validation_data = {
            "cache_id": "invalid_object_id",
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "auteur": "Test Auteur",
            "titre": "Test Titre",
            "user_validated_author": "Test Auteur",
            "user_validated_title": "Test Titre",
        }

        # Act
        response = self.client.post(
            "/api/livres-auteurs/validate-suggestion", json=validation_data
        )

        # Assert
        assert response.status_code == 422

    def test_frontend_payload_structure_matches_backend_expectations(self):
        """Test TDD: Structure des données du frontend correspond aux attentes backend."""
        # Ce test vérifie que les champs envoyés par le frontend sont bien attendus

        # Arrange: Payload typique du frontend
        frontend_payload = {
            "cache_id": "68d5b9099265d804e509dbcb",  # pragma: allowlist secret
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "auteur": "Original Author",
            "titre": "Original Title",
            "editeur": "Original Publisher",
            "user_validated_author": "Validated Author",
            "user_validated_title": "Validated Title",
            "user_validated_publisher": "Validated Publisher",
        }

        # Act: Vérifier que l'endpoint accepte cette structure
        response = self.client.post(
            "/api/livres-auteurs/validate-suggestion", json=frontend_payload
        )

        # Assert: Ne doit pas échouer sur la structure (peut échouer sur les données)
        # Si c'est 422, ça doit être pour les données, pas la structure
        if response.status_code == 422:
            error_detail = response.json()["detail"]
            # Ne doit pas contenir d'erreurs de champs manquants
            forbidden_errors = ["field required", "missing", "required field"]
            error_text = str(error_detail).lower()
            for forbidden in forbidden_errors:
                assert forbidden not in error_text, f"Structure error: {error_detail}"
