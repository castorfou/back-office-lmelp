"""Tests TDD pour l'invalidation automatique du cache dashboard sur écriture MongoDB (Issue #279)."""

from unittest.mock import MagicMock

from back_office_lmelp.services.dashboard_stats_invalidation_listener import (
    DASHBOARD_WATCHED_COLLECTIONS,
    DashboardStatsInvalidationListener,
)


def _make_started_event(command_name: str, collection_name: str) -> MagicMock:
    """Simule un pymongo.monitoring.CommandStartedEvent."""
    event = MagicMock()
    event.command_name = command_name
    event.command = {command_name: collection_name}
    return event


class TestDashboardStatsInvalidationListener:
    """Tests TDD: le listener doit invalider le cache sur toute écriture pertinente."""

    def test_should_invalidate_on_insert_on_watched_collection(self):
        """Un insert sur une collection surveillée doit invalider le cache."""
        invalidate_fn = MagicMock()
        listener = DashboardStatsInvalidationListener(invalidate_fn)

        event = _make_started_event("insert", "livres")
        listener.started(event)

        invalidate_fn.assert_called_once()

    def test_should_invalidate_on_update_on_watched_collection(self):
        """Un update sur une collection surveillée doit invalider le cache."""
        invalidate_fn = MagicMock()
        listener = DashboardStatsInvalidationListener(invalidate_fn)

        event = _make_started_event("update", "avis_critiques")
        listener.started(event)

        invalidate_fn.assert_called_once()

    def test_should_invalidate_on_delete_on_watched_collection(self):
        """Un delete sur une collection surveillée doit invalider le cache."""
        invalidate_fn = MagicMock()
        listener = DashboardStatsInvalidationListener(invalidate_fn)

        event = _make_started_event("delete", "critiques")
        listener.started(event)

        invalidate_fn.assert_called_once()

    def test_should_invalidate_on_find_and_modify_on_watched_collection(self):
        """Un findAndModify sur une collection surveillée doit invalider le cache."""
        invalidate_fn = MagicMock()
        listener = DashboardStatsInvalidationListener(invalidate_fn)

        event = _make_started_event("findAndModify", "emissions")
        listener.started(event)

        invalidate_fn.assert_called_once()

    def test_should_not_invalidate_on_read_command(self):
        """Une commande de lecture (find) ne doit pas invalider le cache."""
        invalidate_fn = MagicMock()
        listener = DashboardStatsInvalidationListener(invalidate_fn)

        event = _make_started_event("find", "livres")
        listener.started(event)

        invalidate_fn.assert_not_called()

    def test_should_not_invalidate_on_write_to_unwatched_collection(self):
        """Une écriture sur une collection non surveillée ne doit pas invalider le cache."""
        invalidate_fn = MagicMock()
        listener = DashboardStatsInvalidationListener(invalidate_fn)

        event = _make_started_event("insert", "some_unrelated_collection")
        listener.started(event)

        invalidate_fn.assert_not_called()

    def test_watched_collections_should_cover_issue_scope(self):
        """Les collections surveillées doivent couvrir les points cités dans l'issue #279."""
        expected = {
            "livres",
            "auteurs",
            "avis_critiques",
            "critiques",
            "emissions",
            "avis",
            "livresauteurs_cache",
            "episodes",
        }
        assert expected.issubset(DASHBOARD_WATCHED_COLLECTIONS)

    def test_failed_event_should_not_raise(self):
        """failed() doit exister et ne rien faire (pas d'invalidation sur échec)."""
        invalidate_fn = MagicMock()
        listener = DashboardStatsInvalidationListener(invalidate_fn)

        listener.failed(MagicMock())

        invalidate_fn.assert_not_called()

    def test_succeeded_event_should_not_raise(self):
        """succeeded() doit exister et ne rien faire (invalidation déjà faite dans started)."""
        invalidate_fn = MagicMock()
        listener = DashboardStatsInvalidationListener(invalidate_fn)

        listener.succeeded(MagicMock())

        invalidate_fn.assert_not_called()
