"""Liste des livres Calibre lue par lot, sans bloquer le backend (Issue #328).

Tests sur une vraie bibliothèque Calibre (`tests/fixtures/calibre_library.py`) :
le nombre de requêtes SQLite et les valeurs relues ne s'observent qu'avec un
vrai fichier, pas avec un `sqlite3.connect` mocké.
"""

import inspect
import sqlite3
from unittest.mock import patch

import pytest

from back_office_lmelp import app as app_module
from back_office_lmelp.services.calibre_service import CalibreService
from tests.fixtures.calibre_library import CalibreLibrary


def make_service(library: CalibreLibrary) -> CalibreService:
    """CalibreService pointé sur la bibliothèque de test."""
    with patch("back_office_lmelp.services.calibre_service.settings") as settings:
        settings.calibre_library_path = str(library.path)
        settings.calibre_virtual_library_tag = None
        return CalibreService()


def count_queries(service: CalibreService) -> list[str]:
    """Enregistre les requêtes SQL de chaque connexion ouverte par le service."""
    queries: list[str] = []
    open_connection = service._open_connection

    def traced() -> sqlite3.Connection:
        conn = open_connection()
        conn.set_trace_callback(queries.append)
        return conn

    service._open_connection = traced  # type: ignore[method-assign]
    return queries


@pytest.fixture
def library(tmp_path):
    return CalibreLibrary(tmp_path)


@pytest.fixture
def detailed_library(library):
    """Deux livres complets et un livre nu."""
    full = library.add_book("Le Silence de la mer", "Vercors", tags=["roman", "lmelp"])
    library.add_details(
        full,
        coauthors=["Jean Bruller"],
        publisher="Minuit",
        series="Classiques",
        rating=8,
        isbn="978-2-7073-0001-2",
        comment="<p>Résumé</p>",
        languages=["fra", "eng"],
        paper=True,
        personal_comment="Relu en 2026",
        ko_progress=0.5062,
        ko_status="reading",
        ko_start="2026-08-23 18:55:06.101000+00:00",
        ko_finish="2026-09-01 10:00:00+00:00",
    )
    library.add_book("Bare", "Anonyme")
    second = library.add_book("Vol de nuit", "Saint-Exupéry", read=True)
    library.add_details(second, publisher="Gallimard", ko_status="finished")
    return library, full, second


class TestBooksAreReadInBatch:
    def test_query_count_does_not_grow_with_the_number_of_books(self, library):
        for i in range(60):
            library.add_book(f"Livre {i}", f"Auteur {i}", tags=["lmelp"])
        service = make_service(library)

        queries = count_queries(service)
        result = service.get_books(limit=100)

        assert len(result.books) == 60
        # ≈ 16 requêtes par livre avant le lot (Issue #328) : 60 livres → ~960
        assert len(queries) < 40

    def test_books_spread_over_several_chunks_keep_their_values(self, library):
        """Au-delà de BATCH_SIZE ids, les requêtes IN sont découpées en paquets."""
        ids = {
            library.add_book(f"Livre {i}", f"Auteur {i}", tags=[f"tag{i}"]): i
            for i in range(20)
        }
        service = make_service(library)

        with patch("back_office_lmelp.services.calibre_service.BATCH_SIZE", 7):
            books = service.get_books(limit=100).books

        assert len(books) == 20
        for book in books:
            i = ids[book.id]
            assert book.authors == [f"Auteur {i}"]
            assert book.tags == [f"tag{i}"]


class TestBatchKeepsBookValues:
    @pytest.mark.parametrize("read_with", ["get_books", "get_book"])
    def test_full_book_values(self, detailed_library, read_with):
        """Toutes les métadonnées, ISBN lu dans `identifiers` (pas de colonne
        `books.isbn` dans Calibre récent, comme dans la fixture)."""
        library, full_id, _ = detailed_library
        service = make_service(library)

        if read_with == "get_books":
            book = {b.id: b for b in service.get_books(limit=100).books}[full_id]
        else:
            found = service.get_book(full_id)
            assert found is not None
            book = found

        assert book.title == "Le Silence de la mer"
        assert book.authors == ["Vercors", "Jean Bruller"]
        assert book.tags == ["lmelp", "roman"]
        assert book.publisher == "Minuit"
        assert book.series == "Classiques"
        assert book.rating == 8
        assert book.isbn == "978-2-7073-0001-2"
        assert book.comments == "<p>Résumé</p>"
        assert book.languages == ["fra", "eng"]  # ordre Calibre (item_order)
        assert book.read is None
        assert book.paper is True
        assert book.personal_comments == "Relu en 2026"
        assert book.ko_progress == 0.5062
        assert book.ko_status == "reading"
        assert book.ko_date_started == "2026-08-23 18:55:06.101000+00:00"
        assert book.ko_date_finished == "2026-09-01 10:00:00+00:00"

    def test_values_are_not_mixed_between_books(self, detailed_library):
        library, _, second_id = detailed_library
        service = make_service(library)

        books = {b.title: b for b in service.get_books(limit=100).books}

        bare = books["Bare"]
        assert bare.authors == ["Anonyme"]
        assert bare.tags == []
        assert bare.publisher is None
        assert bare.isbn is None
        assert bare.languages == []
        assert bare.read is None
        assert bare.ko_status is None
        assert bare.ko_progress is None

        second = books["Vol de nuit"]
        assert second.id == second_id
        assert second.publisher == "Gallimard"
        assert second.read is True
        assert second.ko_status == "finished"
        assert second.paper is None

    def test_get_book_matches_the_list(self, detailed_library):
        library, full_id, second_id = detailed_library
        service = make_service(library)

        listed = {b.id: b for b in service.get_books(limit=100).books}

        for book_id in (full_id, second_id):
            assert service.get_book(book_id) == listed[book_id]
        assert service.get_book(9999) is None

    def test_pagination_returns_complete_books(self, detailed_library):
        library, _, _ = detailed_library
        service = make_service(library)

        page = service.get_books(limit=1, offset=1)

        assert page.total == 3
        assert len(page.books) == 1
        assert page.books[0].authors


class TestBooksEndpointDoesNotBlockTheEventLoop:
    def test_books_endpoint_runs_in_threadpool(self):
        """Synchrone : FastAPI l'exécute hors de la boucle asyncio."""
        assert not inspect.iscoroutinefunction(app_module.get_calibre_books)
