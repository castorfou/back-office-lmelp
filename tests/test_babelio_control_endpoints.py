"""Tests TDD pour les endpoints de contrôle Babelio (Issue #254).

Tests pour :
- GET /api/babelio/status
- GET /api/babelio/cache/entries
- DELETE /api/babelio/cache/{entry_id}
- DELETE /api/babelio/cache
- GET /api/babelio/requests/recent
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from back_office_lmelp.app import app

    return TestClient(app)


@pytest.fixture
def mock_babelio_service():
    with patch("back_office_lmelp.app.babelio_service") as mock:
        mock.get_recent_requests.return_value = []
        mock.min_interval = 2.0
        yield mock


@pytest.fixture
def mock_cache_service(tmp_path):
    from back_office_lmelp.services.babelio_cache_service import BabelioCacheService

    svc = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    with patch("back_office_lmelp.app.babelio_service") as mock_svc:
        mock_svc.cache_service = svc
        mock_svc.get_recent_requests.return_value = []
        mock_svc.min_interval = 2.0
        yield mock_svc, svc


# ── GET /api/babelio/status ───────────────────────────────────────────────────


def test_babelio_status_endpoint_exists(client, mock_babelio_service):
    """GET /api/babelio/status returns 200."""
    response = client.get("/api/babelio/status")
    assert response.status_code == 200


def test_babelio_status_has_required_fields(client, mock_babelio_service):
    """GET /api/babelio/status response contains all required fields."""
    response = client.get("/api/babelio/status")
    data = response.json()
    assert "overall" in data
    assert "cache_entries" in data
    assert "recent_requests_count" in data
    assert "min_interval_sec" in data


def test_babelio_status_overall_values(client, mock_babelio_service):
    """GET /api/babelio/status overall is one of the expected values."""
    response = client.get("/api/babelio/status")
    data = response.json()
    assert data["overall"] in {"ok", "captcha", "blocked_403", "degraded", "unknown"}


def test_babelio_status_ok_when_no_errors(client, mock_babelio_service):
    """GET /api/babelio/status returns overall='ok' when no recent errors."""
    mock_babelio_service.get_recent_requests.return_value = [
        {
            "type": "search",
            "term_or_url": "test",
            "status_code": 200,
            "cache_hit": False,
            "duration_ms": 100,
            "timestamp": 1000000,
        }
    ]
    response = client.get("/api/babelio/status")
    data = response.json()
    assert data["overall"] == "ok"


def test_babelio_status_blocked_when_403(client, mock_babelio_service):
    """GET /api/babelio/status returns overall='blocked_403' when last request was 403."""
    mock_babelio_service.get_recent_requests.return_value = [
        {
            "type": "search",
            "term_or_url": "test",
            "status_code": 403,
            "cache_hit": False,
            "duration_ms": 0,
            "timestamp": 1000000,
        }
    ]
    response = client.get("/api/babelio/status")
    data = response.json()
    assert data["overall"] == "blocked_403"


# ── GET /api/babelio/cache/entries ────────────────────────────────────────────


def test_babelio_cache_entries_endpoint_exists(client, mock_cache_service):
    """GET /api/babelio/cache/entries returns 200."""
    mock_svc, _ = mock_cache_service
    response = client.get("/api/babelio/cache/entries")
    assert response.status_code == 200


def test_babelio_cache_entries_returns_list(client, mock_cache_service):
    """GET /api/babelio/cache/entries returns a list."""
    mock_svc, cache = mock_cache_service
    response = client.get("/api/babelio/cache/entries")
    data = response.json()
    assert isinstance(data, list)


def test_babelio_cache_entries_returns_populated_list(client, mock_cache_service):
    """GET /api/babelio/cache/entries shows entries when cache has data."""
    mock_svc, cache = mock_cache_service
    cache.set_cached("Michel Houellebecq", [{"type": "auteurs"}], search_type="search")

    response = client.get("/api/babelio/cache/entries")
    data = response.json()
    assert len(data) == 1
    entry = data[0]
    assert "id" in entry
    assert "key" in entry
    assert "timestamp" in entry
    assert "expired" in entry


# ── DELETE /api/babelio/cache/{entry_id} ─────────────────────────────────────


def test_delete_cache_entry_removes_it(client, mock_cache_service):
    """DELETE /api/babelio/cache/{entry_id} removes the entry."""
    mock_svc, cache = mock_cache_service
    cache.set_cached("to-delete", {"v": 1}, search_type="search")

    entries = cache.list_entries()
    assert len(entries) == 1
    entry_id = entries[0]["id"]

    response = client.delete(f"/api/babelio/cache/{entry_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] is True

    assert cache.list_entries() == []


def test_delete_cache_entry_nonexistent_returns_404(client, mock_cache_service):
    """DELETE /api/babelio/cache/{entry_id} returns 404 for unknown id."""
    mock_svc, cache = mock_cache_service
    response = client.delete("/api/babelio/cache/nonexistent-id-xyz")
    assert response.status_code == 404


# ── DELETE /api/babelio/cache ─────────────────────────────────────────────────


def test_delete_all_cache_clears_everything(client, mock_cache_service):
    """DELETE /api/babelio/cache removes all entries."""
    mock_svc, cache = mock_cache_service
    cache.set_cached("term1", {"v": 1}, search_type="search")
    cache.set_cached("term2", {"v": 2}, search_type="search")

    response = client.delete("/api/babelio/cache")
    assert response.status_code == 200
    data = response.json()
    assert data["deleted_count"] == 2
    assert cache.list_entries() == []


# ── GET /api/babelio/requests/recent ─────────────────────────────────────────


def test_babelio_recent_requests_endpoint_exists(client, mock_babelio_service):
    """GET /api/babelio/requests/recent returns 200."""
    response = client.get("/api/babelio/requests/recent")
    assert response.status_code == 200


def test_babelio_recent_requests_returns_list(client, mock_babelio_service):
    """GET /api/babelio/requests/recent returns a list."""
    response = client.get("/api/babelio/requests/recent")
    data = response.json()
    assert isinstance(data, list)


def test_babelio_recent_requests_returns_populated_list(client, mock_babelio_service):
    """GET /api/babelio/requests/recent returns request entries."""
    mock_babelio_service.get_recent_requests.return_value = [
        {
            "type": "search",
            "term_or_url": "Houellebecq",
            "status_code": 200,
            "cache_hit": False,
            "duration_ms": 345.6,
            "timestamp": 1700000000.0,
        }
    ]
    response = client.get("/api/babelio/requests/recent")
    data = response.json()
    assert len(data) == 1
    assert data[0]["term_or_url"] == "Houellebecq"
    assert data[0]["status_code"] == 200
