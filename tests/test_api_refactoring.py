"""Tests pour les endpoints API avec la nouvelle logique."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.back_office_lmelp.app import app


class TestAPIRefactoring:
    """Tests pour les endpoints API avec nouvelle logique."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    @patch("src.back_office_lmelp.app.mongodb_service")
    def test_update_episode_title_uses_new_logic(self, mock_service):
        """Test que l'endpoint titre utilise la nouvelle logique."""
        # Mock de la nouvelle méthode
        mock_service.update_episode_title_new.return_value = True
        mock_service.get_episode_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439011"
        }

        # Appel de l'endpoint
        response = self.client.put(
            "/api/episodes/507f1f77bcf86cd799439011/title",
            content="Nouveau titre corrigé",
            headers={"Content-Type": "text/plain"},
        )

        # Vérifications
        assert response.status_code == 200
        mock_service.update_episode_title_new.assert_called_once_with(
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "Nouveau titre corrigé",
        )

    @patch("src.back_office_lmelp.app.mongodb_service")
    def test_update_episode_description_uses_new_logic(self, mock_service):
        """Test que l'endpoint description utilise la nouvelle logique."""
        # Mock de la nouvelle méthode
        mock_service.update_episode_description_new.return_value = True
        mock_service.get_episode_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439011"
        }

        # Appel de l'endpoint
        response = self.client.put(
            "/api/episodes/507f1f77bcf86cd799439011",
            content="Nouvelle description corrigée",
            headers={"Content-Type": "text/plain"},
        )

        # Vérifications
        assert response.status_code == 200
        mock_service.update_episode_description_new.assert_called_once_with(
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "Nouvelle description corrigée",
        )
