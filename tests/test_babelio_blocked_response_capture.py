"""Les réponses 403 de Babelio sont conservées pour diagnostic.

Un 403 de Babelio peut être un refus sec, une page de défi anti-robots ou un
message explicite : seul le contenu de la réponse permet de savoir quoi
corriger. Le service garde les dernières réponses 403 (en-têtes reçus, début
du corps, en-têtes envoyés avec le cookie masqué), exposées par
GET /api/babelio/blocked-responses. Aucune requête supplémentaire.

Test contre un vrai serveur local : un mock ne verrait ni les en-têtes
réellement envoyés ni ceux réellement reçus.
"""

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

import back_office_lmelp.services.babelio_service as babelio_module


CHALLENGE_PAGE = "<html><body><h1>Accès refusé</h1><p>Vérification JS</p></body></html>"
COOKIE = "jstsToken=SECRET-TOKEN; PHPSESSID=SECRET-SESSION; p=FR"


async def _refuse(request: web.Request) -> web.Response:
    return web.Response(
        status=403,
        text=CHALLENGE_PAGE,
        content_type="text/html",
        headers={"X-Blocked-By": "test-waf"},
    )


@pytest.mark.asyncio
async def test_403_response_is_kept_with_cookie_redacted():
    app = web.Application()
    app.router.add_get("/livres/Test/1", _refuse)
    server = TestServer(app)
    await server.start_server()
    service = babelio_module.BabelioService()
    service.min_interval = 0
    service.set_cookie(COOKIE, user_agent="UA-test")

    try:
        with pytest.raises(babelio_module.BabelioBlockedError):
            await service._fetch_page(str(server.make_url("/livres/Test/1")))
    finally:
        await server.close()

    [captured] = service.get_blocked_responses()
    assert captured["status"] == 403
    assert captured["method"] == "GET"
    assert captured["url"].endswith("/livres/Test/1")
    assert "Vérification JS" in captured["body"]
    assert captured["response_headers"]["x-blocked-by"] == "test-waf"
    sent = captured["request_headers"]
    assert sent["User-Agent"] == "UA-test"
    # Le cookie n'est jamais conservé en clair : seulement les noms
    assert "SECRET" not in str(captured)
    assert sent["Cookie"] == "jstsToken=<REDACTED>; PHPSESSID=<REDACTED>; p=<REDACTED>"


def test_blocked_responses_endpoint_lists_captured_403(monkeypatch):
    from fastapi.testclient import TestClient

    from back_office_lmelp.app import app
    from back_office_lmelp.services.babelio_service import (
        BabelioResponse,
        babelio_service,
    )

    monkeypatch.setattr(
        babelio_service,
        "_blocked_responses",
        type(babelio_service._blocked_responses)(maxlen=10),
    )
    babelio_service._record_blocked_response(
        "POST",
        "https://www.babelio.com/aj_recherche.php",
        {"Cookie": COOKIE, "User-Agent": "UA-test"},
        BabelioResponse(status=403, body=CHALLENGE_PAGE.encode("utf-8")),
    )

    response = TestClient(app).get("/api/babelio/blocked-responses")

    assert response.status_code == 200
    [entry] = response.json()
    assert entry["url"] == "https://www.babelio.com/aj_recherche.php"
    assert "Vérification JS" in entry["body"]
    assert "SECRET" not in response.text
