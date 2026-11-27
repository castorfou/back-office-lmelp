"""Segments et Passages d'un épisode en base (Issue #427, tranche 2).

Les Segments whisper (.json) d'un épisode sont enregistrés, le repérage est
recalculé, et `GET /api/episodes/{id}/passages` les rend. Les requêtes
tournent sur mongomock (vrais filtres, vrais types : `episode_oid` est une
String, `book_id` un ObjectId), avec le vrai témoin du 15/11/2026.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import mongomock
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient


TEMOIN = json.loads(
    (
        Path(__file__).parent / "fixtures" / "passages" / "temoin_2026-11-15.json"
    ).read_text()
)


def sortie_whisper() -> dict[str, Any]:
    """Le .json de whisper.cpp -oj, reconstruit depuis le témoin."""
    return {
        "transcription": [
            {"offsets": {"from": debut, "to": fin}, "text": texte}
            for debut, fin, texte in TEMOIN["segments"]
        ]
    }


@pytest.fixture
def db():
    return mongomock.MongoClient().db


@pytest.fixture
def service(db):
    from back_office_lmelp.services.passages_service import passages_service

    mongodb = MagicMock()
    mongodb.get_collection.side_effect = lambda name: db[name]
    with patch.object(passages_service, "mongodb_service", mongodb):
        yield passages_service


@pytest.fixture
def client(service):
    from back_office_lmelp.app import app

    return TestClient(app)


@pytest.fixture
def episode(db: Any) -> str:
    """Épisode du 15/11/2026 avec son résumé ; « Le Fondateur » est validé."""
    episode_id = db.episodes.insert_one(
        {"titre": "Le Masque du 15/11/2026"}
    ).inserted_id
    oid = str(episode_id)
    db.avis_critiques.insert_one({"episode_oid": oid, "summary": TEMOIN["resume"]})
    db.livresauteurs_cache.insert_one(
        {
            "episode_oid": oid,
            "titre": "Le Fondateur",
            "status": "mongo",
            "book_id": ObjectId("6afd594de81df360960133fb"),
        }
    )
    return oid


def test_les_passages_d_un_episode_sont_repere_des_que_ses_segments_arrivent(
    client, service, episode
):
    service.enregistrer_segments(episode, sortie_whisper())

    response = client.get(f"/api/episodes/{episode}/passages")

    assert response.status_code == 200
    data = response.json()
    assert len(data["segments"]) == len(TEMOIN["segments"])
    titres = [p["titre"] for p in data["passages"]]
    assert titres[0] == "Le Fondateur"
    assert len(titres) == 9
    fondateur = data["passages"][0]
    assert abs(fondateur["debut_ms"] // 1000 - (7 * 60 + 32)) <= 10
    assert fondateur["livre_id"] == "6afd594de81df360960133fb"
    assert fondateur["origine"] == "auto"
    assert data["sans_passage"] == []


def test_un_recalcul_garde_les_corrections_et_ne_recree_pas_un_passage_supprime(
    client, service, db, episode
):
    service.enregistrer_segments(episode, sortie_whisper())
    db.passages.update_one(
        {"episode_oid": episode, "titre": "Paradisi Gloria"},
        {"$set": {"debut_ms": 800_000, "origine": "corrige"}},
    )
    db.passages.update_one(
        {"episode_oid": episode, "titre": "Rouge Truite"}, {"$set": {"supprime": True}}
    )

    service.enregistrer_segments(episode, sortie_whisper())  # nouveau .json
    service.recalculer(episode)  # puis une autre écriture

    passages = {
        p["titre"]: p
        for p in client.get(f"/api/episodes/{episode}/passages").json()["passages"]
    }
    assert passages["Paradisi Gloria"]["debut_ms"] == 800_000
    assert passages["Paradisi Gloria"]["origine"] == "corrige"
    assert "Rouge Truite" not in passages
    assert len(passages) == 8
    assert db.passages.count_documents({"episode_oid": episode}) == 9
