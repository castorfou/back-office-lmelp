"""Tests TDD pour BabelioService.health_check() (Issue #287).

health_check() effectue une requête légère à la demande (GET page d'accueil
Babelio) via le rate limiter existant, pour permettre à /api/babelio/status
de refléter un état réellement à jour au lieu de dépendre du hasard des
dernières requêtes applicatives.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from back_office_lmelp.services.babelio_service import (
    BabelioBlockedError,
    BabelioService,
)


def _mock_session_ctx(status: int, text: str = "<html>OK</html>"):
    """Construit un mock aiohttp.ClientSession context manager pour un GET donné."""
    mock_response = Mock()
    mock_response.status = status
    mock_response.text = AsyncMock(return_value=text)

    mock_get_ctx = Mock()
    mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = Mock()
    mock_session.get = Mock(return_value=mock_get_ctx)

    mock_session_ctx = Mock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_session_ctx


@pytest.mark.asyncio
async def test_health_check_success_returns_ok_true():
    """health_check() retourne ok=True quand la page d'accueil répond 200."""
    svc = BabelioService()

    with patch("aiohttp.ClientSession", return_value=_mock_session_ctx(200)):
        result = await svc.health_check()

    assert result["ok"] is True


@pytest.mark.asyncio
async def test_health_check_success_logs_request():
    """health_check() alimente le buffer recent_requests en cas de succès."""
    svc = BabelioService()

    with patch("aiohttp.ClientSession", return_value=_mock_session_ctx(200)):
        await svc.health_check()

    recent = svc.get_recent_requests()
    assert len(recent) == 1
    assert recent[0]["status_code"] == 200
    assert recent[0]["cache_hit"] is False


@pytest.mark.asyncio
async def test_health_check_403_returns_ok_false():
    """health_check() retourne ok=False quand Babelio répond 403 (bloqué)."""
    svc = BabelioService()

    with patch("aiohttp.ClientSession", return_value=_mock_session_ctx(403)):
        result = await svc.health_check()

    assert result["ok"] is False


@pytest.mark.asyncio
async def test_health_check_circuit_already_open_returns_ok_false_without_network():
    """health_check() retourne ok=False sans requête HTTP si le circuit est déjà ouvert."""
    svc = BabelioService()
    svc._circuit_open = True

    with patch("aiohttp.ClientSession") as mock_session_cls:
        result = await svc.health_check()

    mock_session_cls.assert_not_called()
    assert result["ok"] is False


@pytest.mark.asyncio
async def test_health_check_circuit_already_open_logs_request():
    """health_check() journalise quand même une entrée si le circuit est déjà ouvert.

    Sans ce log, /api/babelio/status resterait "unknown" au lieu de "blocked_403"
    même quand on sait déjà (via le circuit breaker) que Babelio est bloqué.
    """
    svc = BabelioService()
    svc._circuit_open = True

    with patch("aiohttp.ClientSession"):
        await svc.health_check()

    recent = svc.get_recent_requests()
    assert len(recent) == 1
    assert recent[0]["status_code"] == 403


@pytest.mark.asyncio
async def test_health_check_timeout_returns_ok_false():
    """health_check() retourne ok=False (sans exception) sur timeout réseau."""
    svc = BabelioService()

    with patch("aiohttp.ClientSession", side_effect=TimeoutError("boom")):
        result = await svc.health_check()

    assert result["ok"] is False


@pytest.mark.asyncio
async def test_health_check_timeout_logs_request_with_status_zero():
    """health_check() journalise un status_code=0 sur timeout (même pattern que search())."""
    svc = BabelioService()

    with patch("aiohttp.ClientSession", side_effect=TimeoutError("boom")):
        await svc.health_check()

    recent = svc.get_recent_requests()
    assert len(recent) == 1
    assert recent[0]["status_code"] == 0


@pytest.mark.asyncio
async def test_health_check_does_not_raise_babelio_blocked_error():
    """health_check() ne doit jamais laisser fuiter BabelioBlockedError à l'appelant.

    C'est un health check "informatif" : l'appelant (endpoint /api/babelio/status)
    ne doit pas planter si Babelio est bloqué, il doit juste voir ok=False.
    """
    svc = BabelioService()

    async def raise_blocked(*_args, **_kwargs):
        raise BabelioBlockedError("403")

    with patch.object(svc, "_fetch_page", side_effect=raise_blocked):
        result = await svc.health_check()

    assert result["ok"] is False
