"""Tests pour l'endpoint /health (Issue #115)."""

from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestHealthEndpoint:
    """Tests pour le endpoint de healthcheck dédié."""

    def test_health_endpoint_exists(self):
        """Test que l'endpoint /health existe."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_correct_format(self):
        """Test que /health retourne le format attendu."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_health_endpoint_is_fast(self):
        """Test que /health répond rapidement (< 100ms)."""
        import time

        client = TestClient(app)
        start = time.time()
        response = client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        # Le healthcheck doit être rapide (< 100ms même avec overhead test)
        assert duration < 0.1

    def test_root_endpoint_still_works(self):
        """Test que l'endpoint / continue de fonctionner (backward compatibility)."""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Back-office LMELP API" in data["message"]
