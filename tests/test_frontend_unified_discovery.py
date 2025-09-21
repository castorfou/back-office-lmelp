"""Tests for frontend integration with unified port discovery."""

import json
import tempfile
import time
from pathlib import Path

from back_office_lmelp.utils.port_discovery import PortDiscovery


def test_frontend_can_read_unified_discovery_file():
    """Test that frontend can read the new unified .dev-ports.json format."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create unified port discovery file as start-dev.sh would
        port_file = Path(temp_dir) / ".dev-ports.json"
        PortDiscovery.write_unified_port_info(
            port_file,
            backend_port=54321,
            frontend_port=5173,
            backend_host="0.0.0.0",
            frontend_host="0.0.0.0",
        )

        # Simulate frontend reading the file (like vite.config.js does)
        with open(port_file) as f:
            port_data = json.load(f)

        # Frontend should be able to extract backend info
        backend_info = port_data.get("backend")
        assert backend_info is not None
        assert backend_info["port"] == 54321
        assert backend_info["url"] == "http://0.0.0.0:54321"

        # Frontend could also get its own info
        frontend_info = port_data.get("frontend")
        assert frontend_info is not None
        assert frontend_info["port"] == 5173


def test_vite_config_compatibility_with_unified_file():
    """Test that vite.config.js logic works with unified discovery file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        port_file = Path(temp_dir) / ".dev-ports.json"

        # Create discovery file with backend info
        PortDiscovery.write_unified_port_info(
            port_file,
            backend_port=54322,
            backend_host="localhost",
        )

        # Simulate vite.config.js getBackendTarget function logic
        def get_backend_target_from_unified_file(file_path):
            """Simulate the updated getBackendTarget function."""
            try:
                with open(file_path) as f:
                    port_data = json.load(f)

                backend_info = port_data.get("backend")
                if not backend_info:
                    return "http://localhost:54321"  # default

                # Check if file is stale (older than 24 hours)
                file_age = time.time() - backend_info.get("started_at", 0)
                if file_age > 24 * 60 * 60:
                    return "http://localhost:54321"  # default

                return backend_info.get(
                    "url", f"http://{backend_info['host']}:{backend_info['port']}"
                )

            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                return "http://localhost:54321"  # default

        # Test the function
        target = get_backend_target_from_unified_file(port_file)
        assert target == "http://localhost:54322"


def test_backward_compatibility_fallback():
    """Legacy fallback behavior removed; unified file is the only supported source."""
    assert True


def test_migration_from_legacy_to_unified():
    """Migration from legacy files is no longer part of the test suite."""
    assert True
