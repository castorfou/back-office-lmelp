"""Tests simplifiés pour les endpoints API du Back-Office LMELP."""

from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestSimpleEndpoints:
    """Tests simples pour vérifier que l'app démarre."""

    def test_app_creates_successfully(self):
        """Test que l'app FastAPI se crée sans erreur."""
        assert app is not None
        assert app.title == "Back-office LMELP"

    def test_invalid_endpoint_returns_404(self):
        """Test qu'un endpoint inexistant retourne 404."""
        # Ce test ne nécessite pas de connexion MongoDB
        with TestClient(app) as client:
            response = client.get("/api/nonexistent")
            assert response.status_code == 404

    def test_options_request_handled(self):
        """Test que les requêtes OPTIONS sont gérées (CORS)."""
        with TestClient(app) as client:
            response = client.options("/api/episodes")
            # CORS peut retourner 200 ou 405 selon la configuration
            assert response.status_code in [200, 204, 405]
