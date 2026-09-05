"""Invalidation automatique du cache dashboard sur écriture MongoDB (Issue #279).

Il n'existe pas de couche d'abstraction d'écriture commune dans le backend :
les collections pymongo sont accédées directement depuis app.py et plusieurs
services (~59 points d'écriture dispersés). Le seul point de centralisation
technique disponible est un `pymongo.monitoring.CommandListener`, enregistré
une seule fois sur le `MongoClient` : il intercepte toute commande, quelle
que soit la façon dont le code applicatif a récupéré la collection.
"""

import logging
from collections.abc import Callable
from typing import Any

from pymongo import monitoring


logger = logging.getLogger(__name__)

# Collections dont une écriture doit invalider le cache des stats dashboard
# (Issue #279 : génération avis critiques, extraction livres/auteurs,
# identification des critiques, liaison Babelio, page Emissions).
DASHBOARD_WATCHED_COLLECTIONS = frozenset(
    {
        "livres",
        "auteurs",
        "avis_critiques",
        "critiques",
        "emissions",
        "avis",
        "livresauteurs_cache",
        "episodes",
    }
)

# Noms de commande MongoDB considérés comme des écritures.
_WRITE_COMMAND_NAMES = frozenset(
    {"insert", "update", "delete", "findAndModify", "bulkWrite"}
)


class DashboardStatsInvalidationListener(monitoring.CommandListener):  # type: ignore[misc]
    """Invalide le cache dashboard sur toute écriture d'une collection surveillée."""

    def __init__(self, invalidate_fn: Callable[[], None]) -> None:
        self._invalidate_fn = invalidate_fn

    def started(self, event: Any) -> None:
        if event.command_name not in _WRITE_COMMAND_NAMES:
            return

        collection_name = event.command.get(event.command_name)
        if collection_name not in DASHBOARD_WATCHED_COLLECTIONS:
            return

        logger.debug(
            "Invalidation cache dashboard suite à %s sur %s",
            event.command_name,
            collection_name,
        )
        self._invalidate_fn()

    def succeeded(self, event: Any) -> None:
        """Pas d'action : l'invalidation est faite dans started()."""

    def failed(self, event: Any) -> None:
        """Pas d'action : l'invalidation est faite dans started()."""
