"""Tests TDD pour les endpoints de contrôle Babelio (Issue #254).

Tests pour :
- GET /api/babelio/status
- GET /api/babelio/cache/entries
- DELETE /api/babelio/cache/{entry_id}
- DELETE /api/babelio/cache
- GET /api/babelio/requests/recent
- POST /api/babelio/probe (Issue #351)
"""

from unittest.mock import AsyncMock, MagicMock, patch

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
        mock.get_cookie_age_sec.return_value = None
        mock.cookie_max_age_sec = 300.0
        mock.probe_reachability = AsyncMock(return_value="reachable")
        mock.get_circuit_reason.return_value = None
        mock.get_last_probe.return_value = None
        yield mock


@pytest.fixture
def mock_cache_service(tmp_path):
    from back_office_lmelp.services.babelio_cache_service import BabelioCacheService

    svc = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    with patch("back_office_lmelp.app.babelio_service") as mock_svc:
        mock_svc.cache_service = svc
        mock_svc.get_recent_requests.return_value = []
        mock_svc.min_interval = 2.0
        mock_svc.get_cookie_age_sec.return_value = None
        mock_svc.cookie_max_age_sec = 300.0
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


def test_babelio_status_unknown_when_no_recent_requests(client, mock_babelio_service):
    """GET /api/babelio/status returns overall='unknown' when no request was ever attempted.

    Issue #287: an empty buffer (fresh restart, or everything served from cache)
    must NOT be reported as "ok" — that falsely implies Babelio was reached
    successfully. The frontend already handles "unknown" (badge "❓ Inconnu").
    """
    mock_babelio_service.get_recent_requests.return_value = []
    response = client.get("/api/babelio/status")
    data = response.json()
    assert data["overall"] == "unknown"


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


def test_babelio_status_without_live_check_does_not_probe(client, mock_babelio_service):
    """GET /api/babelio/status (sans paramètre) ne touche pas au réseau.

    Le polling automatique (30s) du frontend ne doit jamais contacter Babelio,
    même par un simple essai TCP.
    """
    client.get("/api/babelio/status")
    mock_babelio_service.probe_reachability.assert_not_called()


def test_babelio_status_live_check_runs_tcp_probe(client, mock_babelio_service):
    """GET /api/babelio/status?live_check=true lance l'essai TCP (5 s)."""
    from back_office_lmelp.services.babelio_service import PROBE_TIMEOUT_SEC

    client.get("/api/babelio/status?live_check=true")
    mock_babelio_service.probe_reachability.assert_awaited_once_with(
        timeout_sec=PROBE_TIMEOUT_SEC
    )


def test_babelio_status_exposes_circuit_reason_and_last_probe(
    client, mock_babelio_service
):
    mock_babelio_service.get_circuit_reason.return_value = "connect_timeout"
    mock_babelio_service.get_last_probe.return_value = {
        "reachable": False,
        "checked_at": 1763220000.0,
        "duration_ms": 5001.2,
    }

    data = client.get("/api/babelio/status").json()

    assert data["circuit_reason"] == "connect_timeout"
    assert data["last_probe"]["reachable"] is False


def _fake_connection() -> tuple[MagicMock, MagicMock]:
    writer = MagicMock()
    writer.wait_closed = AsyncMock()
    return MagicMock(), writer


def test_babelio_status_live_check_sends_no_http_request(client):
    """« Rafraîchir » ne doit plus envoyer de requête HTTP à Babelio."""
    from back_office_lmelp.services.babelio_service import BabelioService

    service = BabelioService()
    with (
        patch("back_office_lmelp.app.babelio_service", service),
        patch.object(service, "_send", new=AsyncMock()) as send,
        patch(
            "asyncio.open_connection",
            new=AsyncMock(return_value=_fake_connection()),
        ),
    ):
        data = client.get("/api/babelio/status?live_check=true").json()

    send.assert_not_awaited()
    assert data["last_probe"]["reachable"] is True
    assert data["recent_requests_count"] == 0


# ── POST /api/babelio/probe ───────────────────────────────────────────────────


def test_babelio_probe_endpoint_uses_short_precheck_timeout(
    client, mock_babelio_service
):
    from back_office_lmelp.services.babelio_service import (
        PRECHECK_PROBE_TIMEOUT_SEC,
    )

    mock_babelio_service.probe_reachability = AsyncMock(return_value="unreachable")
    mock_babelio_service._circuit_open = True
    mock_babelio_service.get_circuit_reason.return_value = "connect_timeout"

    response = client.post("/api/babelio/probe")

    assert response.status_code == 200
    mock_babelio_service.probe_reachability.assert_awaited_once_with(
        timeout_sec=PRECHECK_PROBE_TIMEOUT_SEC
    )
    assert response.json() == {
        "reachable": False,
        "circuit_open": True,
        "circuit_reason": "connect_timeout",
    }


def test_babelio_probe_endpoint_reports_reachable(client, mock_babelio_service):
    mock_babelio_service.probe_reachability = AsyncMock(return_value="reachable")
    mock_babelio_service._circuit_open = False
    mock_babelio_service.get_circuit_reason.return_value = None

    data = client.post("/api/babelio/probe").json()

    assert data["reachable"] is True
    assert data["circuit_open"] is False


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
