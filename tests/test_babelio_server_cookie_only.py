"""Le cookie Babelio vient uniquement du serveur (Issue #350).

Le serveur date le cookie à sa réception (``set_cookie``) et refuse de l'envoyer
une fois périmé. Un cookie joint par le client à une requête échappait à ce
contrôle : quand le serveur n'avait pas de cookie, ce cookie (souvent un vieux
jstsToken gardé par le navigateur) partait vers Babelio, qui répondait 403, puis
bannissait l'IP environ 24 h.
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.services.babelio_service import BabelioResponse, BabelioService


OLD_BROWSER_COOKIE = "jstsToken=old-browser-cookie; p=FR; disclaimer=1"


@pytest.fixture
def service():
    svc = BabelioService()
    svc.min_interval = 0
    return svc


@pytest.fixture
def client(service):
    from back_office_lmelp.app import app, babelio_migration_service

    with (
        patch("back_office_lmelp.app.babelio_service", service),
        patch.object(babelio_migration_service, "babelio_service", service),
    ):
        yield TestClient(app)


def _sent_cookies(send_mock: AsyncMock) -> list[str]:
    return [call.args[2].get("Cookie", "") for call in send_mock.call_args_list]


def test_verify_babelio_ignores_cookie_sent_by_client(client, service):
    """Sans cookie serveur, le cookie joint à la requête ne part pas vers Babelio."""
    send = AsyncMock(return_value=BabelioResponse(status=200, body=b"[]"))
    with patch.object(service, "_send", send):
        response = client.post(
            "/api/verify-babelio",
            json={
                "type": "author",
                "name": "Annie Ernaux",
                "babelio_cookies": OLD_BROWSER_COOKIE,
            },
        )

    assert response.status_code == 200
    assert send.await_count >= 1
    assert all("old-browser-cookie" not in c for c in _sent_cookies(send))


def test_extract_from_url_ignores_cookie_sent_by_client(client, service):
    """Le scraping d'une page n'utilise pas non plus le cookie du client."""
    send = AsyncMock(
        return_value=BabelioResponse(
            status=200, body="<html><h1>Titre</h1></html>".encode("cp1252")
        )
    )
    with patch.object(service, "_send", send):
        client.post(
            "/api/babelio/extract-from-url",
            json={
                "babelio_url": "https://www.babelio.com/livres/Ernaux-Les-annees/1",
                "babelio_cookies": OLD_BROWSER_COOKIE,
            },
        )

    assert send.await_count >= 1
    assert all("old-browser-cookie" not in c for c in _sent_cookies(send))


def test_status_reports_cookie_age_and_expiry(client, service):
    """Le statut expose l'âge du cookie serveur et s'il est périmé."""
    service.set_cookie("jstsToken=fresh")
    data = client.get("/api/babelio/status").json()
    assert data["cookie_active"] is True
    assert data["cookie_max_age_sec"] == service.cookie_max_age_sec
    assert 0 <= data["cookie_age_sec"] < 5
    assert data["cookie_expired"] is False

    service._cookie_set_at = time.time() - service.cookie_max_age_sec - 1
    data = client.get("/api/babelio/status").json()
    assert data["cookie_active"] is True
    assert data["cookie_age_sec"] >= service.cookie_max_age_sec
    assert data["cookie_expired"] is True


def test_status_without_cookie(client, service):
    data = client.get("/api/babelio/status").json()
    assert data["cookie_active"] is False
    assert data["cookie_age_sec"] is None
    assert data["cookie_expired"] is False
