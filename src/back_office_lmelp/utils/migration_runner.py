"""Gestionnaire de processus de migration Babelio (Issue #124).

Ce module gère:
- Lancement unique du script de migration
- Streaming de la progression en temps réel
- État global du processus
"""

import asyncio
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class MigrationRunner:
    """Singleton pour gérer un seul processus de migration à la fois."""

    _instance: "MigrationRunner | None" = None
    _lock = asyncio.Lock()

    def __new__(cls) -> "MigrationRunner":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the migration runner state."""
        self.process: subprocess.Popen[bytes] | None = None
        self.is_running = False
        self.start_time: datetime | None = None
        self.logs: list[str] = []
        self.books_processed = 0
        self.last_update: datetime | None = None

    @classmethod
    def get_instance(cls) -> "MigrationRunner":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start_migration(self) -> dict[str, Any]:
        """Start the migration script if not already running.

        Returns:
            Dict with status and message
        """
        async with self._lock:
            if self.is_running:
                return {
                    "status": "already_running",
                    "message": "Migration already in progress",
                    "start_time": self.start_time.isoformat()
                    if self.start_time
                    else None,
                }

            # Prepare script path
            script_path = (
                Path(__file__).parent.parent.parent.parent
                / "scripts"
                / "migration_donnees"
                / "migrate_all_url_babelio.sh"
            )

            if not script_path.exists():
                return {
                    "status": "error",
                    "message": f"Migration script not found: {script_path}",
                }

            # Start the process
            try:
                self.process = subprocess.Popen(
                    [str(script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=False,  # Use bytes mode for non-blocking reads
                    bufsize=1,
                )

                self.is_running = True
                self.start_time = datetime.now(UTC)
                self.logs = []
                self.books_processed = 0
                self.last_update = datetime.now(UTC)

                logger.info(f"Migration started at {self.start_time}")

                # Start background task to read output
                asyncio.create_task(self._read_output())

                return {
                    "status": "started",
                    "message": "Migration started successfully",
                    "start_time": self.start_time.isoformat(),
                }

            except Exception as e:
                self.is_running = False
                logger.error(f"Failed to start migration: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to start migration: {str(e)}",
                }

    async def _read_output(self) -> None:
        """Background task to read process output."""
        if self.process is None or self.process.stdout is None:
            return

        try:
            while self.is_running and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    decoded_line = line.decode("utf-8", errors="replace").strip()
                    if decoded_line:
                        self.logs.append(decoded_line)
                        self.last_update = datetime.now(UTC)

                        # Count processed books
                        if "Migration #" in decoded_line:
                            self.books_processed += 1

                        # Keep logs manageable (last 100 lines)
                        if len(self.logs) > 100:
                            self.logs = self.logs[-100:]

                await asyncio.sleep(0.1)  # Small delay to prevent CPU spinning

            # Process finished
            if self.process is not None:
                return_code = self.process.wait()
                self.is_running = False

                if return_code == 0:
                    final_msg = "✅ Migration completed successfully"
                elif return_code == 2:
                    final_msg = "⚠️ Migration stopped: Babelio unavailable"
                else:
                    final_msg = f"❌ Migration failed with code {return_code}"

                self.logs.append(final_msg)
                logger.info(final_msg)

        except Exception as e:
            logger.error(f"Error reading migration output: {e}")
            self.is_running = False
            self.logs.append(f"❌ Error: {str(e)}")

    def get_status(self) -> dict[str, Any]:
        """Get current migration status.

        Returns:
            Dict with running status, logs, and progress
        """
        return {
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "books_processed": self.books_processed,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "logs": self.logs[-20:],  # Return last 20 lines
            "total_logs": len(self.logs),
        }

    def get_detailed_logs(self) -> list[str]:
        """Get all logs for expanded view.

        Returns:
            List of all log lines
        """
        return self.logs

    async def stop_migration(self) -> dict[str, Any]:
        """Stop the running migration process.

        Returns:
            Dict with status and message
        """
        async with self._lock:
            if not self.is_running or self.process is None:
                return {
                    "status": "not_running",
                    "message": "No migration is currently running",
                }

            try:
                self.process.terminate()
                self.is_running = False
                self.logs.append("⚠️ Migration stopped by user")

                return {
                    "status": "stopped",
                    "message": "Migration stopped successfully",
                }

            except Exception as e:
                logger.error(f"Failed to stop migration: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to stop migration: {str(e)}",
                }


# Global instance
migration_runner = MigrationRunner.get_instance()
