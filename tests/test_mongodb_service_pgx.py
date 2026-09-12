"""Tests TDD pour les méthodes de persistance de l'historique PGX (Issue #309).

Un document par cycle complet de transcription (déclenchement → succès ou
abandon), sur le modèle de rss_download_logs (Issue #295) — voir
tests/test_mongodb_service_rss_sync.py::TestRssDownloadLogs.
"""

from datetime import datetime
from unittest.mock import MagicMock

from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


class TestPgxTranscriptionLogs:
    """CRUD pour la collection pgx_transcription_logs (Issue #309)."""

    def test_insert_pgx_transcription_log_returns_inserted_id(self):
        service = MongoDBService()
        service.pgx_transcription_logs_collection = MagicMock()
        service.pgx_transcription_logs_collection.insert_one.return_value.inserted_id = ObjectId(
            "686bf5e18380ee925ae5e318"  # pragma: allowlist secret
        )

        log_data = {"trigger": "manual", "status": "success", "episodes": []}
        result = service.insert_pgx_transcription_log(log_data)

        assert result == "686bf5e18380ee925ae5e318"  # pragma: allowlist secret
        service.pgx_transcription_logs_collection.insert_one.assert_called_once_with(
            log_data
        )

    def test_get_pgx_transcription_logs_sorted_desc(self):
        service = MongoDBService()
        service.pgx_transcription_logs_collection = MagicMock()
        logs = [
            {"_id": ObjectId(), "started_at": datetime(2026, 9, 6)},
            {"_id": ObjectId(), "started_at": datetime(2026, 9, 5)},
        ]
        service.pgx_transcription_logs_collection.find.return_value.sort.return_value.limit.return_value = iter(
            logs
        )

        result = service.get_pgx_transcription_logs(limit=50)

        assert len(result) == 2
        assert all(isinstance(log["_id"], str) for log in result)
        service.pgx_transcription_logs_collection.find.assert_called_once()

    def test_get_pgx_transcription_log_by_id_found(self):
        service = MongoDBService()
        service.pgx_transcription_logs_collection = MagicMock()
        oid = ObjectId("686bf5e18380ee925ae5e318")  # pragma: allowlist secret
        service.pgx_transcription_logs_collection.find_one.return_value = {
            "_id": oid,
            "trigger": "manual",
        }

        result = service.get_pgx_transcription_log_by_id(
            "686bf5e18380ee925ae5e318"  # pragma: allowlist secret
        )

        assert result is not None
        assert result["_id"] == "686bf5e18380ee925ae5e318"

    def test_get_pgx_transcription_log_by_id_not_found(self):
        service = MongoDBService()
        service.pgx_transcription_logs_collection = MagicMock()
        service.pgx_transcription_logs_collection.find_one.return_value = None

        result = service.get_pgx_transcription_log_by_id(
            "686bf5e18380ee925ae5e318"  # pragma: allowlist secret
        )

        assert result is None

    def test_update_pgx_transcription_log_sets_fields_by_id(self):
        """Issue #313 : un cycle qui entre en retry est persisté dès le
        début (statut intermédiaire), puis mis à jour au fil de l'eau —
        nécessite un update ciblé par _id, distinct de l'insert initial."""
        service = MongoDBService()
        service.pgx_transcription_logs_collection = MagicMock()
        log_id = "686bf5e18380ee925ae5e318"  # pragma: allowlist secret

        service.update_pgx_transcription_log(
            log_id, {"status": "pgx", "retry_attempts": [{"reachable": False}]}
        )

        service.pgx_transcription_logs_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(log_id)},
            {"$set": {"status": "pgx", "retry_attempts": [{"reachable": False}]}},
        )
