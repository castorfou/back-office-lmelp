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
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from bson import ObjectId

from ..services import pgx_service
from ..services.mongodb_service import mongodb_service
from ..services.pgx_service import PgxError
from ..services.stats_service import stats_service
from ..settings import settings
from .ntfy import send_ntfy_notification


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
        self.retry_pending: bool = False
        self.next_attempt_at: datetime | None = None
        self.retry_attempts: list[dict[str, Any]] = []
        self.current_log_id: str | None = None

    @classmethod
    def get_instance(cls) -> "PgxTranscriptionRunner":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _log(self, message: str) -> None:
        now = datetime.now(UTC)
        local_now = now.astimezone(ZoneInfo("Europe/Paris"))
        self.logs.append(f"{local_now.strftime('%d/%m/%y %H:%M:%S')} - {message}")
        if len(self.logs) > 200:
            self.logs = self.logs[-200:]
        self.last_update = now
        logger.info(message)

    async def start_transcription(self, trigger: str = "manual") -> dict[str, Any]:
        """Démarre le traitement de la file d'épisodes sans transcription.

        Args:
            trigger: "manual" (bouton UI, défaut) ou "api" (déclenchement
                externe n8n/Automatisch). "api" active le retry horaire
                automatique si PGX est injoignable (Issue #309) ;
                "manual" garde le comportement d'abandon immédiat.

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
            self.retry_pending = False
            self.next_attempt_at = None
            self.retry_attempts = []
            self.current_log_id = None

            asyncio.create_task(self._run(trigger))

            return {"status": "started", "episode_count": len(episodes)}

    async def _send_notification(self, title: str, message: str) -> None:
        await send_ntfy_notification(
            settings.ntfy_server_url, settings.ntfy_topic, title, message
        )

    def _persist_pending_retry_cycle(self, trigger: str) -> None:
        """Persiste le cycle dès la première tentative de retry ratée
        (Issue #313), pour que l'utilisateur voie qu'un cycle est en cours
        dans l'historique sans attendre sa fin (potentiellement des heures
        plus tard). Statut 'pgx' — mis à jour ensuite au fil des tentatives
        puis avec le statut définitif à la fin du cycle."""
        log_document = self._build_log_document(trigger, "pgx", finished=False)
        try:
            self.current_log_id = mongodb_service.insert_pgx_transcription_log(
                dict(log_document)
            )
        except Exception as exc:  # noqa: BLE001 - la persistance ne doit jamais casser le run
            logger.error(f"Erreur lors de la persistance anticipée du log PGX: {exc}")

    def _sync_retry_attempts_to_log(self) -> None:
        """Met à jour le document déjà persisté avec les tentatives de retry
        au fur et à mesure (Issue #313)."""
        if self.current_log_id is None:
            return
        try:
            mongodb_service.update_pgx_transcription_log(
                self.current_log_id, {"retry_attempts": list(self.retry_attempts)}
            )
        except Exception as exc:  # noqa: BLE001 - la persistance ne doit jamais casser le run
            logger.error(f"Erreur lors de la mise à jour du log PGX: {exc}")

    async def _wait_for_reachable_with_retry(self, host: str, trigger: str) -> bool:
        """Retry horaire de joignabilité PGX, plafonné (Issue #309).

        Notifie une seule fois au premier échec (pas à chaque tentative),
        pour que l'utilisateur sache qu'il doit allumer PGX. Retourne True
        dès que PGX redevient joignable, False si le plafond est dépassé.
        """
        retry_deadline = datetime.now(UTC) + timedelta(
            hours=settings.pgx_transcription_retry_max_hours
        )
        self.retry_attempts.append(
            {"attempted_at": datetime.now(UTC).isoformat(), "reachable": False}
        )
        first_attempt = True
        while datetime.now(UTC) < retry_deadline:
            self.retry_pending = True
            self.next_attempt_at = datetime.now(UTC) + timedelta(
                hours=settings.pgx_transcription_retry_interval_hours
            )
            self._log(
                "PGX injoignable — nouvelle tentative dans "
                f"{settings.pgx_transcription_retry_interval_hours}h"
            )
            if first_attempt:
                interval_h = settings.pgx_transcription_retry_interval_hours
                max_h = settings.pgx_transcription_retry_max_hours
                await self._send_notification(
                    "PGX injoignable — transcription en attente",
                    "Allumez PGX pour reprendre la transcription. Nouvelle "
                    f"tentative automatique toutes les {interval_h}h pendant "
                    f"{max_h}h.",
                )
                self._persist_pending_retry_cycle(trigger)
                first_attempt = False

            await asyncio.sleep(settings.pgx_transcription_retry_interval_hours * 3600)

            attempt_reachable = await pgx_service.wait_for_pgx_reachable(
                host, timeout_s=10, poll_interval_s=2
            )
            self.retry_attempts.append(
                {
                    "attempted_at": datetime.now(UTC).isoformat(),
                    "reachable": attempt_reachable,
                }
            )
            self._sync_retry_attempts_to_log()
            if attempt_reachable:
                self.retry_pending = False
                self.next_attempt_at = None
                self._log("PGX de nouveau joignable — reprise du traitement")
                return True

        self.retry_pending = False
        self.next_attempt_at = None
        return False

    @staticmethod
    def _format_episode_date(episode_date: datetime) -> str:
        """Formate la date d'un épisode pour affichage (dd/mm/yy)."""
        return episode_date.strftime("%d/%m/%y")

    def _build_log_document(
        self,
        trigger: str,
        status: str,
        error_message: str | None = None,
        finished: bool = True,
    ) -> dict[str, Any]:
        """Construit le document de cycle persisté dans pgx_transcription_logs.

        `finished=False` pour le document intermédiaire persisté dès l'entrée
        en retry (Issue #313) : le cycle n'est pas terminé, `finished_at` ne
        doit donc pas prendre l'heure de cet instant intermédiaire (trompeur
        pour l'affichage — donnerait la date de la 1re tentative ratée
        plutôt que la vraie fin de cycle).
        """
        return {
            "started_at": self.start_time.isoformat() if self.start_time else None,
            "finished_at": datetime.now(UTC).isoformat() if finished else None,
            "trigger": trigger,
            "status": status,
            "episode_ids": list(self.episode_ids),
            "episodes": list(self.processed),
            "retry_attempts": list(self.retry_attempts),
            "notification_sent": bool(self.processed),
            "error_message": error_message,
        }

    async def _finalize_cycle(
        self, trigger: str, status: str, error_message: str | None = None
    ) -> None:
        """Persiste l'historique du cycle (Issue #309).

        Les notifications ntfy sont envoyées au fil de l'eau, par épisode
        (succès/échec) ou au premier échec de joignabilité — jamais ici en
        résumé groupé (même logique que RssSyncService : un message par
        événement, pas de synthèse de fin de cycle).
        """
        log_document = self._build_log_document(trigger, status, error_message)
        try:
            if self.current_log_id is not None:
                mongodb_service.update_pgx_transcription_log(
                    self.current_log_id, dict(log_document)
                )
            else:
                mongodb_service.insert_pgx_transcription_log(dict(log_document))
        except Exception as exc:  # noqa: BLE001 - la persistance ne doit jamais casser le run
            logger.error(f"Erreur lors de la persistance du log PGX: {exc}")

    async def _run(self, trigger: str = "manual") -> None:
        """Traite la file d'épisodes séquentiellement."""
        status = "success"
        error_message: str | None = None
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
                status = "error"
                error_message = "Configuration PGX incomplète"
                return

            pgx_reachability_checked = False
            abandoned = False

            for index, episode_id in enumerate(self.episode_ids):
                self.current_episode_id = episode_id
                self.current_episode_index = index
                episode = None
                titre = episode_id

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
                                if trigger == "manual":
                                    self._log(
                                        "PGX injoignable — vérifiez qu'elle est "
                                        "allumée et sur le réseau (aucun réveil "
                                        "automatique n'est tenté)"
                                    )
                                    return
                                if not await self._wait_for_reachable_with_retry(
                                    host, trigger
                                ):
                                    self._log(
                                        "PGX toujours injoignable après "
                                        f"{settings.pgx_transcription_retry_max_hours}h "
                                        "— abandon du cycle"
                                    )
                                    abandoned = True
                                    break
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
                        {
                            "episode_id": episode_id,
                            "titre": titre,
                            "date": episode["date"].isoformat(),
                            "success": True,
                            "error": None,
                        }
                    )
                    episode_date_str = self._format_episode_date(episode["date"])
                    await self._send_notification(
                        f"Nouvel épisode Le Masque et la Plume transcrit — {episode_date_str}",
                        titre,
                    )
                except PgxError as exc:
                    self._log(f"[{index + 1}/{len(self.episode_ids)}] Échec: {exc}")
                    self.processed.append(
                        {
                            "episode_id": episode_id,
                            "titre": titre,
                            "date": episode["date"].isoformat()
                            if episode is not None
                            else None,
                            "success": False,
                            "error": str(exc),
                        }
                    )
                    if episode is not None:
                        episode_date_str = self._format_episode_date(episode["date"])
                        title = f"Échec transcription PGX — {episode_date_str}"
                    else:
                        title = "Échec transcription PGX"
                    await self._send_notification(
                        title,
                        f"{titre} : erreur technique, voir l'historique dans "
                        "Back-office LMELP pour le détail",
                    )

            failed_count = sum(1 for entry in self.processed if not entry["success"])
            if abandoned:
                status = "pgx"
            elif failed_count > 0:
                status = "error"
            else:
                status = "success"
        except Exception as exc:  # noqa: BLE001 - garde-fou pour toujours libérer is_running
            self._log(f"Erreur inattendue du pipeline PGX: {exc}")
            status = "error"
            error_message = str(exc)
        finally:
            self.is_running = False
            self.current_episode_id = None
            if self.start_time is not None:
                await self._finalize_cycle(trigger, status, error_message)

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
            "retry_pending": self.retry_pending,
            "next_attempt_at": self.next_attempt_at.isoformat()
            if self.next_attempt_at
            else None,
        }


pgx_transcription_runner = PgxTranscriptionRunner.get_instance()
