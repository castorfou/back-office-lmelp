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
    """Test that system falls back gracefully when unified file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_file = Path(temp_dir) / ".dev-ports.json"

        def get_backend_target_with_fallback(unified_file, legacy_file):
            """Simulate fallback logic for vite.config.js."""
            # Try unified file first
            try:
                with open(unified_file) as f:
                    port_data = json.load(f)
                backend_info = port_data.get("backend")
                if backend_info and "url" in backend_info:
                    return backend_info["url"]
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass

            # Fall back to legacy file
            try:
                with open(legacy_file) as f:
                    legacy_data = json.load(f)
                return legacy_data.get("url", "http://localhost:54321")
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass

            return "http://localhost:54321"  # default

        # Test fallback to default when no files exist
        legacy_file = Path(temp_dir) / ".backend-port.json"
        target = get_backend_target_with_fallback(non_existent_file, legacy_file)
        assert target == "http://localhost:54321"

        # Test fallback to legacy file
        legacy_data = {
            "port": 54321,
            "host": "0.0.0.0",
            "timestamp": int(time.time()),
            "url": "http://0.0.0.0:54321",
        }
        with open(legacy_file, "w") as f:
            json.dump(legacy_data, f)

        target = get_backend_target_with_fallback(non_existent_file, legacy_file)
        assert target == "http://0.0.0.0:54321"


def test_migration_from_legacy_to_unified():
    """Test migration scenario from legacy .backend-port.json to unified."""
    with tempfile.TemporaryDirectory() as temp_dir:
        legacy_file = Path(temp_dir) / ".backend-port.json"
        unified_file = Path(temp_dir) / ".dev-ports.json"

        # Create legacy file
        legacy_data = {
            "port": 54321,
            "host": "0.0.0.0",
            "timestamp": int(time.time()),
            "url": "http://0.0.0.0:54321",
        }
        with open(legacy_file, "w") as f:
            json.dump(legacy_data, f)

        # Migrate to unified format
        PortDiscovery.migrate_from_legacy_backend_file(legacy_file, unified_file)

        # Verify migration worked
        assert unified_file.exists()

        with open(unified_file) as f:
            unified_data = json.load(f)

        assert "backend" in unified_data
        assert unified_data["backend"]["port"] == 54321
        assert unified_data["backend"]["host"] == "0.0.0.0"
