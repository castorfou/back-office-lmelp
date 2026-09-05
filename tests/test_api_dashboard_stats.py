"""Tests TDD pour les endpoints agrégés du cache de statistiques dashboard (Issue #279)."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from back_office_lmelp.app import app


client = TestClient(app)


class TestDashboardStatsEndpoint:
    """Tests TDD pour GET /api/dashboard/stats."""

    def test_dashboard_stats_endpoint_should_aggregate_all_sources(self):
        """L'endpoint doit agréger les 6 sources en un seul payload JSON."""
        mock_statistics = {"totalEpisodes": 42}
        mock_collections_statistics = {
            "episodes_sans_emission": 3,
            "emissions_sans_avis": 1,
        }

        with (
            patch(
                "back_office_lmelp.app.get_statistics",
                new=AsyncMock(return_value=mock_statistics),
            ),
            patch("back_office_lmelp.app.stats_service") as mock_stats_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch("back_office_lmelp.app.duplicate_books_service") as mock_dup,
            patch("back_office_lmelp.app.orphaned_avis_service") as mock_orphaned,
            patch(
                "back_office_lmelp.app.dashboard_stats_cache_service"
            ) as mock_cache_service,
        ):
            mock_stats_service.get_cache_statistics.return_value = (
                mock_collections_statistics
            )
            mock_mongodb.episodes_collection = MagicMock()
            mock_mongodb.avis_critiques_collection = MagicMock()
            mock_mongodb.critiques_collection = MagicMock()
            mock_mongodb.avis_critiques_collection.distinct.return_value = []
            mock_mongodb.episodes_collection.find.return_value = []
            mock_dup.get_duplicate_statistics = AsyncMock(
                return_value={"total_duplicates": 2}
            )
            mock_dup.get_duplicate_authors_statistics = AsyncMock(
                return_value={"total_duplicates": 1}
            )
            mock_orphaned.get_orphaned_statistics = AsyncMock(
                return_value={"orphaned_count": 5}
            )
            # Pas de cache actif dans ce test : get_cached() retourne None, puis set_cache() est appelé
            mock_cache_service.get_cached.return_value = None

            response = client.get("/api/dashboard/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["statistics"] == mock_statistics
            assert data["collections_statistics"] == mock_collections_statistics
            assert data["critiques_manquants_count"] == 0
            assert data["duplicate_books_count"] == 2
            assert data["duplicate_authors_count"] == 1
            assert data["orphaned_avis_count"] == 5

    def test_dashboard_stats_endpoint_should_return_cached_value_without_recomputing(
        self,
    ):
        """Si le cache est valide, l'endpoint doit le retourner sans rien recalculer."""
        with (
            patch(
                "back_office_lmelp.app.dashboard_stats_cache_service"
            ) as mock_cache_service,
            patch(
                "back_office_lmelp.app.get_statistics", new=AsyncMock()
            ) as mock_get_statistics,
        ):
            mock_cache_service.get_cached.return_value = {"cached": True}

            response = client.get("/api/dashboard/stats")

            assert response.status_code == 200
            assert response.json() == {"cached": True}
            mock_get_statistics.assert_not_called()
            mock_cache_service.set_cache.assert_not_called()


class TestDashboardStatsCacheInvalidateEndpoint:
    """Tests TDD pour POST /api/dashboard/stats/cache/invalidate."""

    def test_invalidate_endpoint_should_call_invalidate_cache(self):
        """L'endpoint doit invalider le cache des stats dashboard."""
        with patch(
            "back_office_lmelp.app.dashboard_stats_cache_service"
        ) as mock_cache_service:
            response = client.post("/api/dashboard/stats/cache/invalidate")

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            mock_cache_service.invalidate_cache.assert_called_once()
