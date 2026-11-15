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
        """Test que /health répond rapidement (médiane < 100ms)."""
        import statistics
        import time

        client = TestClient(app)
        # La première requête paie l'initialisation du client de test
        assert client.get("/health").status_code == 200

        durations = []
        for _ in range(5):
            start = time.perf_counter()
            response = client.get("/health")
            durations.append(time.perf_counter() - start)
            assert response.status_code == 200

        # Médiane : une pause ponctuelle du runner CI ne fait pas échouer le test
        assert statistics.median(durations) < 0.1

    def test_root_endpoint_still_works(self):
        """Test que l'endpoint / continue de fonctionner (backward compatibility)."""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "lmelp API" in data["message"]
