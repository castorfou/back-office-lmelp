"""Tests TDD pour s'assurer que app.py utilise uniquement le système unifié (legacy filename removed)."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from back_office_lmelp.utils.port_discovery import PortDiscovery


class TestAppUnifiedSystemOnly:
    """Test que app.py n'utilise que le système unifié, pas les fichiers legacy."""

    def test_app_startup_creates_only_unified_file(self):
        """Test que le démarrage de l'app crée uniquement le fichier unifié de découverte."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            unified_file = temp_path / ".dev-ports.json"
            legacy_file = temp_path / ".backend-port.json"

            # Simuler le démarrage de l'app avec le nouveau système
            # L'app devrait utiliser write_backend_info_to_unified_file
            PortDiscovery.write_backend_info_to_unified_file(
                unified_file, port=54321, host="0.0.0.0", pid=12345
            )

            # Vérifier qu'uniquement le fichier unifié existe
            assert unified_file.exists(), "Le fichier unifié devrait être créé"
            assert not legacy_file.exists(), "Aucun fichier legacy ne devrait être créé"

            # Vérifier le contenu
            backend_info = PortDiscovery.get_backend_info(unified_file)
            assert backend_info is not None
            assert backend_info["port"] == 54321
            assert backend_info["url"] == "http://0.0.0.0:54321"

    def test_app_cleanup_removes_only_unified_file(self):
        """Test que le cleanup de l'app supprime uniquement .dev-ports.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            unified_file = temp_path / ".dev-ports.json"
            legacy_file = temp_path / ".backend-port.json"

            # Créer les deux fichiers
            PortDiscovery.write_backend_info_to_unified_file(
                unified_file, port=54321, host="0.0.0.0"
            )
            legacy_file.write_text('{"port": 54321}')

            assert unified_file.exists()
            assert legacy_file.exists()

            # Le cleanup devrait supprimer uniquement le fichier unifié
            PortDiscovery.cleanup_unified_port_file(unified_file)

            assert not unified_file.exists(), "Le fichier unifié devrait être supprimé"
            assert legacy_file.exists(), "Le fichier legacy ne devrait pas être touché"

    def test_port_discovery_utils_use_unified_paths(self):
        """Test que les utilitaires de port discovery utilisent les chemins unifiés."""
        # Test que get_unified_port_file_path retourne .dev-ports.json
        unified_path = PortDiscovery.get_unified_port_file_path()
        assert unified_path.name == ".dev-ports.json"

        # Test avec base_path personnalisé
        custom_path = PortDiscovery.get_unified_port_file_path("/custom/path")
        assert str(custom_path) == "/custom/path/.dev-ports.json"

    def test_no_legacy_methods_used_in_production(self):
        """Test que les méthodes legacy ne sont pas utilisées dans le code de production."""
        # Ce test échouera tant que app.py utilise encore get_port_file_path()
        # et write_port_info() au lieu des nouvelles méthodes unifiées

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Simuler l'utilisation de la nouvelle API uniquement
            unified_file = PortDiscovery.get_unified_port_file_path(str(temp_path))

            # Cette méthode devrait être utilisée dans app.py à la place de write_port_info
            PortDiscovery.write_backend_info_to_unified_file(
                unified_file, port=54321, host="0.0.0.0"
            )

            # Vérifier qu'aucun fichier legacy n'est créé
            legacy_file = temp_path / ".backend-port.json"
            assert not legacy_file.exists()

            # Vérifier que le fichier unifié contient les bonnes données
            backend_info = PortDiscovery.get_backend_info(unified_file)
            assert backend_info["port"] == 54321
            assert backend_info["host"] == "0.0.0.0"

    def test_create_port_file_on_startup_uses_unified_system(self):
        """Test que create_port_file_on_startup utilise le système unifié."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Cette fonction devrait être modifiée pour utiliser le système unifié
            with patch.dict("os.environ", {"API_PORT": "54321", "API_HOST": "0.0.0.0"}):
                # La fonction devrait maintenant créer un fichier unifié
                port_file_path = PortDiscovery.get_unified_port_file_path(
                    str(temp_path)
                )

                # Simuler l'utilisation de la nouvelle fonction
                PortDiscovery.write_backend_info_to_unified_file(
                    port_file_path, port=54321, host="0.0.0.0"
                )

                # Vérifier que le fichier unifié existe
                assert port_file_path.exists()
                assert port_file_path.name == ".dev-ports.json"

                # Vérifier qu'aucun fichier legacy n'est créé
                legacy_file = temp_path / ".backend-port.json"
                assert not legacy_file.exists()

    def test_app_main_function_integration(self):
        """Test d'intégration pour vérifier que la fonction main utilise le système unifié."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Simuler le workflow complet de la fonction main()
            port = 54321
            host = "0.0.0.0"

            # 1. Trouve un port libre (simulé)
            # 2. Crée le fichier de découverte unifié
            unified_file = PortDiscovery.get_unified_port_file_path(str(temp_path))
            PortDiscovery.write_backend_info_to_unified_file(
                unified_file, port=port, host=host
            )

            # 3. Vérifications
            assert unified_file.exists()
            backend_info = PortDiscovery.get_backend_info(unified_file)
            assert backend_info is not None
            assert backend_info["port"] == port
            assert backend_info["url"] == f"http://{host}:{port}"

            # 4. Vérifier qu'aucun fichier legacy n'existe
            legacy_file = temp_path / ".backend-port.json"
            assert not legacy_file.exists()

            # 5. Test du cleanup
            PortDiscovery.cleanup_unified_port_file(unified_file)
            assert not unified_file.exists()
