"""Port discovery utility for dynamic backend/frontend synchronization."""

import json
import os
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
        # Deprecated: single-file legacy format is removed. Use
        # write_backend_info_to_unified_file instead.
        PortDiscovery.write_backend_info_to_unified_file(
            port_file, port=port, host=host
        )

    @staticmethod
    def read_port_info(port_file: Path) -> dict[str, Any] | None:
        """Read port information from discovery file.

        Args:
            port_file: Path to the port discovery file

        Returns:
            Dictionary with port information or None if file doesn't exist/invalid
        """
        # Deprecated: reading legacy single-file format. Prefer get_backend_info
        # on the unified .dev-ports.json file.
        if not port_file.exists():
            return None

        try:
            with open(port_file) as f:
                data = json.load(f)
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
        # Kept for API compatibility but now returns the unified file path.
        return PortDiscovery.get_unified_port_file_path(base_path)

    @staticmethod
    def cleanup_port_file(port_file: Path) -> None:
        """Clean up the port discovery file.

        Args:
            port_file: Path to the port discovery file to remove
        """
        # Deprecated cleanup for legacy file; prefer cleanup_unified_port_file
        try:
            if port_file.exists():
                port_file.unlink()
        except OSError:
            pass

    @staticmethod
    def find_available_port(
        start_port: int = 8000, max_attempts: int = 100, host: str = "0.0.0.0"
    ) -> int:
        """Find an available port starting from the given port.

        Args:
            start_port: Port to start searching from
            max_attempts: Maximum number of ports to try
            host: Host address to bind to (default: "0.0.0.0")

        Returns:
            Available port number

        Raises:
            RuntimeError: If no available port is found
        """
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((host, port))
                    return port
            except OSError:
                continue

        raise RuntimeError(
            f"No available port found in range {start_port}-{start_port + max_attempts}"
        )

    @staticmethod
    def write_unified_port_info(
        port_file: Path,
        backend_port: int | None = None,
        frontend_port: int | None = None,
        backend_host: str = "0.0.0.0",
        frontend_host: str = "0.0.0.0",
        backend_pid: int | None = None,
        frontend_pid: int | None = None,
        started_at: float | None = None,
    ) -> None:
        """Write unified port information for both backend and frontend services.

        Args:
            port_file: Path to the unified .dev-ports.json file
            backend_port: Backend service port
            frontend_port: Frontend service port
            backend_host: Backend host (default: "0.0.0.0")
            frontend_host: Frontend host (default: "0.0.0.0")
            backend_pid: Backend process ID
            frontend_pid: Frontend process ID
            started_at: Service start timestamp (default: current time)
        """
        if started_at is None:
            started_at = time.time()

        port_data = {}

        if backend_port is not None:
            port_data["backend"] = {
                "port": backend_port,
                "host": backend_host,
                "pid": backend_pid or os.getpid(),
                "started_at": started_at,
                "url": f"http://{backend_host}:{backend_port}",
            }

        if frontend_port is not None:
            port_data["frontend"] = {
                "port": frontend_port,
                "host": frontend_host,
                "pid": frontend_pid or os.getpid(),
                "started_at": started_at,
                "url": f"http://{frontend_host}:{frontend_port}",
            }

        # Ensure parent directory exists
        port_file.parent.mkdir(parents=True, exist_ok=True)

        # Read existing data to merge if file exists
        existing_data = {}
        if port_file.exists():
            try:
                with open(port_file) as f:
                    existing_data = json.load(f)
            except (OSError, json.JSONDecodeError):
                pass

        # Merge with existing data
        existing_data.update(port_data)

        with open(port_file, "w") as f:
            json.dump(existing_data, f, indent=2)

    @staticmethod
    def get_backend_info(port_file: Path) -> dict[str, Any] | None:
        """Get backend service information from unified port file.

        Args:
            port_file: Path to the unified .dev-ports.json file

        Returns:
            Backend service information or None if not found
        """
        try:
            with open(port_file) as f:
                data = json.load(f)
                backend_data = data.get("backend")
                return backend_data if isinstance(backend_data, dict) else None
        except (OSError, json.JSONDecodeError, FileNotFoundError):
            return None

    @staticmethod
    def get_frontend_info(port_file: Path) -> dict[str, Any] | None:
        """Get frontend service information from unified port file.

        Args:
            port_file: Path to the unified .dev-ports.json file

        Returns:
            Frontend service information or None if not found
        """
        try:
            with open(port_file) as f:
                data = json.load(f)
                frontend_data = data.get("frontend")
                return frontend_data if isinstance(frontend_data, dict) else None
        except (OSError, json.JSONDecodeError, FileNotFoundError):
            return None

    @staticmethod
    def is_service_active(service_name: str, port_file: Path) -> bool:
        """Check if a service is currently active based on process validation.

        Args:
            service_name: Name of service ("backend" or "frontend")
            port_file: Path to the unified .dev-ports.json file

        Returns:
            True if service is active, False otherwise
        """
        return PortDiscovery.validate_service_process(service_name, port_file)

    @staticmethod
    def validate_service_process(service_name: str, port_file: Path) -> bool:
        """Validate that a service process is still running.

        Args:
            service_name: Name of service ("backend" or "frontend")
            port_file: Path to the unified .dev-ports.json file

        Returns:
            True if process is running, False otherwise
        """
        try:
            with open(port_file) as f:
                data = json.load(f)

            service_info = data.get(service_name)
            if not service_info or "pid" not in service_info:
                return False

            pid = service_info["pid"]

            # Check if process exists
            try:
                os.kill(pid, 0)  # Signal 0 checks if process exists without killing it
                return True
            except (OSError, ProcessLookupError):
                return False

        except (OSError, json.JSONDecodeError, FileNotFoundError):
            return False

    @staticmethod
    def get_api_base_url(port_file: Path, prefix: str = "") -> str | None:
        """Get API base URL for making HTTP requests.

        Args:
            port_file: Path to the unified .dev-ports.json file
            prefix: Optional path prefix to append (e.g., "/api")

        Returns:
            Complete API base URL or None if backend not found
        """
        backend_info = PortDiscovery.get_backend_info(port_file)
        if not backend_info:
            return None

        base_url = str(backend_info["url"])
        if prefix:
            base_url = base_url.rstrip("/") + "/" + prefix.lstrip("/")

        return base_url

    @staticmethod
    def is_discovery_file_stale(port_file: Path, max_age_hours: int = 24) -> bool:
        """Check if discovery file is stale (too old).

        Args:
            port_file: Path to the unified .dev-ports.json file
            max_age_hours: Maximum age in hours before considering stale

        Returns:
            True if file is stale, False otherwise
        """
        try:
            with open(port_file) as f:
                data = json.load(f)

            # Check if any service has stale timestamp
            for service_info in data.values():
                if isinstance(service_info, dict) and "started_at" in service_info:
                    age_seconds = time.time() - service_info["started_at"]
                    if age_seconds > (max_age_hours * 60 * 60):
                        return True

            return False

        except (OSError, json.JSONDecodeError, FileNotFoundError):
            return True

    @staticmethod
    def cleanup_stale_discovery_files(port_file: Path) -> None:
        """Clean up stale discovery files.

        Args:
            port_file: Path to the unified .dev-ports.json file
        """
        if PortDiscovery.is_discovery_file_stale(port_file):
            try:
                if port_file.exists():
                    port_file.unlink()
            except OSError:
                pass

    @staticmethod
    def migrate_from_legacy_backend_file(legacy_file: Path, unified_file: Path) -> None:
        """Migrate from legacy .backend-port.json to unified .dev-ports.json.

        Args:
            legacy_file: Path to legacy .backend-port.json file
            unified_file: Path to unified .dev-ports.json file
        """
        # Migration helper removed: project no longer supports legacy files.
        return

    @staticmethod
    def get_unified_port_file_path(base_path: str | None = None) -> Path:
        """Get the path for the unified port discovery file.

        Args:
            base_path: Base directory path (default: current working directory)

        Returns:
            Path to the unified .dev-ports.json file
        """
        if base_path:
            return Path(base_path) / ".dev-ports.json"
        return Path.cwd() / ".dev-ports.json"

    @staticmethod
    def write_backend_info_to_unified_file(
        port_file: Path,
        port: int,
        host: str = "0.0.0.0",
        pid: int | None = None,
    ) -> None:
        """Write backend information directly to unified .dev-ports.json file.

        Args:
            port_file: Path to the unified .dev-ports.json file
            port: Backend service port
            host: Backend host (default: "0.0.0.0")
            pid: Backend process ID (default: current process)
        """
        if pid is None:
            pid = os.getpid()

        PortDiscovery.write_unified_port_info(
            port_file,
            backend_port=port,
            backend_host=host,
            backend_pid=pid,
        )

    @staticmethod
    def add_frontend_info_to_unified_file(
        port_file: Path,
        frontend_port: int,
        frontend_host: str = "0.0.0.0",
        frontend_pid: int | None = None,
    ) -> None:
        """Add frontend information to existing unified .dev-ports.json file.

        Args:
            port_file: Path to the unified .dev-ports.json file
            frontend_port: Frontend service port
            frontend_host: Frontend host (default: "0.0.0.0")
            frontend_pid: Frontend process ID (default: current process)
        """
        if frontend_pid is None:
            frontend_pid = os.getpid()

        PortDiscovery.write_unified_port_info(
            port_file,
            frontend_port=frontend_port,
            frontend_host=frontend_host,
            frontend_pid=frontend_pid,
        )

    @staticmethod
    def cleanup_unified_port_file(port_file: Path) -> None:
        """Clean up unified port discovery file only.

        Args:
            port_file: Path to the unified .dev-ports.json file
        """
        try:
            if port_file.exists():
                port_file.unlink()
        except OSError:
            pass

    @staticmethod
    def migrate_to_unified_system(legacy_file: Path, unified_file: Path) -> None:
        """Migrate from legacy .backend-port.json to unified .dev-ports.json.

        Args:
            legacy_file: Path to legacy .backend-port.json file
            unified_file: Path to unified .dev-ports.json file
        """
        # Migration helper removed: legacy support dropped.
        return


def create_port_file_on_startup(
    port: int | None = None,
    host: str | None = None,
    port_file_path: Path | None = None,
) -> Path:
    """Create unified port discovery file on application startup.

    Args:
        port: Port number (if None, will be read from environment)
        host: Host name (if None, will be read from environment)
        port_file_path: Custom path for unified port file (if None, uses default)

    Returns:
        Path to the created unified port file
    """
    import os

    # Use provided values or environment variables
    if port is None:
        port = int(os.getenv("API_PORT", "8000"))
    if host is None:
        host = os.getenv("API_HOST", "localhost")
    if port_file_path is None:
        port_file_path = PortDiscovery.get_unified_port_file_path()

    # Write backend information to the unified .dev-ports.json file. We no
    # longer support the legacy single-file format; the codebase now uses
    # the unified format exclusively.
    PortDiscovery.write_backend_info_to_unified_file(port_file_path, port, host)

    return port_file_path
