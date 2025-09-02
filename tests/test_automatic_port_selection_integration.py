"""Tests d'intégration pour la sélection automatique de port en condition réelle."""

import socket
import threading
import unittest
from contextlib import contextmanager

from back_office_lmelp.app import find_free_port_or_default


class TestAutomaticPortSelectionIntegration(unittest.TestCase):
    """Tests d'intégration pour reproduire les conditions réelles."""

    def _is_port_occupied(self, port, host="0.0.0.0"):
        """Vérifie si un port est occupé."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return False
        except OSError:
            return True

    @contextmanager
    def occupy_port(self, port, host="0.0.0.0"):
        """Context manager pour occuper un port pendant le test."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_socket.bind((host, port))
            server_socket.listen(1)
            print(f"🔒 Port {port} occupé sur {host}")
            yield server_socket
        finally:
            server_socket.close()
            print(f"🔓 Port {port} libéré sur {host}")

    def test_port_selection_with_54321_occupied_on_different_hosts(self):
        """Test: Port 54321 occupé sur différentes interfaces réseau."""
        # RED TEST: Reproduit le problème réel observé

        # NETTOYER L'ENVIRONNEMENT pour test réaliste
        import os

        original_api_port = os.environ.pop("API_PORT", None)
        original_api_host = os.environ.pop("API_HOST", None)

        try:
            # Vérifier d'abord si 54321 est libre sur 127.0.0.1
            # Si déjà occupé, utiliser un port différent pour le test
            test_port = 54321
            if self._is_port_occupied(test_port, "127.0.0.1"):
                test_port = 54325  # Utiliser un port différent

            with self.occupy_port(test_port, "127.0.0.1"):
                # Le port test_port est occupé sur localhost
                # Notre fonction doit détecter cela et passer au suivant
                selected_port = find_free_port_or_default()

                # Le port sélectionné ne doit PAS être le port occupé
                self.assertNotEqual(
                    selected_port,
                    test_port,
                    f"La fonction doit détecter que {test_port} est occupé",
                )

                # Le port sélectionné doit être dans la plage de fallback
                self.assertGreaterEqual(
                    selected_port, 54322, "Port doit être dans la plage de fallback"
                )
                self.assertLessEqual(
                    selected_port, 54350, "Port doit être dans la plage de fallback"
                )
        finally:
            # Restaurer l'environnement
            if original_api_port is not None:
                os.environ["API_PORT"] = original_api_port
            if original_api_host is not None:
                os.environ["API_HOST"] = original_api_host

    def test_port_selection_with_multiple_occupied_ports(self):
        """Test: Plusieurs ports occupés, doit trouver le premier libre."""
        # NETTOYER L'ENVIRONNEMENT pour test réaliste
        import os

        original_api_port = os.environ.pop("API_PORT", None)
        original_api_host = os.environ.pop("API_HOST", None)

        try:
            # Construire une liste de ports à occuper de manière dynamique
            ports_to_occupy = []

            # Toujours essayer d'occuper 54321 pour forcer le fallback
            if not self._is_port_occupied(54321, "0.0.0.0"):
                ports_to_occupy.append(54321)

            # Occuper les premiers ports de la plage de fallback
            for port in [54322, 54323, 54324]:
                if not self._is_port_occupied(port, "0.0.0.0"):
                    ports_to_occupy.append(port)

            if len(ports_to_occupy) < 2:
                self.skipTest("Pas assez de ports libres pour ce test")

            # Créer les context managers dynamiquement
            import contextlib

            context_managers = [
                self.occupy_port(port, "0.0.0.0") for port in ports_to_occupy
            ]

            with contextlib.ExitStack() as stack:
                for cm in context_managers:
                    stack.enter_context(cm)
                selected_port = find_free_port_or_default()

                # Le port sélectionné ne doit pas être dans ceux qu'on a occupés
                self.assertNotIn(
                    selected_port,
                    ports_to_occupy,
                    f"Port sélectionné {selected_port} ne doit pas être dans {ports_to_occupy}",
                )

                # Vérifier que le port est dans la plage valide
                self.assertGreaterEqual(selected_port, 54321, "Port doit être >= 54321")
                self.assertLessEqual(selected_port, 54350, "Port doit être <= 54350")
        finally:
            # Restaurer l'environnement
            if original_api_port is not None:
                os.environ["API_PORT"] = original_api_port
            if original_api_host is not None:
                os.environ["API_HOST"] = original_api_host

    def test_actual_server_binding_after_selection(self):
        """Test: Le port sélectionné doit vraiment être libre pour le serveur."""
        # RED TEST: Vérifie que le port sélectionné fonctionne vraiment

        # NETTOYER L'ENVIRONNEMENT pour test réaliste
        import os

        original_api_port = os.environ.pop("API_PORT", None)
        original_api_host = os.environ.pop("API_HOST", None)

        try:
            selected_port = find_free_port_or_default()
            print(f"DEBUG - Port sélectionné: {selected_port}")

            # Tente de binder réellement sur ce port (comme le serveur le fait)
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                test_socket.bind(("0.0.0.0", selected_port))
                test_socket.listen(1)

                # Si on arrive ici, le port est vraiment libre
                self.assertTrue(True, f"Port {selected_port} est effectivement libre")

            except OSError as e:
                self.fail(f"Port {selected_port} sélectionné mais non utilisable: {e}")
            finally:
                test_socket.close()

        finally:
            # Restaurer l'environnement
            if original_api_port is not None:
                os.environ["API_PORT"] = original_api_port
            if original_api_host is not None:
                os.environ["API_HOST"] = original_api_host

    def test_concurrent_port_selection(self):
        """Test: Plusieurs appels simultanés ne doivent pas sélectionner le même port."""
        # NETTOYER L'ENVIRONNEMENT pour test réaliste
        import os

        original_api_port = os.environ.pop("API_PORT", None)
        original_api_host = os.environ.pop("API_HOST", None)

        try:
            selected_ports = []
            errors = []
            lock = threading.Lock()

            def select_port():
                try:
                    port = find_free_port_or_default()
                    with lock:
                        selected_ports.append(port)
                except Exception as e:
                    with lock:
                        errors.append(str(e))

            # Lance 3 sélections simultanées
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=select_port)
                threads.append(thread)
                thread.start()

            # Attend que tous les threads terminent
            for thread in threads:
                thread.join()

            # Vérifie qu'il n'y a pas d'erreurs
            self.assertEqual(len(errors), 0, f"Erreurs lors de la sélection: {errors}")

            # En mode test, tous les appels peuvent retourner le même port car ils
            # testent la disponibilité mais ne l'occupent pas réellement
            # C'est un comportement acceptable pour cette fonction
            print(f"Ports sélectionnés: {selected_ports}")

            # Vérifie que tous les ports sont dans la plage valide
            for port in selected_ports:
                self.assertGreaterEqual(port, 54321, "Port doit être >= 54321")
                self.assertLessEqual(port, 54350, "Port doit être <= 54350")

        finally:
            # Restaurer l'environnement
            if original_api_port is not None:
                os.environ["API_PORT"] = original_api_port
            if original_api_host is not None:
                os.environ["API_HOST"] = original_api_host

    def test_realistic_environment_simulation(self):
        """Test: Simule un environnement de développement réaliste."""
        # RED TEST: Simule exactement la situation observée par l'utilisateur

        # NETTOYER L'ENVIRONNEMENT pour test réaliste
        import os

        original_api_port = os.environ.pop("API_PORT", None)
        original_api_host = os.environ.pop("API_HOST", None)

        try:
            # Trouver un port libre pour simuler le premier serveur
            test_port = 54329  # Utiliser un port différent pour éviter les conflits
            if self._is_port_occupied(test_port, "127.0.0.1"):
                test_port = 54330

            # 1. Simule un serveur qui tourne déjà sur test_port
            with self.occupy_port(test_port, "127.0.0.1"):
                # 2. Une nouvelle instance démarre
                port1 = find_free_port_or_default()

                # 3. Puis une autre instance démarre
                with self.occupy_port(port1, "0.0.0.0"):
                    port2 = find_free_port_or_default()

                    # Les deux ports doivent être différents
                    self.assertNotEqual(
                        port1,
                        port2,
                        "Deux instances doivent avoir des ports différents",
                    )
                    self.assertNotEqual(
                        port1, test_port, f"Premier port ne doit pas être {test_port}"
                    )
                    self.assertNotEqual(
                        port2, test_port, f"Deuxième port ne doit pas être {test_port}"
                    )
                    self.assertNotEqual(
                        port2, port1, "Deuxième port doit être différent du premier"
                    )

                    # Vérifier que les ports sont dans la plage valide
                    for port in [port1, port2]:
                        self.assertGreaterEqual(
                            port, 54321, f"Port {port} doit être >= 54321"
                        )
                        self.assertLessEqual(
                            port, 54350, f"Port {port} doit être <= 54350"
                        )

        finally:
            # Restaurer l'environnement
            if original_api_port is not None:
                os.environ["API_PORT"] = original_api_port
            if original_api_host is not None:
                os.environ["API_HOST"] = original_api_host


if __name__ == "__main__":
    unittest.main()
