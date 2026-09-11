"""Tests TDD pour les endpoints PGX (Issue #302).

Tests pour :
- GET /api/pgx/diagnostics
- GET /api/pgx/episodes-without-transcription
- POST /api/pgx/transcription/start
- GET /api/pgx/transcription/progress
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from back_office_lmelp.app import app

    return TestClient(app)


class TestGetPgxDiagnostics:
    def test_should_return_diagnostics_list(self, client):
        diagnostics = [
            {"name": "Machine joignable", "status": "ok", "detail": "..."},
        ]
        with (
            patch("back_office_lmelp.app.settings") as mock_settings,
            patch("back_office_lmelp.app.pgx_service") as mock_pgx,
        ):
            mock_settings.pgx_host = "192.168.50.151"
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_pgx.get_pgx_config_missing_vars.return_value = []
            mock_pgx.run_pgx_diagnostics = AsyncMock(return_value=diagnostics)

            response = client.get("/api/pgx/diagnostics")

        assert response.status_code == 200
        assert response.json() == {"diagnostics": diagnostics, "missing_vars": []}

    def test_should_skip_network_call_when_config_incomplete(self, client):
        """Piège lmelp #110 : pas d'appel réseau si la config est incomplète."""
        with (
            patch("back_office_lmelp.app.settings") as mock_settings,
            patch("back_office_lmelp.app.pgx_service") as mock_pgx,
        ):
            mock_settings.pgx_host = None
            mock_settings.pgx_user = "pgxuser"
            mock_settings.pgx_ssh_key_path = None
            mock_settings.pgx_remote_audio_root = "/data/audios"
            mock_settings.pgx_remote_transcription_root = "/data/transcriptions"
            mock_pgx.get_pgx_config_missing_vars.return_value = [
                "PGX_HOST",
                "PGX_SSH_KEY_PATH",
            ]
            mock_pgx.run_pgx_diagnostics = AsyncMock()

            response = client.get("/api/pgx/diagnostics")

        assert response.status_code == 200
        assert response.json() == {
            "diagnostics": [],
            "missing_vars": ["PGX_HOST", "PGX_SSH_KEY_PATH"],
        }
        mock_pgx.run_pgx_diagnostics.assert_not_called()


class TestGetPgxSshKey:
    """Issue #310: endpoint pour afficher la clé SSH publique PGX dans l'UI."""

    def test_should_return_public_key(self, client):
        with (
            patch("back_office_lmelp.app.settings") as mock_settings,
            patch("back_office_lmelp.app.pgx_service") as mock_pgx,
        ):
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_pgx.ensure_pgx_ssh_key = AsyncMock(return_value="ssh-ed25519 AAAA...")

            response = client.get("/api/pgx/ssh-key")

        assert response.status_code == 200
        assert response.json() == {
            "public_key": "ssh-ed25519 AAAA...",
            "missing_config": False,
        }
        mock_pgx.ensure_pgx_ssh_key.assert_called_once_with("/keys/pgx_ed25519")

    def test_should_not_call_ensure_key_when_path_missing(self, client):
        with (
            patch("back_office_lmelp.app.settings") as mock_settings,
            patch("back_office_lmelp.app.pgx_service") as mock_pgx,
        ):
            mock_settings.pgx_ssh_key_path = None
            mock_pgx.ensure_pgx_ssh_key = AsyncMock()

            response = client.get("/api/pgx/ssh-key")

        assert response.status_code == 200
        assert response.json() == {"public_key": None, "missing_config": True}
        mock_pgx.ensure_pgx_ssh_key.assert_not_called()

    def test_should_return_500_on_pgx_error(self, client):
        from back_office_lmelp.services.pgx_service import PgxError

        with (
            patch("back_office_lmelp.app.settings") as mock_settings,
            patch("back_office_lmelp.app.pgx_service") as mock_pgx,
        ):
            mock_settings.pgx_ssh_key_path = "/keys/pgx_ed25519"
            mock_pgx.ensure_pgx_ssh_key = AsyncMock(
                side_effect=PgxError("Échec ssh-keygen: command not found")
            )

            response = client.get("/api/pgx/ssh-key")

        assert response.status_code == 500
        assert "ssh-keygen" in response.json()["error"]


class TestGetEpisodesWithoutTranscription:
    def test_should_return_episode_list(self, client):
        episodes = [{"id": "abc123", "titre": "Un épisode", "date": "2026-03-01"}]
        with patch("back_office_lmelp.app.stats_service") as mock_stats:
            mock_stats.get_episodes_without_transcription = MagicMock(
                return_value=episodes
            )

            response = client.get("/api/pgx/episodes-without-transcription")

        assert response.status_code == 200
        assert response.json() == {"episodes": episodes}


class TestStartPgxTranscription:
    def test_should_return_started_status(self, client):
        with patch(
            "back_office_lmelp.utils.pgx_transcription_runner.pgx_transcription_runner"
        ) as mock_runner:
            mock_runner.start_transcription = AsyncMock(
                return_value={"status": "started", "episode_count": 2}
            )

            response = client.post("/api/pgx/transcription/start")

        assert response.status_code == 200
        assert response.json() == {"status": "started", "episode_count": 2}

    def test_should_return_nothing_to_do_status(self, client):
        with patch(
            "back_office_lmelp.utils.pgx_transcription_runner.pgx_transcription_runner"
        ) as mock_runner:
            mock_runner.start_transcription = AsyncMock(
                return_value={"status": "nothing_to_do"}
            )

            response = client.post("/api/pgx/transcription/start")

        assert response.status_code == 200
        assert response.json() == {"status": "nothing_to_do"}


class TestGetPgxTranscriptionProgress:
    def test_should_return_current_status(self, client):
        status = {
            "is_running": True,
            "episode_ids": ["abc123"],
            "current_episode_id": "abc123",
            "current_episode_index": 0,
            "processed": [],
            "start_time": "2026-03-01T10:00:00+00:00",
            "logs": ["Vérification de la disponibilité de PGX…"],
            "last_update": "2026-03-01T10:00:00+00:00",
        }
        with patch(
            "back_office_lmelp.utils.pgx_transcription_runner.pgx_transcription_runner"
        ) as mock_runner:
            mock_runner.get_status = MagicMock(return_value=status)

            response = client.get("/api/pgx/transcription/progress")

        assert response.status_code == 200
        assert response.json() == status
