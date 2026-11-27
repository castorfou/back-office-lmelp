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
    fetch_segments_from_pgx,
    fetch_transcription_from_pgx,
    get_pgx_config_missing_vars,
    host_key_fingerprint,
    install_pgx_host_key,
    parse_pgx_host_key,
    pgx_fully_configured,
    remote_file_exists,
    requeue_pgx_audio,
    run_pgx_diagnostics,
    send_audio_to_pgx,
    wait_for_pgx_transcription,
)


# Clés publiques d'hôte générées pour ces tests (`ssh-keygen -t ed25519`), et leurs
# empreintes calculées par `ssh-keygen -lf`
PGX_KEY_B64 = "AAAAC3NzaC1lZDI1NTE5AAAAIFwHMNuxrSKMJxd5UALz3Cx8yg9E0sm0A/hDvHPwbA8d"  # pragma: allowlist secret
OTHER_KEY_B64 = "AAAAC3NzaC1lZDI1NTE5AAAAIFgWg0KeBqeXTeAPCfrOrt9g0Qh3B5QdfwCfI1b0DbUu"  # pragma: allowlist secret
PGX_FINGERPRINT = "SHA256:3lUWrXecKY6L1mZAIResebD/lOeIy3CuYex6u1hU9wU"
OTHER_FINGERPRINT = "SHA256:s9QpZso9EwJYjw+fW9spBV5bEKm5I93R6ZO/h7jHAgk"

PGX_TEST_CONFIG = {
    "host": "192.168.50.151",
    "user": "pgxuser",
    "key_path": "/keys/pgx_ed25519",
    "remote_audio_root": "/data/audios",
    "remote_transcription_root": "/data/transcriptions",
    # Contenu de /etc/ssh/ssh_host_ed25519_key.pub
    "host_key": f"ssh-ed25519 {PGX_KEY_B64} root@pgx",
}

# Sortie réelle de `ssh-keyscan -t ed25519 <ip>` : la clé sur stdout, la bannière
# du serveur en commentaire sur stderr
KEYSCAN_STDOUT_PGX = f"192.168.50.151 ssh-ed25519 {PGX_KEY_B64}\n".encode()
KEYSCAN_STDOUT_OTHER = f"192.168.50.151 ssh-ed25519 {OTHER_KEY_B64}\n".encode()
KEYSCAN_STDERR = b"# 192.168.50.151:22 SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.5\n"

# stderr réels cités dans l'issue #354
STDERR_PERMISSION_DENIED = (
    b"pgxuser@192.168.49.6: Permission denied (publickey,password).\r\n"
)
STDERR_HOST_KEY_CHANGED = (
    b"@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\r\n"
    b"@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @\r\n"
    b"@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\r\n"
    b"IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!\r\n"
    b"The fingerprint for the ED25519 key sent by the remote host is\r\n"
    b"SHA256:25SQCoKsuvCVdRNxfmcQdwC2wbSns6z4sMrziDVcMCc.\r\n"
    b"Offending ED25519 key in /tmp/back_office_lmelp_pgx_known_hosts:1\r\n"
    b"Host key verification failed.\r\n"
)


def _make_subprocess_mock(
    returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""
) -> AsyncMock:
    """Construit un mock d'asyncio.subprocess.Process."""
    process_mock = AsyncMock()
    process_mock.returncode = returncode
    process_mock.communicate = AsyncMock(return_value=(stdout, stderr))
    return process_mock


@pytest.fixture(autouse=True)
def known_hosts_in_tmp(tmp_path):
    """Le known_hosts généré vit dans tmp_path, jamais dans le /tmp partagé."""
    path = tmp_path / "pgx_known_hosts"
    with patch(
        "back_office_lmelp.services.pgx_service._known_hosts_path",
        return_value=str(path),
    ):
        yield path


class _ExecDispatch:
    """Faux create_subprocess_exec : ssh-keyscan répond avec `keyscan_stdout`,
    chaque appel ssh/scp consomme le mock suivant de `ssh_results`."""

    def __init__(
        self, ssh_results: list[AsyncMock], keyscan_stdout: bytes = KEYSCAN_STDOUT_PGX
    ) -> None:
        self._ssh_iter = iter(ssh_results)
        self._keyscan_stdout = keyscan_stdout
        self.calls: list[tuple] = []

    async def __call__(self, *args, **kwargs):
        self.calls.append(args)
        if args[0] == "ssh-keyscan":
            return _make_subprocess_mock(
                0, stdout=self._keyscan_stdout, stderr=KEYSCAN_STDERR
            )
        return next(self._ssh_iter)


def _patch_exec(side_effect):
    # AsyncMock n'attend le side_effect que s'il est une fonction coroutine
    async def call(*args, **kwargs):
        return await side_effect(*args, **kwargs)

    return patch(
        "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
        side_effect=call,
    )


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
            "host_key": PGX_TEST_CONFIG["host_key"],
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
            "host_key": None,
        }

        missing = get_pgx_config_missing_vars(config)

        assert missing == ["PGX_HOST", "PGX_SSH_KEY_PATH", "PGX_HOST_KEY"]

    def test_should_return_all_env_var_names_when_config_empty(self):
        """Toutes les variables sont listées quand la config est vide."""
        config = {
            "host": None,
            "user": None,
            "key_path": None,
            "remote_audio_root": None,
            "remote_transcription_root": None,
            "host_key": None,
        }

        missing = get_pgx_config_missing_vars(config)

        assert missing == [
            "PGX_HOST",
            "PGX_USER",
            "PGX_SSH_KEY_PATH",
            "PGX_REMOTE_AUDIO_ROOT",
            "PGX_REMOTE_TRANSCRIPTION_ROOT",
            "PGX_HOST_KEY",
        ]


class TestPgxFullyConfigured:
    """Tests de pgx_fully_configured() — checklist entièrement au vert."""

    def test_should_return_true_when_all_checks_ok(self):
        """True quand tous les diagnostics sont 'ok'."""
        diagnostics = [
            {"name": "PGX localisée", "status": "ok", "detail": "..."},
            {"name": "Authentification SSH", "status": "ok", "detail": "..."},
        ]

        assert pgx_fully_configured(diagnostics) is True

    def test_should_return_false_when_any_check_fails(self):
        """False dès qu'un diagnostic est 'fail' ou 'skipped'."""
        diagnostics = [
            {"name": "PGX localisée", "status": "fail", "detail": "..."},
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


class TestRemoteFileExists:
    """Tests de remote_file_exists() — test ponctuel d'un fichier sur PGX (Issue #320)."""

    @pytest.mark.asyncio
    async def test_should_return_true_when_file_exists(self):
        exec_mock = AsyncMock(return_value=_make_subprocess_mock(returncode=0))
        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            exec_mock,
        ):
            result = await remote_file_exists(
                "/data/audios/2026/episode.mp3",
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
            )

        assert result is True
        assert "test -f '/data/audios/2026/episode.mp3'" in exec_mock.call_args.args

    @pytest.mark.asyncio
    async def test_should_return_false_when_file_is_missing(self):
        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            AsyncMock(return_value=_make_subprocess_mock(returncode=1)),
        ):
            result = await remote_file_exists(
                "/data/audios/2026/episode.mp3",
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
            )

        assert result is False


class TestRequeuePgxAudio:
    """Tests de requeue_pgx_audio() — relance via la file de whisper (Issue #320)."""

    @staticmethod
    async def _requeue() -> None:
        await requeue_pgx_audio(
            "/data/audios/2026/episode.mp3",
            container="whisper-arm64",
            host="192.168.50.151",
            user="pgxuser",
            key_path="/keys/pgx_ed25519",
        )

    @pytest.mark.asyncio
    async def test_should_enqueue_audio_in_whisper_container(self):
        exec_mock = AsyncMock(return_value=_make_subprocess_mock(returncode=0))
        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            exec_mock,
        ):
            await self._requeue()

        assert exec_mock.call_args.args[-1] == (
            "docker exec 'whisper-arm64' python3 -m whisper_docker.queue_manager "
            "enqueue '/data/audios/2026/episode.mp3'"
        )

    @pytest.mark.asyncio
    async def test_should_accept_audio_already_in_queue(self):
        """Un job déjà pending/running n'est pas une erreur : il va aboutir."""
        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            AsyncMock(
                return_value=_make_subprocess_mock(
                    returncode=1,
                    stderr=b"Fichier d\xc3\xa9j\xc3\xa0 en queue: /data/x.mp3",
                )
            ),
        ):
            await self._requeue()

    @pytest.mark.asyncio
    async def test_should_detect_already_queued_message_on_stdout(self):
        """Le message passe par le logger de whisper : son flux n'est pas garanti."""
        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            AsyncMock(
                return_value=_make_subprocess_mock(
                    returncode=1,
                    stdout=b"Fichier d\xc3\xa9j\xc3\xa0 en queue: /data/x.mp3",
                )
            ),
        ):
            await self._requeue()

    @pytest.mark.asyncio
    async def test_should_raise_pgx_error_when_enqueue_fails(self):
        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                AsyncMock(
                    return_value=_make_subprocess_mock(
                        returncode=1, stderr=b"No such container: whisper-arm64"
                    )
                ),
            ),
            pytest.raises(PgxError, match="No such container"),
        ):
            await self._requeue()


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
        """4 checks 'ok' quand PGX localisée + auth SSH + les 2 répertoires."""
        ok = _make_subprocess_mock(returncode=0, stdout=b"ok\n")
        with _reachable(), _patch_exec(_ExecDispatch([ok, ok, ok])):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert [r["status"] for r in results] == ["ok"] * 4
        assert PGX_FINGERPRINT in results[0]["detail"]
        assert [r["name"] for r in results] == [
            "PGX localisée",
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
                "back_office_lmelp.services.pgx_service.asyncio.open_connection",
                AsyncMock(side_effect=OSError(113, "No route to host")),
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec"
            ) as mock_exec,
        ):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert results[0]["status"] == "fail"
        assert "192.168.50.151 ne répond pas sur le port 22" in results[0]["detail"]
        assert [r["status"] for r in results[1:]] == ["skipped"] * 3
        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_skip_directory_checks_when_ssh_auth_fails(self):
        """PGX reconnue mais elle refuse la clé => authorized_keys, et les 2 checks
        répertoires sont 'skipped'."""
        dispatch = _ExecDispatch(
            [_make_subprocess_mock(returncode=255, stderr=STDERR_PERMISSION_DENIED)]
        )
        with _reachable(), _patch_exec(dispatch):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert results[0]["status"] == "ok"
        assert results[1]["status"] == "fail"
        assert "authorized_keys" in results[1]["detail"]
        # Piège #111 : le detail inclut le vrai stderr, pas un message générique statique.
        assert "Permission denied (publickey,password)" in results[1]["detail"]
        assert [r["status"] for r in results[2:]] == ["skipped", "skipped"]
        # ssh-keyscan puis l'auth, pas les checks répertoires
        assert [c[0] for c in dispatch.calls] == ["ssh-keyscan", "ssh"]

    @pytest.mark.asyncio
    async def test_host_key_failure_should_show_raw_stderr_not_authorized_keys(self):
        """Un échec de vérification de clé d'hôte n'est pas un refus de clé : le
        stderr ssh brut est affiché, sans renvoyer vers authorized_keys."""
        dispatch = _ExecDispatch(
            [_make_subprocess_mock(returncode=255, stderr=STDERR_HOST_KEY_CHANGED)]
        )
        with _reachable(), _patch_exec(dispatch):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert results[1]["status"] == "fail"
        assert "Host key verification failed." in results[1]["detail"]
        assert "authorized_keys" not in results[1]["detail"]

    @pytest.mark.asyncio
    async def test_should_report_generic_message_when_ssh_auth_fails_with_empty_stderr(
        self,
    ):
        """Piège #111 (cas limite) : stderr vide => message générique, pas un
        detail vide, et pas de fausse piste authorized_keys."""
        dispatch = _ExecDispatch([_make_subprocess_mock(returncode=1, stderr=b"")])
        with _reachable(), _patch_exec(dispatch):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert results[1]["status"] == "fail"
        assert results[1]["detail"]
        assert "authorized_keys" not in results[1]["detail"]

    @pytest.mark.asyncio
    async def test_should_report_fail_per_directory_independently(self):
        """Joignable + auth OK mais un seul répertoire distant manque : l'autre check
        reste indépendant (pas de court-circuit entre les 2 vérifications de répertoires)."""
        dispatch = _ExecDispatch(
            [
                _make_subprocess_mock(returncode=0, stdout=b"ok\n"),  # auth SSH
                _make_subprocess_mock(returncode=0),  # répertoire audio
                _make_subprocess_mock(returncode=1),  # répertoire transcriptions
            ]
        )
        with _reachable(), _patch_exec(dispatch):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert results[2]["status"] == "ok"
        assert results[3]["status"] == "fail"


def _make_hanging_subprocess_mock() -> AsyncMock:
    """Processus ssh qui ne rend jamais la main (connexion morte sans keepalive)."""

    async def never_returns() -> tuple[bytes, bytes]:
        await asyncio.Event().wait()
        return b"", b""

    process_mock = AsyncMock()
    process_mock.returncode = None
    process_mock.communicate = never_returns
    process_mock.kill = lambda: None
    process_mock.wait = AsyncMock(return_value=-9)
    return process_mock


class TestNoUnboundedSshCommand:
    """Aucune commande ssh/scp ne peut bloquer le pipeline PGX (Issue #337).

    Cas réel du 11/11/2026 : la transcription était sur PGX, mais le cycle est
    resté sur « attente… » : une vérification `ssh test -f` lancée sans délai
    ne rendait jamais la main, le délai global n'était donc jamais revérifié et
    is_running restait True (bouton « Lancer » grisé jusqu'au redémarrage).
    """

    @pytest.mark.asyncio
    async def test_wait_should_survive_a_hanging_check_and_find_the_file(self):
        processes = [_make_hanging_subprocess_mock(), _make_subprocess_mock(0)]
        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                AsyncMock(side_effect=processes),
            ),
            patch("back_office_lmelp.services.pgx_service.asyncio.sleep", AsyncMock()),
        ):
            result = await wait_for_pgx_transcription(
                "/data/transcriptions/2024/episode.txt",
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
                timeout_s=30,
                poll_interval_s=1,
                command_timeout_s=0.05,
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_should_respect_its_deadline_when_every_check_hangs(self):
        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            AsyncMock(side_effect=lambda *a, **k: _make_hanging_subprocess_mock()),
        ):
            result = await asyncio.wait_for(
                wait_for_pgx_transcription(
                    "/data/transcriptions/2024/episode.txt",
                    host="192.168.50.151",
                    user="pgxuser",
                    key_path="/keys/pgx_ed25519",
                    timeout_s=0.2,
                    poll_interval_s=0.01,
                    command_timeout_s=0.05,
                ),
                timeout=5,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_hanging_remote_check_should_fail_the_episode_not_hang(self):
        """Une PgxError fait échouer l'épisode sans arrêter la file d'attente."""
        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                AsyncMock(return_value=_make_hanging_subprocess_mock()),
            ),
            patch("back_office_lmelp.services.pgx_service.SSH_COMMAND_TIMEOUT_S", 0.05),
            pytest.raises(PgxError),
        ):
            await asyncio.wait_for(
                remote_file_exists(
                    "/data/transcriptions/2024/episode.txt",
                    host="192.168.50.151",
                    user="pgxuser",
                    key_path="/keys/pgx_ed25519",
                ),
                timeout=5,
            )

    @pytest.mark.asyncio
    async def test_ssh_should_never_prompt_nor_keep_a_dead_connection(self):
        exec_mock = AsyncMock(return_value=_make_subprocess_mock(0))
        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            exec_mock,
        ):
            await remote_file_exists(
                "/data/transcriptions/2024/episode.txt",
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
            )

        args = exec_mock.call_args.args
        assert "BatchMode=yes" in args
        assert any(a.startswith("ConnectTimeout=") for a in args)
        assert any(a.startswith("ServerAliveInterval=") for a in args)
        assert exec_mock.call_args.kwargs["stdin"] == asyncio.subprocess.DEVNULL


def _reachable():
    return patch(
        "back_office_lmelp.services.pgx_service.asyncio.open_connection",
        AsyncMock(return_value=(AsyncMock(), AsyncMock(close=lambda: None))),
    )


class TestPgxIdentityCheck:
    """La checklist reconnaît PGX à sa clé d'hôte, jamais à son adresse (#361)."""

    @pytest.mark.asyncio
    async def test_other_machine_on_pgx_address_should_be_named_as_the_cause(self):
        exec_mock = AsyncMock(
            return_value=_make_subprocess_mock(
                0, stdout=KEYSCAN_STDOUT_OTHER, stderr=KEYSCAN_STDERR
            )
        )
        with (
            _reachable(),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                exec_mock,
            ),
        ):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        identity = results[0]
        assert identity["name"] == "PGX localisée"
        assert identity["status"] == "fail"
        assert "192.168.50.151 n'est pas PGX" in identity["detail"]
        assert "clé d'hôte différente" in identity["detail"]
        assert PGX_FINGERPRINT in identity["detail"]
        assert OTHER_FINGERPRINT in identity["detail"]
        assert "authorized_keys" not in identity["detail"]
        assert [r["status"] for r in results[1:]] == ["skipped"] * 3
        # Un seul appel : ssh-keyscan, sans authentification
        assert exec_mock.call_count == 1
        assert exec_mock.call_args.args[0] == "ssh-keyscan"

    @pytest.mark.asyncio
    async def test_pgx_at_a_new_address_should_still_be_recognized(self):
        """Même clé, autre IP : PGX est reconnue, pas de « host key changed »."""
        keyscan = KEYSCAN_STDOUT_PGX.replace(b"192.168.50.151", b"192.168.49.10")
        config = {**PGX_TEST_CONFIG, "host": "192.168.49.10"}
        dispatch = _ExecDispatch(
            [_make_subprocess_mock(0, stdout=b"ok\n")] * 3, keyscan_stdout=keyscan
        )
        with _reachable(), _patch_exec(dispatch):
            results = await run_pgx_diagnostics(config)

        assert [r["status"] for r in results] == ["ok"] * 4
        assert "PGX trouvée en 192.168.49.10" in results[0]["detail"]

    @pytest.mark.asyncio
    async def test_no_host_key_received_should_fail_with_keyscan_detail(self):
        dispatch = _ExecDispatch([], keyscan_stdout=b"")
        with _reachable(), _patch_exec(dispatch):
            results = await run_pgx_diagnostics(PGX_TEST_CONFIG)

        assert results[0]["status"] == "fail"
        assert "aucune clé d'hôte" in results[0]["detail"]
        assert PGX_FINGERPRINT in results[0]["detail"]
        assert [r["status"] for r in results[1:]] == ["skipped"] * 3

    @pytest.mark.asyncio
    async def test_invalid_pgx_host_key_should_fail_without_any_command(self):
        config = {**PGX_TEST_CONFIG, "host_key": "pas une clé"}
        dispatch = _ExecDispatch([])
        with _reachable(), _patch_exec(dispatch):
            results = await run_pgx_diagnostics(config)

        assert results[0]["status"] == "fail"
        assert "PGX_HOST_KEY invalide" in results[0]["detail"]
        assert dispatch.calls == []

    @pytest.mark.asyncio
    async def test_keyscan_should_be_bounded_in_time(self):
        """ssh-keyscan a son propre délai (-T) et la commande entière est bornée."""
        with (
            _reachable(),
            _patch_exec(
                lambda *a, **k: asyncio.sleep(0, result=_make_hanging_subprocess_mock())
            ),
            patch(
                "back_office_lmelp.services.pgx_service.KEYSCAN_COMMAND_TIMEOUT_S",
                0.05,
            ),
        ):
            results = await asyncio.wait_for(
                run_pgx_diagnostics(PGX_TEST_CONFIG), timeout=5
            )

        assert results[0]["status"] == "fail"
        assert "à temps" in results[0]["detail"]

    @pytest.mark.asyncio
    async def test_keyscan_command_should_ask_only_for_the_pinned_key_type(self):
        dispatch = _ExecDispatch([_make_subprocess_mock(0, stdout=b"ok\n")] * 3)
        with _reachable(), _patch_exec(dispatch):
            await run_pgx_diagnostics(PGX_TEST_CONFIG)

        keyscan = dispatch.calls[0]
        assert keyscan[0] == "ssh-keyscan"
        assert keyscan[keyscan.index("-t") + 1] == "ed25519"
        assert "-T" in keyscan
        assert keyscan[-1] == "192.168.50.151"


class TestPinnedHostKey:
    """ssh/scp n'acceptent que la clé de PGX, sous un alias fixe (#361, ADR 0002)."""

    def test_parse_should_accept_the_pub_file_content(self):
        assert parse_pgx_host_key(PGX_TEST_CONFIG["host_key"]) == (
            "ssh-ed25519",
            PGX_KEY_B64,
        )

    def test_parse_should_accept_a_keyscan_line(self):
        key_type, _ = parse_pgx_host_key(KEYSCAN_STDOUT_PGX.decode())
        assert key_type == "ssh-ed25519"

    def test_parse_should_reject_a_non_ed25519_key(self):
        """Seule la clé ED25519 est épinglée : ssh-keyscan -t ed25519 la demande."""
        with pytest.raises(ValueError):
            parse_pgx_host_key("ecdsa-sha2-nistp256 AAAAE2VjZHNh root@pgx")

    def test_parse_should_reject_garbage(self):
        with pytest.raises(ValueError):
            parse_pgx_host_key("ssh-ed25519 pas-du-base64!")

    def test_fingerprint_should_match_ssh_keygen(self):
        _, key_b64 = parse_pgx_host_key(PGX_TEST_CONFIG["host_key"])
        assert host_key_fingerprint(key_b64) == PGX_FINGERPRINT

    def test_known_hosts_should_hold_only_pgx_key_under_the_alias(
        self, known_hosts_in_tmp
    ):
        known_hosts_in_tmp.write_text("192.168.49.6 ssh-ed25519 AAAAancienne\n")

        install_pgx_host_key(PGX_TEST_CONFIG["host_key"])

        assert known_hosts_in_tmp.read_text() == f"pgx ssh-ed25519 {PGX_KEY_B64}\n"

    @pytest.mark.asyncio
    async def test_ssh_and_scp_should_never_accept_an_unknown_host_key(
        self, known_hosts_in_tmp, tmp_path
    ):
        exec_mock = AsyncMock(return_value=_make_subprocess_mock(0))
        with patch(
            "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
            exec_mock,
        ):
            await remote_file_exists(
                "/data/x.txt", host="192.168.49.6", user="u", key_path="/k"
            )
            (tmp_path / "x.txt").write_text("t")
            await fetch_transcription_from_pgx(
                "/data/x.txt",
                str(tmp_path / "x.txt"),
                host="192.168.49.6",
                user="u",
                key_path="/k",
            )

        for call in exec_mock.call_args_list:
            args = call.args
            assert args[0] in ("ssh", "scp")
            assert "StrictHostKeyChecking=yes" in args
            assert "HostKeyAlias=pgx" in args
            assert f"UserKnownHostsFile={known_hosts_in_tmp}" in args
            assert not any("accept-new" in a for a in args)


class TestFetchSegmentsFromPgx:
    """Rapatriement du .json horodaté de whisper (Issue #427).

    PGX peut encore écrire le .json quand il est rapatrié : un contenu qui ne
    se décode pas est relu après une attente.
    """

    @pytest.mark.asyncio
    async def test_un_json_en_cours_d_ecriture_est_relu(self, tmp_path):
        local_json = tmp_path / "episode.json"
        contenus = iter(
            ['{"transcription": [{"offsets": {"from": 0', '{"transcription": []}']
        )

        async def fake_create_subprocess_exec(*args, **kwargs):
            local_json.write_text(next(contenus))
            return _make_subprocess_mock(returncode=0)

        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                side_effect=fake_create_subprocess_exec,
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.sleep",
                new=AsyncMock(),
            ) as attente,
        ):
            whisper = await fetch_segments_from_pgx(
                "/data/transcriptions/2026/episode.json",
                str(local_json),
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
                attente_s=10,
            )

        assert whisper == {"transcription": []}
        attente.assert_awaited_once_with(10)

    @pytest.mark.asyncio
    async def test_un_json_toujours_illisible_fait_echouer_l_episode(self, tmp_path):
        local_json = tmp_path / "episode.json"

        async def fake_create_subprocess_exec(*args, **kwargs):
            local_json.write_text('{"transcription": [')
            return _make_subprocess_mock(returncode=0)

        with (
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.create_subprocess_exec",
                side_effect=fake_create_subprocess_exec,
            ),
            patch(
                "back_office_lmelp.services.pgx_service.asyncio.sleep",
                new=AsyncMock(),
            ),
            pytest.raises(PgxError, match="illisibles"),
        ):
            await fetch_segments_from_pgx(
                "/data/transcriptions/2026/episode.json",
                str(local_json),
                host="192.168.50.151",
                user="pgxuser",
                key_path="/keys/pgx_ed25519",
                tentatives=3,
            )

        # retiré du disque : la reprise de l'épisode le rapatriera de nouveau
        assert not local_json.exists()
