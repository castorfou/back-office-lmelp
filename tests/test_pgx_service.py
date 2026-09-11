"""Tests pour le service PGX (Issue #302).

Pipeline de transcription automatisée via la station GPU PGX, porté depuis
castorfou/lmelp (nbs/pgx.py). Aucun test ne touche au réseau réel : tout
appel subprocess (ssh/scp/ssh-keygen) est mocké.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from back_office_lmelp.services.pgx_service import (
    PgxError,
    ensure_pgx_ssh_key,
    fetch_transcription_from_pgx,
    get_pgx_config_missing_vars,
    pgx_fully_configured,
    run_pgx_diagnostics,
    send_audio_to_pgx,
    wait_for_pgx_reachable,
    wait_for_pgx_transcription,
)


PGX_TEST_CONFIG = {
    "host": "192.168.50.151",
    "user": "pgxuser",
    "key_path": "/keys/pgx_ed25519",
    "remote_audio_root": "/data/audios",
    "remote_transcription_root": "/data/transcriptions",
}


def _make_subprocess_mock(
    returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""
):
    """Construit un mock d'asyncio.subprocess.Process."""
    process_mock = AsyncMock()
    process_mock.returncode = returncode
    process_mock.communicate = AsyncMock(return_value=(stdout, stderr))
    return process_mock


class TestGetPgxConfigMissingVars:
    """Tests de get_pgx_config_missing_vars() — variables d'env PGX absentes."""

    def test_should_return_empty_list_when_all_vars_present(self):
        """Aucune variable manquante quand toute la config est renseignée."""
        config = {
            "host": "192.168.50.151",
            "user": "pgxuser",
            "key_path": "/app/keys/pgx_ed25519",
            "remote_audio_root": "/data/audios",
            "remote_transcription_root": "/data/transcriptions",
        }

        missing = get_pgx_config_missing_vars(config)

        assert missing == []

    def test_should_return_env_var_names_for_missing_keys(self):
        """Les noms de variables d'env manquantes sont retournés, pas les clés dict."""
        config = {
            "host": None,
            "user": "pgxuser",
            "key_path": None,
            "remote_audio_root": "/data/audios",
            "remote_transcription_root": "/data/transcriptions",
        }

        missing = get_pgx_config_missing_vars(config)

        assert missing == ["PGX_HOST", "PGX_SSH_KEY_PATH"]

    def test_should_return_all_env_var_names_when_config_empty(self):
        """Toutes les variables sont listées quand la config est vide."""
        config = {
            "host": None,
            "user": None,
            "key_path": None,
            "remote_audio_root": None,
            "remote_transcription_root": None,
        }

        missing = get_pgx_config_missing_vars(config)

        assert missing == [
            "PGX_HOST",
            "PGX_USER",
            "PGX_SSH_KEY_PATH",
            "PGX_REMOTE_AUDIO_ROOT",
            "PGX_REMOTE_TRANSCRIPTION_ROOT",
        ]


class TestPgxFullyConfigured:
    """Tests de pgx_fully_configured() — checklist entièrement au vert."""

    def test_should_return_true_when_all_checks_ok(self):
        """True quand tous les diagnostics sont 'ok'."""
        diagnostics = [
            {"name": "Machine joignable", "status": "ok", "detail": "..."},
            {"name": "Authentification SSH", "status": "ok", "detail": "..."},
        ]

        assert pgx_fully_configured(diagnostics) is True

    def test_should_return_false_when_any_check_fails(self):
        """False dès qu'un diagnostic est 'fail' ou 'skipped'."""
        diagnostics = [
            {"name": "Machine joignable", "status": "fail", "detail": "..."},
            {"name": "Authentification SSH", "status": "skipped", "detail": "..."},
        ]

        assert pgx_fully_configured(diagnostics) is False

    def test_should_return_false_when_diagnostics_empty(self):
        """False quand la liste de diagnostics est vide (pas encore vérifié)."""
        assert pgx_fully_configured([]) is False


class TestEnsurePgxSshKey:
    """Tests de ensure_pgx_ssh_key() — génération idempotente de la clé dédiée."""

    @pytest.mark.asyncio
    async def test_should_return_existing_public_key_without_regenerating(
        self, tmp_path
    ):
        """Ne régénère pas une clé déjà présente — invaliderait l'autorisation PGX."""
        key_path = tmp_path / "pgx_ed25519"
        key_path.write_text("existing-private-key")
        pub_key_path = tmp_path / "pgx_ed25519.pub"
        pub_key_path.write_text("ssh-ed25519 AAAAExisting back-office-lmelp-pgx\n")

        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec"
        ) as mock_exec:
            result = await ensure_pgx_ssh_key(str(key_path))

        mock_exec.assert_not_called()
        assert result == "ssh-ed25519 AAAAExisting back-office-lmelp-pgx"

    @pytest.mark.asyncio
    async def test_should_generate_key_when_missing(self, tmp_path):
        """Génère la paire de clés ed25519 quand absente, puis lit la clé publique."""
        key_path = tmp_path / "subdir" / "pgx_ed25519"

        async def fake_create_subprocess_exec(*args, **kwargs):
            # Simule ssh-keygen en écrivant les fichiers attendus.
            key_path.write_text("generated-private-key")
            (tmp_path / "subdir" / "pgx_ed25519.pub").write_text(
                "ssh-ed25519 AAAAGenerated back-office-lmelp-pgx\n"
            )
            return _make_subprocess_mock(returncode=0)

        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            side_effect=fake_create_subprocess_exec,
        ) as mock_exec:
            result = await ensure_pgx_ssh_key(str(key_path))

        mock_exec.assert_called_once()
        call_args = mock_exec.call_args.args
        assert call_args[0] == "ssh-keygen"
        assert "-t" in call_args
        assert "ed25519" in call_args
        assert "-N" in call_args
        assert result == "ssh-ed25519 AAAAGenerated back-office-lmelp-pgx"

    @pytest.mark.asyncio
    async def test_should_raise_pgx_error_when_ssh_keygen_fails(self, tmp_path):
        """Lève PgxError si ssh-keygen échoue (returncode non nul)."""
        key_path = tmp_path / "pgx_ed25519"

        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                AsyncMock(
                    return_value=_make_subprocess_mock(
                        returncode=1, stderr=b"ssh-keygen: permission denied"
                    )
                ),
            ),
            pytest.raises(PgxError, match="permission denied"),
        ):
            await ensure_pgx_ssh_key(str(key_path))


class TestWaitForPgxReachable:
    """Tests de wait_for_pgx_reachable() — poll TCP port 22."""

    @pytest.mark.asyncio
    async def test_should_return_true_when_connection_succeeds_immediately(self):
        """True dès que la connexion TCP réussit, sans attendre le poll suivant."""
        writer_mock = AsyncMock()
        writer_mock.close = lambda: None

        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.open_connection",
            AsyncMock(return_value=(AsyncMock(), writer_mock)),
        ):
            result = await wait_for_pgx_reachable(
                "192.168.50.151", timeout_s=5, poll_interval_s=1
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_should_return_false_when_deadline_exceeded(self):
        """False si aucune connexion n'a réussi avant l'expiration du délai."""
        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.open_connection",
                AsyncMock(side_effect=OSError("connection refused")),
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.sleep",
                AsyncMock(),
            ),
        ):
            result = await wait_for_pgx_reachable(
                "192.168.50.151", timeout_s=0, poll_interval_s=1
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_should_retry_after_timeout_error_then_succeed(self):
        """Une première tentative en timeout n'empêche pas un succès au poll suivant."""
        writer_mock = AsyncMock()
        writer_mock.close = lambda: None

        call_count = 0

        async def fake_open_connection(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError
            return AsyncMock(), writer_mock

        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.open_connection",
                side_effect=fake_open_connection,
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.sleep",
                AsyncMock(),
            ),
        ):
            result = await wait_for_pgx_reachable(
                "192.168.50.151", timeout_s=30, poll_interval_s=1
            )

        assert result is True
        assert call_count == 2


class TestSendAudioToPgx:
    """Tests de send_audio_to_pgx() — envoi scp avec création préalable du répertoire distant."""

    @pytest.mark.asyncio
    async def test_should_create_remote_dir_then_scp_the_file(self, tmp_path):
        """Crée d'abord le répertoire distant (ssh mkdir -p) puis envoie par scp."""
        local_file = tmp_path / "episode.mp3"
        local_file.write_text("fake audio")

        calls = []

        async def fake_create_subprocess_exec(*args, **kwargs):
            calls.append(args)
            return _make_subprocess_mock(returncode=0)

        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            side_effect=fake_create_subprocess_exec,
        ):
            await send_audio_to_pgx(
                str(local_file),
                "/data/audios/2026",
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
            )

        assert len(calls) == 2
        mkdir_call = calls[0]
        assert mkdir_call[0] == "ssh"
        assert "mkdir -p '/data/audios/2026'" in mkdir_call
        scp_call = calls[1]
        assert scp_call[0] == "scp"
        assert str(local_file) in scp_call
        assert "pgxuser@192.168.50.151:/data/audios/2026/" in scp_call

    @pytest.mark.asyncio
    async def test_should_raise_pgx_error_when_remote_dir_creation_fails(
        self, tmp_path
    ):
        """Lève PgxError si le mkdir -p distant échoue."""
        local_file = tmp_path / "episode.mp3"
        local_file.write_text("fake audio")

        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                AsyncMock(
                    return_value=_make_subprocess_mock(
                        returncode=1, stderr=b"mkdir: permission denied"
                    )
                ),
            ),
            pytest.raises(PgxError, match="répertoire distant"),
        ):
            await send_audio_to_pgx(
                str(local_file),
                "/data/audios/2026",
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
            )

    @pytest.mark.asyncio
    async def test_should_raise_pgx_error_when_scp_fails(self, tmp_path):
        """Lève PgxError si le scp d'envoi échoue (mkdir a réussi)."""
        local_file = tmp_path / "episode.mp3"
        local_file.write_text("fake audio")

        call_count = 0

        async def fake_create_subprocess_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_subprocess_mock(returncode=0)
            return _make_subprocess_mock(returncode=1, stderr=b"scp: connection lost")

        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                side_effect=fake_create_subprocess_exec,
            ),
            pytest.raises(PgxError, match="envoi du fichier audio"),
        ):
            await send_audio_to_pgx(
                str(local_file),
                "/data/audios/2026",
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
            )

    @pytest.mark.asyncio
    async def test_should_raise_pgx_error_on_timeout(self, tmp_path):
        """Lève PgxError (pas TimeoutError brut) si le scp dépasse le timeout."""
        local_file = tmp_path / "episode.mp3"
        local_file.write_text("fake audio")

        call_count = 0

        async def fake_create_subprocess_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_subprocess_mock(returncode=0)
            process_mock = AsyncMock()
            process_mock.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
            process_mock.kill = lambda: None
            process_mock.wait = AsyncMock()
            return process_mock

        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                side_effect=fake_create_subprocess_exec,
            ),
            pytest.raises(PgxError, match="Timeout"),
        ):
            await send_audio_to_pgx(
                str(local_file),
                "/data/audios/2026",
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
                timeout_s=5,
            )


class TestWaitForPgxTranscription:
    """Tests de wait_for_pgx_transcription() — poll ssh de l'apparition du .txt distant."""

    @pytest.mark.asyncio
    async def test_should_return_true_as_soon_as_file_exists(self):
        """True dès que 'test -f' réussit (returncode 0), sans attendre le timeout."""
        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_make_subprocess_mock(returncode=0)),
        ):
            result = await wait_for_pgx_transcription(
                "/data/transcriptions/2026/episode.txt",
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
                timeout_s=30,
                poll_interval_s=1,
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_should_return_false_when_timeout_exceeded(self):
        """False si le fichier n'apparaît jamais avant expiration du délai."""
        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                AsyncMock(return_value=_make_subprocess_mock(returncode=1)),
            ),
            patch("back_office_lmelp.services.pgx_service.asyncio.sleep", AsyncMock()),
        ):
            result = await wait_for_pgx_transcription(
                "/data/transcriptions/2026/episode.txt",
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
                timeout_s=0,
                poll_interval_s=1,
            )

        assert result is False


class TestFetchTranscriptionFromPgx:
    """Tests de fetch_transcription_from_pgx() — rapatriement scp puis lecture du contenu."""

    @pytest.mark.asyncio
    async def test_should_scp_and_return_file_content(self, tmp_path):
        """Rapatrie le fichier par scp puis retourne son contenu texte."""
        local_txt = tmp_path / "episode.txt"

        async def fake_create_subprocess_exec(*args, **kwargs):
            local_txt.write_text("Ceci est la transcription complète.")
            return _make_subprocess_mock(returncode=0)

        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            side_effect=fake_create_subprocess_exec,
        ):
            result = await fetch_transcription_from_pgx(
                "/data/transcriptions/2026/episode.txt",
                str(local_txt),
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
            )

        assert result == "Ceci est la transcription complète."

    @pytest.mark.asyncio
    async def test_should_raise_pgx_error_when_scp_fails(self, tmp_path):
        """Lève PgxError si le scp de rapatriement échoue."""
        local_txt = tmp_path / "episode.txt"

        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                AsyncMock(
                    return_value=_make_subprocess_mock(
                        returncode=1, stderr=b"scp: no such file"
                    )
                ),
            ),
            pytest.raises(PgxError, match="rapatriement"),
        ):
            await fetch_transcription_from_pgx(
                "/data/transcriptions/2026/episode.txt",
                str(local_txt),
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
            )


class TestRunPgxDiagnostics:
    """Tests de run_pgx_diagnostics() — checklist en cascade (piège lmelp #110/#111)."""

    @pytest.mark.asyncio
    async def test_should_return_all_ok_when_everything_succeeds(self):
        """4 checks 'ok' quand joignable + auth SSH + les 2 répertoires existent."""
        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                AsyncMock(
                    return_value=_make_subprocess_mock(returncode=0, stdout=b"ok\n")
                ),
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.open_connection",
                AsyncMock(return_value=(AsyncMock(), AsyncMock(close=lambda: None))),
            ),
        ):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert [r["status"] for r in results] == ["ok", "ok", "ok", "ok"]
        assert [r["name"] for r in results] == [
            "Machine joignable",
            "Authentification SSH (clé dédiée)",
            "Répertoire audio distant",
            "Répertoire transcriptions distant",
        ]

    @pytest.mark.asyncio
    async def test_should_skip_remaining_checks_when_unreachable(self):
        """Piège #110 : injoignable => les 3 checks suivants sont 'skipped', pas de
        tentative d'authentification SSH (qui planterait sur host=None dans d'autres
        contextes, ou perdrait du temps ici)."""
        with (
            patch(
                "back_office_lmelp.services.pgx_service.wait_for_pgx_reachable",
                AsyncMock(return_value=False),
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec"
            ) as mock_exec,
        ):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert results[0]["status"] == "fail"
        assert [r["status"] for r in results[1:]] == ["skipped", "skipped", "skipped"]
        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_skip_directory_checks_when_ssh_auth_fails(self):
        """Joignable mais authentification SSH échoue => les 2 checks répertoires
        sont 'skipped' (inutile de tester des répertoires sans authentification)."""
        call_count = 0

        async def fake_create_subprocess_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_subprocess_mock(
                returncode=1, stderr=b"Permission denied (publickey)"
            )

        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.open_connection",
                AsyncMock(return_value=(AsyncMock(), AsyncMock(close=lambda: None))),
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                side_effect=fake_create_subprocess_exec,
            ),
        ):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert results[0]["status"] == "ok"
        assert results[1]["status"] == "fail"
        # Piège #111 : le detail inclut le vrai stderr, pas un message générique statique.
        assert "Permission denied (publickey)" in results[1]["detail"]
        assert [r["status"] for r in results[2:]] == ["skipped", "skipped"]
        assert call_count == 1  # un seul appel ssh (l'auth), pas les checks répertoires

    @pytest.mark.asyncio
    async def test_should_report_generic_message_when_ssh_auth_fails_with_empty_stderr(
        self,
    ):
        """Piège #111 (cas limite) : si stderr est vide, garder le message générique
        plutôt que d'afficher un detail vide."""
        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.open_connection",
                AsyncMock(return_value=(AsyncMock(), AsyncMock(close=lambda: None))),
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                AsyncMock(return_value=_make_subprocess_mock(returncode=1, stderr=b"")),
            ),
        ):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert results[1]["status"] == "fail"
        assert "authorized_keys" in results[1]["detail"]
        assert "détail SSH" not in results[1]["detail"]

    @pytest.mark.asyncio
    async def test_should_report_fail_per_directory_independently(self):
        """Joignable + auth OK mais un seul répertoire distant manque : l'autre check
        reste indépendant (pas de court-circuit entre les 2 vérifications de répertoires)."""
        call_count = 0

        async def fake_create_subprocess_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # auth SSH
                return _make_subprocess_mock(returncode=0, stdout=b"ok\n")
            if call_count == 2:  # répertoire audio
                return _make_subprocess_mock(returncode=0)
            return _make_subprocess_mock(returncode=1)  # répertoire transcriptions

        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.open_connection",
                AsyncMock(return_value=(AsyncMock(), AsyncMock(close=lambda: None))),
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                side_effect=fake_create_subprocess_exec,
            ),
        ):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert results[2]["status"] == "ok"
        assert results[3]["status"] == "fail"
