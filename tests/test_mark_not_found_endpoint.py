"""Tests TDD pour l'endpoint mark-not-found - Issue #124.

L'endpoint doit supporter item_type='auteur' en plus de 'livre'.
"""

from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient


class TestMarkNotFoundEndpoint:
    """Tests pour l'endpoint POST /api/babelio-migration/mark-not-found."""

    @pytest.fixture
    def client(self):
        """Fixture pour le client FastAPI."""
        from back_office_lmelp.app import app

        return TestClient(app)

    def test_should_mark_author_as_not_found_via_api(self, client):
        """Test TDD: L'endpoint doit accepter item_type='auteur'.

        Problème UI:
        - L'utilisateur veut marquer un auteur comme "Pas sur Babelio"
        - L'endpoint ne supporte que les livres

        Solution:
        - Ajouter item_type='auteur' dans le modèle MarkNotFoundRequest
        - Appeler mark_as_not_found() avec item_type='auteur'
        """
        # Arrange
        auteur_id = str(ObjectId())

        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            mock_migration_service.mark_as_not_found.return_value = True

            # Act
            response = client.post(
                "/api/babelio-migration/mark-not-found",
                json={
                    "item_id": auteur_id,
                    "reason": "Auteur introuvable sur Babelio",
                    "item_type": "auteur",
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Auteur" in data["message"]
            assert auteur_id in data["message"]

            # Vérifier l'appel au service
            mock_migration_service.mark_as_not_found.assert_called_once_with(
                item_id=auteur_id,
                reason="Auteur introuvable sur Babelio",
                item_type="auteur",
            )

    def test_should_still_support_livre_type(self, client):
        """Test TDD: L'endpoint doit toujours supporter item_type='livre'."""
        # Arrange
        livre_id = str(ObjectId())

        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            mock_migration_service.mark_as_not_found.return_value = True

            # Act
            response = client.post(
                "/api/babelio-migration/mark-not-found",
                json={
                    "item_id": livre_id,
                    "reason": "Livre introuvable sur Babelio",
                    "item_type": "livre",
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Livre" in data["message"]

    def test_should_default_to_livre_when_item_type_not_provided(self, client):
        """Test TDD: item_type doit par défaut être 'livre' (rétrocompatibilité)."""
        # Arrange
        livre_id = str(ObjectId())

        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            mock_migration_service.mark_as_not_found.return_value = True

            # Act
            response = client.post(
                "/api/babelio-migration/mark-not-found",
                json={
                    "item_id": livre_id,
                    "reason": "Livre introuvable",
                    # Pas de item_type fourni -> doit defaulter à "livre"
                },
            )

            # Assert
            assert response.status_code == 200

            # Vérifier que le service a été appelé avec item_type="livre"
            mock_migration_service.mark_as_not_found.assert_called_once_with(
                item_id=livre_id,
                reason="Livre introuvable",
                item_type="livre",  # Valeur par défaut
            )

    def test_should_return_404_when_author_not_found(self, client):
        """Test TDD: Retourner 404 si l'auteur n'existe pas dans MongoDB."""
        # Arrange
        auteur_id = str(ObjectId())

        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            mock_migration_service.mark_as_not_found.return_value = False

            # Act
            response = client.post(
                "/api/babelio-migration/mark-not-found",
                json={
                    "item_id": auteur_id,
                    "reason": "Test",
                    "item_type": "auteur",
                },
            )

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert data["status"] == "error"
            assert "Auteur" in data["message"]
