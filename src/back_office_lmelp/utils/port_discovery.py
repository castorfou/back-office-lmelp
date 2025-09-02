"""Port discovery utility for dynamic backend/frontend synchronization."""

import json
import socket
import time
from pathlib import Path
from typing import Any


class PortDiscovery:
    """Handles dynamic port discovery between backend and frontend."""

    @staticmethod
    def write_port_info(port: int, port_file: Path, host: str = "localhost") -> None:
        """Write port information to a discoverable file.

        Args:
            port: The port number the backend is running on
            port_file: Path to the port discovery file
            host: The host the backend is running on (default: localhost)
        """
        port_data = {
            "port": port,
            "host": host,
            "timestamp": int(time.time()),
            "url": f"http://{host}:{port}",
        }

        # Ensure parent directory exists
        port_file.parent.mkdir(parents=True, exist_ok=True)

        with open(port_file, "w") as f:
            json.dump(port_data, f, indent=2)

    @staticmethod
    def read_port_info(port_file: Path) -> dict[str, Any] | None:
        """Read port information from discovery file.

        Args:
            port_file: Path to the port discovery file

        Returns:
            Dictionary with port information or None if file doesn't exist/invalid
        """
        if not port_file.exists():
            return None

        try:
            with open(port_file) as f:
                data = json.load(f)
                # Type assertion for MyPy
                return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def get_port_file_path(base_path: str | None = None) -> Path:
        """Get the path for the port discovery file.

        Args:
            base_path: Base directory path (default: current working directory)

        Returns:
            Path to the port discovery file
        """
        if base_path:
            return Path(base_path) / ".backend-port.json"
        return Path.cwd() / ".backend-port.json"

    @staticmethod
    def cleanup_port_file(port_file: Path) -> None:
        """Clean up the port discovery file.

        Args:
            port_file: Path to the port discovery file to remove
        """
        try:
            if port_file.exists():
                port_file.unlink()
        except OSError:
            # Ignore cleanup errors
            pass

    @staticmethod
    def find_available_port(start_port: int = 8000, max_attempts: int = 100) -> int:
        """Find an available port starting from the given port.

        Args:
            start_port: Port to start searching from
            max_attempts: Maximum number of ports to try

        Returns:
            Available port number

        Raises:
            RuntimeError: If no available port is found
        """
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", port))
                    return port
            except OSError:
                continue

        raise RuntimeError(
            f"No available port found in range {start_port}-{start_port + max_attempts}"
        )


def create_port_file_on_startup(
    port: int | None = None,
    host: str | None = None,
    port_file_path: Path | None = None,
) -> Path:
    """Create port discovery file on application startup.

    Args:
        port: Port number (if None, will be read from environment)
        host: Host name (if None, will be read from environment)
        port_file_path: Custom path for port file (if None, uses default)

    Returns:
        Path to the created port file
    """
    import os

    # Use provided values or environment variables
    if port is None:
        port = int(os.getenv("API_PORT", "8000"))
    if host is None:
        host = os.getenv("API_HOST", "localhost")
    if port_file_path is None:
        port_file_path = PortDiscovery.get_port_file_path()

    # Write port information
    PortDiscovery.write_port_info(port, port_file_path, host)

    return port_file_path
