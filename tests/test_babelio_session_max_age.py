"""Durée de validité du cookie Babelio selon sa nature (Issue #370).

Un cookie qui porte un ``jstsToken`` vit le temps de ce jeton (environ 5 min,
``BABELIO_COOKIE_MAX_AGE_SEC``). Babelio ne pose plus ce jeton : le cookie
repose alors sur la session PHP (``PHPSESSID``), dont la durée de vie se règle
par ``BABELIO_SESSION_MAX_AGE_SEC``. Le décompte part toujours de
l'enregistrement du cookie.
"""

import time
from unittest.mock import AsyncMock, patch

import pytest

# Le module, pas ses classes : test_babelio_service.py le recharge, et une
# classe importée avant ce rechargement n'est plus celle que le service lève.
import back_office_lmelp.services.babelio_service as babelio_module


SESSION_COOKIE = "PHPSESSID=sess123; id_user=42; bbac=abc; p=FR"
JSTS_COOKIE = "jstsToken=AbCd; PHPSESSID=sess123; id_user=42; p=FR"
PAGE_URL = "https://www.babelio.com/livres/Ernaux-Les-annees/1"


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setenv("BABELIO_COOKIE_MAX_AGE_SEC", "300")
    monkeypatch.setenv("BABELIO_SESSION_MAX_AGE_SEC", "1200")
    svc = babelio_module.BabelioService()
    svc.min_interval = 0
    svc.cache_service = None
    return svc


def _age_cookie(svc: babelio_module.BabelioService, age_sec: float) -> None:
    assert svc._cookie_set_at is not None
    svc._cookie_set_at = time.time() - age_sec


@pytest.mark.asyncio
async def test_session_cookie_still_sent_past_jsts_token_lifetime(service):
    """Sans jstsToken, un cookie de 10 min reste valide si la session dure 20 min."""
    service.set_cookie(SESSION_COOKIE)
    _age_cookie(service, 600)
    send = AsyncMock(
        return_value=babelio_module.BabelioResponse(
            status=200, body="<html></html>".encode("cp1252")
        )
    )

    with patch.object(service, "_send", send):
        await service._fetch_page(PAGE_URL)

    send.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_cookie_refused_past_session_lifetime(service):
    """Au-delà de la durée de session, aucune requête ne part (403 évité)."""
    service.set_cookie(SESSION_COOKIE)
    _age_cookie(service, 1201)
    send = AsyncMock(side_effect=AssertionError("requête HTTP émise"))

    with (
        patch.object(service, "_send", send),
        pytest.raises(babelio_module.BabelioCookieExpiredError),
    ):
        await service._fetch_page(PAGE_URL)

    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_jsts_token_cookie_keeps_token_lifetime(service):
    """Avec un jstsToken, la durée du jeton s'applique toujours."""
    service.set_cookie(JSTS_COOKIE)
    _age_cookie(service, 301)
    send = AsyncMock(side_effect=AssertionError("requête HTTP émise"))

    with (
        patch.object(service, "_send", send),
        pytest.raises(babelio_module.BabelioCookieExpiredError),
    ):
        await service._fetch_page(PAGE_URL)

    send.assert_not_awaited()


@pytest.fixture
def client(service):
    from fastapi.testclient import TestClient

    from back_office_lmelp.app import app

    with patch("back_office_lmelp.app.babelio_service", service):
        yield TestClient(app)


@pytest.mark.parametrize(
    ("cookie", "max_age", "age", "expired"),
    [
        (SESSION_COOKIE, 1200, 600, False),
        (SESSION_COOKIE, 1200, 1201, True),
        (JSTS_COOKIE, 300, 301, True),
    ],
)
def test_status_reports_lifetime_of_stored_cookie(
    client, service, cookie, max_age, age, expired
):
    """Le panneau Cookie Babelio décompte la même durée que le serveur."""
    service.set_cookie(cookie)
    _age_cookie(service, age)

    data = client.get("/api/babelio/status").json()

    assert data["cookie_max_age_sec"] == max_age
    assert data["cookie_expired"] is expired


@pytest.mark.asyncio
async def test_403_records_cookie_age(service):
    """Chaque 403 note l'âge du cookie : la mesure de la durée de session se
    fait sur les usages réels, jamais par des requêtes répétées."""
    from aiohttp import web
    from aiohttp.test_utils import TestServer

    async def refuse(request: web.Request) -> web.Response:
        return web.Response(status=403, text="<html>Refus</html>")

    app = web.Application()
    app.router.add_get("/livres/Test/1", refuse)
    server = TestServer(app)
    await server.start_server()
    service.set_cookie(SESSION_COOKIE)
    _age_cookie(service, 900)

    try:
        with pytest.raises(babelio_module.BabelioBlockedError):
            await service._fetch_page(str(server.make_url("/livres/Test/1")))
    finally:
        await server.close()

    [captured] = service.get_blocked_responses()
    assert 899 <= captured["cookie_age_sec"] < 905
    assert captured["cookie_max_age_sec"] == 1200
