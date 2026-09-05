"""Cache TTL in-memory pour les statistiques du dashboard (Issue #279).

Pattern repris de `CalibreMatchingService._get_data()` (Issue #199) : un dict
en mémoire avec un timestamp, invalidé soit par expiration du TTL, soit
explicitement via `invalidate_cache()`.
"""

import logging
import time
from collections.abc import Callable
from typing import Any


logger = logging.getLogger(__name__)


class DashboardStatsCacheService:
    """Cache en mémoire pour les statistiques agrégées du dashboard."""

    def __init__(self, ttl_seconds: float = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, Any] | None = None
        self._cache_timestamp: float = 0

    def get_stats(self, compute_fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        """Retourne les stats en cache si valides, sinon recalcule via compute_fn."""
        cached = self.get_cached()
        if cached is not None:
            return cached

        result = compute_fn()
        self.set_cache(result)
        return result

    def get_cached(self) -> dict[str, Any] | None:
        """Retourne la valeur en cache si elle est encore valide (TTL), sinon None.

        Utilisé par les appelants async (le calcul ne peut pas être passé comme
        `compute_fn` synchrone à `get_stats()`) : lire le cache, et si absent,
        calculer côté appelant puis `set_cache()` le résultat.
        """
        now = time.time()
        if self._cache is not None and (now - self._cache_timestamp) < self.ttl_seconds:
            return self._cache
        return None

    def set_cache(self, value: dict[str, Any]) -> None:
        """Pose une valeur en cache avec un nouveau timestamp."""
        self._cache = value
        self._cache_timestamp = time.time()

    def invalidate_cache(self) -> None:
        """Invalide le cache des statistiques dashboard."""
        self._cache = None
        self._cache_timestamp = 0


dashboard_stats_cache_service = DashboardStatsCacheService()
