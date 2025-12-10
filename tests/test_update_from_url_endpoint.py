"""Tests TDD pour l'endpoint update-from-url - Issue #124.

L'endpoint doit permettre à l'utilisateur d'entrer manuellement une URL Babelio.
"""

from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient


class TestUpdateFromUrlEndpoint:
    """Tests pour l'endpoint POST /api/babelio-migration/update-from-url."""

    @pytest.fixture
    def client(self):
        """Fixture pour le client FastAPI."""
        from back_office_lmelp.app import app

        return TestClient(app)

    def test_should_update_livre_from_url_via_api(self, client):
        """Test TDD: L'endpoint doit accepter une URL Babelio pour un livre.

        Problème UI:
        - L'utilisateur connaît l'URL Babelio du livre
        - Il veut entrer l'URL manuellement et récupérer les données

        Solution:
        - Endpoint POST /api/babelio-migration/update-from-url
        - Appeler update_from_babelio_url() avec item_type='livre'
        """
        # Arrange
        livre_id = str(ObjectId())

        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            # Mock du service retournant succès
            mock_migration_service.update_from_babelio_url = AsyncMock(
                return_value={
                    "success": True,
                    "scraped_data": {
                        "titre": "Le Titre Correct",
                        "url_babelio": "https://www.babelio.com/livres/auteur/titre/123456",
                        "auteur_url_babelio": "https://www.babelio.com/auteur/Nom-Auteur/12345",
                    },
                }
            )

            # Act
            response = client.post(
                "/api/babelio-migration/update-from-url",
                json={
                    "item_id": livre_id,
                    "babelio_url": "https://www.babelio.com/livres/auteur/titre/123456",
                    "item_type": "livre",
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Livre" in data["message"]
            assert data["data"]["titre"] == "Le Titre Correct"

            # Vérifier l'appel au service
            mock_migration_service.update_from_babelio_url.assert_called_once_with(
                item_id=livre_id,
                babelio_url="https://www.babelio.com/livres/auteur/titre/123456",
                item_type="livre",
            )

    def test_should_update_auteur_from_url_via_api(self, client):
        """Test TDD: L'endpoint doit accepter une URL Babelio pour un auteur."""
        # Arrange
        auteur_id = str(ObjectId())

        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            # Mock du service retournant succès
            mock_migration_service.update_from_babelio_url = AsyncMock(
                return_value={
                    "success": True,
                    "scraped_data": {
                        "nom": "Nom Auteur",
                        "url_babelio": "https://www.babelio.com/auteur/Nom-Auteur/12345",
                    },
                }
            )

            # Act
            response = client.post(
                "/api/babelio-migration/update-from-url",
                json={
                    "item_id": auteur_id,
                    "babelio_url": "https://www.babelio.com/auteur/Nom-Auteur/12345",
                    "item_type": "auteur",
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Auteur" in data["message"]
            assert data["data"]["nom"] == "Nom Auteur"

    def test_should_return_400_on_invalid_url(self, client):
        """Test TDD: Retourner 400 si l'URL n'est pas valide."""
        # Arrange
        livre_id = str(ObjectId())

        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            # Mock du service retournant erreur
            mock_migration_service.update_from_babelio_url = AsyncMock(
                return_value={
                    "success": False,
                    "error": "URL invalide: doit être une URL Babelio",
                }
            )

            # Act
            response = client.post(
                "/api/babelio-migration/update-from-url",
                json={
                    "item_id": livre_id,
                    "babelio_url": "https://www.google.com/search?q=livre",
                    "item_type": "livre",
                },
            )

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"
            assert "invalide" in data["message"].lower()

    def test_should_default_to_livre_when_item_type_not_provided(self, client):
        """Test TDD: item_type doit par défaut être 'livre' (rétrocompatibilité)."""
        # Arrange
        livre_id = str(ObjectId())

        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            mock_migration_service.update_from_babelio_url = AsyncMock(
                return_value={
                    "success": True,
                    "scraped_data": {
                        "titre": "Titre",
                        "url_babelio": "https://www.babelio.com/livres/auteur/titre/123",
                    },
                }
            )

            # Act
            response = client.post(
                "/api/babelio-migration/update-from-url",
                json={
                    "item_id": livre_id,
                    "babelio_url": "https://www.babelio.com/livres/auteur/titre/123",
                    # Pas de item_type fourni -> doit defaulter à "livre"
                },
            )

            # Assert
            assert response.status_code == 200

            # Vérifier que le service a été appelé avec item_type="livre"
            mock_migration_service.update_from_babelio_url.assert_called_once_with(
                item_id=livre_id,
                babelio_url="https://www.babelio.com/livres/auteur/titre/123",
                item_type="livre",  # Valeur par défaut
            )

    def test_should_return_400_on_scraping_failure(self, client):
        """Test TDD: Retourner 400 si le scraping échoue."""
        # Arrange
        livre_id = str(ObjectId())

        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            # Mock du service retournant erreur de scraping
            mock_migration_service.update_from_babelio_url = AsyncMock(
                return_value={"success": False, "error": "Page introuvable"}
            )

            # Act
            response = client.post(
                "/api/babelio-migration/update-from-url",
                json={
                    "item_id": livre_id,
                    "babelio_url": "https://www.babelio.com/livres/auteur/titre/999999",
                    "item_type": "livre",
                },
            )

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"
