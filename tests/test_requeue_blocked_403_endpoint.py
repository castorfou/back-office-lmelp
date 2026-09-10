"""Tests TDD pour l'endpoint requeue-blocked-403 - Issue #304.

Action groupée qui libère tous les cas problématiques bloqués par un 403
Babelio transitoire (cookie expiré), pour qu'ils soient repris au prochain
run du batch de migration.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestRequeueBlocked403Endpoint:
    """Tests pour l'endpoint POST /api/babelio-migration/requeue-blocked-403."""

    @pytest.fixture
    def client(self):
        """Fixture pour le client FastAPI."""
        from back_office_lmelp.app import app

        return TestClient(app)

    def test_should_requeue_blocked_403_cases_via_api(self, client):
        """Test TDD: L'endpoint doit appeler le service et retourner le compte."""
        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            mock_migration_service.requeue_blocked_403_cases.return_value = 5

            response = client.post("/api/babelio-migration/requeue-blocked-403")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["requeued_count"] == 5

            mock_migration_service.requeue_blocked_403_cases.assert_called_once_with()

    def test_should_return_success_when_zero_cases_to_requeue(self, client):
        """Test TDD: 0 cas libérés doit rester un succès (pas une erreur)."""
        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            mock_migration_service.requeue_blocked_403_cases.return_value = 0

            response = client.post("/api/babelio-migration/requeue-blocked-403")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["requeued_count"] == 0

    def test_should_return_500_when_service_raises(self, client):
        """Test TDD: une exception du service doit retourner 500."""
        with patch(
            "back_office_lmelp.app.babelio_migration_service"
        ) as mock_migration_service:
            mock_migration_service.requeue_blocked_403_cases.side_effect = RuntimeError(
                "MongoDB not connected"
            )

            response = client.post("/api/babelio-migration/requeue-blocked-403")

            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "error"
