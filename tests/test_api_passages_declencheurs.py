"""Ce qui relance le repérage des Passages d'un épisode (Issue #427, tranche 2b).

Le repérage est recalculé quand le résumé est enregistré ou qu'un titre est
écarté ou rétabli. À la validation d'un livre, le Passage existant est
seulement rattaché au livre, sans nouveau repérage.

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


def test_valider_un_livre_rattache_son_passage_sans_le_reperer_de_nouveau(
    client, db, episode
):
    from back_office_lmelp.services.passages_service import passages_service

    # une correction à la main avant la validation
    db.passages.update_one(
        {"episode_oid": episode, "titre": "Vivre après"},
        {"$set": {"debut_ms": 2_500_000, "origine": "corrige"}},
    )

    with patch(
        "back_office_lmelp.services.passages_service.reperer_passages"
    ) as reperage:
        passages_service.rattacher_livre(
            episode, "Vivre après", "Vivre après (récit)", LIVRE_VIVRE_APRES
        )

    reperage.assert_not_called()
    passage = db.passages.find_one(
        {"episode_oid": episode, "livre_oid": LIVRE_VIVRE_APRES}
    )
    assert passage["titre"] == "Vivre après (récit)"  # le titre corrigé du résumé
    assert passage["debut_ms"] == 2_500_000
    assert passage["origine"] == "corrige"
