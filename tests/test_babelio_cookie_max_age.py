"""Durée de validité du cookie Babelio (Issue #370).

Mesure grandeur nature : un cookie connecté (``PHPSESSID``, avec ou sans
``jstsToken``) a servi jusqu'à 1 h 51 d'âge et 30 min d'inactivité, recherche
et pages, sans 403. Le serveur l'accepte donc 30 min
(``BABELIO_COOKIE_MAX_AGE_SEC``), décomptées depuis son enregistrement : âge
et inactivité restent dans ce qui a été mesuré. Le ``jstsToken`` ne change
rien à cette durée.
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
BOTH_COOKIES = pytest.mark.parametrize(
    "cookie", [SESSION_COOKIE, JSTS_COOKIE], ids=["session", "jstsToken"]
)


@pytest.fixture
def service(monkeypatch):
    monkeypatch.delenv("BABELIO_COOKIE_MAX_AGE_SEC", raising=False)
    svc = babelio_module.BabelioService()
    svc.min_interval = 0
    svc.cache_service = None
    return svc


def _age_cookie(svc: babelio_module.BabelioService, age_sec: float) -> None:
    assert svc._cookie_set_at is not None
    svc._cookie_set_at = time.time() - age_sec


@BOTH_COOKIES
@pytest.mark.asyncio
async def test_cookie_still_sent_after_25_minutes(service, cookie):
    """Un cookie de 25 min part encore, jstsToken ou pas."""
    service.set_cookie(cookie)
    _age_cookie(service, 25 * 60)
    send = AsyncMock(
        return_value=babelio_module.BabelioResponse(
            status=200, body="<html></html>".encode("cp1252")
        )
    )

    with patch.object(service, "_send", send):
        await service._fetch_page(PAGE_URL)

    send.assert_awaited_once()


@BOTH_COOKIES
@pytest.mark.asyncio
async def test_cookie_refused_after_30_minutes(service, cookie):
    """Au-delà de 30 min, aucune requête ne part (403 évité)."""
    service.set_cookie(cookie)
    _age_cookie(service, 30 * 60 + 1)
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


@pytest.mark.parametrize(("age", "expired"), [(25 * 60, False), (30 * 60 + 1, True)])
def test_status_reports_30_minute_lifetime(client, service, age, expired):
    """Le panneau Cookie Babelio décompte la même durée que le serveur."""
    service.set_cookie(SESSION_COOKIE)
    _age_cookie(service, age)

    data = client.get("/api/babelio/status").json()

    assert data["cookie_max_age_sec"] == 1800
    assert data["cookie_expired"] is expired


@pytest.mark.asyncio
async def test_403_records_cookie_age(service):
    """Chaque 403 note l'âge du cookie et la limite appliquée : de quoi revoir
    la durée sur les usages réels, jamais par des requêtes répétées."""
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
    assert captured["cookie_max_age_sec"] == 1800
