"""Service de synchronisation RSS Le Masque et la Plume (Issue #295).

Récupère le flux RSS France Inter, filtre les épisodes "livres" de plus de
15 minutes non encore connus, télécharge l'audio, insère en MongoDB et
journalise chaque opération dans rss_download_logs.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import aiohttp
import feedparser
import openai


if TYPE_CHECKING:
    from .mongodb_service import MongoDBService

logger = logging.getLogger(__name__)

RSS_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S %z"
AUDIO_LINK_TYPES = {"audio/mpeg", "audio/x-m4a", "audio/mp4", "audio/aac"}


class RssSyncService:
    """Service pour synchroniser les épisodes du flux RSS Le Masque et la Plume."""

    def __init__(self, mongodb_service: MongoDBService, settings: Any = None) -> None:
        """Initialise le service de synchronisation RSS."""
        self.mongodb_service = mongodb_service

        if settings is None:
            from ..settings import settings as app_settings

            settings = app_settings
        self.settings = settings

        self._debug_log_enabled = self.settings.rss_debug_log

        self.azure_endpoint = os.getenv("AZURE_ENDPOINT")
        self.api_key = os.getenv("AZURE_API_KEY")
        self.api_version = os.getenv("AZURE_API_VERSION", "2024-09-01-preview")
        self.deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")

        self.client: openai.AzureOpenAI | None = None
        if self.azure_endpoint and self.api_key:
            try:
                self.client = openai.AzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.azure_endpoint,
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Erreur initialisation Azure OpenAI client (RssSyncService): "
                    f"{type(e).__name__}: {e}"
                )
                self.client = None

    async def fetch_feed_entries(self) -> list[dict[str, Any]]:
        """Télécharge et parse le flux RSS, retourne la liste brute d'entries."""
        feed_url = self.settings.rss_masque_et_la_plume_url
        parsed = await asyncio.to_thread(feedparser.parse, feed_url)
        return list(parsed.entries)

    @staticmethod
    def get_duree_in_seconds(duree: str) -> int:
        """Convertit une durée iTunes RSS (HH:MM:SS | MM:SS | SS) en secondes."""
        parts = duree.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(parts[0])

    def filter_new_candidate_entries(
        self,
        entries: list[dict[str, Any]],
        last_known_date: datetime | None,
        duree_mini_minutes: int | None = None,
    ) -> list[dict[str, Any]]:
        """Garde les entries publiées après last_known_date et durant >= seuil."""
        if duree_mini_minutes is None:
            duree_mini_minutes = self.settings.rss_duree_mini_minutes
        seuil_secondes = duree_mini_minutes * 60

        candidates = []
        for entry in entries:
            published = entry.get("published")
            if not published:
                continue
            entry_date = datetime.strptime(published, RSS_DATE_FORMAT)
            if last_known_date is not None:
                if last_known_date.tzinfo is None:
                    last_known_date = last_known_date.replace(tzinfo=UTC)
                if entry_date <= last_known_date:
                    continue

            itunes_duration = entry.get("itunes_duration")
            if not itunes_duration:
                continue
            duree_secondes = self.get_duree_in_seconds(itunes_duration)
            if duree_secondes < seuil_secondes:
                continue

            candidates.append(entry)
        return candidates

    @staticmethod
    def _format_episode_date(episode_date: datetime) -> str:
        """Formate la date d'un épisode pour affichage (dd/mm/yy)."""
        return episode_date.strftime("%d/%m/%y")

    @staticmethod
    def _extract_audio_url(entry: dict[str, Any]) -> str | None:
        """Extrait l'URL du fichier audio depuis les liens de l'entry RSS."""
        for link in entry.get("links", []):
            if link.get("type") in AUDIO_LINK_TYPES:
                href = link.get("href")
                return str(href) if href is not None else None
        return None

    async def classify_episode_type(self, titre: str, description: str) -> str:
        """Classifie un épisode en 'livres' | 'films' | 'théâtre' | 'inconnu'."""
        if not self.client:
            logger.warning(
                "⚠️ Client OpenAI non configuré, classification RSS impossible"
            )
            return "inconnu"

        prompt = f"""Tu classifies une émission "Le Masque et la Plume" de France Inter en trois catégories possibles: "livres", "films", "théâtre".
Réponds UNIQUEMENT avec un JSON: {{"type": "livres" | "films" | "théâtre"}}

Titre: {titre}
Description: {description}"""

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: self.client.chat.completions.create(  # type: ignore[union-attr]
                        model=self.deployment_name,
                        messages=[
                            {
                                "role": "system",
                                "content": "Tu es un assistant qui classifie des émissions. Tu réponds UNIQUEMENT en JSON valide.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=50,
                        temperature=0.1,
                    )
                ),
                timeout=30,
            )
            content = response.choices[0].message.content or ""
            content = content.strip()
            content = re.sub(r"```json\s*", "", content)
            content = re.sub(r"```\s*$", "", content)
            data = json.loads(content)
            episode_type = data.get("type")
            if episode_type not in ("livres", "films", "théâtre"):
                return "inconnu"
            return str(episode_type)
        except Exception as e:
            logger.warning(f"⚠️ Erreur classification LLM RSS: {type(e).__name__}: {e}")
            return "inconnu"

    async def download_audio(self, audio_url: str, episode_date: datetime) -> str:
        """Télécharge l'audio et retourne le audio_rel_filename."""
        year = str(episode_date.year)
        basename = os.path.basename(audio_url)
        audio_rel_filename = f"{year}/{basename}"

        base_dir = self.settings.audio_storage_path
        full_dir = os.path.join(base_dir, year)
        os.makedirs(full_dir, exist_ok=True)
        full_filename = os.path.join(full_dir, basename)

        if os.path.exists(full_filename):
            return audio_rel_filename

        timeout = aiohttp.ClientTimeout(total=60)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.get(audio_url) as response,
        ):
            content = await response.read()
        with open(full_filename, "wb") as f:
            f.write(content)

        return audio_rel_filename

    async def send_ntfy_notification(
        self, title: str, message: str, tags: list[str] | None = None
    ) -> None:
        """Envoie une notification ntfy.sh (no-op si non configuré)."""
        server_url = self.settings.ntfy_server_url
        topic = self.settings.ntfy_topic
        if not server_url or not topic:
            return

        url = f"{server_url.rstrip('/')}/{topic}"
        headers = {"Title": title}
        if tags:
            headers["Tags"] = ",".join(tags)

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with (
                aiohttp.ClientSession(timeout=timeout) as session,
                session.post(url, data=message.encode("utf-8"), headers=headers),
            ):
                pass
        except Exception as e:
            logger.warning(
                f"⚠️ Erreur envoi notification ntfy.sh: {type(e).__name__}: {e}"
            )

    def build_episode_document(
        self,
        entry: dict[str, Any],
        episode_type: str,
        audio_rel_filename: str,
        audio_url: str,
        entry_date: datetime,
        duree: int,
    ) -> dict[str, Any]:
        """Construit le document épisode à insérer en MongoDB."""
        return {
            "titre": entry.get("title", ""),
            "date": entry_date,
            "description": entry.get("summary", ""),
            "url": audio_url,
            "audio_rel_filename": audio_rel_filename,
            "transcription": None,
            "type": episode_type,
            "duree": duree,
            "masked": False,
        }

    async def sync(self, trigger: str = "api") -> dict[str, Any]:
        """Orchestre la synchronisation complète du flux RSS."""
        started_at = datetime.now(UTC)
        feed_url = self.settings.rss_masque_et_la_plume_url
        episodes_log: list[dict[str, Any]] = []

        try:
            entries = await self.fetch_feed_entries()
            # Dédup niveau 1 : ne jamais retraiter un épisode déjà VU, même
            # non-livres. get_last_episode_date() ne voit que les épisodes
            # réellement insérés dans `episodes` (donc jamais les
            # "skipped_not_book") — on retient la date la plus récente entre
            # le dernier épisode inséré et le dernier épisode traité (tous
            # outcomes confondus, via rss_download_logs).
            last_inserted_date = self.mongodb_service.get_last_episode_date()
            last_processed_date = self.mongodb_service.get_last_processed_episode_date()
            candidate_dates = [
                d for d in (last_inserted_date, last_processed_date) if d is not None
            ]
            last_known_date = max(candidate_dates) if candidate_dates else None
            candidates = self.filter_new_candidate_entries(entries, last_known_date)

            for entry in candidates:
                titre = entry.get("title", "")
                entry_date = datetime.strptime(entry["published"], RSS_DATE_FORMAT)
                duree = self.get_duree_in_seconds(entry["itunes_duration"])
                description = entry.get("summary", "")
                audio_url = self._extract_audio_url(entry)

                episode_log: dict[str, Any] = {
                    "titre": titre,
                    "date": entry_date,
                    "duree": duree,
                    "outcome": "error",
                    "episode_id": None,
                    "audio_downloaded": False,
                    "error_message": None,
                }

                try:
                    if self.mongodb_service.find_episode_by_titre_and_date(
                        titre, entry_date
                    ):
                        episode_log["outcome"] = "already_exists"
                        episodes_log.append(episode_log)
                        continue

                    episode_type = await self.classify_episode_type(titre, description)

                    if episode_type != "livres":
                        episode_log["outcome"] = "skipped_not_book"
                        episodes_log.append(episode_log)
                        episode_date_str = self._format_episode_date(entry_date)
                        await self.send_ntfy_notification(
                            f"Épisode Le Masque et la Plume détecté (non retenu) — {episode_date_str}",
                            f"{titre} — type détecté: {episode_type}, non téléchargé.",
                        )
                        continue

                    if audio_url is None:
                        episode_log["outcome"] = "error"
                        episode_log["error_message"] = (
                            "Aucune URL audio trouvée dans le flux RSS"
                        )
                        episodes_log.append(episode_log)
                        continue

                    audio_rel_filename = await self.download_audio(
                        audio_url, entry_date
                    )
                    episode_doc = self.build_episode_document(
                        entry,
                        episode_type,
                        audio_rel_filename,
                        audio_url,
                        entry_date,
                        duree,
                    )
                    episode_id = self.mongodb_service.insert_episode(episode_doc)

                    episode_log["outcome"] = "downloaded"
                    episode_log["episode_id"] = str(episode_id)
                    episode_log["audio_downloaded"] = True
                    episodes_log.append(episode_log)

                    episode_date_str = self._format_episode_date(entry_date)
                    await self.send_ntfy_notification(
                        f"Nouvel épisode Le Masque et la Plume téléchargé — {episode_date_str}",
                        titre,
                    )
                except Exception as e:
                    episode_log["outcome"] = "error"
                    episode_log["error_message"] = str(e)
                    episodes_log.append(episode_log)

            status = "success"
            if any(e["outcome"] == "error" for e in episodes_log):
                status = "partial_error"

            result: dict[str, Any] = {
                "started_at": started_at,
                "finished_at": datetime.now(UTC),
                "trigger": trigger,
                "status": status,
                "feed_url": feed_url,
                "episodes": episodes_log,
                "notification_sent": any(
                    e["outcome"] in ("downloaded", "skipped_not_book")
                    for e in episodes_log
                ),
                "error_message": None,
            }
        except Exception as e:
            result = {
                "started_at": started_at,
                "finished_at": datetime.now(UTC),
                "trigger": trigger,
                "status": "error",
                "feed_url": feed_url,
                "episodes": episodes_log,
                "notification_sent": False,
                "error_message": str(e),
            }

        # Copie défensive : pymongo insert_one() mute le dict passé en
        # argument en y injectant un _id (ObjectId), non JSON-sérialisable.
        # Le dict retourné à l'appelant (endpoint FastAPI) ne doit jamais
        # porter cette mutation.
        self.mongodb_service.insert_rss_download_log(dict(result))
        return result


def _build_rss_sync_service() -> RssSyncService:
    """Construit l'instance singleton du service (import différé anti-cycle)."""
    from .mongodb_service import mongodb_service

    return RssSyncService(mongodb_service=mongodb_service)


rss_sync_service = _build_rss_sync_service()
