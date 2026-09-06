"""Tests TDD pour les méthodes RSS sync du MongoDBService (Issue #295).

Types réels vérifiés via mcp__MongoDB__collection-schema +
mcp__MongoDB__find (masque_et_la_plume.episodes) : date est un vrai
datetime (pas une string), titre est une string.
"""

from datetime import datetime
from unittest.mock import MagicMock

from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


class TestFindEpisodeByTitreAndDate:
    """Dédup niveau 2 (Issue #295)."""

    def test_returns_episode_when_found(self):
        service = MongoDBService()
        service.episodes_collection = MagicMock()
        expected = {
            "_id": ObjectId("686bf5e18380ee925ae5e318"),  # pragma: allowlist secret
            "titre": "Titre existant",
            "date": datetime(2026, 8, 23, 10, 10, 50),
        }
        service.episodes_collection.find_one.return_value = expected

        result = service.find_episode_by_titre_and_date(
            "Titre existant", datetime(2026, 8, 23, 10, 10, 50)
        )

        assert result == expected
        service.episodes_collection.find_one.assert_called_once_with(
            {"titre": "Titre existant", "date": datetime(2026, 8, 23, 10, 10, 50)}
        )

    def test_returns_none_when_not_found(self):
        service = MongoDBService()
        service.episodes_collection = MagicMock()
        service.episodes_collection.find_one.return_value = None

        result = service.find_episode_by_titre_and_date(
            "Titre inconnu", datetime(2026, 9, 6)
        )

        assert result is None


class TestGetLastEpisodeDate:
    """Dédup niveau 1 (Issue #295)."""

    def test_returns_date_of_most_recent_episode(self):
        service = MongoDBService()
        service.episodes_collection = MagicMock()
        service.episodes_collection.find_one.return_value = {
            "date": datetime(2026, 8, 23, 10, 10, 50)
        }

        result = service.get_last_episode_date()

        assert result == datetime(2026, 8, 23, 10, 10, 50)

    def test_returns_none_when_no_episode(self):
        service = MongoDBService()
        service.episodes_collection = MagicMock()
        service.episodes_collection.find_one.return_value = None

        result = service.get_last_episode_date()

        assert result is None


class TestGetLastProcessedEpisodeDate:
    """Dédup niveau 1 étendue (Issue #295 - bug notif dupliquée épisode non-livres).

    Un épisode non-livres (skipped_not_book) n'est jamais inséré dans
    `episodes`, donc `get_last_episode_date()` ne le voit jamais comme
    "dernier connu" — il resterait indéfiniment un candidat re-classifié
    et re-notifié à chaque run tant qu'aucun nouvel épisode livres n'est
    inséré après lui. Cette méthode cherche la date max parmi les
    épisodes "skipped_not_book" (jamais insérés) dans rss_download_logs,
    pour ne plus jamais les retraiter.

    CRITIQUE : ne doit PAS considérer les épisodes "downloaded" — sinon un
    épisode livres inséré puis supprimé manuellement de `episodes` (test
    manuel, correction d'erreur) ne serait plus jamais retéléchargé, alors
    que `get_last_episode_date()` (qui, lui, consulte `episodes` en temps
    réel) le considérerait à nouveau comme absent.
    """

    def test_returns_max_date_across_skipped_not_book_episodes_only(self):
        service = MongoDBService()
        service.rss_download_logs_collection = MagicMock()
        service.rss_download_logs_collection.aggregate.return_value = iter(
            [{"_id": None, "max_date": datetime(2026, 8, 30, 10, 12, 40)}]
        )

        result = service.get_last_processed_episode_date()

        assert result == datetime(2026, 8, 30, 10, 12, 40)
        pipeline = service.rss_download_logs_collection.aggregate.call_args[0][0]
        match_stage = next(stage for stage in pipeline if "$match" in stage)
        assert match_stage["$match"] == {"episodes.outcome": "skipped_not_book"}

    def test_returns_none_when_no_logs(self):
        service = MongoDBService()
        service.rss_download_logs_collection = MagicMock()
        service.rss_download_logs_collection.aggregate.return_value = iter([])

        result = service.get_last_processed_episode_date()

        assert result is None


class TestRssDownloadLogs:
    """CRUD pour la collection rss_download_logs (Issue #295)."""

    def test_insert_rss_download_log_returns_inserted_id(self):
        service = MongoDBService()
        service.rss_download_logs_collection = MagicMock()
        service.rss_download_logs_collection.insert_one.return_value.inserted_id = (
            ObjectId("686bf5e18380ee925ae5e318")  # pragma: allowlist secret
        )

        log_data = {"trigger": "manual", "status": "success", "episodes": []}
        result = service.insert_rss_download_log(log_data)

        assert result == "686bf5e18380ee925ae5e318"  # pragma: allowlist secret
        service.rss_download_logs_collection.insert_one.assert_called_once_with(
            log_data
        )

    def test_get_rss_download_logs_sorted_desc(self):
        service = MongoDBService()
        service.rss_download_logs_collection = MagicMock()
        logs = [
            {"_id": ObjectId(), "started_at": datetime(2026, 9, 6)},
            {"_id": ObjectId(), "started_at": datetime(2026, 9, 5)},
        ]
        service.rss_download_logs_collection.find.return_value.sort.return_value.limit.return_value = iter(
            logs
        )

        result = service.get_rss_download_logs(limit=50)

        assert len(result) == 2
        assert all(isinstance(log["_id"], str) for log in result)
        service.rss_download_logs_collection.find.assert_called_once()

    def test_get_rss_download_log_by_id_found(self):
        service = MongoDBService()
        service.rss_download_logs_collection = MagicMock()
        oid = ObjectId("686bf5e18380ee925ae5e318")  # pragma: allowlist secret
        service.rss_download_logs_collection.find_one.return_value = {
            "_id": oid,
            "trigger": "manual",
        }

        result = service.get_rss_download_log_by_id("686bf5e18380ee925ae5e318")

        assert result is not None
        assert result["_id"] == "686bf5e18380ee925ae5e318"

    def test_get_rss_download_log_by_id_not_found(self):
        service = MongoDBService()
        service.rss_download_logs_collection = MagicMock()
        service.rss_download_logs_collection.find_one.return_value = None

        result = service.get_rss_download_log_by_id(
            "686bf5e18380ee925ae5e318"  # pragma: allowlist secret
        )

        assert result is None
