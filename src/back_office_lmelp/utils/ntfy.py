"""Helper générique de notification ntfy.sh (Issue #309).

Extraction du pattern introduit par RssSyncService.send_ntfy_notification
(Issue #295) vers une fonction standalone, réutilisable par tout service
(ici la transcription PGX) sans dupliquer la logique HTTP. Le comportement
de RssSyncService lui-même n'est pas modifié par cette extraction.
"""

import logging

import aiohttp


logger = logging.getLogger(__name__)


async def send_ntfy_notification(
    server_url: str | None,
    topic: str | None,
    title: str,
    message: str,
    tags: list[str] | None = None,
) -> None:
    """Envoie une notification ntfy.sh (no-op si server_url/topic absent)."""
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
        logger.warning(f"⚠️ Erreur envoi notification ntfy.sh: {type(e).__name__}: {e}")
