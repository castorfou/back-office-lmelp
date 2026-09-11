"""Tests pour PgxTranscriptionRunner (Issue #302).

Singleton orchestrant le traitement séquentiel de la file d'épisodes sans
transcription, calqué sur MigrationRunner (utils/migration_runner.py).
Aucun test ne touche au réseau réel : pgx_service est entièrement mocké.
"""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from back_office_lmelp.services.pgx_service import PgxError
from back_office_lmelp.utils.pgx_transcription_runner import PgxTranscriptionRunner


def _make_episode(episode_id: str, titre: str = "Un épisode") -> dict:
    from datetime import UTC, datetime

    return {
        "_id": episode_id,
        "titre": titre,
        "date": datetime(2026, 3, 1, tzinfo=UTC),
        "audio_rel_filename": "2026/episode.mp3",
        "transcription": None,
    }


EP1_ID = "507f1f77bcf86cd799439011"
EP2_ID = "507f1f77bcf86cd799439012"


@pytest.fixture(autouse=True)
def reset_singleton():
    """Réinitialise le singleton entre chaque test (état de classe partagé)."""
    PgxTranscriptionRunner._instance = None
    yield
    PgxTranscriptionRunner._instance = None


class TestPgxTranscriptionRunnerSingleton:
    """Le runner est un singleton, comme MigrationRunner."""

    def test_get_instance_should_return_same_object(self):
        runner1 = PgxTranscriptionRunner.get_instance()
        runner2 = PgxTranscriptionRunner.get_instance()

        assert runner1 is runner2

    def test_initial_state_should_be_idle(self):
        runner = PgxTranscriptionRunner.get_instance()

        status = runner.get_status()

        assert status["is_running"] is False
        assert status["processed"] == []
        assert status["current_episode_id"] is None


class TestStartTranscription:
    """Tests de start_transcription() — déclenchement de la file."""

    @pytest.mark.asyncio
    async def test_should_return_already_running_when_called_twice(self):
        runner = PgxTranscriptionRunner.get_instance()
        runner.is_running = True

        result = await runner.start_transcription()

        assert result == {"status": "already_running"}

    @pytest.mark.asyncio
    async def test_should_return_nothing_to_do_when_no_episodes(self):
        runner = PgxTranscriptionRunner.get_instance()

        with patch(
            "back_office_lmelp.utils.pgx_transcription_runner.stats_service"
        ) as mock_stats:
            mock_stats.get_episodes_without_transcription = MagicMock(return_value=[])
            result = await runner.start_transcription()

        assert result == {"status": "nothing_to_do"}
        assert runner.is_running is False

    @pytest.mark.asyncio
    async def test_should_start_background_task_when_episodes_pending(self):
        runner = PgxTranscriptionRunner.get_instance()
        episodes = [
            {"id": EP1_ID, "titre": "Episode Un", "date": "2026-03-01"},
            {"id": EP2_ID, "titre": "Episode Deux", "date": "2026-03-02"},
        ]

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.stats_service"
            ) as mock_stats,
            patch.object(runner, "_run", new=AsyncMock()) as mock_run,
        ):
            mock_stats.get_episodes_without_transcription = MagicMock(
                return_value=episodes
            )
            result = await runner.start_transcription()
            # Laisse le event loop planifier la tâche créée par create_task
            await __import__("asyncio").sleep(0)

        assert result == {"status": "started", "episode_count": 2}
        mock_run.assert_called_once()


class TestRunSequentialProcessing:
    """Tests de _run() — traitement séquentiel réel de la file (mocks pgx_service)."""

    @pytest.mark.asyncio
    async def test_should_process_all_episodes_and_write_transcription_on_success(
        self,
    ):
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID, EP2_ID]
        runner.is_running = True

        episodes_by_id = {
            EP1_ID: _make_episode(EP1_ID, "Episode Un"),
            EP2_ID: _make_episode(EP2_ID, "Episode Deux"),
        }

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.mongodb_service"
            ) as mock_mongo,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: episodes_by_id[eid]
            )
            mock_mongo.episodes_collection.update_one = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = "/app/audios"

            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=True)
            mock_pgx.send_audio_to_pgx = AsyncMock()
            mock_pgx.wait_for_pgx_transcription = AsyncMock(return_value=True)
            mock_pgx.fetch_transcription_from_pgx = AsyncMock(
                side_effect=["Transcription 1", "Transcription 2"]
            )

            await runner._run()

        assert runner.is_running is False
        assert len(runner.processed) == 2
        assert runner.processed[0] == {
            "episode_id": EP1_ID,
            "success": True,
            "error": None,
        }
        assert runner.processed[1] == {
            "episode_id": EP2_ID,
            "success": True,
            "error": None,
        }
        assert mock_mongo.episodes_collection.update_one.call_count == 2

    @pytest.mark.asyncio
    async def test_should_not_interrupt_queue_when_one_episode_fails(self):
        """Un PgxError sur un épisode n'empêche pas le traitement du suivant."""
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID, EP2_ID]
        runner.is_running = True

        episodes_by_id = {
            EP1_ID: _make_episode(EP1_ID),
            EP2_ID: _make_episode(EP2_ID),
        }

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.mongodb_service"
            ) as mock_mongo,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: episodes_by_id[eid]
            )
            mock_mongo.episodes_collection.update_one = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = "/app/audios"

            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=True)
            mock_pgx.send_audio_to_pgx = AsyncMock(
                side_effect=[PgxError("scp failed"), None]
            )
            mock_pgx.wait_for_pgx_transcription = AsyncMock(return_value=True)
            mock_pgx.fetch_transcription_from_pgx = AsyncMock(
                return_value="Transcription 2"
            )

            await runner._run()

        assert runner.is_running is False
        assert len(runner.processed) == 2
        assert runner.processed[0]["success"] is False
        assert "scp failed" in runner.processed[0]["error"]
        assert runner.processed[1]["success"] is True
        # Seul le 2e épisode réussi a déclenché une écriture Mongo.
        assert mock_mongo.episodes_collection.update_one.call_count == 1

    @pytest.mark.asyncio
    async def test_should_stop_entire_queue_when_pgx_unreachable_from_start(
        self, tmp_path
    ):
        """Si PGX est injoignable dès qu'un épisode sans cache local en a besoin,
        toute la file s'arrête — pas de re-test par épisode (ne se résoudra pas
        tout seul)."""
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID, EP2_ID]
        runner.is_running = True

        episodes_by_id = {
            EP1_ID: _make_episode(EP1_ID),
            EP2_ID: _make_episode(EP2_ID),
        }

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.mongodb_service"
            ) as mock_mongo,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: episodes_by_id[eid]
            )
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = str(tmp_path)

            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=False)

            await runner._run()

        assert runner.is_running is False
        assert runner.processed == []
        mock_pgx.send_audio_to_pgx.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_always_reset_is_running_even_on_unexpected_exception(self):
        """is_running repasse à False même si une exception inattendue survient."""
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
        ):
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = "/app/audios"

            mock_pgx.wait_for_pgx_reachable = AsyncMock(
                side_effect=RuntimeError("unexpected")
            )

            await runner._run()

        assert runner.is_running is False


class TestLogTimestamps:
    """Chaque ligne de log doit être horodatée (date + heure), un run pouvant
    s'étaler sur plusieurs dizaines de minutes voire chevaucher minuit."""

    def test_log_should_be_prefixed_with_date_and_time_timestamp(self):
        runner = PgxTranscriptionRunner.get_instance()

        runner._log("Message de test")

        assert len(runner.logs) == 1
        assert re.match(
            r"^\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} - Message de test$", runner.logs[0]
        )


class TestLocalCacheFirst:
    """Cache-first : si le fichier .txt local existe déjà (à côté de l'audio),
    l'utiliser directement sans passer par PGX (scp/attente), comme le faisait
    set_transcription() dans lmelp."""

    @pytest.mark.asyncio
    async def test_should_use_local_cache_without_calling_pgx_when_txt_file_exists(
        self, tmp_path
    ):
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True

        mp3_path = tmp_path / "2026" / "episode.mp3"
        mp3_path.parent.mkdir(parents=True)
        mp3_path.write_text("fake audio")
        txt_path = tmp_path / "2026" / "episode.txt"
        txt_path.write_text("Transcription déjà en cache local")

        episode = _make_episode(EP1_ID)
        episode["audio_rel_filename"] = "2026/episode.mp3"

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.mongodb_service"
            ) as mock_mongo,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
        ):
            mock_mongo.get_episode_by_id = MagicMock(return_value=episode)
            mock_mongo.episodes_collection.update_one = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = str(tmp_path)

            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=True)
            mock_pgx.send_audio_to_pgx = AsyncMock()
            mock_pgx.wait_for_pgx_transcription = AsyncMock()
            mock_pgx.fetch_transcription_from_pgx = AsyncMock()

            await runner._run()

        mock_pgx.send_audio_to_pgx.assert_not_called()
        mock_pgx.wait_for_pgx_transcription.assert_not_called()
        mock_pgx.fetch_transcription_from_pgx.assert_not_called()
        mock_mongo.episodes_collection.update_one.assert_called_once()
        update_call_kwargs = mock_mongo.episodes_collection.update_one.call_args
        assert (
            update_call_kwargs[0][1]["$set"]["transcription"]
            == "Transcription déjà en cache local"
        )
        assert runner.processed == [
            {"episode_id": EP1_ID, "success": True, "error": None}
        ]

    @pytest.mark.asyncio
    async def test_should_not_check_pgx_reachable_when_all_episodes_have_local_cache(
        self, tmp_path
    ):
        """Si tous les épisodes de la file ont déjà un cache local, PGX
        injoignable ne doit pas bloquer le traitement (aucun besoin réseau)."""
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True

        mp3_path = tmp_path / "2026" / "episode.mp3"
        mp3_path.parent.mkdir(parents=True)
        mp3_path.write_text("fake audio")
        txt_path = tmp_path / "2026" / "episode.txt"
        txt_path.write_text("Transcription déjà en cache local")

        episode = _make_episode(EP1_ID)
        episode["audio_rel_filename"] = "2026/episode.mp3"

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.mongodb_service"
            ) as mock_mongo,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
        ):
            mock_mongo.get_episode_by_id = MagicMock(return_value=episode)
            mock_mongo.episodes_collection.update_one = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = str(tmp_path)

            # PGX injoignable — ne doit pas empêcher le traitement du cache local.
            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=False)

            await runner._run()

        mock_pgx.wait_for_pgx_reachable.assert_not_called()
        assert runner.processed == [
            {"episode_id": EP1_ID, "success": True, "error": None}
        ]

    @pytest.mark.asyncio
    async def test_should_fallback_to_pgx_pipeline_when_no_local_cache(self, tmp_path):
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True

        mp3_path = tmp_path / "2026" / "episode.mp3"
        mp3_path.parent.mkdir(parents=True)
        mp3_path.write_text("fake audio")
        # Pas de fichier .txt local à côté.

        episode = _make_episode(EP1_ID)
        episode["audio_rel_filename"] = "2026/episode.mp3"

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.mongodb_service"
            ) as mock_mongo,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
        ):
            mock_mongo.get_episode_by_id = MagicMock(return_value=episode)
            mock_mongo.episodes_collection.update_one = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = str(tmp_path)

            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=True)
            mock_pgx.send_audio_to_pgx = AsyncMock()
            mock_pgx.wait_for_pgx_transcription = AsyncMock(return_value=True)
            mock_pgx.fetch_transcription_from_pgx = AsyncMock(
                return_value="Transcription via PGX"
            )

            await runner._run()

        mock_pgx.send_audio_to_pgx.assert_called_once()
        mock_pgx.wait_for_pgx_transcription.assert_called_once()
        mock_pgx.fetch_transcription_from_pgx.assert_called_once()
        assert runner.processed == [
            {"episode_id": EP1_ID, "success": True, "error": None}
        ]


class TestGetStatus:
    """Tests de get_status() — payload consommé par le polling GET."""

    def test_should_include_all_expected_keys(self):
        runner = PgxTranscriptionRunner.get_instance()

        status = runner.get_status()

        assert set(status.keys()) == {
            "is_running",
            "episode_ids",
            "current_episode_id",
            "current_episode_index",
            "processed",
            "start_time",
            "logs",
            "last_update",
        }
