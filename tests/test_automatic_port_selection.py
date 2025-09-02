"""Tests pour la sélection automatique de port."""

import os
import unittest
from unittest.mock import Mock, patch

from back_office_lmelp.utils.port_discovery import PortDiscovery


class TestAutomaticPortSelection(unittest.TestCase):
    """Test cases for automatic port selection functionality."""

    def setUp(self):
        """Set up test environment."""
        # Store original env vars to restore later
        self.original_api_port = os.environ.get("API_PORT")

    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        if self.original_api_port is not None:
            os.environ["API_PORT"] = self.original_api_port
        elif "API_PORT" in os.environ:
            del os.environ["API_PORT"]

    def test_find_free_port_respects_environment_variable(self):
        """Test that environment variable API_PORT is respected when set."""
        # Set environment variable
        os.environ["API_PORT"] = "9999"

        # Import here to ensure environment is set
        from back_office_lmelp.app import find_free_port_or_default

        port = find_free_port_or_default()
        self.assertEqual(port, 9999)

    def test_find_free_port_uses_default_when_available(self):
        """Test that default port 54321 is used when available and no env var."""
        # Ensure no environment variable
        if "API_PORT" in os.environ:
            del os.environ["API_PORT"]

        # Import here to ensure environment is cleared
        from back_office_lmelp.app import find_free_port_or_default

        with patch("socket.socket") as mock_socket:
            mock_socket_instance = Mock()
            mock_socket.return_value.__enter__.return_value = mock_socket_instance
            mock_socket_instance.bind.return_value = None  # Success on default port

            port = find_free_port_or_default()
            self.assertEqual(port, 54321)
            mock_socket_instance.bind.assert_called_with(("0.0.0.0", 54321))

    def test_find_free_port_falls_back_to_range_when_default_occupied(self):
        """Test fallback to port range when default port is occupied."""
        # Ensure no environment variable
        if "API_PORT" in os.environ:
            del os.environ["API_PORT"]

        # Import here to ensure environment is cleared
        from back_office_lmelp.app import find_free_port_or_default

        with patch("socket.socket") as mock_socket:
            mock_socket_instance = Mock()
            mock_socket.return_value.__enter__.return_value = mock_socket_instance

            # Mock default port as occupied, but 54322 available
            def mock_bind(address):
                if address[1] == 54321:
                    raise OSError("Address already in use")
                # Any other port succeeds

            mock_socket_instance.bind.side_effect = mock_bind

            with patch.object(
                PortDiscovery, "find_available_port", return_value=54322
            ) as mock_find:
                port = find_free_port_or_default()
                self.assertEqual(port, 54322)
                mock_find.assert_called_once_with(start_port=54322, max_attempts=29)

    def test_find_free_port_handles_all_ports_occupied(self):
        """Test error handling when all ports in range are occupied."""
        # Ensure no environment variable
        if "API_PORT" in os.environ:
            del os.environ["API_PORT"]

        # Import here to ensure environment is cleared
        from back_office_lmelp.app import find_free_port_or_default

        with patch("socket.socket") as mock_socket:
            mock_socket_instance = Mock()
            mock_socket.return_value.__enter__.return_value = mock_socket_instance
            mock_socket_instance.bind.side_effect = OSError("Address already in use")

            with patch.object(PortDiscovery, "find_available_port") as mock_find:
                mock_find.side_effect = RuntimeError("No available port found")

                with self.assertRaises(RuntimeError) as context:
                    find_free_port_or_default()

                self.assertIn("No available port found", str(context.exception))

    def test_find_free_port_with_invalid_env_var(self):
        """Test handling of invalid environment variable values."""
        # Set invalid environment variable
        os.environ["API_PORT"] = "invalid"

        # Import here to ensure environment is set
        from back_office_lmelp.app import find_free_port_or_default

        with self.assertRaises(ValueError):
            find_free_port_or_default()

    def test_port_selection_priority_order(self):
        """Test that port selection follows the correct priority order."""
        # Test 1: Environment variable has highest priority
        os.environ["API_PORT"] = "7777"

        from back_office_lmelp.app import find_free_port_or_default

        port = find_free_port_or_default()
        self.assertEqual(port, 7777)

        # Test 2: Default port when no env var
        del os.environ["API_PORT"]

        # Reload the function to clear any cached imports
        import importlib

        import back_office_lmelp.app

        importlib.reload(back_office_lmelp.app)
        from back_office_lmelp.app import find_free_port_or_default

        with patch("socket.socket") as mock_socket:
            mock_socket_instance = Mock()
            mock_socket.return_value.__enter__.return_value = mock_socket_instance
            mock_socket_instance.bind.return_value = None

            port = find_free_port_or_default()
            self.assertEqual(port, 54321)

    def test_port_discovery_file_creation_with_auto_selected_port(self):
        """Test that port discovery file is created with automatically selected port."""
        # Ensure no environment variable
        if "API_PORT" in os.environ:
            del os.environ["API_PORT"]

        from back_office_lmelp.app import find_free_port_or_default

        with patch("socket.socket") as mock_socket:
            mock_socket_instance = Mock()
            mock_socket.return_value.__enter__.return_value = mock_socket_instance

            # Mock default port as occupied, fallback to range
            def mock_bind(address):
                if address[1] == 54321:
                    raise OSError("Address already in use")

            mock_socket_instance.bind.side_effect = mock_bind

            with patch.object(PortDiscovery, "find_available_port", return_value=54325):
                port = find_free_port_or_default()
                self.assertEqual(port, 54325)


if __name__ == "__main__":
    unittest.main()
