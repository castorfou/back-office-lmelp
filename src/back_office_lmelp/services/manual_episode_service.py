"""Ajout manuel d'une émission absente du flux RSS (Issue #334).

Le flux RSS France Inter ne conserve que les épisodes récents : une émission
plus ancienne absente de la base ne peut être récupérée que depuis sa page
radiofrance.fr, dont le JSON-LD `RadioEpisode` donne titre, description,
date, durée et URL du fichier audio complet.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup


if TYPE_CHECKING:
    from ..utils.pgx_transcription_runner import PgxTranscriptionRunner
    from .mongodb_service import MongoDBService
    from .rss_sync_service import RssSyncService

logger = logging.getLogger(__name__)

# Une émission complète dure ~47 min ; une séquence sur un livre ~8-10 min.
MIN_FULL_EPISODE_SECONDS = 1800
MASQUE_PAGE_PATH_PREFIX = "/franceinter/podcasts/le-masque-et-la-plume/"


class ManualEpisodeError(Exception):
    """Ajout refusé ou impossible, avec un message destiné à l'utilisateur."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ManualEpisodeService:
    """Ajoute une émission à partir de sa page radiofrance.fr."""

    def __init__(
        self,
        mongodb_service: MongoDBService,
        rss_sync_service: RssSyncService,
        transcription_runner: PgxTranscriptionRunner | None = None,
        notify: Callable[..., Awaitable[None]] | None = None,
    ) -> None:
        self.mongodb_service = mongodb_service
        self.rss_sync_service = rss_sync_service
        self.transcription_runner = transcription_runner
        self.notify = notify

    async def fetch_page_html(self, page_url: str) -> str:
        """Télécharge le HTML de la page radiofrance.fr de l'émission.

        Raises:
            ManualEpisodeError (502): page injoignable ou statut HTTP d'erreur.
        """
        from .radiofrance_service import radiofrance_service

        try:
            async with (
                aiohttp.ClientSession(
                    headers=radiofrance_service.http_headers
                ) as session,
                session.get(
                    page_url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response,
            ):
                if response.status != 200:
                    raise ManualEpisodeError(
                        f"Page radiofrance.fr inaccessible (HTTP {response.status})",
                        status_code=502,
                    )
                return await response.text()
        except (aiohttp.ClientError, TimeoutError) as e:
            raise ManualEpisodeError(
                f"Page radiofrance.fr inaccessible ({type(e).__name__})",
                status_code=502,
            ) from e

    @staticmethod
    def _check_page_url(page_url: str) -> None:
        """Refuse toute URL qui n'est pas une page Le Masque et la Plume."""
        parsed = urlparse(page_url.strip())
        if (
            parsed.scheme != "https"
            or parsed.netloc != "www.radiofrance.fr"
            or not parsed.path.startswith(MASQUE_PAGE_PATH_PREFIX)
            or parsed.path.rstrip("/") == MASQUE_PAGE_PATH_PREFIX.rstrip("/")
        ):
            raise ManualEpisodeError(
                "L'URL doit être une page d'émission Le Masque et la Plume : "
                f"https://www.radiofrance.fr{MASQUE_PAGE_PATH_PREFIX}…"
            )

    @staticmethod
    def _format_duration(seconds: int) -> str:
        minutes, secs = divmod(seconds, 60)
        return f"{minutes} min {secs:02d} s"

    @staticmethod
    def _iter_json_ld_items(soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Aplatit tous les objets des scripts JSON-LD de la page."""
        items: list[dict[str, Any]] = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except json.JSONDecodeError:
                continue
            candidates = data.get("@graph", [data]) if isinstance(data, dict) else []
            items.extend(item for item in candidates if isinstance(item, dict))
        return items

    @staticmethod
    def parse_radiofrance_episode_page(html: str) -> dict[str, Any]:
        """Extrait titre, description, date, durée et audio du JSON-LD.

        Raises:
            ManualEpisodeError: page sans `RadioEpisode` exploitable.
        """
        from .radiofrance_service import radiofrance_service

        soup = BeautifulSoup(html, "html.parser")
        episode = next(
            (
                item
                for item in ManualEpisodeService._iter_json_ld_items(soup)
                if item.get("@type") == "RadioEpisode"
            ),
            None,
        )
        if episode is None:
            raise ManualEpisodeError(
                "Page sans données RadioEpisode : ce n'est pas une page d'émission"
            )

        main_entity = episode.get("mainEntity") or {}
        audio_url = main_entity.get("contentUrl")
        if not audio_url:
            raise ManualEpisodeError("Aucune URL audio dans la page de l'émission")

        date_raw = episode.get("dateCreated")
        if not date_raw:
            raise ManualEpisodeError("Date de l'émission absente de la page")
        date = datetime.fromisoformat(str(date_raw).replace("Z", "+00:00"))

        duree = radiofrance_service._parse_iso_duration(
            str(main_entity.get("duration", ""))
        )
        if duree is None:
            raise ManualEpisodeError("Durée de l'émission absente de la page")

        return {
            "titre": str(episode.get("name", "")).strip(),
            "description": str(episode.get("description", "")).strip(),
            "date": date,
            "duree": duree,
            "audio_url": str(audio_url),
        }

    async def add_from_radiofrance_page(self, page_url: str) -> dict[str, Any]:
        """Ajoute l'émission décrite par la page radiofrance.fr.

        L'épisode n'est inséré qu'une fois l'audio complet sur le disque.
        """
        self._check_page_url(page_url)
        html = await self.fetch_page_html(page_url)
        parsed = self.parse_radiofrance_episode_page(html)

        if parsed["duree"] < MIN_FULL_EPISODE_SECONDS:
            raise ManualEpisodeError(
                f"Audio de {self._format_duration(parsed['duree'])} : c'est une "
                "séquence, pas une émission complète (30 min minimum)",
                status_code=422,
            )

        existing = self.mongodb_service.find_episode_on_same_day(parsed["date"])
        if existing is not None:
            raise ManualEpisodeError(
                f"Une émission existe déjà le {parsed['date']:%d/%m/%Y} : "
                f"« {existing.get('titre', '')} »",
                status_code=409,
            )

        try:
            audio_rel_filename = await self.rss_sync_service.download_audio(
                parsed["audio_url"], parsed["date"]
            )
        except (aiohttp.ClientError, TimeoutError) as e:
            raise ManualEpisodeError(
                f"Téléchargement de l'audio impossible ({type(e).__name__}) : "
                "relancer l'ajout",
                status_code=502,
            ) from e
        episode_id = self.mongodb_service.insert_episode(
            {
                "titre": parsed["titre"],
                "date": parsed["date"],
                "description": parsed["description"],
                "url": parsed["audio_url"],
                "audio_rel_filename": audio_rel_filename,
                "transcription": None,
                "type": "livres",
                "duree": parsed["duree"],
                "masked": False,
                "episode_page_url": page_url,
                "source": "radiofrance_page",
            }
        )
        logger.info(f"✅ Émission ajoutée depuis {page_url} : {parsed['titre']}")

        # Même suite qu'un épisode RSS déclenché par Automatisch : notification,
        # puis transcription PGX en mode « api » (réessai horaire si PGX dort).
        if self.notify is not None:
            await self.notify(
                "Nouvel épisode Le Masque et la Plume téléchargé — "
                f"{parsed['date']:%d/%m/%y}",
                parsed["titre"],
                prefix="Ajout manuel",
            )
        transcription_status = await self._start_transcription()

        return {
            "episode_id": episode_id,
            "titre": parsed["titre"],
            "date": parsed["date"].strftime("%Y-%m-%d"),
            "duree": parsed["duree"],
            "episode_page_url": page_url,
            "audio_rel_filename": audio_rel_filename,
            "transcription_status": transcription_status,
        }

    async def _start_transcription(self) -> str:
        """Lance la file de transcription PGX ; un échec n'annule pas l'ajout.

        Returns:
            "started", "already_running", "nothing_to_do" ou "error".
        """
        if self.transcription_runner is None:
            return "error"
        try:
            result = await self.transcription_runner.start_transcription(trigger="api")
            return str(result.get("status", "error"))
        except Exception as e:
            logger.error(f"Erreur lancement transcription PGX après ajout: {e}")
            return "error"


def _build_manual_episode_service() -> ManualEpisodeService:
    """Construit l'instance singleton du service (import différé anti-cycle)."""
    from ..settings import settings
    from ..utils.ntfy import send_ntfy_notification
    from ..utils.pgx_transcription_runner import pgx_transcription_runner
    from .mongodb_service import mongodb_service
    from .rss_sync_service import rss_sync_service

    async def notify(title: str, message: str, prefix: str) -> None:
        await send_ntfy_notification(
            settings.ntfy_server_url,
            settings.ntfy_topic,
            title,
            message,
            prefix=prefix,
        )

    return ManualEpisodeService(
        mongodb_service=mongodb_service,
        rss_sync_service=rss_sync_service,
        transcription_runner=pgx_transcription_runner,
        notify=notify,
    )


manual_episode_service = _build_manual_episode_service()
