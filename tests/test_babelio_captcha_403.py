"""Un 403 « Vérification de sécurité » de Babelio ouvre le circuit pour captcha.

Un cookie copié sans être connecté au compte Babelio (ni `id_user` ni `bbac`)
reçoit dès la première requête un 403 dont le corps est une page de
vérification humaine (curseur à glisser, `x-debug-message: 003`). Ce n'est pas
un cookie expiré : il faut se connecter à Babelio, puis recopier un cookie.
Le disjoncteur note donc le motif `captcha`, exposé par GET /api/babelio/status,
pour que l'interface affiche la bonne consigne.

Test contre un vrai serveur local : un mock de `_send()` ne verrait ni le corps
ni les en-têtes réellement reçus par curl_cffi.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from fastapi.testclient import TestClient

import back_office_lmelp.services.babelio_service as babelio_module


CAPTCHA_PAGE = (
    Path(__file__).parent / "fixtures" / "babelio_captcha_403.html"
).read_text(encoding="utf-8")
PLAIN_403_PAGE = "<html><body><h1>Accès refusé</h1></body></html>"
ANONYMOUS_COOKIE = "jstsToken=AbCd%2FeF; PHPSESSID=fakesession123; disclaimer=1"


async def _captcha(request: web.Request) -> web.Response:
    return web.Response(
        status=403,
        text=CAPTCHA_PAGE,
        content_type="text/html",
        charset="utf-8",
        headers={
            "x-debug-message": "003",
            "set-cookie": "jstsToken=NEW; Max-Age=300; path=/; secure",
        },
    )


async def _plain_403(request: web.Request) -> web.Response:
    return web.Response(status=403, text=PLAIN_403_PAGE, content_type="text/html")


async def _start(
    handler: Callable[[web.Request], Awaitable[web.Response]],
) -> TestServer:
    app = web.Application()
    app.router.add_post("/aj_recherche.php", handler)
    app.router.add_get("/livres/Test/1", handler)
    server = TestServer(app)
    await server.start_server()
    return server


def _service(server: TestServer) -> babelio_module.BabelioService:
    service = babelio_module.BabelioService()
    service.min_interval = 0
    service.base_url = str(server.make_url("")).rstrip("/")
    service.set_cookie(ANONYMOUS_COOKIE, user_agent="UA-test")
    return service


@pytest.mark.asyncio
async def test_search_captcha_403_opens_circuit_for_captcha():
    server = await _start(_captcha)
    service = _service(server)
    try:
        with pytest.raises(babelio_module.BabelioBlockedError):
            await service.search("Paradisi Gloria")
        # La requête suivante ne part pas, et dit quoi faire
        with pytest.raises(babelio_module.BabelioBlockedError) as following:
            await service.search("Saint Lucky Luke")
    finally:
        await server.close()

    assert service.get_circuit_reason() == babelio_module.CIRCUIT_REASON_CAPTCHA
    assert "vérification humaine" in str(following.value)
    assert "connectez-vous à Babelio" in str(following.value)


@pytest.mark.asyncio
async def test_fetch_page_captcha_403_opens_circuit_for_captcha():
    server = await _start(_captcha)
    service = _service(server)
    try:
        with pytest.raises(babelio_module.BabelioBlockedError):
            await service._fetch_page(str(server.make_url("/livres/Test/1")))
    finally:
        await server.close()

    assert service.get_circuit_reason() == babelio_module.CIRCUIT_REASON_CAPTCHA


@pytest.mark.asyncio
async def test_plain_403_keeps_http_403_reason():
    server = await _start(_plain_403)
    service = _service(server)
    try:
        with pytest.raises(babelio_module.BabelioBlockedError):
            await service.search("Paradisi Gloria")
    finally:
        await server.close()

    assert service.get_circuit_reason() == babelio_module.CIRCUIT_REASON_HTTP_403


@pytest.mark.asyncio
async def test_captcha_circuit_closes_with_a_new_cookie_not_with_a_probe():
    service = babelio_module.BabelioService()
    service._open_circuit(babelio_module.CIRCUIT_REASON_CAPTCHA)

    # Babelio répond en TCP : ce n'est pas un ban IP, le captcha demeure
    probe_server = await _start(_plain_403)
    try:
        await service.probe_reachability(
            host=probe_server.host, port=probe_server.port, timeout_sec=1.0
        )
    finally:
        await probe_server.close()
    assert service.get_circuit_reason() == babelio_module.CIRCUIT_REASON_CAPTCHA

    service.set_cookie("jstsToken=fresh; id_user=1")
    assert service.get_circuit_reason() is None


def test_status_exposes_captcha_reason(monkeypatch):
    from back_office_lmelp.app import app
    from back_office_lmelp.services.babelio_service import babelio_service

    monkeypatch.setattr(babelio_service, "_circuit_open", True)
    monkeypatch.setattr(
        babelio_service, "_circuit_reason", babelio_module.CIRCUIT_REASON_CAPTCHA
    )

    body = TestClient(app).get("/api/babelio/status").json()

    assert body["circuit_reason"] == "captcha"
    assert body["overall"] == "captcha"
