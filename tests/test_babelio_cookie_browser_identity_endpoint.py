"""POST /api/babelio/cookie retient l'identité du navigateur qui l'envoie.

Cette requête part du navigateur qui vient de récupérer le cookie sur
babelio.com : son User-Agent et son Accept-Language sont ceux pour lesquels
Babelio a émis le jstsToken.
"""

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.services.babelio_service import babelio_service


BROWSER_UA = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:159.0) Gecko/20100101 Firefox/159.0"
)
BROWSER_LANGUAGE = "fr,en-US;q=0.9,en;q=0.8"


@pytest.fixture(autouse=True)
def _reset_cookie():
    yield
    babelio_service.set_cookie(None)


def test_cookie_endpoint_records_browser_identity():
    client = TestClient(app)
    response = client.post(
        "/api/babelio/cookie",
        json={"cookie": "jstsToken=<REDACTED>"},
        headers={"User-Agent": BROWSER_UA, "Accept-Language": BROWSER_LANGUAGE},
    )
    assert response.status_code == 200

    status = client.get("/api/babelio/status").json()
    assert status["browser_user_agent"] == BROWSER_UA
    assert status["browser_accept_language"] == BROWSER_LANGUAGE


def test_clearing_cookie_forgets_browser_identity():
    client = TestClient(app)
    client.post(
        "/api/babelio/cookie",
        json={"cookie": "jstsToken=<REDACTED>"},
        headers={"User-Agent": BROWSER_UA},
    )
    client.delete("/api/babelio/cookie")

    assert client.get("/api/babelio/status").json()["browser_user_agent"] is None
