"""Tests statiques sur la configuration Docker du backend (Issue #258).

Vérifie que le conteneur backend tourne sous un utilisateur non-root
configurable via PUID/PGID, pour éviter des fichiers root:root sur le
volume de cache Babelio bind-monté depuis l'hôte.

Approche statique (assertions texte brut sur Dockerfile/entrypoint.sh),
pas de build Docker réel — pattern repris de lmelp/tests/integration/
test_streamlit_config.py::TestDockerfile.
"""

from pathlib import Path


DOCKERFILE_PATH = (
    Path(__file__).parent.parent / "docker" / "build" / "backend" / "Dockerfile"
)
ENTRYPOINT_PATH = (
    Path(__file__).parent.parent / "docker" / "build" / "backend" / "entrypoint.sh"
)


class TestDockerfile:
    def test_dockerfile_installs_gosu(self):
        """Vérifie que gosu est installé pour permettre de dropper les privilèges."""
        content = DOCKERFILE_PATH.read_text()

        assert "gosu" in content, "gosu not installed in Dockerfile"

    def test_dockerfile_declares_uid_gid_build_args(self):
        """Vérifie que l'UID/GID par défaut sont déclarés via des ARG."""
        content = DOCKERFILE_PATH.read_text()

        assert "ARG APP_UID=" in content, "APP_UID build arg not declared"
        assert "ARG APP_GID=" in content, "APP_GID build arg not declared"

    def test_dockerfile_creates_non_root_user_from_args(self):
        """Vérifie que l'utilisateur non-root est créé à partir des ARG."""
        content = DOCKERFILE_PATH.read_text()

        assert "useradd" in content, "useradd not used to create a non-root user"
        assert "$APP_UID" in content, "useradd does not reference $APP_UID"
        assert "$APP_GID" in content, "groupadd does not reference $APP_GID"

    def test_dockerfile_sets_home_for_non_root_user(self):
        """Vérifie que HOME est positionné vers le home du non-root user."""
        content = DOCKERFILE_PATH.read_text()

        assert "ENV HOME=" in content, "HOME env var not set for the non-root user"

    def test_dockerfile_does_not_hardcode_static_user_directive(self):
        """Vérifie que le switch d'utilisateur se fait dynamiquement dans
        l'entrypoint, pas via une directive USER statique au build."""
        lines = DOCKERFILE_PATH.read_text().splitlines()

        user_lines = [line for line in lines if line.strip().startswith("USER ")]
        assert not user_lines, (
            f"Static USER directive found, UID switch should happen "
            f"in entrypoint.sh: {user_lines}"
        )

    def test_dockerfile_uses_entrypoint_script(self):
        """Vérifie que l'image utilise le script entrypoint.sh dédié."""
        content = DOCKERFILE_PATH.read_text()

        assert "ENTRYPOINT" in content, "No ENTRYPOINT directive found"
        assert "entrypoint.sh" in content, "entrypoint.sh not referenced"

    def test_dockerfile_makes_app_readable_by_non_root_user(self):
        """Vérifie que /app appartient à appuser, quelles que soient les
        permissions des fichiers sources sur l'hôte de build (COPY préserve
        les permissions source, potentiellement 700), et pour permettre à
        l'app d'écrire son fichier runtime .dev-ports.json."""
        content = DOCKERFILE_PATH.read_text()

        assert "chown -R appuser:appuser /app" in content, "/app not chowned to appuser"


class TestDockerEntrypoint:
    def test_entrypoint_exists(self):
        """Vérifie que le script entrypoint.sh existe."""
        assert ENTRYPOINT_PATH.exists(), (
            f"Entrypoint script not found at {ENTRYPOINT_PATH}"
        )
        assert ENTRYPOINT_PATH.is_file()

    def test_entrypoint_reads_puid_pgid_with_defaults(self):
        """Vérifie que PUID/PGID sont lus avec une valeur par défaut."""
        content = ENTRYPOINT_PATH.read_text()

        assert "PUID=${PUID:-" in content, "PUID not read with a default value"
        assert "PGID=${PGID:-" in content, "PGID not read with a default value"

    def test_entrypoint_remaps_uid_gid(self):
        """Vérifie que l'utilisateur non-root est remappé vers PUID/PGID."""
        content = ENTRYPOINT_PATH.read_text()

        assert "usermod" in content, "usermod not used to remap the non-root user UID"
        assert "groupmod" in content, (
            "groupmod not used to remap the non-root group GID"
        )

    def test_entrypoint_chowns_cache_directory(self):
        """Vérifie que le volume de cache est chowné vers PUID/PGID."""
        content = ENTRYPOINT_PATH.read_text()

        assert "chown" in content, "chown not used on the cache directory"
        assert "/cache" in content, "/cache not referenced for chown"

    def test_entrypoint_chowns_app_directory_when_uid_remapped(self):
        """Vérifie que /app est re-chowné quand PUID/PGID diffère du défaut
        baked-in (l'app y écrit .dev-ports.json au démarrage)."""
        content = ENTRYPOINT_PATH.read_text()

        assert "chown" in content and "/app" in content, (
            "/app not re-chowned when PUID/PGID differs from the built-in default"
        )

    def test_entrypoint_drops_privileges_with_gosu(self):
        """Vérifie que le process applicatif est lancé sous l'utilisateur non-root."""
        content = ENTRYPOINT_PATH.read_text()

        assert "gosu appuser" in content, "gosu not used to drop privileges to appuser"
