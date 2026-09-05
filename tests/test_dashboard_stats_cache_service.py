"""Tests TDD pour le cache TTL des statistiques du dashboard (Issue #279)."""

from unittest.mock import MagicMock

from back_office_lmelp.services.dashboard_stats_cache_service import (
    DashboardStatsCacheService,
)


class TestDashboardStatsCacheServiceGetStats:
    """Tests TDD: get_stats() doit mettre en cache le résultat de compute_fn."""

    def test_get_stats_should_call_compute_fn_only_once_within_ttl(self):
        """Deux appels rapprochés à get_stats() ne doivent recalculer qu'une fois."""
        # Arrange
        compute_fn = MagicMock(return_value={"foo": "bar"})
        service = DashboardStatsCacheService(ttl_seconds=300)

        # Act
        first_result = service.get_stats(compute_fn)
        second_result = service.get_stats(compute_fn)

        # Assert
        assert first_result == {"foo": "bar"}
        assert second_result == {"foo": "bar"}
        compute_fn.assert_called_once()

    def test_get_stats_should_recompute_after_ttl_expires(self):
        """Après expiration du TTL, get_stats() doit recalculer."""
        # Arrange
        compute_fn = MagicMock(
            side_effect=[{"value": 1}, {"value": 2}],
        )
        service = DashboardStatsCacheService(ttl_seconds=0)

        # Act
        first_result = service.get_stats(compute_fn)
        second_result = service.get_stats(compute_fn)

        # Assert
        assert first_result == {"value": 1}
        assert second_result == {"value": 2}
        assert compute_fn.call_count == 2

    def test_get_stats_should_recompute_after_invalidate_cache(self):
        """Après invalidate_cache(), get_stats() doit recalculer même dans le TTL."""
        # Arrange
        compute_fn = MagicMock(
            side_effect=[{"value": 1}, {"value": 2}],
        )
        service = DashboardStatsCacheService(ttl_seconds=300)

        # Act
        first_result = service.get_stats(compute_fn)
        service.invalidate_cache()
        second_result = service.get_stats(compute_fn)

        # Assert
        assert first_result == {"value": 1}
        assert second_result == {"value": 2}
        assert compute_fn.call_count == 2


class TestDashboardStatsCacheServiceGetCachedSetCache:
    """Tests TDD: get_cached()/set_cache() pour usage async (endpoint FastAPI)."""

    def test_get_cached_should_return_none_when_no_cache(self):
        """get_cached() doit retourner None si aucune valeur n'a été mise en cache."""
        service = DashboardStatsCacheService(ttl_seconds=300)

        assert service.get_cached() is None

    def test_get_cached_should_return_value_set_by_set_cache(self):
        """get_cached() doit retourner la valeur posée par set_cache() dans le TTL."""
        service = DashboardStatsCacheService(ttl_seconds=300)

        service.set_cache({"foo": "bar"})

        assert service.get_cached() == {"foo": "bar"}

    def test_get_cached_should_return_none_after_ttl_expires(self):
        """get_cached() doit retourner None une fois le TTL expiré."""
        service = DashboardStatsCacheService(ttl_seconds=0)

        service.set_cache({"foo": "bar"})

        assert service.get_cached() is None

    def test_get_cached_should_return_none_after_invalidate_cache(self):
        """get_cached() doit retourner None après invalidate_cache()."""
        service = DashboardStatsCacheService(ttl_seconds=300)

        service.set_cache({"foo": "bar"})
        service.invalidate_cache()

        assert service.get_cached() is None


class TestDashboardStatsCacheServiceDefaults:
    """Tests TDD: valeurs par défaut du service."""

    def test_default_ttl_should_be_300_seconds(self):
        """Le TTL par défaut doit être de 300 secondes (5 minutes), documenté dans l'issue #279."""
        service = DashboardStatsCacheService()

        assert service.ttl_seconds == 300
