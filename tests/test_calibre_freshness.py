"""Fraîcheur Calibre et lecture de la copie servie (Issue #327).

Seam : l'API HTTP, au-dessus d'une vraie bibliothèque Calibre sur disque
(`tests/fixtures/calibre_library.py`). La date de modification de metadata.db
et son remplacement ne sont observables qu'avec un vrai fichier.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.services.calibre_service import CalibreService
from tests.fixtures.calibre_library import CalibreLibrary


SYNC_TIME = datetime(2026, 11, 7, 14, 0, 30, tzinfo=UTC)


def make_service(library: CalibreLibrary, tag: str | None = None) -> CalibreService:
    """CalibreService pointé sur la bibliothèque de test."""
    with patch("back_office_lmelp.services.calibre_service.settings") as settings:
        settings.calibre_library_path = str(library.path)
        settings.calibre_virtual_library_tag = tag
        return CalibreService()


@pytest.fixture
def library(tmp_path):
    return CalibreLibrary(tmp_path)


@pytest.fixture
def client():
    return TestClient(app)


def serve(service: CalibreService):
    """Branche le service sur l'app et sur le service de correspondance."""
    return patch.multiple(
        "back_office_lmelp.app",
        calibre_service=service,
    )


class TestCalibreStatusFreshness:
    def test_status_exposes_sync_date_and_latest_book_change(self, library, client):
        library.add_book("Ancien", "Auteur A", "2026-10-01 08:00:00+00:00")
        library.add_book("Hamnet", "Maggie O'Farrell", "2026-11-07 14:01:08+00:00")
        library.add_book("Moyen", "Auteur B", "2026-11-01 08:00:00+00:00")
        library.set_mtime(SYNC_TIME.timestamp())

        with serve(make_service(library)):
            data = client.get("/api/calibre/status").json()

        assert data["available"] is True
        assert datetime.fromisoformat(data["metadata_updated_at"]) == SYNC_TIME
        assert data["latest_book_change"]["title"] == "Hamnet"
        assert datetime.fromisoformat(
            data["latest_book_change"]["last_modified"]
        ) == datetime(2026, 11, 7, 14, 1, 8, tzinfo=UTC)

    def test_latest_book_change_respects_virtual_library(self, library, client):
        library.add_book("Le mien", "A", "2026-11-01 08:00:00+00:00", tags=["moi"])
        library.add_book("Pas le mien", "B", "2026-11-07 08:00:00+00:00")

        with serve(make_service(library, tag="moi")):
            data = client.get("/api/calibre/status").json()

        assert data["latest_book_change"]["title"] == "Le mien"

    def test_freshness_is_null_when_calibre_unavailable(self, client):
        with patch("back_office_lmelp.services.calibre_service.settings") as settings:
            settings.calibre_library_path = None
            service = CalibreService()

        with serve(service):
            data = client.get("/api/calibre/status").json()

        assert data["available"] is False
        assert data["metadata_updated_at"] is None
        assert data["latest_book_change"] is None


class TestMatchingCacheFollowsServedCopy:
    """La correspondance Calibre ↔ lmelp suit les changements de metadata.db."""

    @pytest.fixture
    def matching(self, library):
        from bson import ObjectId

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        auteur_id = str(ObjectId())
        mongo = MagicMock()
        # Formes renvoyées par MongoDBService.get_all_books/get_all_authors :
        # documents réels (vérifiés via MCP) avec les ObjectId convertis en str
        mongo.get_all_books.return_value = [
            {"_id": str(ObjectId()), "titre": "La Serpe", "auteur_id": auteur_id}
        ]
        mongo.get_all_authors.return_value = [
            {"_id": auteur_id, "nom": "Philippe Jaenada"}
        ]
        service = make_service(library)
        matching_service = CalibreMatchingService(service, mongo)
        with patch.multiple(
            "back_office_lmelp.app",
            calibre_service=service,
            calibre_matching_service=matching_service,
        ):
            yield

    def matched_titles(self, client):
        response = client.get("/api/calibre/matching").json()
        return [m["calibre_title"] for m in response["matches"]]

    def test_change_in_served_copy_is_visible_immediately(
        self, library, client, matching
    ):
        book_id = library.add_book("Titre provisoire", "Philippe Jaenada")
        library.set_mtime(SYNC_TIME.timestamp())
        assert self.matched_titles(client) == []

        library.rename_book(book_id, "La Serpe", "2026-11-07 15:00:00+00:00")
        library.set_mtime(SYNC_TIME.timestamp() + 60)

        assert self.matched_titles(client) == ["La Serpe"]

    def test_cache_is_kept_while_served_copy_is_unchanged(
        self, library, client, matching
    ):
        book_id = library.add_book("Titre provisoire", "Philippe Jaenada")
        library.set_mtime(SYNC_TIME.timestamp())
        assert self.matched_titles(client) == []

        library.rename_book(book_id, "La Serpe", "2026-11-07 15:00:00+00:00")
        library.set_mtime(SYNC_TIME.timestamp())  # même date : rien n'est arrivé

        assert self.matched_titles(client) == []


class TestReadRetryDuringReplacement:
    """Une lecture qui tombe pendant le remplacement de metadata.db est relancée."""

    @pytest.fixture
    def flaky_connect(self, tmp_path):
        """sqlite3.connect qui ouvre d'abord N fois un fichier illisible."""
        import sqlite3

        real_connect = sqlite3.connect
        garbage = tmp_path / "en-cours-de-remplacement.db"
        garbage.write_bytes(b"pas une base sqlite " * 100)

        def make(failures: int):
            calls = {"n": 0}

            def connect(database, *args, **kwargs):
                calls["n"] += 1
                if calls["n"] <= failures:
                    return real_connect(f"file:{garbage}?mode=ro", uri=True)
                return real_connect(database, *args, **kwargs)

            return patch(
                "back_office_lmelp.services.calibre_service.sqlite3.connect",
                side_effect=connect,
            )

        return make

    @pytest.fixture(autouse=True)
    def no_wait(self):
        with patch("back_office_lmelp.services.calibre_service.time.sleep"):
            yield

    def test_transient_failure_is_retried(self, library, client, flaky_connect):
        library.add_book("Hamnet", "Maggie O'Farrell")
        library.add_book("White", "Bret Easton Ellis")
        service = make_service(library)

        with serve(service), flaky_connect(failures=1):
            data = client.get("/api/calibre/status").json()

        assert data["total_books"] == 2

    def test_startup_during_replacement_keeps_calibre_available(
        self, library, flaky_connect
    ):
        library.add_book("Hamnet", "Maggie O'Farrell")

        with flaky_connect(failures=1):
            service = make_service(library)

        assert service.is_available() is True

    def test_persistent_failure_keeps_current_behaviour(
        self, library, client, flaky_connect
    ):
        library.add_book("Hamnet", "Maggie O'Farrell")
        service = make_service(library)

        with serve(service), flaky_connect(failures=1000):
            response = client.get("/api/calibre/status")

        assert response.status_code == 200
        assert response.json()["total_books"] is None
