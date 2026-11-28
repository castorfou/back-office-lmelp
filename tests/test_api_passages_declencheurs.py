"""Ce qui relance le repérage des Passages d'un épisode (Issue #427, tranche 2b).

Le repérage est recalculé quand le résumé est enregistré ou qu'un titre est
écarté ou rétabli. La validation d'un livre ne déclenche rien : le livre d'un
Passage se retrouve à la lecture, par les noms connus du livre (cache
livres-auteurs) et les livres de l'épisode en base.

Les routes tournent sur une base mongomock branchée sur le vrai
`mongodb_service` (vrais filtres, vrais types), avec le témoin du 15/11/2026.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import mongomock
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient


FIXTURE = Path(__file__).parent / "fixtures" / "passages" / "temoin_2026-11-15.json"
TEMOIN = json.loads(FIXTURE.read_text())
# id du livre « Vivre après » (livres._id), une String dans passages.livre_oid
LIVRE_VIVRE_APRES = "6afd594de81df360960133fc"  # pragma: allowlist secret


def sortie_whisper() -> dict[str, Any]:
    return {
        "transcription": [
            {"offsets": {"from": debut, "to": fin}, "text": texte}
            for debut, fin, texte in TEMOIN["segments"]
        ]
    }


@pytest.fixture
def db() -> Iterator[Any]:
    """Le vrai mongodb_service, branché sur une base mongomock."""
    from back_office_lmelp.services.mongodb_service import mongodb_service

    base: Any = mongomock.MongoClient().db
    collections: dict[str, Any] = {
        "db": base,
        "episodes_collection": base.episodes,
        "avis_critiques_collection": base.avis_critiques,
        "emissions_collection": base.emissions,
        "livresauteurs_cache_collection": base.livresauteurs_cache,
    }
    with patch.multiple(mongodb_service, **collections):
        yield base


@pytest.fixture
def client(db: Any) -> TestClient:
    from back_office_lmelp.app import app

    return TestClient(app)


@pytest.fixture
def episode(db: Any) -> str:
    """Épisode du 15/11/2026, son résumé, son émission et ses Passages repérés."""
    from back_office_lmelp.services.passages_service import passages_service

    episode_id = db.episodes.insert_one(
        {"titre": "Le Masque du 15/11/2026"}
    ).inserted_id
    oid = str(episode_id)
    avis_id = db.avis_critiques.insert_one(
        {"episode_oid": oid, "summary": TEMOIN["resume"]}
    ).inserted_id
    db.emissions.insert_one({"episode_id": episode_id, "avis_critique_id": avis_id})
    passages_service.enregistrer_segments(oid, sortie_whisper())
    return oid


def titres_des_passages(client: TestClient, episode: str) -> list[str]:
    data = client.get(f"/api/episodes/{episode}/passages").json()
    return [p["titre"] for p in data["passages"]]


def test_ecarter_un_titre_retire_son_passage(client, episode):
    assert "Vivre après" in titres_des_passages(client, episode)

    response = client.post(
        "/api/livres-auteurs/ecarter",
        json={
            "episode_oid": episode,
            "titre": "Vivre après",
            "auteur": "Jérôme Garcin",
        },
    )

    assert response.status_code == 200
    data = client.get(f"/api/episodes/{episode}/passages").json()
    assert "Vivre après" not in [p["titre"] for p in data["passages"]]
    assert "Vivre après" not in [s["titre"] for s in data["sans_passage"]]


def test_retablir_un_titre_ecarte_lui_rend_son_passage(client, db, episode):
    emission = db.emissions.find_one({"episode_id": ObjectId(episode)})
    client.post(
        f"/api/emissions/{emission['_id']}/livres-ecartes",
        json={"titre": "Vivre après", "auteur": "Jérôme Garcin"},
    )

    response = client.delete(
        f"/api/emissions/{emission['_id']}/livres-ecartes",
        params={"titre": "Vivre après"},
    )

    assert response.status_code == 200
    assert "Vivre après" in titres_des_passages(client, episode)


def test_un_nouveau_resume_relance_le_reperage(client, episode):
    sans_vivre_apres = "\n".join(
        ligne for ligne in TEMOIN["resume"].splitlines() if "Vivre après" not in ligne
    )

    response = client.post(
        "/api/avis-critiques/save",
        json={
            "episode_id": episode,
            "summary": sans_vivre_apres,
            "summary_phase1": sans_vivre_apres,
            "metadata": {},
        },
    )

    assert response.status_code == 200
    titres = titres_des_passages(client, episode)
    assert "Vivre après" not in titres
    assert len(titres) == 8


def passages_et_sans_passage(client: TestClient, episode: str) -> dict[str, Any]:
    return dict(client.get(f"/api/episodes/{episode}/passages").json())


def valider(
    db: Any, episode: str, titre: str, titre_valide: str, livre_oid: str
) -> None:
    """Ce que fait une validation : le cache reçoit le livre et le titre validé,
    puis le résumé est réécrit avec le titre validé. Aucun déclencheur."""
    db.livresauteurs_cache.insert_one(
        {
            "episode_oid": episode,
            "titre": titre,
            "validated_title": titre_valide,
            "status": "mongo",
            "book_id": ObjectId(livre_oid),
        }
    )
    avis = db.avis_critiques.find_one({"episode_oid": episode})
    db.avis_critiques.update_one(
        {"_id": avis["_id"]},
        {"$set": {"summary": avis["summary"].replace(titre, titre_valide)}},
    )


def test_un_livre_valide_est_retrouve_a_la_lecture_sans_declencheur(
    client, db, episode
):
    valider(db, episode, "Vivre après", "Vivre après (récit)", LIVRE_VIVRE_APRES)

    data = passages_et_sans_passage(client, episode)

    vivre_apres = [p for p in data["passages"] if p["livre_id"] == LIVRE_VIVRE_APRES]
    assert len(vivre_apres) == 1
    assert vivre_apres[0]["auteur"] == "Jérôme Garcin"
    assert data["sans_passage"] == []


def test_un_passage_corrige_puis_valide_n_est_pas_double_par_un_recalcul(
    client, db, episode
):
    from back_office_lmelp.services.passages_service import passages_service

    db.passages.update_one(
        {"episode_oid": episode, "titre": "Vivre après"},
        {"$set": {"debut_ms": 2_500_000, "origine": "corrige"}},
    )
    valider(db, episode, "Vivre après", "Vivre après (récit)", LIVRE_VIVRE_APRES)

    passages_service.recalculer(episode)

    vivre_apres = [
        p
        for p in passages_et_sans_passage(client, episode)["passages"]
        if p["livre_id"] == LIVRE_VIVRE_APRES
    ]
    assert len(vivre_apres) == 1
    assert vivre_apres[0]["debut_ms"] == 2_500_000
    assert vivre_apres[0]["origine"] == "corrige"


def test_un_nouveau_resume_garde_le_lien_des_livres_deja_en_base(client, db, episode):
    # le livre est en base pour cet épisode ; un nouveau résumé vide le cache
    db.livres.insert_one(
        {
            "_id": ObjectId(LIVRE_VIVRE_APRES),
            "titre": "Vivre après",
            "episodes": [episode],
        }
    )

    client.post(
        "/api/avis-critiques/save",
        json={
            "episode_id": episode,
            "summary": TEMOIN["resume"],
            "summary_phase1": TEMOIN["resume"],
            "metadata": {},
        },
    )

    passages = {
        p["titre"]: p for p in passages_et_sans_passage(client, episode)["passages"]
    }
    assert passages["Vivre après"]["livre_id"] == LIVRE_VIVRE_APRES


def test_un_passage_corrige_d_un_titre_ecarte_est_masque_puis_revient(
    client, db, episode
):
    db.passages.update_one(
        {"episode_oid": episode, "titre": "Vivre après"},
        {"$set": {"debut_ms": 2_500_000, "origine": "corrige"}},
    )
    emission = db.emissions.find_one({"episode_id": ObjectId(episode)})
    route = f"/api/emissions/{emission['_id']}/livres-ecartes"

    client.post(route, json={"titre": "Vivre après", "auteur": "Jérôme Garcin"})
    assert "Vivre après" not in titres_des_passages(client, episode)

    client.delete(route, params={"titre": "Vivre après"})
    passages = {
        p["titre"]: p for p in passages_et_sans_passage(client, episode)["passages"]
    }
    assert passages["Vivre après"]["debut_ms"] == 2_500_000
