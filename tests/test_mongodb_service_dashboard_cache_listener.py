"""Tests TDD : mongodb_service.connect() doit enregistrer le listener d'invalidation du cache dashboard (Issue #279)."""

from unittest.mock import MagicMock, patch

from back_office_lmelp.services.dashboard_stats_invalidation_listener import (
    DashboardStatsInvalidationListener,
)
from back_office_lmelp.services.mongodb_service import MongoDBService


class TestMongoDBServiceDashboardCacheListener:
    """Tests TDD : le MongoClient doit être créé avec le listener d'invalidation."""

    def test_connect_should_register_dashboard_invalidation_listener(self):
        """connect() doit passer un DashboardStatsInvalidationListener en event_listeners."""
        with patch(
            "back_office_lmelp.services.mongodb_service.MongoClient"
        ) as mock_mongo_client_class:
            mock_client_instance = MagicMock()
            mock_mongo_client_class.return_value = mock_client_instance

            service = MongoDBService()
            service.connect()

            _, kwargs = mock_mongo_client_class.call_args
            listeners = kwargs.get("event_listeners", [])
            assert any(
                isinstance(listener, DashboardStatsInvalidationListener)
                for listener in listeners
            )
