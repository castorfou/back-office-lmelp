"""Tests TDD pour BabelioService.health_check() (Issue #287).

health_check() effectue une requête légère à la demande (GET page d'accueil
Babelio) via le rate limiter existant, pour permettre à /api/babelio/status
de refléter un état réellement à jour au lieu de dépendre du hasard des
dernières requêtes applicatives.
"""

from unittest.mock import AsyncMock, patch

import pytest

from back_office_lmelp.services.babelio_service import (
    BabelioBlockedError,
    BabelioResponse,
    BabelioService,
)


def _send_returning(status: int, text: str = "<html>OK</html>") -> AsyncMock:
    """Simule le point de sortie HTTP unique de BabelioService."""
    return AsyncMock(
        return_value=BabelioResponse(status=status, body=text.encode("cp1252"))
    )


@pytest.mark.asyncio
async def test_health_check_success_returns_ok_true():
    """health_check() retourne ok=True quand la page d'accueil répond 200."""
    svc = BabelioService()

    with patch.object(svc, "_send", new=_send_returning(200)):
        result = await svc.health_check()

    assert result["ok"] is True


@pytest.mark.asyncio
async def test_health_check_success_logs_request():
    """health_check() alimente le buffer recent_requests en cas de succès."""
    svc = BabelioService()

    with patch.object(svc, "_send", new=_send_returning(200)):
        await svc.health_check()

    recent = svc.get_recent_requests()
    assert len(recent) == 1
    assert recent[0]["status_code"] == 200
    assert recent[0]["cache_hit"] is False


@pytest.mark.asyncio
async def test_health_check_403_returns_ok_false():
    """health_check() retourne ok=False quand Babelio répond 403 (bloqué)."""
    svc = BabelioService()

    with patch.object(svc, "_send", new=_send_returning(403)):
        result = await svc.health_check()

    assert result["ok"] is False


@pytest.mark.asyncio
async def test_health_check_circuit_already_open_returns_ok_false_without_network():
    """health_check() retourne ok=False sans requête HTTP si le circuit est déjà ouvert."""
    svc = BabelioService()
    svc._circuit_open = True

    with patch.object(svc, "_send", new=AsyncMock()) as send:
        result = await svc.health_check()

    send.assert_not_awaited()
    assert result["ok"] is False


@pytest.mark.asyncio
async def test_health_check_circuit_already_open_logs_request():
    """health_check() journalise quand même une entrée si le circuit est déjà ouvert.

    Sans ce log, /api/babelio/status resterait "unknown" au lieu de "blocked_403"
    même quand on sait déjà (via le circuit breaker) que Babelio est bloqué.
    """
    svc = BabelioService()
    svc._circuit_open = True

    with patch.object(svc, "_send", new=AsyncMock()):
        await svc.health_check()

    recent = svc.get_recent_requests()
    assert len(recent) == 1
    assert recent[0]["status_code"] == 403


@pytest.mark.asyncio
async def test_health_check_timeout_returns_ok_false():
    """health_check() retourne ok=False (sans exception) sur timeout réseau."""
    svc = BabelioService()

    with patch.object(svc, "_send", new=AsyncMock(side_effect=TimeoutError("boom"))):
        result = await svc.health_check()

    assert result["ok"] is False


@pytest.mark.asyncio
async def test_health_check_timeout_logs_request_with_status_zero():
    """health_check() journalise un status_code=0 sur timeout (même pattern que search())."""
    svc = BabelioService()

    with patch.object(svc, "_send", new=AsyncMock(side_effect=TimeoutError("boom"))):
        await svc.health_check()

    recent = svc.get_recent_requests()
    assert len(recent) == 1
    assert recent[0]["status_code"] == 0


@pytest.mark.asyncio
async def test_health_check_bypasses_cache_and_logs_non_cache_hit(tmp_path):
    """Test TDD (Issue #304): health_check() doit contourner le cache de la page
    d'accueil et journaliser un vrai résultat réseau (cache_hit=False).

    Bug racine: la page d'accueil Babelio est mise en cache 24h (comme toute
    autre page scrapée) — un health_check() ultérieur sert alors ce cache et
    journalise cache_hit=True, jamais filtré comme "requête récente réelle"
    par /api/babelio/status (qui exclut explicitement les cache_hit). Résultat:
    l'état du service Babelio reste bloqué à "Inconnu" tant que le cache de la
    page d'accueil n'expire pas, même après un clic sur "Rafraîchir".
    """
    from back_office_lmelp.services.babelio_cache_service import BabelioCacheService

    svc = BabelioService()
    svc.cache_service = BabelioCacheService(cache_dir=tmp_path)

    # Pré-remplir le cache comme si la page d'accueil avait déjà été scrapée
    svc.cache_service.set_cached(
        svc.base_url, "<html>cached</html>", search_type="page"
    )

    with patch.object(svc, "_send", new=_send_returning(200)):
        result = await svc.health_check()

    assert result["ok"] is True
    recent = svc.get_recent_requests()
    assert len(recent) == 1
    assert recent[0]["cache_hit"] is False


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
