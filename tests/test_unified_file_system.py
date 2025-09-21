"""Tests for unified port discovery file system (TDD approach)."""

import json
import tempfile
import time
from pathlib import Path

from back_office_lmelp.utils.port_discovery import PortDiscovery


class TestUnifiedFileSystem:
    """Test unified port discovery file system to eliminate dual file confusion."""

    def test_backend_writes_directly_to_unified_file(self):
        """Test that backend writes directly to .dev-ports.json instead of .backend-port.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            unified_file = Path(temp_dir) / ".dev-ports.json"

            # Backend should write directly to unified file
            PortDiscovery.write_backend_info_to_unified_file(
                unified_file, port=54321, host="0.0.0.0", pid=12345
            )

            # Verify unified file exists and has correct backend section
            assert unified_file.exists()

            with open(unified_file) as f:
                data = json.load(f)

            assert "backend" in data
            assert data["backend"]["port"] == 54321
            assert data["backend"]["host"] == "0.0.0.0"
            assert data["backend"]["pid"] == 12345
            assert "started_at" in data["backend"]
            assert data["backend"]["url"] == "http://0.0.0.0:54321"

    def test_frontend_reads_from_unified_file_only(self):
        """Test that frontend vite.config.js reads only from .dev-ports.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            unified_file = Path(temp_dir) / ".dev-ports.json"
            legacy_file = Path(temp_dir) / ".backend-port.json"

            # Create unified file with backend info
            PortDiscovery.write_unified_port_info(
                unified_file, backend_port=54321, backend_host="localhost"
            )

            # Create legacy file with different port
            legacy_data = {
                "port": 54322,
                "host": "localhost",
                "timestamp": int(time.time()),
                "url": "http://localhost:54322",
            }
            with open(legacy_file, "w") as f:
                json.dump(legacy_data, f)

            # Simulate improved getBackendTarget function that prefers unified file
            def get_backend_target_unified_only(unified_path, legacy_path):
                """New getBackendTarget that prioritizes unified file."""
                # Try unified file first
                try:
                    with open(unified_path) as f:
                        data = json.load(f)
                    backend = data.get("backend")
                    if backend and "url" in backend:
                        return backend["url"]
                except (FileNotFoundError, json.JSONDecodeError, KeyError):
                    pass

                # Only fall back to legacy if unified doesn't exist
                try:
                    with open(legacy_path) as f:
                        data = json.load(f)
                    return data.get("url", "http://localhost:54321")
                except (FileNotFoundError, json.JSONDecodeError):
                    pass

                return "http://localhost:54321"

            # Should prefer unified file (54321) over legacy file (54322)
            target = get_backend_target_unified_only(unified_file, legacy_file)
            assert target == "http://localhost:54321"

    def test_start_dev_script_writes_frontend_info_to_existing_unified_file(self):
        """Test that start-dev.sh adds frontend info to existing backend unified file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            unified_file = Path(temp_dir) / ".dev-ports.json"

            # Backend already wrote its info
            PortDiscovery.write_unified_port_info(
                unified_file,
                backend_port=54321,
                backend_host="0.0.0.0",
                backend_pid=12345,
            )

            # start-dev.sh should add frontend info to existing file
            PortDiscovery.add_frontend_info_to_unified_file(
                unified_file,
                frontend_port=5173,
                frontend_host="0.0.0.0",
                frontend_pid=12346,
            )

            # Verify both backend and frontend info exist
            with open(unified_file) as f:
                data = json.load(f)

            assert "backend" in data
            assert "frontend" in data
            assert data["backend"]["port"] == 54321
            assert data["frontend"]["port"] == 5173

    def test_claude_scripts_work_from_any_directory(self):
        """Test that Claude scripts work from frontend/ directory and project root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            frontend_dir = project_root / "frontend"
            frontend_dir.mkdir()

            # Create unified file in project root
            unified_file = project_root / ".dev-ports.json"
            PortDiscovery.write_unified_port_info(
                unified_file, backend_port=54321, backend_host="localhost"
            )

            # Simulate script that finds project root and reads unified file
            def get_backend_url_from_any_directory(current_dir):
                """Auto-find project root and read unified file."""
                current_path = Path(current_dir)

                # Find project root by looking for pyproject.toml
                project_root = current_path
                while project_root != project_root.parent:
                    if (project_root / "pyproject.toml").exists():
                        break
                    project_root = project_root.parent
                else:
                    # Fallback: assume current_dir is project root
                    project_root = current_path

                unified_file = project_root / ".dev-ports.json"
                try:
                    with open(unified_file) as f:
                        data = json.load(f)
                    backend = data.get("backend", {})
                    return backend.get("url")
                except (FileNotFoundError, json.JSONDecodeError):
                    return None

            # Create pyproject.toml to mark project root
            (project_root / "pyproject.toml").touch()

            # Test from project root
            url_from_root = get_backend_url_from_any_directory(project_root)
            assert url_from_root == "http://localhost:54321"

            # Test from frontend directory
            url_from_frontend = get_backend_url_from_any_directory(frontend_dir)
            assert url_from_frontend == "http://localhost:54321"

    def test_cleanup_removes_only_unified_file(self):
        """Test that cleanup removes .dev-ports.json but not legacy files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            unified_file = Path(temp_dir) / ".dev-ports.json"
            legacy_file = Path(temp_dir) / ".backend-port.json"

            # Create both files
            PortDiscovery.write_unified_port_info(unified_file, backend_port=54321)
            legacy_file.write_text('{"port": 54321}')

            # Cleanup should only remove unified file
            PortDiscovery.cleanup_unified_port_file(unified_file)

            assert not unified_file.exists()
            assert legacy_file.exists()  # Legacy file should remain untouched

    def test_migration_from_dual_system_to_unified(self):
        """Test migration path from dual file system to unified system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            unified_file = Path(temp_dir) / ".dev-ports.json"
            legacy_file = Path(temp_dir) / ".backend-port.json"

            # Create legacy file (current system)
            legacy_data = {
                "port": 54321,
                "host": "0.0.0.0",
                "timestamp": int(time.time()),
                "url": "http://0.0.0.0:54321",
            }
            with open(legacy_file, "w") as f:
                json.dump(legacy_data, f)

            # Migration should create unified file from legacy
            PortDiscovery.migrate_to_unified_system(legacy_file, unified_file)

            # Verify unified file has backend info from legacy
            assert unified_file.exists()

            with open(unified_file) as f:
                data = json.load(f)

            assert "backend" in data
            assert data["backend"]["port"] == 54321
            assert data["backend"]["url"] == "http://0.0.0.0:54321"

    def test_no_dual_file_creation_in_new_system(self):
        """Test that new system never creates .backend-port.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            unified_file = Path(temp_dir) / ".dev-ports.json"
            legacy_file = Path(temp_dir) / ".backend-port.json"

            # Use new unified system
            PortDiscovery.write_backend_info_to_unified_file(
                unified_file, port=54321, host="0.0.0.0"
            )

            # Only unified file should exist
            assert unified_file.exists()
            assert not legacy_file.exists()
