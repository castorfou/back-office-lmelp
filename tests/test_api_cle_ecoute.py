"""Clé d'écoute de lmelp-mobile (Issue #427, tranche 6, ADR 0003).

Une clé unique, partagée par le cercle des auditeurs, vit dans MongoDB :
créée au premier démarrage, invalidable depuis « Configuration mobile ».
lmelp-streaming la fait vérifier au backend (`auth_request`) : 204 ou 403.
Seules les dates des changements sont gardées, jamais les anciennes clés.
"""

from collections.abc import Iterator
from datetime import datetime
from typing import Any
from unittest.mock import patch

import mongomock
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def db() -> Iterator[Any]:
    """Le vrai mongodb_service sur mongomock."""
    from back_office_lmelp.services.mongodb_service import mongodb_service

    base: Any = mongomock.MongoClient().db
    with patch.multiple(mongodb_service, db=base):
        yield base


@pytest.fixture
def client(db: Any) -> TestClient:
    from back_office_lmelp.app import app

    return TestClient(app)


def test_la_cle_est_creee_une_seule_fois(db: Any) -> None:
    from back_office_lmelp.services.cle_ecoute_service import cle_ecoute_service

    cle_ecoute_service.assurer()
    premiere = db.parametres.find_one({"_id": "cle_ecoute"})
    cle_ecoute_service.assurer()

    assert db.parametres.count_documents({}) == 1
    assert db.parametres.find_one({"_id": "cle_ecoute"})["cle"] == premiere["cle"]
    assert len(premiere["cle"]) >= 20
    assert premiere["changements"] == []
    assert isinstance(premiere["creee_le"], datetime)


def test_la_page_lit_la_cle_et_ses_dates(client: TestClient) -> None:
    reponse = client.get("/api/cle-ecoute")

    assert reponse.status_code == 200
    corps = reponse.json()
    assert set(corps) == {"cle", "creee_le", "changements"}
    assert corps["changements"] == []
    # date en UTC explicite : le navigateur la convertit en heure locale
    assert datetime.fromisoformat(corps["creee_le"]).utcoffset() is not None
    # la même clé tant qu'elle n'est pas invalidée
    assert client.get("/api/cle-ecoute").json()["cle"] == corps["cle"]


def test_la_cle_valide_est_acceptee_en_en_tete_ou_en_parametre(
    client: TestClient,
) -> None:
    cle = client.get("/api/cle-ecoute").json()["cle"]

    assert (
        client.get("/api/cle-ecoute/verifier", headers={"X-Lmelp-Cle": cle}).status_code
        == 204
    )
    assert (
        client.get("/api/cle-ecoute/verifier", params={"cle": cle}).status_code == 204
    )


@pytest.mark.parametrize(
    "headers,params",
    [
        ({}, {}),
        ({"X-Lmelp-Cle": "mauvaise"}, {}),
        ({}, {"cle": "mauvaise"}),
        ({"X-Lmelp-Cle": ""}, {}),
    ],
)
def test_une_cle_absente_ou_fausse_est_refusee(
    client: TestClient, headers: dict[str, str], params: dict[str, str]
) -> None:
    client.get("/api/cle-ecoute")

    reponse = client.get("/api/cle-ecoute/verifier", headers=headers, params=params)

    assert reponse.status_code == 403


def test_sans_cle_en_base_tout_est_refuse(client: TestClient) -> None:
    assert (
        client.get("/api/cle-ecoute/verifier", params={"cle": "nimporte"}).status_code
        == 403
    )


def test_invalider_refuse_aussitot_l_ancienne_cle(client: TestClient, db: Any) -> None:
    ancienne = client.get("/api/cle-ecoute").json()

    reponse = client.post("/api/cle-ecoute/invalider")

    assert reponse.status_code == 200
    nouvelle = reponse.json()
    assert nouvelle["cle"] != ancienne["cle"]
    assert len(nouvelle["changements"]) == 1
    assert nouvelle["creee_le"] == nouvelle["changements"][0]
    verifier = "/api/cle-ecoute/verifier"
    assert client.get(verifier, params={"cle": ancienne["cle"]}).status_code == 403
    assert client.get(verifier, params={"cle": nouvelle["cle"]}).status_code == 204
    # l'ancienne clé n'est gardée nulle part
    assert ancienne["cle"] not in str(list(db.parametres.find()))


def test_chaque_invalidation_ajoute_une_date(client: TestClient) -> None:
    client.post("/api/cle-ecoute/invalider")
    client.post("/api/cle-ecoute/invalider")

    assert len(client.get("/api/cle-ecoute").json()["changements"]) == 2
