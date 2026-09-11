"""Tests pour le module settings.

Ce module teste la classe Settings et ses propriétés d'environnement.
"""

import os

from back_office_lmelp.settings import Settings


class TestSettings:
    """Tests de la classe Settings."""

    def test_annas_archive_url_should_return_env_value_when_set(self):
        """Test que annas_archive_url retourne la valeur de l'env var quand définie."""
        # GIVEN: Env var ANNAS_ARCHIVE_URL définie
        os.environ["ANNAS_ARCHIVE_URL"] = "https://fr.annas-archive.se"

        try:
            # WHEN: On crée une instance Settings
            settings = Settings()

            # THEN: La propriété retourne la valeur de l'env var
            assert settings.annas_archive_url == "https://fr.annas-archive.se"
        finally:
            # Cleanup
            os.environ.pop("ANNAS_ARCHIVE_URL", None)

    def test_annas_archive_url_should_return_none_when_not_set(self):
        """Test que annas_archive_url retourne None si env var non définie."""
        # GIVEN: Env var ANNAS_ARCHIVE_URL non définie
        os.environ.pop("ANNAS_ARCHIVE_URL", None)

        # WHEN: On crée une instance Settings
        settings = Settings()

        # THEN: La propriété retourne None
        assert settings.annas_archive_url is None

    def test_annas_archive_url_should_return_none_when_empty_string(self):
        """Test que annas_archive_url retourne None si env var est vide."""
        # GIVEN: Env var ANNAS_ARCHIVE_URL vide
        os.environ["ANNAS_ARCHIVE_URL"] = ""

        try:
            # WHEN: On crée une instance Settings
            settings = Settings()

            # THEN: La propriété retourne None (pas une chaîne vide)
            assert settings.annas_archive_url is None
        finally:
            # Cleanup
            os.environ.pop("ANNAS_ARCHIVE_URL", None)


class TestPgxSettings:
    """Tests des propriétés de configuration PGX (Issue #302)."""

    PGX_ENV_VARS = (
        "PGX_HOST",
        "PGX_USER",
        "PGX_SSH_KEY_PATH",
        "PGX_REMOTE_AUDIO_ROOT",
        "PGX_REMOTE_TRANSCRIPTION_ROOT",
        "PGX_TRANSCRIPTION_TIMEOUT_S",
        "PGX_POLL_INTERVAL_S",
    )

    def teardown_method(self):
        """Nettoie toutes les env vars PGX après chaque test."""
        for var in self.PGX_ENV_VARS:
            os.environ.pop(var, None)

    def test_pgx_host_should_return_env_value_when_set(self):
        """pgx_host retourne la valeur de PGX_HOST quand définie."""
        os.environ["PGX_HOST"] = "192.168.50.151"

        settings = Settings()

        assert settings.pgx_host == "192.168.50.151"

    def test_pgx_host_should_return_none_when_not_set(self):
        """pgx_host retourne None si PGX_HOST n'est pas définie."""
        settings = Settings()

        assert settings.pgx_host is None

    def test_pgx_user_should_return_env_value_when_set(self):
        """pgx_user retourne la valeur de PGX_USER quand définie."""
        os.environ["PGX_USER"] = "pgxuser"

        settings = Settings()

        assert settings.pgx_user == "pgxuser"

    def test_pgx_user_should_return_none_when_not_set(self):
        """pgx_user retourne None si PGX_USER n'est pas définie."""
        settings = Settings()

        assert settings.pgx_user is None

    def test_pgx_ssh_key_path_should_return_env_value_when_set(self):
        """pgx_ssh_key_path retourne la valeur de PGX_SSH_KEY_PATH quand définie."""
        os.environ["PGX_SSH_KEY_PATH"] = "/app/keys/pgx_ed25519"

        settings = Settings()

        assert settings.pgx_ssh_key_path == "/app/keys/pgx_ed25519"

    def test_pgx_ssh_key_path_should_return_none_when_not_set(self):
        """pgx_ssh_key_path retourne None si PGX_SSH_KEY_PATH n'est pas définie."""
        settings = Settings()

        assert settings.pgx_ssh_key_path is None

    def test_pgx_remote_audio_root_should_return_env_value_when_set(self):
        """pgx_remote_audio_root retourne la valeur de PGX_REMOTE_AUDIO_ROOT quand définie."""
        os.environ["PGX_REMOTE_AUDIO_ROOT"] = "/data/audios"

        settings = Settings()

        assert settings.pgx_remote_audio_root == "/data/audios"

    def test_pgx_remote_audio_root_should_return_none_when_not_set(self):
        """pgx_remote_audio_root retourne None si non définie."""
        settings = Settings()

        assert settings.pgx_remote_audio_root is None

    def test_pgx_remote_transcription_root_should_return_env_value_when_set(self):
        """pgx_remote_transcription_root retourne la valeur d'env quand définie."""
        os.environ["PGX_REMOTE_TRANSCRIPTION_ROOT"] = "/data/transcriptions"

        settings = Settings()

        assert settings.pgx_remote_transcription_root == "/data/transcriptions"

    def test_pgx_remote_transcription_root_should_return_none_when_not_set(self):
        """pgx_remote_transcription_root retourne None si non définie."""
        settings = Settings()

        assert settings.pgx_remote_transcription_root is None

    def test_pgx_transcription_timeout_s_should_return_env_value_when_set(self):
        """pgx_transcription_timeout_s retourne la valeur convertie en float."""
        os.environ["PGX_TRANSCRIPTION_TIMEOUT_S"] = "900"

        settings = Settings()

        assert settings.pgx_transcription_timeout_s == 900.0

    def test_pgx_transcription_timeout_s_should_return_default_when_not_set(self):
        """pgx_transcription_timeout_s retourne 1800.0 (30 min) par défaut."""
        settings = Settings()

        assert settings.pgx_transcription_timeout_s == 1800.0

    def test_pgx_poll_interval_s_should_return_env_value_when_set(self):
        """pgx_poll_interval_s retourne la valeur convertie en float."""
        os.environ["PGX_POLL_INTERVAL_S"] = "5"

        settings = Settings()

        assert settings.pgx_poll_interval_s == 5.0

    def test_pgx_poll_interval_s_should_return_default_when_not_set(self):
        """pgx_poll_interval_s retourne 10.0 par défaut."""
        settings = Settings()

        assert settings.pgx_poll_interval_s == 10.0
