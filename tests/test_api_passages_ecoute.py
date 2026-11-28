"""Écouter un Passage dans lmelp (Issue #427, tranche 3).

lmelp lit l'audio de l'épisode depuis son propre backend, en réseau local et
sans clé : `GET /api/episodes/{id}/audio` sert le fichier tel quel, avec Range,
et le lecteur borne le Passage. Le fichier audio est un vrai fichier sur disque
(Range, en-têtes) ; MongoDB tourne sur mongomock branché sur le vrai service.
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
AUDIO_REL = "2026/24613-15.11.2026-ITEMA_24753344.m4a"
CONTENU = bytes(range(256)) * 40  # 10 240 octets


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Any]:
    """Le vrai mongodb_service sur mongomock, et un dossier audio temporaire."""
    from back_office_lmelp.services.mongodb_service import mongodb_service

    base: Any = mongomock.MongoClient().db
    collections: dict[str, Any] = {
        "db": base,
        "episodes_collection": base.episodes,
        "avis_critiques_collection": base.avis_critiques,
        "livresauteurs_cache_collection": base.livresauteurs_cache,
        "livres_collection": base.livres,
    }
    audio = tmp_path / "audios" / AUDIO_REL
    audio.parent.mkdir(parents=True)
    audio.write_bytes(CONTENU)
    with (
        patch.multiple(mongodb_service, **collections),
        patch.dict("os.environ", {"AUDIO_STORAGE_PATH": str(tmp_path / "audios")}),
    ):
        yield base


@pytest.fixture
def client(db: Any) -> TestClient:
    from back_office_lmelp.app import app

    return TestClient(app)


def ajouter_episode(db: Any, audio_rel_filename: str = AUDIO_REL) -> str:
    return str(
        db.episodes.insert_one(
            {
                "titre": "Le Masque du 15/11/2026",
                "audio_rel_filename": audio_rel_filename,
            }
        ).inserted_id
    )


def test_l_audio_de_l_episode_se_lit_par_morceaux(client, db):
    episode = ajouter_episode(db)

    response = client.get(
        f"/api/episodes/{episode}/audio", headers={"Range": "bytes=1000-1999"}
    )

    assert response.status_code == 206
    assert response.content == CONTENU[1000:2000]
    assert response.headers["content-range"] == f"bytes 1000-1999/{len(CONTENU)}"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"] == "audio/mp4"


def test_un_fichier_audio_absent_repond_404(client, db):
    episode = ajouter_episode(db, "2026/absent.m4a")

    assert client.get(f"/api/episodes/{episode}/audio").status_code == 404


def test_un_episode_inconnu_repond_404(client):
    assert client.get(f"/api/episodes/{ObjectId()}/audio").status_code == 404


def test_un_chemin_qui_sort_du_dossier_audio_est_refuse(client, db, tmp_path):
    (tmp_path / "secret.txt").write_text("hors du dossier audio")
    episode = ajouter_episode(db, "../secret.txt")

    assert client.get(f"/api/episodes/{episode}/audio").status_code == 404


def sortie_whisper() -> dict[str, Any]:
    return {
        "transcription": [
            {"offsets": {"from": debut, "to": fin}, "text": texte}
            for debut, fin, texte in TEMOIN["segments"]
        ]
    }


@pytest.fixture
def episode(db: Any) -> str:
    """Le 15/11/2026, son résumé et ses Passages repérés."""
    from datetime import datetime

    from back_office_lmelp.services.passages_service import passages_service

    oid = str(
        db.episodes.insert_one(
            {
                "titre": "Le Masque du 15/11/2026",
                "date": datetime(2026, 11, 15, 9, 12, 40),
                "audio_rel_filename": AUDIO_REL,
            }
        ).inserted_id
    )
    db.avis_critiques.insert_one({"episode_oid": oid, "summary": TEMOIN["resume"]})
    passages_service.enregistrer_segments(oid, sortie_whisper())
    return oid


def test_les_passages_d_une_emission_se_lisent_sans_ses_segments(client, episode):
    data = client.get(f"/api/episodes/{episode}/passages?segments=false").json()

    assert data["segments"] == []
    assert data["a_des_segments"] is True
    assert len(data["passages"]) == 9
    # même forme de Passage que sur la fiche livre : de quoi lire l'audio
    assert {p["episode_id"] for p in data["passages"]} == {episode}
    assert {p["date"] for p in data["passages"]} == {"2026-11-15"}


def test_un_livre_sans_passage_dit_pourquoi(client, db, episode):
    db.passages.update_one(
        {"episode_oid": episode, "titre": "Vivre après"}, {"$set": {"supprime": True}}
    )
    db.passages.delete_one({"episode_oid": episode, "titre": "Rouge Truite"})

    data = client.get(f"/api/episodes/{episode}/passages?segments=false").json()

    raisons = {s["titre"]: s["raison"] for s in data["sans_passage"]}
    assert raisons == {"Vivre après": "supprime", "Rouge Truite": "non_repere"}


def test_une_emission_sans_segments_le_dit(client, db):
    oid = ajouter_episode(db)
    db.avis_critiques.insert_one({"episode_oid": oid, "summary": TEMOIN["resume"]})

    data = client.get(f"/api/episodes/{oid}/passages?segments=false").json()

    assert data["a_des_segments"] is False
    assert {s["raison"] for s in data["sans_passage"]} == {"pas_de_segments"}


def test_les_passages_d_un_livre_portent_leur_emission(client, db, episode):
    livre = db.livres.insert_one({"titre": "Le Fondateur", "episodes": [episode]})

    response = client.get(f"/api/livres/{livre.inserted_id}/passages")

    assert response.status_code == 200
    (passage,) = response.json()["passages"]
    assert passage["titre"] == "Le Fondateur"
    assert passage["livre_id"] == str(livre.inserted_id)
    assert passage["episode_id"] == episode
    assert passage["date"] == "2026-11-15"
    assert abs(passage["debut_ms"] // 1000 - (7 * 60 + 32)) <= 10


def test_un_livre_sans_passage_dans_une_emission_dit_pourquoi(client, db, episode):
    sans_segments = ajouter_episode(db)
    db.avis_critiques.insert_one(
        {"episode_oid": sans_segments, "summary": TEMOIN["resume"]}
    )
    livre = db.livres.insert_one(
        {"titre": "Le Fondateur", "episodes": [episode, sans_segments]}
    )

    data = client.get(f"/api/livres/{livre.inserted_id}/passages").json()

    assert [p["episode_id"] for p in data["passages"]] == [episode]
    assert data["sans_passage"] == [
        {"episode_id": sans_segments, "raison": "pas_de_segments"}
    ]


def test_un_livre_sans_passage_porte_son_id_quand_il_est_valide(client, db, episode):
    """La fiche émission retrouve la raison par le livre, pas par le titre,
    qui peut avoir été corrigé à la validation."""
    livre = db.livres.insert_one({"titre": "Vivre après", "episodes": [episode]})
    db.passages.update_one(
        {"episode_oid": episode, "titre": "Vivre après"}, {"$set": {"supprime": True}}
    )

    data = client.get(f"/api/episodes/{episode}/passages?segments=false").json()

    (absent,) = data["sans_passage"]
    assert absent["livre_id"] == str(livre.inserted_id)
    assert absent["raison"] == "supprime"
