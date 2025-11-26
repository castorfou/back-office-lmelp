"""Middleware de logging enrichi pour FastAPI (Issue #115).

Ce middleware remplace le logging uvicorn par défaut pour fournir un format
enrichi similaire à nginx, tout en filtrant les healthchecks.
"""

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Logger pour les requêtes HTTP (remplace uvicorn.access)
access_logger = logging.getLogger("back_office_lmelp.access")


class EnrichedLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware pour logger les requêtes avec un format enrichi."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Intercepte les requêtes pour logger avec format enrichi."""
        # Exclure /health du logging (healthchecks Docker)
        if request.url.path == "/health":
            return await call_next(request)

        # Mesurer le temps de traitement
        start_time = time.time()

        # Traiter la requête
        response: Response = await call_next(request)

        # Calculer la durée
        duration = time.time() - start_time

        # Extraire les informations de la requête
        method = request.method
        path = request.url.path
        status_code = response.status_code

        # Obtenir la taille de la réponse si disponible
        content_length = response.headers.get("content-length", "?")

        # Obtenir le User-Agent
        user_agent = request.headers.get("user-agent", "-")

        # Timestamp au format ISO 8601 avec timezone
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S%z")

        # Format de log enrichi (style nginx simplifié)
        # Format: timestamp "METHOD /path HTTP/1.1" status size duration "User-Agent"
        log_message = (
            f'{timestamp} "{method} {path} HTTP/1.1" '
            f'{status_code} {content_length} {duration:.3f}s "{user_agent}"'
        )

        # Logger selon le niveau approprié
        if status_code >= 500:
            access_logger.error(log_message)
        elif status_code >= 400:
            access_logger.warning(log_message)
        else:
            access_logger.info(log_message)

        return response
