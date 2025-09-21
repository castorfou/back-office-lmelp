"""Tests TDD pour vérifier que app.py n'appelle plus les méthodes legacy."""

import inspect
from pathlib import Path


class TestAppNoLegacyCalls:
    """Test que app.py n'utilise plus les méthodes legacy de PortDiscovery."""

    def test_app_py_does_not_call_get_port_file_path(self):
        """Test que app.py n'appelle plus get_port_file_path() (legacy)."""
        app_file = Path("/workspaces/back-office-lmelp/src/back_office_lmelp/app.py")
        content = app_file.read_text()

        # Ce test échouera tant que app.py contient des appels à get_port_file_path
        assert "get_port_file_path" not in content, (
            "app.py ne devrait plus appeler get_port_file_path() - "
            "utiliser get_unified_port_file_path() à la place"
        )

    def test_app_py_does_not_call_write_port_info(self):
        """Test que app.py n'appelle plus write_port_info() (legacy)."""
        app_file = Path("/workspaces/back-office-lmelp/src/back_office_lmelp/app.py")
        content = app_file.read_text()

        # Ce test échouera tant que app.py contient des appels à write_port_info
        assert "write_port_info" not in content, (
            "app.py ne devrait plus appeler write_port_info() - "
            "utiliser write_backend_info_to_unified_file() à la place"
        )

    def test_app_py_does_not_call_cleanup_port_file(self):
        """Test que app.py n'appelle plus cleanup_port_file() (legacy)."""
        app_file = Path("/workspaces/back-office-lmelp/src/back_office_lmelp/app.py")
        content = app_file.read_text()

        # Ce test échouera tant que app.py contient des appels à cleanup_port_file
        assert "cleanup_port_file" not in content, (
            "app.py ne devrait plus appeler cleanup_port_file() - "
            "utiliser cleanup_unified_port_file() à la place"
        )

    def test_app_py_uses_unified_methods_only(self):
        """Test que app.py utilise uniquement les méthodes unifiées."""
        app_file = Path("/workspaces/back-office-lmelp/src/back_office_lmelp/app.py")
        content = app_file.read_text()

        # Ces méthodes DOIVENT être présentes dans app.py
        required_unified_methods = [
            "get_unified_port_file_path",
            "write_backend_info_to_unified_file",
            "cleanup_unified_port_file",
        ]

        for method in required_unified_methods:
            assert method in content, (
                f"app.py doit utiliser {method}() du système unifié"
            )

    def test_create_port_file_on_startup_function_updated(self):
        """Test que create_port_file_on_startup utilise le système unifié."""
        from back_office_lmelp.utils.port_discovery import create_port_file_on_startup

        # Inspecter le code source de la fonction
        source = inspect.getsource(create_port_file_on_startup)

        # Cette fonction devrait utiliser les nouvelles méthodes
        assert (
            "get_unified_port_file_path" in source
            or "write_backend_info_to_unified_file" in source
        ), "create_port_file_on_startup() doit utiliser le système unifié"

        # Et ne plus utiliser les anciennes
        assert "get_port_file_path" not in source, (
            "create_port_file_on_startup() ne doit plus utiliser get_port_file_path()"
        )
        assert "write_port_info" not in source, (
            "create_port_file_on_startup() ne doit plus utiliser write_port_info()"
        )

    def test_no_backend_port_json_strings_in_app(self):
        """Test qu'il n'y a plus de références à '.backend-port.json' dans app.py."""
        app_file = Path("/workspaces/back-office-lmelp/src/back_office_lmelp/app.py")
        content = app_file.read_text()

        # Ce test échouera s'il reste des références au fichier legacy
        assert ".backend-port.json" not in content, (
            "app.py ne devrait plus référencer '.backend-port.json' - "
            "toutes les références doivent pointer vers '.dev-ports.json'"
        )
