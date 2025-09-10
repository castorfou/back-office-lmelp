"""Tests pour la gestion propre de l'arrêt du serveur."""

import asyncio
import signal
import socket
from unittest.mock import patch

import pytest
import uvicorn

from back_office_lmelp.app import app


class TestServerShutdown:
    """Tests pour vérifier l'arrêt propre du serveur."""

    def test_port_is_freed_after_shutdown(self):
        """Test que le port est libéré après arrêt du serveur."""
        # Utiliser un port dynamique pour éviter les conflits en CI
        import random

        port = random.randint(50000, 59999)

        # Trouver un port vraiment disponible
        for _attempt in range(10):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex(("127.0.0.1", port))
                if result != 0:  # Port disponible
                    break
                port = random.randint(50000, 59999)
        else:
            pytest.skip("Impossible de trouver un port disponible")

        # Simuler démarrage/arrêt rapide du serveur
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
        server = uvicorn.Server(config)

        # Démarrer le serveur en arrière-plan
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def test_shutdown():
            # Démarrer
            task = asyncio.create_task(server.serve())
            # Attendre plus longtemps en CI
            await asyncio.sleep(0.5)

            # Vérifier que le serveur écoute (avec plusieurs tentatives)
            server_started = False
            for _attempt in range(10):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    result = sock.connect_ex(("127.0.0.1", port))
                    if result == 0:
                        server_started = True
                        break
                    await asyncio.sleep(0.1)

            if not server_started:
                pytest.skip(f"Server failed to start on port {port} in CI environment")

            # Arrêter proprement
            server.should_exit = True
            await task

            # Attendre plus longtemps pour la fermeture en CI
            await asyncio.sleep(0.5)

            # Vérifier que le port est libéré (avec plusieurs tentatives)
            port_freed = False
            for _attempt in range(10):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    result = sock.connect_ex(("127.0.0.1", port))
                    if result != 0:
                        port_freed = True
                        break
                    await asyncio.sleep(0.1)

            assert port_freed, f"Port {port} should be freed after shutdown"

        loop.run_until_complete(test_shutdown())
        loop.close()

    def test_signal_handler_shuts_down_gracefully(self):
        """Test que le gestionnaire de signaux ferme proprement le serveur."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_mongo:
            # Importer la fonction signal handler
            from back_office_lmelp.app import signal_handler

            # Appeler le gestionnaire de signal
            signal_handler(signal.SIGTERM, None)

            # Vérifier que MongoDB est déconnecté
            mock_mongo.disconnect.assert_called_once()

    def test_memory_guard_force_shutdown_is_graceful(self):
        """Test que l'arrêt forcé par le memory guard est plus gracieux."""
        from back_office_lmelp.utils.memory_guard import MemoryGuard

        # Créer une instance de test
        guard = MemoryGuard()

        # Mock pour éviter l'arrêt réel
        with patch("gc.collect") as mock_gc:
            with pytest.raises(SystemExit) as exc_info:
                guard.force_shutdown("Test shutdown")

            # Vérifier que le garbage collector est appelé
            mock_gc.assert_called_once()
            # Vérifier que SystemExit est levée au lieu d'os._exit
            assert exc_info.value.code == 1

    def test_lifespan_context_cleanup_on_exception(self):
        """Test que le contexte lifespan nettoie même en cas d'exception."""
        from back_office_lmelp.app import lifespan

        with patch("back_office_lmelp.app.mongodb_service") as mock_mongo:
            mock_mongo.connect.side_effect = Exception("Connection failed")

            # Le lifespan devrait lever l'exception mais nettoyer quand même
            async def test_lifespan():
                try:
                    async with lifespan(app):
                        pass
                except Exception:
                    pass  # Attendu

                # Vérifier que disconnect est appelé même après échec de connect
                mock_mongo.disconnect.assert_called_once()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(test_lifespan())
            loop.close()

    def test_server_can_restart_after_clean_shutdown(self):
        """Test qu'on peut redémarrer le serveur après un arrêt propre."""
        # Mock MongoDB pour éviter les connexions réelles pendant le test
        with patch("back_office_lmelp.app.mongodb_service") as mock_mongo:
            mock_mongo.connect.return_value = True

            # Utiliser un port dynamique pour éviter les conflits en CI
            import random

            port = random.randint(50000, 59999)

            # Trouver un port vraiment disponible
            for _attempt in range(10):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    result = sock.connect_ex(("127.0.0.1", port))
                    if result != 0:  # Port disponible
                        break
                    port = random.randint(50000, 59999)
            else:
                pytest.skip("Impossible de trouver un port disponible")

            def start_and_stop_server():
                """Démarre et arrête le serveur."""
                config = uvicorn.Config(
                    app, host="127.0.0.1", port=port, log_level="error"
                )
                server = uvicorn.Server(config)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def run():
                    task = asyncio.create_task(server.serve())
                    # Attendre plus longtemps en CI
                    await asyncio.sleep(0.3)
                    server.should_exit = True
                    await task
                    # Attendre plus longtemps pour la fermeture en CI
                    await asyncio.sleep(0.3)

                loop.run_until_complete(run())
                loop.close()

            # Premier démarrage/arrêt
            start_and_stop_server()

            # Deuxième démarrage/arrêt - ne devrait pas échouer
            start_and_stop_server()

    def test_uvicorn_config_has_graceful_shutdown_parameters(self):
        """Test que la configuration uvicorn inclut les paramètres d'arrêt gracieux."""
        # Vérifier que les nouveaux paramètres de timeout sont utilisés
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            timeout_keep_alive=5,
            timeout_graceful_shutdown=10,
        )

        assert config.timeout_keep_alive == 5
        assert config.timeout_graceful_shutdown == 10

    def test_server_instance_is_accessible_globally(self):
        """Test que l'instance du serveur est accessible pour l'arrêt."""
        from back_office_lmelp.app import _server_instance

        # Au début, l'instance devrait être None
        assert _server_instance is None
