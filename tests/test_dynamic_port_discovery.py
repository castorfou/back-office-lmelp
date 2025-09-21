"""Tests for dynamic port discovery functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from back_office_lmelp.utils.port_discovery import PortDiscovery


class TestPortDiscovery:
    """Tests for the port discovery functionality."""

    def test_port_discovery_class_exists(self):
        """Test that PortDiscovery class exists and can be imported."""
        # This test will initially fail - we need to create the PortDiscovery class
        assert PortDiscovery is not None

    def test_write_port_info_to_file(self):
        """Test that port information is written to a discoverable file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Test writing port info
            PortDiscovery.write_port_info(54321, port_file)

            # Verify file exists and contains correct data
            assert port_file.exists()

            with open(port_file) as f:
                port_data = json.load(f)

            # write_port_info now writes unified format via write_backend_info_to_unified_file
            assert isinstance(port_data, dict)
            assert "backend" in port_data
            assert port_data["backend"].get("port") == 54321
            assert "host" in port_data["backend"]

    def test_read_port_info_from_file(self):
        """Test that port information can be read from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Create test unified port file
            port_data = {
                "backend": {
                    "port": 54321,
                    "host": "localhost",
                    "started_at": 1706720000,
                }
            }

            with open(port_file, "w") as f:
                json.dump(port_data, f)

            # Test reading port info (deprecated helper still returns raw dict)
            read_data = PortDiscovery.read_port_info(port_file)
            assert read_data is not None

            assert "backend" in read_data
            assert read_data["backend"]["port"] == 54321
            assert read_data["backend"]["host"] == "localhost"

    def test_get_port_file_path(self):
        """Test that port file path is correctly generated."""

    # get_port_file_path kept for API compatibility but should now point to unified path
    default_path = PortDiscovery.get_port_file_path()
    expected_unified = Path.cwd() / ".dev-ports.json"
    assert default_path == expected_unified

    # Test unified file path helper
    unified_default = PortDiscovery.get_unified_port_file_path()
    assert unified_default == expected_unified

    def test_cleanup_port_file(self):
        """Test that port file can be cleaned up."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Create a port file
            PortDiscovery.write_port_info(54321, port_file)
            assert port_file.exists()

            # Clean up the file
            PortDiscovery.cleanup_port_file(port_file)
            assert not port_file.exists()

    def test_port_discovery_integration_with_app_startup(self):
        """Test that port discovery is integrated with app startup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Mock environment variables for testing
            with patch.dict(os.environ, {"API_PORT": "54322"}):
                # This should trigger port file creation during app startup
                # We'll need to implement this integration
                from back_office_lmelp.utils.port_discovery import (
                    create_port_file_on_startup,
                )

                create_port_file_on_startup(port_file_path=port_file)

                # Verify file was created with unified format only
                assert port_file.exists()

                with open(port_file) as f:
                    port_data = json.load(f)

                # Unified format: {'backend': {'port': ...}}
                assert isinstance(port_data, dict)
                assert "backend" in port_data
                assert isinstance(port_data["backend"], dict)
                assert port_data["backend"].get("port") == 54322

    def test_port_file_contains_required_fields(self):
        """Test that port file contains all required fields for frontend."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Use the unified writer for required fields
            PortDiscovery.write_backend_info_to_unified_file(
                port_file, port=54321, host="0.0.0.0"
            )

            with open(port_file) as f:
                port_data = json.load(f)

            # Required fields for frontend proxy configuration in unified file
            assert "backend" in port_data
            assert "port" in port_data["backend"]
            assert "host" in port_data["backend"]
            assert "started_at" in port_data["backend"]
            assert "url" in port_data["backend"]

            # Verify URL format
            expected_url = "http://0.0.0.0:54321"
            assert port_data["backend"]["url"] == expected_url

    def test_port_discovery_with_dynamic_port_selection(self):
        """Test port discovery when backend selects port dynamically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Test with port 0 (OS selects available port)
            # This would be used when API_PORT=0 for dynamic selection
            selected_port = PortDiscovery.find_available_port()

            # Write the selected port info into unified format
            PortDiscovery.write_unified_port_info(port_file, backend_port=selected_port)

            # Verify a valid port was selected and written
            with open(port_file) as f:
                port_data = json.load(f)

            # Unified format stores backend.port
            assert isinstance(port_data.get("backend"), dict)
            assert port_data["backend"]["port"] > 1024
            assert port_data["backend"]["port"] < 65536
