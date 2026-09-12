"""Tests pour PgxTranscriptionRunner (Issue #302).

Singleton orchestrant le traitement séquentiel de la file d'épisodes sans
transcription, calqué sur MigrationRunner (utils/migration_runner.py).
Aucun test ne touche au réseau réel : pgx_service est entièrement mocké.
"""

import re
from datetime import UTC, datetime
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
            "titre": "Episode Un",
            "date": "2026-03-01T00:00:00+00:00",
            "success": True,
            "error": None,
        }
        assert runner.processed[1] == {
            "episode_id": EP2_ID,
            "titre": "Episode Deux",
            "date": "2026-03-01T00:00:00+00:00",
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

    def test_log_timestamp_should_use_paris_timezone_not_utc(self):
        """Issue #313 : les logs affichés dans /transcription-pgx doivent être
        en heure de Paris (utilisateur basé à Paris), pas en UTC brut — un
        décalage de 1h (hiver) ou 2h (été, CEST) sinon."""
        from zoneinfo import ZoneInfo

        runner = PgxTranscriptionRunner.get_instance()

        with patch(
            "back_office_lmelp.utils.pgx_transcription_runner.datetime"
        ) as mock_datetime:
            fixed_utc = datetime(2026, 7, 14, 10, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = fixed_utc

            runner._log("Message de test")

        expected_local = fixed_utc.astimezone(ZoneInfo("Europe/Paris"))
        assert runner.logs[0] == (
            f"{expected_local.strftime('%d/%m/%y %H:%M:%S')} - Message de test"
        )
        assert expected_local.hour == 12  # CEST = UTC+2 en juillet


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
            {
                "episode_id": EP1_ID,
                "titre": "Un épisode",
                "date": "2026-03-01T00:00:00+00:00",
                "success": True,
                "error": None,
            }
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
            {
                "episode_id": EP1_ID,
                "titre": "Un épisode",
                "date": "2026-03-01T00:00:00+00:00",
                "success": True,
                "error": None,
            }
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
            {
                "episode_id": EP1_ID,
                "titre": "Un épisode",
                "date": "2026-03-01T00:00:00+00:00",
                "success": True,
                "error": None,
            }
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
            "retry_pending",
            "next_attempt_at",
        }

    def test_should_expose_idle_retry_state_by_default(self):
        runner = PgxTranscriptionRunner.get_instance()

        status = runner.get_status()

        assert status["retry_pending"] is False
        assert status["next_attempt_at"] is None


class TestTriggerParameter:
    """trigger="manual" (défaut) conserve le comportement actuel ; trigger="api"
    ne doit plus abandonner immédiatement le cycle si PGX est injoignable
    (Issue #309)."""

    @pytest.mark.asyncio
    async def test_start_transcription_should_default_to_manual_trigger(self):
        runner = PgxTranscriptionRunner.get_instance()
        episodes = [{"id": EP1_ID, "titre": "Episode Un", "date": "2026-03-01"}]

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
            await __import__("asyncio").sleep(0)

        assert result == {"status": "started", "episode_count": 1}
        mock_run.assert_called_once_with("manual")

    @pytest.mark.asyncio
    async def test_start_transcription_should_pass_api_trigger_through(self):
        runner = PgxTranscriptionRunner.get_instance()
        episodes = [{"id": EP1_ID, "titre": "Episode Un", "date": "2026-03-01"}]

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.stats_service"
            ) as mock_stats,
            patch.object(runner, "_run", new=AsyncMock()) as mock_run,
        ):
            mock_stats.get_episodes_without_transcription = MagicMock(
                return_value=episodes
            )
            await runner.start_transcription(trigger="api")
            await __import__("asyncio").sleep(0)

        mock_run.assert_called_once_with("api")

    @pytest.mark.asyncio
    async def test_manual_trigger_should_still_abort_immediately_when_unreachable(
        self, tmp_path
    ):
        """Comportement inchangé pour trigger="manual" : abandon immédiat."""
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True

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
                side_effect=lambda eid: _make_episode(eid)
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

            await runner._run("manual")

        assert runner.is_running is False
        assert runner.processed == []
        mock_pgx.send_audio_to_pgx.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_trigger_should_not_abort_immediately_when_pgx_unreachable(
        self, tmp_path
    ):
        """Business failure réelle : contrairement à "manual", trigger="api" doit
        finir par traiter l'épisode une fois PGX de nouveau joignable, pas
        abandonner tout de suite."""
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True

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
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.asyncio.sleep",
                new=AsyncMock(),
            ),
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: _make_episode(eid)
            )
            mock_mongo.episodes_collection.update_one = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = str(tmp_path)
            mock_settings.pgx_transcription_retry_interval_hours = 1.0
            mock_settings.pgx_transcription_retry_max_hours = 24.0

            mock_pgx.wait_for_pgx_reachable = AsyncMock(side_effect=[False, True])
            mock_pgx.send_audio_to_pgx = AsyncMock()
            mock_pgx.wait_for_pgx_transcription = AsyncMock(return_value=True)
            mock_pgx.fetch_transcription_from_pgx = AsyncMock(
                return_value="Transcription 1"
            )

            await runner._run("api")

        assert runner.is_running is False
        assert len(runner.processed) == 1
        assert runner.processed[0]["success"] is True


class TestApiRetryScheduling:
    """Tests isolés de _wait_for_reachable_with_retry() (Issue #309)."""

    @pytest.mark.asyncio
    async def test_should_retry_after_sleep_and_return_true_when_reachable(self):
        runner = PgxTranscriptionRunner.get_instance()

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.asyncio.sleep",
                new=AsyncMock(),
            ) as mock_sleep,
            patch.object(runner, "_send_notification", new=AsyncMock()),
        ):
            mock_settings.pgx_transcription_retry_interval_hours = 1.0
            mock_settings.pgx_transcription_retry_max_hours = 24.0
            mock_pgx.wait_for_pgx_reachable = AsyncMock(side_effect=[False, True])

            result = await runner._wait_for_reachable_with_retry(
                "192.168.50.151", "api"
            )

        assert result is True
        assert mock_pgx.wait_for_pgx_reachable.call_count == 2
        mock_sleep.assert_awaited_with(3600.0)
        assert runner.retry_pending is False
        assert runner.next_attempt_at is None
        # Issue #313 : la 1re entrée correspond au health-check initial qui
        # a déclenché l'entrée en retry (avant même le 1er sleep), les
        # suivantes aux tentatives de reprise faites dans la boucle.
        assert len(runner.retry_attempts) == 3
        assert runner.retry_attempts[0]["reachable"] is False
        assert runner.retry_attempts[1]["reachable"] is False
        assert runner.retry_attempts[2]["reachable"] is True

    @pytest.mark.asyncio
    async def test_should_abandon_after_max_hours_reached(self):
        """asyncio.sleep() est mocké (instantané) mais le temps réel (datetime.now)
        continue d'avancer très peu à chaque itération — utiliser des intervalles
        en secondes (via des heures fractionnaires minuscules) plutôt qu'en heures
        réelles permet à la boucle de vraiment atteindre son deadline en un temps
        de test négligeable, sans mocker datetime lui-même."""
        runner = PgxTranscriptionRunner.get_instance()

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.asyncio.sleep",
                new=AsyncMock(),
            ),
            patch.object(runner, "_send_notification", new=AsyncMock()),
        ):
            # 1h simulée = 0.0001h réelle (~0.36s) : le deadline (2x ce délai)
            # est bien atteint après exactement 2 itérations, dans un temps
            # de test négligeable — pas besoin de mocker datetime.now().
            mock_settings.pgx_transcription_retry_interval_hours = 0.0001
            mock_settings.pgx_transcription_retry_max_hours = 0.0002
            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=False)

            result = await runner._wait_for_reachable_with_retry(
                "192.168.50.151", "api"
            )

        assert result is False
        assert mock_pgx.wait_for_pgx_reachable.call_count >= 1
        assert runner.retry_pending is False
        assert runner.next_attempt_at is None
        assert len(runner.retry_attempts) >= 1
        assert all(not a["reachable"] for a in runner.retry_attempts)

    @pytest.mark.asyncio
    async def test_should_expose_retry_pending_state_during_wait(self):
        runner = PgxTranscriptionRunner.get_instance()
        seen_pending_during_sleep = []

        async def fake_sleep(_seconds):
            seen_pending_during_sleep.append(runner.retry_pending)
            seen_pending_during_sleep.append(runner.next_attempt_at is not None)

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.asyncio.sleep",
                new=AsyncMock(side_effect=fake_sleep),
            ),
            patch.object(runner, "_send_notification", new=AsyncMock()),
        ):
            mock_settings.pgx_transcription_retry_interval_hours = 1.0
            mock_settings.pgx_transcription_retry_max_hours = 24.0
            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=True)

            await runner._wait_for_reachable_with_retry("192.168.50.151", "api")

        assert seen_pending_during_sleep == [True, True]
        assert runner.retry_pending is False
        assert runner.next_attempt_at is None

    @pytest.mark.asyncio
    async def test_should_notify_only_once_on_first_unreachable_attempt(self):
        runner = PgxTranscriptionRunner.get_instance()

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.asyncio.sleep",
                new=AsyncMock(),
            ),
            patch.object(runner, "_send_notification", new=AsyncMock()) as mock_notify,
        ):
            mock_settings.pgx_transcription_retry_interval_hours = 1.0
            mock_settings.pgx_transcription_retry_max_hours = 3.0
            mock_pgx.wait_for_pgx_reachable = AsyncMock(
                side_effect=[False, False, True]
            )

            await runner._wait_for_reachable_with_retry("192.168.50.151", "api")

        mock_notify.assert_awaited_once()
        message = mock_notify.call_args_list[0].args[1]
        assert "toutes les 1.0h" in message
        assert "pendant 3.0h" in message
        assert "toutes les heures" not in message

    @pytest.mark.asyncio
    async def test_should_persist_log_as_soon_as_retry_starts_then_update_per_attempt(
        self,
    ):
        """Issue #313 : un cycle qui bascule en retry doit apparaître dans
        l'historique dès la première tentative ratée (statut 'pgx'), pas
        seulement à la fin du cycle — sinon l'utilisateur voit "rien" dans
        l'historique pendant potentiellement des heures d'attente alors que
        le système travaille activement en arrière-plan."""
        runner = PgxTranscriptionRunner.get_instance()
        runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)
        runner.episode_ids = [EP1_ID]

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.settings"
            ) as mock_settings,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.pgx_service"
            ) as mock_pgx,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.mongodb_service"
            ) as mock_mongo,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.asyncio.sleep",
                new=AsyncMock(),
            ),
            patch.object(runner, "_send_notification", new=AsyncMock()),
        ):
            mock_settings.pgx_transcription_retry_interval_hours = 1.0
            mock_settings.pgx_transcription_retry_max_hours = 3.0
            mock_pgx.wait_for_pgx_reachable = AsyncMock(
                side_effect=[False, False, True]
            )
            mock_mongo.insert_pgx_transcription_log = MagicMock(
                return_value="log-id-123"
            )
            mock_mongo.update_pgx_transcription_log = MagicMock()

            await runner._wait_for_reachable_with_retry("192.168.50.151", "api")

        mock_mongo.insert_pgx_transcription_log.assert_called_once()
        inserted_doc = mock_mongo.insert_pgx_transcription_log.call_args[0][0]
        assert inserted_doc["status"] == "pgx"
        assert inserted_doc["episode_ids"] == [EP1_ID]
        # Issue #313 : le health-check initial qui a déclenché le retry est
        # déjà dans retry_attempts au moment de l'insertion (1re entrée,
        # reachable=false).
        assert len(inserted_doc["retry_attempts"]) == 1
        assert inserted_doc["retry_attempts"][0]["reachable"] is False
        # Le cycle n'est pas terminé : finished_at ne doit pas prendre
        # l'heure de cette insertion intermédiaire (trompeur pour l'affichage
        # de la colonne Date, qui montre finished_at une fois le cycle fini).
        assert inserted_doc["finished_at"] is None

        assert runner.current_log_id == "log-id-123"
        # Une mise à jour par tentative de retry faite DANS la boucle (3 :
        # 2 ratées puis 1 réussie) — la 1re tentative (health-check initial)
        # ne déclenche pas d'update, elle est déjà dans le insert ci-dessus.
        assert mock_mongo.update_pgx_transcription_log.call_count == 3
        last_update_call = mock_mongo.update_pgx_transcription_log.call_args_list[-1]
        assert last_update_call[0][0] == "log-id-123"
        assert len(last_update_call[0][1]["retry_attempts"]) == 4


class TestConcurrentStartDuringRetry:
    """Garde anti-chevauchement : is_running reste True pendant tout le retry
    (Issue #309) — déjà couvert nativement par le verrou existant."""

    @pytest.mark.asyncio
    async def test_start_transcription_should_return_already_running_during_pending_retry(
        self,
    ):
        runner = PgxTranscriptionRunner.get_instance()
        # Simule une fenêtre de retry en cours (is_running resterait True
        # pendant tout l'appel réel à _wait_for_reachable_with_retry).
        runner.is_running = True
        runner.retry_pending = True

        result = await runner.start_transcription(trigger="api")

        assert result == {"status": "already_running"}


class TestPgxTranscriptionLogPersistence:
    """Un document par cycle complet, persisté quel que soit le statut final
    (Issue #309)."""

    @pytest.mark.asyncio
    async def test_should_persist_one_log_document_on_success(self, tmp_path):
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True
        runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)

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
            patch.object(runner, "_send_notification", new=AsyncMock()),
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: _make_episode(eid)
            )
            mock_mongo.episodes_collection.update_one = MagicMock()
            mock_mongo.insert_pgx_transcription_log = MagicMock()
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
                return_value="Transcription 1"
            )

            await runner._run("manual")

        mock_mongo.insert_pgx_transcription_log.assert_called_once()
        log_doc = mock_mongo.insert_pgx_transcription_log.call_args[0][0]
        assert log_doc["status"] == "success"
        assert log_doc["trigger"] == "manual"
        assert len(log_doc["episodes"]) == 1

    @pytest.mark.asyncio
    async def test_should_persist_json_serializable_log_document(self, tmp_path):
        """Le document persisté doit être restituable tel quel par l'API HTTP.

        Reproduit Issue #313 : un `started_at`/`finished_at` stocké comme
        `datetime` Python fait planter `JSONResponse` avec "Object of type
        datetime is not JSON serializable" dès que GET /api/pgx/logs relit
        ce document depuis MongoDB — bug invisible tant que le mock de test
        n'utilise pas le vrai type de donnée persisté.
        """
        import json

        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True
        runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)

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
            patch.object(runner, "_send_notification", new=AsyncMock()),
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: _make_episode(eid)
            )
            mock_mongo.episodes_collection.update_one = MagicMock()
            mock_mongo.insert_pgx_transcription_log = MagicMock()
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
                return_value="Transcription 1"
            )

            await runner._run("manual")

        log_doc = mock_mongo.insert_pgx_transcription_log.call_args[0][0]
        json.dumps(log_doc)  # ne doit pas lever TypeError
        assert isinstance(log_doc["started_at"], str)
        assert isinstance(log_doc["finished_at"], str)

    @pytest.mark.asyncio
    async def test_should_persist_error_status_when_all_attempted_episodes_fail(
        self, tmp_path
    ):
        """Issue #313 : quand TOUS les épisodes tentés échouent (ici 1/1), le
        statut doit être 'error' — 'partial_error' est trompeur pour un échec
        total (aucun succès dans le cycle), il est réservé au cas où au
        moins un épisode a réussi et au moins un autre a échoué."""
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True
        runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)

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
            patch.object(runner, "_send_notification", new=AsyncMock()),
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: _make_episode(eid)
            )
            mock_mongo.insert_pgx_transcription_log = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = str(tmp_path)

            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=True)
            mock_pgx.send_audio_to_pgx = AsyncMock(side_effect=PgxError("scp failed"))

            await runner._run("manual")

        log_doc = mock_mongo.insert_pgx_transcription_log.call_args[0][0]
        assert log_doc["status"] == "error"
        assert log_doc["episodes"][0]["titre"] == "Un épisode"
        assert log_doc["episodes"][0]["date"] == "2026-03-01T00:00:00+00:00"

    @pytest.mark.asyncio
    async def test_should_persist_error_status_when_some_but_not_all_episodes_fail(
        self, tmp_path
    ):
        """Issue #313 : statuts simplifiés à 3 valeurs (success/error/pgx) —
        un échec partiel (au moins un succès ET au moins un échec dans le
        même cycle) est aussi classé 'error', comme un échec total. La
        distinction fine reste visible dans le détail (`episodes[].success`),
        seul le badge résumé est simplifié."""
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID, EP2_ID]
        runner.is_running = True
        runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)

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
            patch.object(runner, "_send_notification", new=AsyncMock()),
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: episodes_by_id[eid]
            )
            mock_mongo.episodes_collection.update_one = MagicMock()
            mock_mongo.insert_pgx_transcription_log = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = str(tmp_path)

            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=True)
            mock_pgx.send_audio_to_pgx = AsyncMock(
                side_effect=[PgxError("scp failed"), None]
            )
            mock_pgx.wait_for_pgx_transcription = AsyncMock(return_value=True)
            mock_pgx.fetch_transcription_from_pgx = AsyncMock(
                return_value="Transcription 2"
            )

            await runner._run("manual")

        log_doc = mock_mongo.insert_pgx_transcription_log.call_args[0][0]
        assert log_doc["status"] == "error"

    @pytest.mark.asyncio
    async def test_should_persist_error_status_on_unexpected_exception(self):
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True
        runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)

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
            patch.object(runner, "_send_notification", new=AsyncMock()),
        ):
            mock_mongo.insert_pgx_transcription_log = MagicMock()
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

            await runner._run("manual")

        log_doc = mock_mongo.insert_pgx_transcription_log.call_args[0][0]
        assert log_doc["status"] == "error"
        assert log_doc["error_message"] == "unexpected"

    @pytest.mark.asyncio
    async def test_should_persist_pgx_status_when_abandoned_after_retry_cap(
        self, tmp_path
    ):
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True
        runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)

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
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.asyncio.sleep",
                new=AsyncMock(),
            ),
            patch.object(runner, "_send_notification", new=AsyncMock()) as mock_notify,
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: _make_episode(eid)
            )
            mock_mongo.insert_pgx_transcription_log = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = str(tmp_path)
            # Intervalles minuscules pour que le deadline réel soit atteint
            # quasi instantanément malgré asyncio.sleep() mocké (cf. commentaire
            # de test_should_abandon_after_max_hours_reached).
            mock_settings.pgx_transcription_retry_interval_hours = 0.0001
            mock_settings.pgx_transcription_retry_max_hours = 0.0001

            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=False)
            mock_mongo.insert_pgx_transcription_log = MagicMock(
                return_value="log-id-abandoned"
            )
            mock_mongo.update_pgx_transcription_log = MagicMock()

            await runner._run("api")

        # Issue #313 : le cycle est déjà persisté (insert) dès la première
        # tentative de retry ratée ; la mise à jour finale (statut définitif
        # + retry_attempts complet) passe donc par update, pas un second insert.
        final_update_call = mock_mongo.update_pgx_transcription_log.call_args_list[-1]
        assert final_update_call[0][0] == "log-id-abandoned"
        log_doc = final_update_call[0][1]
        assert log_doc["status"] == "pgx"
        assert log_doc["episodes"] == []
        assert log_doc["episode_ids"] == [EP1_ID]
        assert len(log_doc["retry_attempts"]) >= 1
        # Seule la notification "allumez PGX" (1er échec) part — pas de
        # notification finale distincte pour l'abandon.
        mock_notify.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_not_persist_log_when_nothing_to_do(self):
        runner = PgxTranscriptionRunner.get_instance()

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.stats_service"
            ) as mock_stats,
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.mongodb_service"
            ) as mock_mongo,
        ):
            mock_stats.get_episodes_without_transcription = MagicMock(return_value=[])
            mock_mongo.insert_pgx_transcription_log = MagicMock()

            result = await runner.start_transcription()

        assert result == {"status": "nothing_to_do"}
        mock_mongo.insert_pgx_transcription_log.assert_not_called()


class TestPgxNtfyNotifications:
    """Notification par épisode transcrit (succès ou échec), même logique que
    RssSyncService : un message par événement, pas de résumé groupé en fin de
    cycle (Issue #309, révisé suite à retour utilisateur sur le wording)."""

    @pytest.mark.asyncio
    async def test_should_notify_once_per_successful_episode(self, tmp_path):
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID, EP2_ID]
        runner.is_running = True
        runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)

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
            patch.object(runner, "_send_notification", new=AsyncMock()) as mock_notify,
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: episodes_by_id[eid]
            )
            mock_mongo.episodes_collection.update_one = MagicMock()
            mock_mongo.insert_pgx_transcription_log = MagicMock()
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
                side_effect=["Transcription 1", "Transcription 2"]
            )

            await runner._run("manual")

        assert mock_notify.await_count == 2
        first_call = mock_notify.call_args_list[0]
        assert "Episode Un" in first_call.args[1]
        assert "Nouvel épisode Le Masque et la Plume transcrit" in first_call.args[0]
        second_call = mock_notify.call_args_list[1]
        assert "Episode Deux" in second_call.args[1]

    @pytest.mark.asyncio
    async def test_should_notify_once_per_failed_episode(self, tmp_path):
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True
        runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)

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
            patch.object(runner, "_send_notification", new=AsyncMock()) as mock_notify,
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: _make_episode(eid, "Episode En Échec")
            )
            mock_mongo.insert_pgx_transcription_log = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = str(tmp_path)

            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=True)
            mock_pgx.send_audio_to_pgx = AsyncMock(side_effect=PgxError("scp failed"))

            await runner._run("manual")

        mock_notify.assert_awaited_once()
        call = mock_notify.call_args_list[0]
        assert "Episode En Échec" in call.args[1]

    @pytest.mark.asyncio
    async def test_should_not_leak_raw_ssh_error_detail_in_failure_notification(
        self, tmp_path
    ):
        """Issue #313 : un message ntfy visible par un utilisateur non
        initié ne doit jamais contenir de détail technique brut (stderr
        SSH multi-lignes, ex. 'kex_exchange_identification: read:
        Connection reset by peer') — seul l'historique /transcription-pgx
        (destiné à un usage de diagnostic) affiche ce détail.
        """
        runner = PgxTranscriptionRunner.get_instance()
        runner.episode_ids = [EP1_ID]
        runner.is_running = True
        runner.start_time = datetime(2026, 3, 1, tzinfo=UTC)

        raw_ssh_error = (
            "Échec de la création du répertoire distant sur PGX: "
            "kex_exchange_identification: read: Connection reset by peer\r\n"
            "Connection reset by 192.168.50.151 port 22\r\n"
        )

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
            patch.object(runner, "_send_notification", new=AsyncMock()) as mock_notify,
        ):
            mock_mongo.get_episode_by_id = MagicMock(
                side_effect=lambda eid: _make_episode(eid)
            )
            mock_mongo.insert_pgx_transcription_log = MagicMock()
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_settings.pgx_transcription_timeout_s = 1800.0
            mock_settings.pgx_poll_interval_s = 10.0
            mock_settings.audio_storage_path = str(tmp_path)

            mock_pgx.wait_for_pgx_reachable = AsyncMock(return_value=True)
            mock_pgx.send_audio_to_pgx = AsyncMock(side_effect=PgxError(raw_ssh_error))

            await runner._run("manual")

        mock_notify.assert_awaited_once()
        call = mock_notify.call_args_list[0]
        assert "kex_exchange_identification" not in call.args[1]
        assert "Connection reset by peer" not in call.args[1]
        assert "Un épisode" in call.args[1]

    @pytest.mark.asyncio
    async def test_should_not_notify_when_nothing_to_do(self):
        runner = PgxTranscriptionRunner.get_instance()

        with (
            patch(
                "back_office_lmelp.utils.pgx_transcription_runner.stats_service"
            ) as mock_stats,
            patch.object(runner, "_send_notification", new=AsyncMock()) as mock_notify,
        ):
            mock_stats.get_episodes_without_transcription = MagicMock(return_value=[])

            await runner.start_transcription()

        mock_notify.assert_not_called()
