"""Tests for Claude Code auto-discovery use cases."""

import tempfile
import time
from pathlib import Path

from back_office_lmelp.utils.port_discovery import PortDiscovery


def test_claude_code_can_discover_active_backend():
    """Test that Claude Code can automatically discover if backend is active."""
    with tempfile.TemporaryDirectory() as temp_dir:
        port_file = Path(temp_dir) / ".dev-ports.json"

        # Simulate backend running
        PortDiscovery.write_unified_port_info(
            port_file,
            backend_port=54321,
            backend_host="localhost",
            backend_pid=12345,
        )

        # Claude Code auto-discovery workflow
        backend_info = PortDiscovery.get_backend_info(port_file)
        assert backend_info is not None
        assert backend_info["port"] == 54321

        # Get API URL for curl commands
        api_url = PortDiscovery.get_api_base_url(port_file)
        assert api_url == "http://localhost:54321"

        # Get API URL with prefix
        api_url_with_prefix = PortDiscovery.get_api_base_url(port_file, prefix="/api")
        assert api_url_with_prefix == "http://localhost:54321/api"


def test_claude_code_detects_recent_backend_restart():
    """Test that Claude Code can detect if backend was recently restarted."""
    with tempfile.TemporaryDirectory() as temp_dir:
        port_file = Path(temp_dir) / ".dev-ports.json"

        # Simulate backend that just restarted (1 minute ago)
        recent_start = time.time() - 60
        PortDiscovery.write_unified_port_info(
            port_file,
            backend_port=54321,
            started_at=recent_start,
        )

        backend_info = PortDiscovery.get_backend_info(port_file)
        restart_age = time.time() - backend_info["started_at"]

        # Backend restarted less than 5 minutes ago - might need to wait
        assert restart_age < 300  # Less than 5 minutes
        assert restart_age > 0  # But not negative


def test_claude_code_handles_no_backend_gracefully():
    """Test that Claude Code handles missing backend gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        port_file = Path(temp_dir) / ".dev-ports.json"

        # No backend running
        backend_info = PortDiscovery.get_backend_info(port_file)
        assert backend_info is None

        api_url = PortDiscovery.get_api_base_url(port_file)
        assert api_url is None


def test_claude_code_validates_backend_is_still_running():
    """Test that Claude Code can validate backend process is still active."""
    with tempfile.TemporaryDirectory() as temp_dir:
        port_file = Path(temp_dir) / ".dev-ports.json"

        # Simulate backend with invalid PID (process died)
        PortDiscovery.write_unified_port_info(
            port_file,
            backend_port=54321,
            backend_pid=99999,  # Invalid PID
        )

        # Check if backend is still active
        is_active = PortDiscovery.is_service_active("backend", port_file)
        assert is_active is False


def test_claude_code_discovers_both_backend_and_frontend():
    """Test that Claude Code can discover both services when running."""
    with tempfile.TemporaryDirectory() as temp_dir:
        port_file = Path(temp_dir) / ".dev-ports.json"

        # Simulate both services running
        PortDiscovery.write_unified_port_info(
            port_file,
            backend_port=54321,
            frontend_port=5173,
            backend_host="localhost",
            frontend_host="localhost",
        )

        # Check backend discovery
        backend_info = PortDiscovery.get_backend_info(port_file)
        assert backend_info["port"] == 54321
        assert backend_info["url"] == "http://localhost:54321"

        # Check frontend discovery
        frontend_info = PortDiscovery.get_frontend_info(port_file)
        assert frontend_info["port"] == 5173
        assert frontend_info["url"] == "http://localhost:5173"


def test_claude_code_api_discovery_workflow():
    """Test the complete Claude Code API discovery workflow."""
    with tempfile.TemporaryDirectory() as temp_dir:
        port_file = Path(temp_dir) / ".dev-ports.json"

        # Simulate services started by start-dev.sh
        start_time = time.time()
        PortDiscovery.write_unified_port_info(
            port_file,
            backend_port=54321,
            frontend_port=5173,
            backend_host="0.0.0.0",  # As per start-dev.sh
            frontend_host="0.0.0.0",
            started_at=start_time,
        )

        # Claude Code workflow:
        # 1. Check if backend is available
        backend_info = PortDiscovery.get_backend_info(port_file)
        if backend_info is None:
            # No backend found, can't make API calls
            raise AssertionError("Backend should be discoverable")

        # 2. Check if backend was recently restarted (might need to wait)
        restart_age = time.time() - backend_info["started_at"]
        if restart_age < 30:  # Less than 30 seconds ago
            # Recently restarted, might want to wait a bit
            print(f"Backend recently restarted {restart_age:.1f}s ago")

        # 3. Get API base URL for curl commands
        api_base = PortDiscovery.get_api_base_url(port_file)
        api_endpoints = {
            "health": f"{api_base}/",
            "docs": f"{api_base}/docs",
            "openapi": f"{api_base}/openapi.json",
            "verify_babelio": f"{api_base}/api/verify-babelio",
        }

        # 4. Verify we have valid URLs
        assert api_endpoints["health"] == "http://0.0.0.0:54321/"
        assert (
            api_endpoints["verify_babelio"] == "http://0.0.0.0:54321/api/verify-babelio"
        )

        print("Claude Code auto-discovery successful!")
        print(f"Backend: {backend_info['url']}")
        print(f"Available endpoints: {list(api_endpoints.keys())}")


def test_claude_code_handles_stale_discovery_files():
    """Test that Claude Code handles stale discovery files properly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        port_file = Path(temp_dir) / ".dev-ports.json"

        # Create stale discovery file (25 hours old)
        stale_time = time.time() - (25 * 60 * 60)
        PortDiscovery.write_unified_port_info(
            port_file,
            backend_port=54321,
            started_at=stale_time,
        )

        # Check if file is stale
        is_stale = PortDiscovery.is_discovery_file_stale(port_file)
        assert is_stale is True

        # Claude Code should clean up stale files
        PortDiscovery.cleanup_stale_discovery_files(port_file)
        assert not port_file.exists()

        # After cleanup, no backend should be discoverable
        backend_info = PortDiscovery.get_backend_info(port_file)
        assert backend_info is None
