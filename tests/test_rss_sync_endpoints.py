"""Tests TDD pour les endpoints de synchronisation RSS (Issue #295).

Tests pour :
- POST /api/rss/sync
- GET /api/rss/logs
- GET /api/rss/logs/{log_id}
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from back_office_lmelp.app import app

    return TestClient(app)


@pytest.fixture
def mock_rss_sync_service():
    with patch("back_office_lmelp.app.rss_sync_service") as mock:
        mock.sync = AsyncMock(
            return_value={
                "status": "success",
                "trigger": "manual",
                "episodes": [],
            }
        )
        yield mock


@pytest.fixture
def mock_mongodb_service():
    with patch("back_office_lmelp.app.mongodb_service") as mock:
        mock.get_rss_download_logs.return_value = []
        mock.get_rss_download_log_by_id.return_value = None
        yield mock


class TestTriggerRssSync:
    def test_post_rss_sync_returns_summary(self, client, mock_rss_sync_service):
        response = client.post("/api/rss/sync", json={"trigger": "manual"})

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_rss_sync_service.sync.assert_awaited_once_with(trigger="manual")

    def test_post_rss_sync_defaults_trigger_to_api(self, client, mock_rss_sync_service):
        response = client.post("/api/rss/sync", json={})

        assert response.status_code == 200
        mock_rss_sync_service.sync.assert_awaited_once_with(trigger="api")

    def test_post_rss_sync_returns_500_on_error(self, client, mock_rss_sync_service):
        mock_rss_sync_service.sync.side_effect = Exception("boom")

        response = client.post("/api/rss/sync", json={"trigger": "manual"})

        assert response.status_code == 500


class TestGetRssSyncLogs:
    def test_get_rss_logs_returns_list(self, client, mock_mongodb_service):
        mock_mongodb_service.get_rss_download_logs.return_value = [
            {"_id": "1", "trigger": "manual"}
        ]

        response = client.get("/api/rss/logs")

        assert response.status_code == 200
        assert response.json() == [{"_id": "1", "trigger": "manual"}]

    def test_get_rss_logs_returns_500_on_error(self, client, mock_mongodb_service):
        mock_mongodb_service.get_rss_download_logs.side_effect = Exception("boom")

        response = client.get("/api/rss/logs")

        assert response.status_code == 500


class TestGetRssSyncLogDetail:
    def test_get_rss_log_detail_returns_log(self, client, mock_mongodb_service):
        mock_mongodb_service.get_rss_download_log_by_id.return_value = {
            "_id": "1",
            "trigger": "manual",
        }

        response = client.get("/api/rss/logs/1")

        assert response.status_code == 200
        assert response.json()["_id"] == "1"

    def test_get_rss_log_detail_returns_404_when_not_found(
        self, client, mock_mongodb_service
    ):
        mock_mongodb_service.get_rss_download_log_by_id.return_value = None

        response = client.get("/api/rss/logs/unknown")

        assert response.status_code == 404
