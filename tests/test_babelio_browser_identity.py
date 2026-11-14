"""Les requêtes Babelio portent l'identité du navigateur qui a fourni le cookie.

Babelio émet le jstsToken pour le navigateur qui a résolu son défi anti-robots.
Présenté par un client à l'identité différente (autre User-Agent, empreinte
TLS de Python), le jeton trahit un robot et l'IP est bannie dès la première
requête. Le serveur reprend donc le User-Agent et l'Accept-Language du
navigateur, captés à l'enregistrement du cookie.

Test contre un vrai serveur local : un mock ne verrait pas les en-têtes
réellement envoyés sur le réseau.
"""

import json

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

import back_office_lmelp.services.babelio_service as babelio_module


BROWSER_UA = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:159.0) Gecko/20100101 Firefox/159.0"
)
BROWSER_LANGUAGE = "fr,en-US;q=0.9,en;q=0.8"
COOKIE = "jstsToken=<REDACTED>; PHPSESSID=<REDACTED>"


async def _echo_headers(request: web.Request) -> web.Response:
    return web.Response(text=json.dumps(dict(request.headers)))


async def _start_echo_server() -> TestServer:
    app = web.Application()
    app.router.add_get("/livres/Test/1", _echo_headers)
    server = TestServer(app)
    await server.start_server()
    return server


@pytest.mark.asyncio
async def test_fetch_page_sends_browser_identity():
    server = await _start_echo_server()
    service = babelio_module.BabelioService()
    service.min_interval = 0
    service.set_cookie(COOKIE, user_agent=BROWSER_UA, accept_language=BROWSER_LANGUAGE)

    try:
        html = await service._fetch_page(str(server.make_url("/livres/Test/1")))
    finally:
        await service.close()
        await server.close()

    sent = {k.lower(): v for k, v in json.loads(html).items()}
    assert sent["user-agent"] == BROWSER_UA
    assert sent["accept-language"] == BROWSER_LANGUAGE
    assert sent["cookie"] == COOKIE
    # En-têtes propres à Firefox, absents d'un client aiohttp
    assert sent["priority"] == "u=0, i"
    assert "zstd" in sent["accept-encoding"]


async def _echo_headers_as_search_results(request: web.Request) -> web.Response:
    return web.Response(text=json.dumps([{"headers": dict(request.headers)}]))


@pytest.mark.asyncio
async def test_search_sends_browser_identity():
    app = web.Application()
    app.router.add_post("/aj_recherche.php", _echo_headers_as_search_results)
    server = TestServer(app)
    await server.start_server()
    service = babelio_module.BabelioService()
    service.min_interval = 0
    service.base_url = str(server.make_url("")).rstrip("/")
    service.set_cookie(COOKIE, user_agent=BROWSER_UA, accept_language=BROWSER_LANGUAGE)

    try:
        results = await service.search("Ni de lait, ni de laine")
    finally:
        await service.close()
        await server.close()

    sent = {k.lower(): v for k, v in results[0]["headers"].items()}
    assert sent["user-agent"] == BROWSER_UA
    assert sent["accept-language"] == BROWSER_LANGUAGE
    assert sent["cookie"] == COOKIE
    # Requête AJAX same-origin, comme celle du moteur de recherche de Babelio
    assert sent["sec-fetch-mode"] == "cors"
    assert sent["sec-fetch-site"] == "same-origin"
    assert "zstd" in sent["accept-encoding"]
