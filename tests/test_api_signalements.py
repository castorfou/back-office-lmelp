"""Signaler un Passage mal découpé (Issue #427, tranche 7, US 12 à 21).

Un auditeur signale un Passage depuis le lecteur, de façon anonyme : motif,
commentaire facultatif, instant d'écoute et bornes écoutées. Le Passage est
désigné par `(episode_id, livre_id)`, jamais par son id, qui change à chaque
recalcul. Un signalement reste ouvert jusqu'à une correction à la main du
Passage ou un rejet, jamais clos par un recalcul. Routes réelles, vrai
`mongodb_service` sur mongomock, témoin du 15/11/2026.
"""

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import mongomock
import pytest
from fastapi.testclient import TestClient


FIXTURE = Path(__file__).parent / "fixtures" / "passages" / "temoin_2026-11-15.json"
TEMOIN = json.loads(FIXTURE.read_text())


@pytest.fixture
def db() -> Iterator[Any]:
    from back_office_lmelp.services.mongodb_service import mongodb_service

    base: Any = mongomock.MongoClient().db
    collections: dict[str, Any] = {
        "db": base,
        "episodes_collection": base.episodes,
        "avis_critiques_collection": base.avis_critiques,
        "livresauteurs_cache_collection": base.livresauteurs_cache,
        "livres_collection": base.livres,
    }
    with patch.multiple(mongodb_service, **collections):
        yield base


@pytest.fixture
def client(db: Any) -> TestClient:
    from back_office_lmelp.app import app

    return TestClient(app)


@pytest.fixture
def episode(db: Any) -> str:
    from back_office_lmelp.services.passages_service import passages_service

    oid = str(
        db.episodes.insert_one(
            {"titre": "Le Masque du 15/11/2026", "date": datetime(2026, 11, 15)}
        ).inserted_id
    )
    db.avis_critiques.insert_one({"episode_oid": oid, "summary": TEMOIN["resume"]})
    # deux livres en base : leurs Passages ont un livre
    for titre in ("Le Fondateur", "Paradisi Gloria"):
        db.livres.insert_one({"titre": titre, "episodes": [oid]})
    whisper = {
        "transcription": [
            {"offsets": {"from": debut, "to": fin}, "text": texte}
            for debut, fin, texte in TEMOIN["segments"]
        ]
    }
    passages_service.enregistrer_segments(oid, whisper)
    return oid


def passage(client: TestClient, episode: str, titre: str) -> dict[str, Any]:
    etat = client.get(f"/api/episodes/{episode}/passages?segments=false").json()
    return next(p for p in etat["passages"] if p["titre"] == titre)


def signaler(client: TestClient, episode: str, p: dict[str, Any], **champs: Any) -> Any:
    corps = {
        "episode_id": episode,
        "livre_id": p["livre_id"],
        "debut_ms": p["debut_ms"],
        "fin_ms": p["fin_ms"],
        "motif": "fin_trop_tot",
        "instant_ms": p["fin_ms"] - 5_000,
        **champs,
    }
    return client.post("/api/signalements", json=corps)


def ouverts(client: TestClient) -> list[dict[str, Any]]:
    return list(client.get("/api/signalements").json())


def test_un_signalement_est_enregistre_et_liste(client, episode):
    fondateur = passage(client, episode, "Le Fondateur")

    reponse = signaler(client, episode, fondateur, commentaire="Coupé en pleine phrase")

    assert reponse.status_code == 201
    [signalement] = ouverts(client)
    assert signalement["episode_id"] == episode
    assert signalement["date"] == "2026-11-15"
    assert signalement["livre_id"] == fondateur["livre_id"]
    assert signalement["titre"] == "Le Fondateur"
    assert signalement["motif"] == "fin_trop_tot"
    assert signalement["instant_ms"] == fondateur["fin_ms"] - 5_000
    assert signalement["commentaire"] == "Coupé en pleine phrase"
    assert signalement["source"] == "web"
    assert signalement["bornes_ecoutees"] == {
        "debut_ms": fondateur["debut_ms"],
        "fin_ms": fondateur["fin_ms"],
    }
    assert signalement["bornes_actuelles"] == signalement["bornes_ecoutees"]
    assert signalement["passage_id"] == fondateur["id"]
    assert client.get("/api/signalements/compte").json() == {"ouverts": 1}


def test_le_signalement_est_anonyme(client, db, episode):
    signaler(client, episode, passage(client, episode, "Le Fondateur"))

    stocke = db.signalements.find_one()
    assert set(stocke) == {
        "_id",
        "episode_oid",
        "livre_oid",
        "debut_ms",
        "fin_ms",
        "motif",
        "instant_ms",
        "commentaire",
        "cree_le",
        "source",
        "etat",
    }
    assert isinstance(stocke["episode_oid"], str)
    assert isinstance(stocke["cree_le"], datetime)


def test_un_signalement_relaye_par_lmelp_streaming_vient_du_mobile(client, episode):
    fondateur = passage(client, episode, "Le Fondateur")
    corps = {
        "episode_id": episode,
        "livre_id": fondateur["livre_id"],
        "debut_ms": fondateur["debut_ms"],
        "fin_ms": fondateur["fin_ms"],
        "motif": "autre",
        "instant_ms": fondateur["debut_ms"],
    }

    client.post("/api/signalements", json=corps, headers={"X-Lmelp-Source": "mobile"})

    assert ouverts(client)[0]["source"] == "mobile"


@pytest.mark.parametrize(
    "champs",
    [
        {"motif": "trop_long"},
        {"commentaire": "x" * 501},
        {"debut_ms": "début"},
        {"instant_ms": None},
        {"fin_ms": 0},
    ],
)
def test_un_corps_invalide_est_refuse_en_400(client, episode, champs):
    reponse = signaler(
        client, episode, passage(client, episode, "Le Fondateur"), **champs
    )

    assert reponse.status_code == 400
    assert ouverts(client) == []


def test_un_livre_sans_passage_dans_l_emission_donne_404(client, episode):
    fondateur = passage(client, episode, "Le Fondateur")

    reponse = signaler(client, episode, fondateur, livre_id="6af9eec5640a04d882f7fa00")

    assert reponse.status_code == 404


def test_rejeter_clot_le_signalement(client, db, episode):
    signaler(client, episode, passage(client, episode, "Le Fondateur"))
    [signalement] = ouverts(client)

    reponse = client.post(f"/api/signalements/{signalement['id']}/rejeter")

    assert reponse.status_code == 200
    assert ouverts(client) == []
    assert db.signalements.find_one()["etat"] == "rejete"
    assert (
        client.post(f"/api/signalements/{signalement['id']}/rejeter").status_code == 409
    )


def test_rejeter_un_signalement_inconnu_donne_404(client):
    assert (
        client.post("/api/signalements/000000000000000000000000/rejeter").status_code
        == 404
    )
    assert client.post("/api/signalements/inconnu/rejeter").status_code == 404


def test_corriger_le_passage_a_la_main_clot_ses_signalements(client, db, episode):
    fondateur = passage(client, episode, "Le Fondateur")
    paradisi = passage(client, episode, "Paradisi Gloria")
    signaler(client, episode, fondateur)
    signaler(client, episode, paradisi, motif="debut_trop_tot")
    nouvelle_fin = next(
        d
        for d, _f, t in TEMOIN["segments"]
        if d > fondateur["fin_ms"] + 10_000 and t.strip(" .")
    )

    client.patch(f"/api/passages/{fondateur['id']}/fin", json={"fin_ms": nouvelle_fin})

    # la fin du Fondateur et le début de Paradisi Gloria ont bougé ensemble
    assert ouverts(client) == []
    assert {s["etat"] for s in db.signalements.find()} == {"corrige"}


def test_supprimer_le_passage_clot_ses_signalements(client, episode):
    fondateur = passage(client, episode, "Le Fondateur")
    signaler(client, episode, fondateur, motif="mauvais_livre")

    client.post(f"/api/passages/{fondateur['id']}/supprimer")

    assert ouverts(client) == []


def test_un_recalcul_ne_clot_pas_un_signalement(client, episode):
    from back_office_lmelp.services.passages_service import passages_service

    signaler(client, episode, passage(client, episode, "Le Fondateur"))

    passages_service.recalculer(episode)

    assert len(ouverts(client)) == 1


def test_une_correction_d_un_autre_passage_ne_clot_pas_le_signalement(client, episode):
    fondateur = passage(client, episode, "Le Fondateur")
    signaler(client, episode, fondateur)
    autre = passage(client, episode, "Saint Lucky Luke")

    client.post(f"/api/passages/{autre['id']}/supprimer")

    assert len(ouverts(client)) == 1


def test_les_bornes_actuelles_montrent_une_correction_faite_depuis(client, db, episode):
    fondateur = passage(client, episode, "Le Fondateur")
    signaler(client, episode, fondateur)
    # correction faite hors de la page (le signalement reste ouvert)
    db.passages.update_one({"titre": "Le Fondateur"}, {"$set": {"fin_ms": 700_000}})

    [signalement] = ouverts(client)

    assert signalement["bornes_actuelles"]["fin_ms"] == 700_000
    assert signalement["bornes_ecoutees"]["fin_ms"] == fondateur["fin_ms"]
