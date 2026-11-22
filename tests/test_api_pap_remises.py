"""Endpoints de la page « Émissions anciennes » (Issue #378).

GET  /api/pap/remises            → remises livrées pas encore intégrées
POST /api/pap/remises/integrer   {"remise_id": "<URL de l'enregistrement pap>"}

L'identifiant d'une remise est une URL (avec des `/`) : il passe dans le corps.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.services.pap_remises_service import PapRemiseError


REMISE_ID = (
    "https://media.radiofrance-podcast.net/podcast09/"
    "14007-05.06.2016-ITEMA_21002286-2016F4007S0157-27.m4a"
)


@pytest.fixture
def client():
    from back_office_lmelp.app import app

    return TestClient(app)


@pytest.fixture
def mock_service():
    with patch("back_office_lmelp.app.pap_remises_service") as mock:
        yield mock


def test_liste_les_remises_a_integrer(client, mock_service):
    remises = [
        {
            "remise_id": REMISE_ID,
            "titre": "Le Masque et la Plume du 5 juin 2016",
            "date": "2016-06-05",
            "duree": 3287,
            "description": "durée : 00:54:47  - Le Masque et la Plume",
            "episode_page_url": None,
        }
    ]
    mock_service.list_a_integrer.return_value = remises

    response = client.get("/api/pap/remises")

    assert response.status_code == 200
    assert response.json() == remises


def test_integre_la_remise_passee_dans_le_corps(client, mock_service):
    result = {
        "episode_id": "6af47e76a1c0d162e8518b99",  # pragma: allowlist secret
        "remise_id": REMISE_ID,
        "titre": "Le Masque et la Plume du 5 juin 2016",
        "date": "2016-06-05",
        "transcription_status": "started",
    }
    mock_service.integrer = AsyncMock(return_value=result)

    response = client.post("/api/pap/remises/integrer", json={"remise_id": REMISE_ID})

    assert response.status_code == 200
    assert response.json() == result
    mock_service.integrer.assert_awaited_once_with(REMISE_ID)


@pytest.mark.parametrize(
    ("status_code", "message"),
    [
        (404, "Émission inconnue de lmelp-pap"),
        (409, "Émission déjà intégrée"),
        (422, "Fichier audio absent du dossier audio de lmelp : 2016/x.m4a"),
    ],
)
def test_un_refus_garde_son_statut_et_son_message(
    client, mock_service, status_code, message
):
    mock_service.integrer = AsyncMock(side_effect=PapRemiseError(message, status_code))

    response = client.post("/api/pap/remises/integrer", json={"remise_id": REMISE_ID})

    assert response.status_code == status_code
    assert response.json() == {"detail": message}


def test_une_erreur_inattendue_renvoie_500(client, mock_service):
    mock_service.integrer = AsyncMock(side_effect=RuntimeError("Mongo"))

    response = client.post("/api/pap/remises/integrer", json={"remise_id": REMISE_ID})

    assert response.status_code == 500
