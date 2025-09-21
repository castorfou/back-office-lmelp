"""Tests for unified port discovery functionality with frontend support."""

import json
import os
import tempfile
import time
from pathlib import Path

from back_office_lmelp.utils.port_discovery import PortDiscovery


class TestUnifiedPortDiscovery:
    """Tests for unified port discovery supporting both backend and frontend."""

    def test_unified_port_discovery_file_format(self):
        """Test that unified port discovery creates the expected .dev-ports.json format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Test writing unified port info for both backend and frontend
            PortDiscovery.write_unified_port_info(
                port_file,
                backend_port=54321,
                frontend_port=5173,
                backend_host="0.0.0.0",
                frontend_host="0.0.0.0",
            )

            # Verify file exists and contains correct unified format
            assert port_file.exists()

            with open(port_file) as f:
                port_data = json.load(f)

            # Check unified structure
            assert "backend" in port_data
            assert "frontend" in port_data

            # Check backend section
            backend = port_data["backend"]
            assert backend["port"] == 54321
            assert backend["host"] == "0.0.0.0"
            assert "pid" in backend
            assert "started_at" in backend
            assert backend["url"] == "http://0.0.0.0:54321"

            # Check frontend section
            frontend = port_data["frontend"]
            assert frontend["port"] == 5173
            assert frontend["host"] == "0.0.0.0"
            assert "pid" in frontend
            assert "started_at" in frontend
            assert frontend["url"] == "http://0.0.0.0:5173"

    def test_auto_discovery_for_api_calls(self):
        """Test that Claude Code can auto-discover backend for API calls."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Simulate running services
            PortDiscovery.write_unified_port_info(
                port_file,
                backend_port=54321,
                frontend_port=5173,
                backend_pid=12345,
                frontend_pid=12346,
            )

            # Test auto-discovery methods
            backend_info = PortDiscovery.get_backend_info(port_file)
            assert backend_info is not None
            assert backend_info["port"] == 54321
            assert backend_info["url"] == "http://0.0.0.0:54321"
            assert backend_info["pid"] == 12345

            # Test service status checking
            # This will depend on process validation implementation

    def test_service_restart_detection(self):
        """Test detection of recent service restarts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Create port file with recent timestamp
            recent_time = time.time() - 60  # 1 minute ago
            PortDiscovery.write_unified_port_info(
                port_file, backend_port=54321, backend_pid=12345, started_at=recent_time
            )

            # Test restart detection
            backend_info = PortDiscovery.get_backend_info(port_file)
            assert backend_info is not None
            restart_age = time.time() - backend_info["started_at"]

            # Service was restarted recently (less than 5 minutes)
            assert restart_age < 300

    def test_process_validation(self):
        """Test that process validation works for service health checking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Write port info with current process PID (should be valid)
            current_pid = os.getpid()
            PortDiscovery.write_unified_port_info(
                port_file, backend_port=54321, backend_pid=current_pid
            )

            # Test process validation
            is_valid = PortDiscovery.validate_service_process("backend", port_file)
            assert is_valid is True

            # Test with invalid PID
            PortDiscovery.write_unified_port_info(
                port_file,
                backend_port=54321,
                backend_pid=99999,  # Likely invalid PID
            )

            is_valid = PortDiscovery.validate_service_process("backend", port_file)
            assert is_valid is False

    def test_get_api_base_url_for_testing(self):
        """Test utility method to get API base URL for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            PortDiscovery.write_unified_port_info(
                port_file, backend_port=54321, backend_host="localhost"
            )

            # Test getting API base URL
            api_url = PortDiscovery.get_api_base_url(port_file)
            assert api_url == "http://localhost:54321"

            # Test with custom path prefix
            api_url_with_prefix = PortDiscovery.get_api_base_url(
                port_file, prefix="/api"
            )
            assert api_url_with_prefix == "http://localhost:54321/api"

    def test_cleanup_stale_discovery_files(self):
        """Test cleanup of stale discovery files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            port_file = Path(temp_dir) / ".dev-ports.json"

            # Create stale port file (24+ hours old)
            stale_time = time.time() - (25 * 60 * 60)  # 25 hours ago
            PortDiscovery.write_unified_port_info(
                port_file, backend_port=54321, started_at=stale_time
            )

            # Test stale detection
            is_stale = PortDiscovery.is_discovery_file_stale(port_file)
            assert is_stale is True

            # Test cleanup
            PortDiscovery.cleanup_stale_discovery_files(port_file)
            assert not port_file.exists()

    def test_backward_compatibility_with_existing_backend_file(self):
        """No backward compatibility tests remain; legacy files are no longer supported."""
        # This test intentionally left as a placeholder to document that
        # legacy single-file format is no longer supported by the codebase.
        assert True
