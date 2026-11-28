"""Retranscrire toute l'archive avec la sortie horodatée (Issue #427, US 58).

Un bouton met une fois en file, sur PGX, tous les épisodes qui ont un audio
mais pas encore de Segments. C'est la même boucle que la transcription des
nouveaux épisodes : un épisode dont le `.json` manque repasse par PGX, sa
transcription texte est remplacée et ses Segments enregistrés. Pendant la
retranscription, pas de notification par épisode : un seul bilan à la fin.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import mongomock
import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.services.pgx_service import PgxError, PgxLocation
from back_office_lmelp.utils.pgx_transcription_runner import PgxTranscriptionRunner


EP1_ID = "507f1f77bcf86cd799439011"
EP2_ID = "507f1f77bcf86cd799439012"
PGX_FOUND = PgxLocation("192.168.50.151", "PGX trouvée en 192.168.50.151")


@pytest.fixture(autouse=True)
def reset_singleton() -> Iterator[None]:
    PgxTranscriptionRunner._instance = None
    yield
    PgxTranscriptionRunner._instance = None


@pytest.fixture(autouse=True)
def no_new_pending_episodes() -> Iterator[Any]:
    with patch(
        "back_office_lmelp.utils.pgx_transcription_runner.stats_service"
    ) as mock_stats:
        mock_stats.get_episodes_without_transcription = MagicMock(return_value=[])
        yield mock_stats


# ------------------------------------------------- épisodes sans Segments
@pytest.fixture
def db() -> Iterator[Any]:
    from back_office_lmelp.services.mongodb_service import mongodb_service

    base: Any = mongomock.MongoClient().db
    with patch.multiple(mongodb_service, db=base, episodes_collection=base.episodes):
        yield base


def ajouter(db: Any, jour: int, **champs: Any) -> str:
    document = {
        "titre": f"Le Masque du {jour}",
        "date": datetime(2026, 3, jour),
        "audio_rel_filename": f"2026/episode-{jour}.mp3",
        "transcription": "texte de l'ancienne passe",
        **champs,
    }
    return str(db.episodes.insert_one(document).inserted_id)


def test_l_archive_a_retranscrire_est_les_episodes_avec_audio_sans_segments(db):
    from back_office_lmelp.services.passages_service import passages_service

    ancien = ajouter(db, 1)
    recent = ajouter(db, 8)
    sans_transcription = ajouter(db, 15, transcription=None)
    deja_horodate = ajouter(db, 22)
    db.episode_segments.insert_one(
        {
            "episode_oid": deja_horodate,
            "segments": [{"debut_ms": 0, "fin_ms": 1, "texte": "x"}],
        }
    )
    ajouter(db, 29, masked=True)
    ajouter(db, 30, audio_rel_filename=None)

    episodes = passages_service.episodes_sans_segments()

    # du plus récent au plus ancien
    assert [e["id"] for e in episodes] == [sans_transcription, recent, ancien]
    assert set(episodes[0]) == {"id", "titre", "date"}


# ------------------------------------------------------------- démarrage
@pytest.mark.asyncio
async def test_lancer_l_archive_met_en_file_les_episodes_sans_segments():
    runner = PgxTranscriptionRunner.get_instance()
    episodes = [{"id": EP1_ID, "titre": "Un", "date": "2026-03-01"}]
    with (
        patch(
            "back_office_lmelp.utils.pgx_transcription_runner.passages_service"
        ) as mock_passages,
        patch.object(runner, "_run", new=AsyncMock()),
    ):
        mock_passages.episodes_sans_segments = MagicMock(return_value=episodes)
        resultat = await runner.start_transcription(archive=True)

    assert resultat == {"status": "started", "episode_count": 1}
    assert runner.episode_ids == [EP1_ID]
    assert runner.get_status()["archive"] is True


@pytest.mark.asyncio
async def test_rien_a_retranscrire_quand_tout_a_ses_segments():
    runner = PgxTranscriptionRunner.get_instance()
    with patch(
        "back_office_lmelp.utils.pgx_transcription_runner.passages_service"
    ) as mock_passages:
        mock_passages.episodes_sans_segments = MagicMock(return_value=[])
        resultat = await runner.start_transcription(archive=True)

    assert resultat == {"status": "nothing_to_do"}
    assert runner.is_running is False


@pytest.mark.asyncio
async def test_une_transcription_normale_n_est_pas_l_archive():
    runner = PgxTranscriptionRunner.get_instance()
    with patch.object(runner, "_run", new=AsyncMock()):
        runner_stats = "back_office_lmelp.utils.pgx_transcription_runner.stats_service"
        with patch(runner_stats) as mock_stats:
            mock_stats.get_episodes_without_transcription = MagicMock(
                return_value=[{"id": EP1_ID, "titre": "Un", "date": "2026-03-01"}]
            )
            await runner.start_transcription()

    assert runner.get_status()["archive"] is False


# ------------------------------------------------------------- traitement
def _episode(episode_id: str, titre: str) -> dict[str, Any]:
    return {
        "_id": episode_id,
        "titre": titre,
        "date": datetime(2026, 3, 1, tzinfo=UTC),
        "audio_rel_filename": "2026/episode.mp3",
        "transcription": "texte de l'ancienne passe",
    }


async def _retranscrire(
    runner: Any, tmp_path: Path, echec_sur: str | None = None
) -> Any:
    runner.episode_ids = [EP1_ID, EP2_ID]
    runner.is_running = True
    runner.archive = True
    runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)
    episodes = {
        EP1_ID: _episode(EP1_ID, "Episode Un"),
        EP2_ID: _episode(EP2_ID, "Episode Deux"),
    }

    def envoyer(local_path: str, *args: Any, **kwargs: Any) -> None:
        if echec_sur and runner.current_episode_id == echec_sur:
            raise PgxError("scp a échoué")

    with (
        patch(
            "back_office_lmelp.utils.pgx_transcription_runner.mongodb_service"
        ) as mongo,
        patch("back_office_lmelp.utils.pgx_transcription_runner.settings") as reglages,
        patch("back_office_lmelp.utils.pgx_transcription_runner.pgx_service") as pgx,
        patch("back_office_lmelp.utils.pgx_transcription_runner.passages_service"),
        patch.object(runner, "_send_notification", new=AsyncMock()) as notifier,
    ):
        mongo.get_episode_by_id = MagicMock(side_effect=lambda eid: episodes[eid])
        mongo.episodes_collection.update_one = MagicMock()
        mongo.insert_pgx_transcription_log = MagicMock()
        reglages.pgx_host = "192.168.50.151"
        reglages.pgx_user = "pgxuser"
        reglages.pgx_ssh_key_path = "/keys/pgx_ed25519"
        reglages.pgx_remote_audio_root = "/data/audios"
        reglages.pgx_remote_transcription_root = "/data/transcriptions"
        reglages.pgx_transcription_timeout_s = 1800.0
        reglages.pgx_poll_interval_s = 10.0
        reglages.audio_storage_path = str(tmp_path)
        pgx.locate_pgx = AsyncMock(return_value=PGX_FOUND)
        pgx.remote_file_exists = AsyncMock(return_value=False)
        pgx.send_audio_to_pgx = AsyncMock(side_effect=envoyer)
        pgx.wait_for_pgx_transcription = AsyncMock(return_value=True)
        pgx.fetch_segments_from_pgx = AsyncMock(return_value={"transcription": []})
        pgx.fetch_transcription_from_pgx = AsyncMock(
            return_value="Nouvelle transcription"
        )

        await runner._run("manual")
        return notifier, mongo


@pytest.mark.asyncio
async def test_la_retranscription_remplace_le_texte_et_notifie_un_seul_bilan(tmp_path):
    runner = PgxTranscriptionRunner.get_instance()
    # un .txt en cache local, sans .json : l'épisode repasse par PGX
    (tmp_path / "2026").mkdir()
    (tmp_path / "2026" / "episode.txt").write_text("texte de l'ancienne passe")

    notifier, mongo = await _retranscrire(runner, tmp_path)

    textes = [
        c.args[1]["$set"]["transcription"]
        for c in mongo.episodes_collection.update_one.call_args_list
    ]
    assert textes == ["Nouvelle transcription", "Nouvelle transcription"]
    assert notifier.await_count == 1
    titre, message = notifier.call_args.args
    assert titre == "Archive retranscrite (horodatage)"
    assert message == "2 épisode(s) retranscrit(s), 0 échec(s)"


@pytest.mark.asyncio
async def test_le_bilan_compte_les_echecs_sans_notifier_chaque_echec(tmp_path):
    runner = PgxTranscriptionRunner.get_instance()

    notifier, _ = await _retranscrire(runner, tmp_path, echec_sur=EP1_ID)

    assert notifier.await_count == 1
    assert notifier.call_args.args[1] == "1 épisode(s) retranscrit(s), 1 échec(s)"


@pytest.mark.asyncio
async def test_l_historique_du_cycle_dit_qu_il_s_agit_de_l_archive(tmp_path):
    runner = PgxTranscriptionRunner.get_instance()

    _, mongo = await _retranscrire(runner, tmp_path)

    document = mongo.insert_pgx_transcription_log.call_args.args[0]
    assert document["archive"] is True


# ------------------------------------------------------------------ routes
def test_la_page_pgx_lit_les_episodes_sans_segments():
    from back_office_lmelp.app import app

    episodes = [{"id": EP1_ID, "titre": "Un", "date": "2026-03-01T00:00:00"}]
    with patch(
        "back_office_lmelp.services.passages_service.passages_service.episodes_sans_segments",
        return_value=episodes,
    ):
        reponse = TestClient(app).get("/api/pgx/episodes-sans-segments")

    assert reponse.status_code == 200
    assert reponse.json() == {"episodes": episodes}


def test_le_bouton_lance_la_retranscription_de_l_archive():
    from back_office_lmelp.app import app
    from back_office_lmelp.utils.pgx_transcription_runner import (
        pgx_transcription_runner,
    )

    with patch.object(
        pgx_transcription_runner,
        "start_transcription",
        new=AsyncMock(return_value={"status": "started", "episode_count": 250}),
    ) as demarrer:
        reponse = TestClient(app).post("/api/pgx/transcription/archive")

    assert reponse.status_code == 200
    assert reponse.json() == {"status": "started", "episode_count": 250}
    demarrer.assert_awaited_once_with(trigger="manual", archive=True)
