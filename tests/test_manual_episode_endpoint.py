"""Tests de l'endpoint d'ajout manuel d'une émission (Issue #334).

POST /api/episodes/from-radiofrance-page {"url": "<page radiofrance.fr>"}
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.services.manual_episode_service import ManualEpisodeError


PAGE_URL = (
    "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/"
    "le-masque-et-la-plume-du-dimanche-21-juillet-2024-6686255"
)
ENDPOINT = "/api/episodes/from-radiofrance-page"


@pytest.fixture
def client():
    from back_office_lmelp.app import app

    return TestClient(app)


@pytest.fixture
def mock_service():
    with patch("back_office_lmelp.app.manual_episode_service") as mock:
        yield mock


def test_returns_added_episode(client, mock_service):
    added = {
        "episode_id": "6732a1b2c3d4e5f6a7b8c9d0",  # pragma: allowlist secret
        "titre": "Zadie Smith, Emmanuelle Salasc... Que lire cet été ?",
        "date": "2024-07-21",
        "duree": 2809,
        "episode_page_url": PAGE_URL,
        "audio_rel_filename": "2024/14007-21.07.2024-ITEMA_23808923.m4a",
    }
    mock_service.add_from_radiofrance_page = AsyncMock(return_value=added)

    response = client.post(ENDPOINT, json={"url": PAGE_URL})

    assert response.status_code == 200
    assert response.json() == added
    mock_service.add_from_radiofrance_page.assert_awaited_once_with(PAGE_URL)


@pytest.mark.parametrize("status_code", [400, 409, 422, 502])
def test_refusal_keeps_its_status_and_message(client, mock_service, status_code):
    mock_service.add_from_radiofrance_page = AsyncMock(
        side_effect=ManualEpisodeError("Une émission existe déjà", status_code)
    )

    response = client.post(ENDPOINT, json={"url": PAGE_URL})

    assert response.status_code == status_code
    assert response.json() == {"detail": "Une émission existe déjà"}


def test_unexpected_error_is_a_500(client, mock_service):
    mock_service.add_from_radiofrance_page = AsyncMock(
        side_effect=RuntimeError("Connexion MongoDB non établie")
    )

    response = client.post(ENDPOINT, json={"url": PAGE_URL})

    assert response.status_code == 500


def test_missing_url_is_rejected(client, mock_service):
    response = client.post(ENDPOINT, json={})

    assert response.status_code == 422
