"""Remises de lmelp-pap et leur intégration comme épisodes (collection `pap_remises`).

lmelp-pap copie le fichier audio dans le dossier audio de lmelp, puis écrit une
fiche dans `pap_remises`. lmelp ne fait que lire cette collection : il n'y écrit
jamais, et ne renomme ni ne déplace le fichier audio (pap reconnaît l'entrée
d'une émission dans lmelp par son chemin).

L'intégration fait d'une remise livrée un épisode, remise par remise. Les
doublons avec les épisodes venus d'autres voies sont écartés en amont par pap :
lmelp ne refuse que la double intégration d'une même remise.
"""

import asyncio
import hashlib
import logging
import os
from datetime import datetime
from typing import Any


logger = logging.getLogger(__name__)

PAP_REMISES_COLLECTION = "pap_remises"


def sha256_of_file(path: str) -> str:
    """Empreinte SHA-256 hexadécimale d'un fichier, lu par morceaux de 1 Mo."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PapRemiseError(Exception):
    """Intégration refusée, avec un message destiné à l'utilisateur."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class PapRemisesService:
    """Liste et intègre les remises livrées par lmelp-pap."""

    def __init__(
        self,
        mongodb_service: Any,
        audio_root: str,
        transcription_runner: Any = None,
        notify: Any = None,
    ) -> None:
        self.mongodb_service = mongodb_service
        self.audio_root = audio_root
        self.transcription_runner = transcription_runner
        self.notify = notify
        # Remises dont l'intégration est en cours : un double clic, ou un
        # second onglet, arrive pendant le calcul de l'empreinte (un seul
        # process backend, pas de verrou partagé à prévoir).
        self._en_cours: set[str] = set()

    def _remises(self) -> Any:
        return self.mongodb_service.get_collection(PAP_REMISES_COLLECTION)

    def _ids_integres(self) -> set[str]:
        episodes = self.mongodb_service.episodes_collection
        return {i for i in episodes.distinct("pap_remise_id") if i is not None}

    def _audio_path(self, fiche: dict[str, Any]) -> str | None:
        """Chemin du fichier audio de la remise s'il est présent, sinon None."""
        rel = fiche.get("audio_rel_filename") or ""
        path = os.path.join(self.audio_root, rel)
        if rel and os.path.isfile(path):
            return path
        return None

    def _fiches_a_integrer(self) -> list[dict[str, Any]]:
        """Remises livrées pas encore intégrées, des plus récentes aux plus anciennes.

        Le fichier n'est testé que pour les fiches pas encore intégrées ; chaque
        fichier absent produit une ligne de log (signe d'un montage du dossier
        audio mal réglé entre les deux applis).
        """
        integres = self._ids_integres()
        fiches = []
        for fiche in self._remises().find({}):
            if fiche.get("_id") in integres:
                continue
            if self._audio_path(fiche) is None:
                logger.warning(
                    "fiche pap %s : fichier absent dans %s",
                    fiche.get("_id"),
                    os.path.join(
                        self.audio_root, fiche.get("audio_rel_filename") or ""
                    ),
                )
                continue
            fiches.append(fiche)
        fiches.sort(key=lambda f: f.get("date") or datetime.min, reverse=True)
        return fiches

    def list_a_integrer(self) -> list[dict[str, Any]]:
        """Remises à intégrer, telles que la page « Remises pap » les affiche."""
        return [
            {
                "remise_id": fiche["_id"],
                "titre": fiche.get("titre", ""),
                "date": fiche["date"].strftime("%Y-%m-%d")
                if fiche.get("date")
                else None,
                "duree": fiche.get("duree"),
                "description": fiche.get("description", ""),
                "episode_page_url": fiche.get("episode_page_url"),
            }
            for fiche in self._fiches_a_integrer()
        ]

    def count_a_integrer(self) -> int:
        """Nombre de remises à intégrer : la taille de la même liste."""
        return len(self._fiches_a_integrer())

    async def integrer(self, remise_id: str) -> dict[str, Any]:
        """Fait de la remise livrée un épisode, puis lance sa transcription."""
        fiche = self._remises().find_one({"_id": remise_id})
        if fiche is None:
            raise PapRemiseError("Remise inconnue", 404)
        if remise_id in self._en_cours or remise_id in self._ids_integres():
            raise PapRemiseError("Remise déjà intégrée", 409)
        self._en_cours.add(remise_id)
        try:
            return await self._integrer(remise_id, fiche)
        finally:
            self._en_cours.discard(remise_id)

    async def _integrer(self, remise_id: str, fiche: dict[str, Any]) -> dict[str, Any]:
        path = self._audio_path(fiche)
        if path is None:
            raise PapRemiseError(
                "Fichier audio absent du dossier audio de lmelp : "
                f"{fiche.get('audio_rel_filename') or '(non renseigné)'}",
                422,
            )
        # ~70 Mo à lire : par morceaux, hors de la boucle d'événements
        empreinte = await asyncio.to_thread(sha256_of_file, path)
        if empreinte != str(fiche.get("sha256", "")).lower():
            raise PapRemiseError(
                "Empreinte SHA-256 du fichier audio différente de celle de la "
                "remise : copie incomplète ou corrompue",
                422,
            )
        episode_id = self.mongodb_service.insert_episode(
            {
                "titre": fiche.get("titre", ""),
                "date": fiche["date"],
                "type": fiche.get("type", "livres"),
                "duree": fiche.get("duree"),
                "description": fiche.get("description", ""),
                "url": fiche.get("url"),
                "audio_rel_filename": fiche["audio_rel_filename"],
                "episode_page_url": fiche.get("episode_page_url"),
                "transcription": None,
                "masked": False,
                "source": "pap",
                "pap_remise_id": remise_id,
            }
        )
        logger.info(f"✅ Remise pap intégrée : {remise_id}")

        if self.notify is not None:
            await self.notify(
                "Nouvel épisode Le Masque et la Plume intégré — "
                f"{fiche['date']:%d/%m/%y}",
                fiche.get("titre", ""),
                prefix="pap",
            )
        transcription_status = await self._start_transcription()

        return {
            "episode_id": episode_id,
            "remise_id": remise_id,
            "titre": fiche.get("titre", ""),
            "date": fiche["date"].strftime("%Y-%m-%d"),
            "transcription_status": transcription_status,
        }

    async def _start_transcription(self) -> str:
        """Lance la file PGX en mode « api » ; un échec n'annule pas l'intégration.

        Returns:
            "started", "already_running", "nothing_to_do" ou "error".
        """
        if self.transcription_runner is None:
            return "error"
        try:
            result = await self.transcription_runner.start_transcription(trigger="api")
            return str(result.get("status", "error"))
        except Exception as e:
            logger.error(f"Erreur lancement transcription PGX après intégration: {e}")
            return "error"


def _build_pap_remises_service() -> PapRemisesService:
    """Construit l'instance singleton du service (import différé anti-cycle)."""
    from ..settings import settings
    from ..utils.ntfy import send_ntfy_notification
    from ..utils.pgx_transcription_runner import pgx_transcription_runner
    from .mongodb_service import mongodb_service

    async def notify(title: str, message: str, prefix: str) -> None:
        await send_ntfy_notification(
            settings.ntfy_server_url,
            settings.ntfy_topic,
            title,
            message,
            prefix=prefix,
        )

    return PapRemisesService(
        mongodb_service=mongodb_service,
        audio_root=settings.audio_storage_path,
        transcription_runner=pgx_transcription_runner,
        notify=notify,
    )


pap_remises_service = _build_pap_remises_service()
