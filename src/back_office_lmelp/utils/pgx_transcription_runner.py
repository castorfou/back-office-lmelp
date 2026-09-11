"""Orchestrateur de la file de transcription PGX (Issue #302).

Singleton calqué sur MigrationRunner (utils/migration_runner.py) : traite
séquentiellement tous les épisodes sans transcription au moment du
lancement — une seule machine PGX, pas de parallélisme possible. Déclenché
par POST /api/pgx/transcription/start, suivi par polling GET
/api/pgx/transcription/progress (pas de SSE, cf. convention du projet).
"""

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from ..services import pgx_service
from ..services.mongodb_service import mongodb_service
from ..services.pgx_service import PgxError
from ..services.stats_service import stats_service
from ..settings import settings


logger = logging.getLogger(__name__)


class PgxTranscriptionRunner:
    """Singleton pour gérer un seul traitement de file PGX à la fois."""

    _instance: "PgxTranscriptionRunner | None" = None
    _lock = asyncio.Lock()

    def __new__(cls) -> "PgxTranscriptionRunner":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the runner state."""
        self.is_running = False
        self.episode_ids: list[str] = []
        self.current_episode_id: str | None = None
        self.current_episode_index: int = 0
        self.processed: list[dict[str, Any]] = []
        self.start_time: datetime | None = None
        self.logs: list[str] = []
        self.last_update: datetime | None = None

    @classmethod
    def get_instance(cls) -> "PgxTranscriptionRunner":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _log(self, message: str) -> None:
        now = datetime.now(UTC)
        self.logs.append(f"{now.strftime('%d/%m/%y %H:%M:%S')} - {message}")
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]
        self.last_update = now
        logger.info(message)

    async def start_transcription(self) -> dict[str, Any]:
        """Démarre le traitement de la file d'épisodes sans transcription.

        Returns:
            {"status": "already_running"} si un traitement est déjà en cours,
            {"status": "nothing_to_do"} si aucun épisode n'est en attente,
            {"status": "started", "episode_count": N} sinon.
        """
        async with self._lock:
            if self.is_running:
                return {"status": "already_running"}

            episodes = stats_service.get_episodes_without_transcription()
            if not episodes:
                return {"status": "nothing_to_do"}

            self.is_running = True
            self.episode_ids = [ep["id"] for ep in episodes]
            self.current_episode_id = None
            self.current_episode_index = 0
            self.processed = []
            self.start_time = datetime.now(UTC)
            self.logs = []
            self.last_update = self.start_time

            asyncio.create_task(self._run())

            return {"status": "started", "episode_count": len(episodes)}

    async def _run(self) -> None:
        """Traite la file d'épisodes séquentiellement."""
        try:
            host = settings.pgx_host
            user = settings.pgx_user
            key_path = settings.pgx_ssh_key_path
            remote_audio_root = settings.pgx_remote_audio_root
            remote_transcription_root = settings.pgx_remote_transcription_root
            transcription_timeout_s = settings.pgx_transcription_timeout_s
            poll_interval_s = settings.pgx_poll_interval_s

            if not (
                host
                and user
                and key_path
                and remote_audio_root
                and remote_transcription_root
            ):
                self._log("Configuration PGX incomplète — abandon")
                return

            pgx_reachability_checked = False

            for index, episode_id in enumerate(self.episode_ids):
                self.current_episode_id = episode_id
                self.current_episode_index = index

                try:
                    episode = mongodb_service.get_episode_by_id(episode_id)
                    if episode is None:
                        raise PgxError(f"Épisode {episode_id} introuvable en base")

                    titre = episode.get("titre", episode_id)

                    year = str(episode["date"].year)
                    mp3_fullpath = os.path.join(
                        settings.audio_storage_path, episode["audio_rel_filename"]
                    )
                    stem = os.path.splitext(os.path.basename(mp3_fullpath))[0]
                    local_txt_path = os.path.splitext(mp3_fullpath)[0] + ".txt"

                    if os.path.exists(local_txt_path):
                        self._log(
                            f"[{index + 1}/{len(self.episode_ids)}] {titre}: "
                            "transcription trouvée en cache local"
                        )
                        with open(local_txt_path) as f:
                            transcription_text = f.read()
                    else:
                        if not pgx_reachability_checked:
                            self._log("Vérification de la disponibilité de PGX…")
                            if not await pgx_service.wait_for_pgx_reachable(
                                host, timeout_s=10, poll_interval_s=2
                            ):
                                self._log(
                                    "PGX injoignable — vérifiez qu'elle est allumée "
                                    "et sur le réseau (aucun réveil automatique "
                                    "n'est tenté)"
                                )
                                return
                            pgx_reachability_checked = True

                        self._log(
                            f"[{index + 1}/{len(self.episode_ids)}] {titre}: envoi…"
                        )
                        remote_audio_dir = f"{remote_audio_root}/{year}"

                        await pgx_service.send_audio_to_pgx(
                            mp3_fullpath,
                            remote_audio_dir,
                            host=host,
                            user=user,
                            key_path=key_path,
                        )

                        self._log(
                            f"[{index + 1}/{len(self.episode_ids)}] {titre}: attente…"
                        )
                        remote_txt_path = (
                            f"{remote_transcription_root}/{year}/{stem}.txt"
                        )
                        if not await pgx_service.wait_for_pgx_transcription(
                            remote_txt_path,
                            host=host,
                            user=user,
                            key_path=key_path,
                            timeout_s=transcription_timeout_s,
                            poll_interval_s=poll_interval_s,
                        ):
                            raise PgxError(
                                f"Timeout: transcription non disponible sur PGX "
                                f"après {transcription_timeout_s}s"
                            )

                        self._log(
                            f"[{index + 1}/{len(self.episode_ids)}] {titre}: "
                            "rapatriement…"
                        )
                        transcription_text = (
                            await pgx_service.fetch_transcription_from_pgx(
                                remote_txt_path,
                                local_txt_path,
                                host=host,
                                user=user,
                                key_path=key_path,
                            )
                        )

                    if mongodb_service.episodes_collection is None:
                        raise PgxError("Connexion MongoDB non établie")
                    mongodb_service.episodes_collection.update_one(
                        {"_id": ObjectId(episode_id)},
                        {"$set": {"transcription": transcription_text}},
                    )
                    self._log(
                        f"[{index + 1}/{len(self.episode_ids)}] {titre}: terminé ✅"
                    )
                    self.processed.append(
                        {"episode_id": episode_id, "success": True, "error": None}
                    )
                except PgxError as exc:
                    self._log(f"[{index + 1}/{len(self.episode_ids)}] Échec: {exc}")
                    self.processed.append(
                        {"episode_id": episode_id, "success": False, "error": str(exc)}
                    )
        except Exception as exc:  # noqa: BLE001 - garde-fou pour toujours libérer is_running
            self._log(f"Erreur inattendue du pipeline PGX: {exc}")
        finally:
            self.is_running = False
            self.current_episode_id = None

    def get_status(self) -> dict[str, Any]:
        """Récupère l'état actuel de la file, consommé par le polling GET."""
        return {
            "is_running": self.is_running,
            "episode_ids": self.episode_ids,
            "current_episode_id": self.current_episode_id,
            "current_episode_index": self.current_episode_index,
            "processed": self.processed,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "logs": self.logs[-50:],
            "last_update": self.last_update.isoformat() if self.last_update else None,
        }


pgx_transcription_runner = PgxTranscriptionRunner.get_instance()
