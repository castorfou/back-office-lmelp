"""Un appel Babelio refusé (cookie périmé, circuit ouvert) répond 403, pas 500.

Le refus est volontaire : le serveur n'envoie pas à Babelio une requête vouée
au 403, que Babelio transforme en ban IP. Le frontend doit pouvoir le distinguer
d'une panne serveur et inviter à coller un cookie frais.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.services.babelio_service import babelio_service


BABELIO_URL = "https://www.babelio.com/livres/Hassaine-Je/2033456"


@pytest.fixture
def stale_cookie(monkeypatch):
    monkeypatch.setattr(babelio_service, "cache_service", None)
    monkeypatch.setattr(babelio_service, "min_interval", 0)
    babelio_service.set_cookie("jstsToken=<REDACTED>")
    monkeypatch.setattr(babelio_service, "cookie_max_age_sec", 0)
    yield
    babelio_service.set_cookie(None)


@pytest.mark.parametrize(
    ("endpoint", "body"),
    [
        ("/api/babelio/extract-from-url", {"babelio_url": BABELIO_URL}),
        (
            "/api/babelio/extract-cover-url",
            {"babelio_url": BABELIO_URL, "expected_title": "Je"},
        ),
    ],
)
def test_stale_cookie_answers_403_without_calling_babelio(stale_cookie, endpoint, body):
    send = AsyncMock(side_effect=AssertionError("requête HTTP émise"))
    with patch.object(babelio_service, "_send", new=send):
        response = TestClient(app).post(endpoint, json=body)

    assert response.status_code == 403
    assert response.json()["status"] == "blocked"
    assert "cookie frais" in response.json()["message"]
    send.assert_not_awaited()
