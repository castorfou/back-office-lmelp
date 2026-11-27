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


# id du livre « Le Fondateur » (livres._id) ; une String dans passages.livre_oid
LIVRE_FONDATEUR = "6afd594de81df360960133fb"  # pragma: allowlist secret
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
            "book_id": ObjectId(LIVRE_FONDATEUR),
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
    # les Segments vides ou réduits à « ... » ne sont pas gardés
    non_vides = [t for _, _, t in TEMOIN["segments"] if t.strip(" .")]
    assert len(data["segments"]) == len(non_vides)
    titres = [p["titre"] for p in data["passages"]]
    assert titres[0] == "Le Fondateur"
    assert len(titres) == 9
    fondateur = data["passages"][0]
    assert abs(fondateur["debut_ms"] // 1000 - (7 * 60 + 32)) <= 10
    assert fondateur["livre_id"] == LIVRE_FONDATEUR
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


def passages_par_titre(client: TestClient, episode: str) -> dict[str, dict[str, Any]]:
    data = client.get(f"/api/episodes/{episode}/passages").json()
    return {p["titre"]: p for p in data["passages"]}


def test_les_segments_vides_ou_reduits_a_des_points_ne_sont_pas_gardes(
    client, service, episode
):
    whisper = sortie_whisper()
    whisper["transcription"] += [
        {"offsets": {"from": 2_900_000, "to": 2_901_000}, "text": " ..."},
        {"offsets": {"from": 2_901_000, "to": 2_902_000}, "text": "  "},
    ]

    service.enregistrer_segments(episode, whisper)

    segments = client.get(f"/api/episodes/{episode}/passages").json()["segments"]
    assert all(texte.strip(" .") for _, _, texte in segments)


def test_la_section_et_l_auteur_viennent_du_resume_sans_etre_stockes(
    client, service, db, episode
):
    service.enregistrer_segments(episode, sortie_whisper())

    stocke = db.passages.find_one({"episode_oid": episode, "titre": "Vivre après"})
    rendu = passages_par_titre(client, episode)["Vivre après"]
    assert "section" not in stocke and "auteur" not in stocke
    assert rendu["section"] == 2
    assert rendu["auteur"] == "Jérôme Garcin"


def test_un_passage_auto_ne_chevauche_pas_un_passage_corrige_voisin(
    client, service, db, episode
):
    service.enregistrer_segments(episode, sortie_whisper())
    # le début de Paradisi Gloria est avancé de 2 min, dans Le Fondateur
    paradisi = db.passages.find_one(
        {"episode_oid": episode, "titre": "Paradisi Gloria"}
    )
    db.passages.update_one(
        {"_id": paradisi["_id"]},
        {"$set": {"debut_ms": paradisi["debut_ms"] - 120_000, "origine": "corrige"}},
    )

    service.recalculer(episode)

    passages = passages_par_titre(client, episode)
    assert passages["Le Fondateur"]["fin_ms"] <= passages["Paradisi Gloria"]["debut_ms"]


def test_un_livre_n_a_qu_un_passage_meme_si_son_passage_corrige_a_un_autre_titre(
    client, service, db, episode
):
    service.enregistrer_segments(episode, sortie_whisper())
    db.passages.update_one(
        {"episode_oid": episode, "titre": "Le Fondateur"},
        {"$set": {"titre": "Le fondateur (titre corrigé)", "origine": "corrige"}},
    )

    service.recalculer(episode)

    filtre = {"episode_oid": episode, "livre_oid": LIVRE_FONDATEUR}
    assert db.passages.count_documents(filtre) == 1


def test_un_episode_sans_segments_n_a_ni_segments_ni_passages(client, episode):
    data = client.get(f"/api/episodes/{episode}/passages").json()

    assert data["segments"] == []
    assert data["passages"] == []
    assert len(data["sans_passage"]) == 9


def test_un_episode_sans_resume_garde_ses_segments_sans_passage(client, service, db):
    oid = str(db.episodes.insert_one({"titre": "Sans résumé"}).inserted_id)

    service.enregistrer_segments(oid, sortie_whisper())

    data = client.get(f"/api/episodes/{oid}/passages").json()
    assert len(data["segments"]) > 0
    assert data["passages"] == []
    assert data["sans_passage"] == []
