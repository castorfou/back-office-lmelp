"""Tests pour les endpoints Calibre (TDD)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.models.calibre_models import (
    CalibreAuthor,
    CalibreBook,
    CalibreBookList,
    CalibreStatistics,
    CalibreStatus,
)
from back_office_lmelp.services.calibre_service import calibre_service


@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)


@pytest.fixture
def mock_calibre_service():
    """Mock du service Calibre."""
    with (
        patch.object(calibre_service, "get_status") as mock_status,
        patch.object(calibre_service, "get_books") as mock_books,
        patch.object(calibre_service, "get_book") as mock_book,
        patch.object(calibre_service, "get_authors") as mock_authors,
        patch.object(calibre_service, "get_statistics") as mock_stats,
    ):
        yield {
            "get_status": mock_status,
            "get_books": mock_books,
            "get_book": mock_book,
            "get_authors": mock_authors,
            "get_statistics": mock_stats,
        }


class TestCalibreStatusEndpoint:
    """Tests pour l'endpoint GET /api/calibre/status."""

    def test_get_status_available(self, client, mock_calibre_service):
        """Test du statut quand Calibre est disponible."""
        # Arrange
        mock_status = CalibreStatus(
            available=True,
            library_path="/calibre",
            total_books=516,
            virtual_library_tag="guillaume",
            custom_columns={"read": "Read (bool)", "paper": "paper (bool)"},
            error=None,
        )
        mock_calibre_service["get_status"].return_value = mock_status

        # Act
        response = client.get("/api/calibre/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["library_path"] == "/calibre"
        assert data["total_books"] == 516
        assert data["virtual_library_tag"] == "guillaume"
        assert "read" in data["custom_columns"]

    def test_get_status_unavailable(self, client, mock_calibre_service):
        """Test du statut quand Calibre n'est pas disponible."""
        # Arrange
        mock_status = CalibreStatus(
            available=False,
            library_path=None,
            total_books=None,
            virtual_library_tag=None,
            custom_columns={},
            error="CALIBRE_LIBRARY_PATH not configured",
        )
        mock_calibre_service["get_status"].return_value = mock_status

        # Act
        response = client.get("/api/calibre/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert data["error"] == "CALIBRE_LIBRARY_PATH not configured"


class TestCalibreBooksEndpoint:
    """Tests pour l'endpoint GET /api/calibre/books."""

    def test_get_books_default_pagination(self, client, mock_calibre_service):
        """Test de récupération des livres avec pagination par défaut."""
        # Arrange
        mock_books_list = CalibreBookList(
            total=516,
            offset=0,
            limit=50,
            books=[
                CalibreBook(
                    id=3,
                    title="Le Silence de la mer",
                    authors=["Vercors"],
                    isbn="978-2-7011-1234-5",
                    rating=8,
                    tags=["guillaume"],
                    read=True,
                ),
                CalibreBook(
                    id=42,
                    title="L'Étranger",
                    authors=["Camus, Albert"],
                    isbn="978-2-07-036002-4",
                    rating=10,
                    tags=["guillaume"],
                    read=False,
                ),
            ],
        )
        mock_calibre_service["get_books"].return_value = mock_books_list

        # Act
        response = client.get("/api/calibre/books")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 516
        assert data["offset"] == 0
        assert data["limit"] == 50
        assert len(data["books"]) == 2
        assert data["books"][0]["title"] == "Le Silence de la mer"
        assert "Vercors" in data["books"][0]["authors"]

    def test_get_books_with_pagination(self, client, mock_calibre_service):
        """Test de récupération avec paramètres de pagination."""
        # Arrange
        mock_books_list = CalibreBookList(
            total=516,
            offset=50,
            limit=25,
            books=[],
        )
        mock_calibre_service["get_books"].return_value = mock_books_list

        # Act
        response = client.get("/api/calibre/books?limit=25&offset=50")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 50
        assert data["limit"] == 25
        mock_calibre_service["get_books"].assert_called_once_with(
            limit=25, offset=50, read_filter=None, search=None
        )

    def test_get_books_with_read_filter_true(self, client, mock_calibre_service):
        """Test de récupération des livres lus."""
        # Arrange
        mock_books_list = CalibreBookList(
            total=299,
            offset=0,
            limit=50,
            books=[],
        )
        mock_calibre_service["get_books"].return_value = mock_books_list

        # Act
        response = client.get("/api/calibre/books?read_filter=true")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 299
        mock_calibre_service["get_books"].assert_called_once_with(
            limit=50, offset=0, read_filter=True, search=None
        )

    def test_get_books_with_read_filter_false(self, client, mock_calibre_service):
        """Test de récupération des livres non lus."""
        # Arrange
        mock_books_list = CalibreBookList(
            total=217,
            offset=0,
            limit=50,
            books=[],
        )
        mock_calibre_service["get_books"].return_value = mock_books_list

        # Act
        response = client.get("/api/calibre/books?read_filter=false")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 217
        mock_calibre_service["get_books"].assert_called_once_with(
            limit=50, offset=0, read_filter=False, search=None
        )

    def test_get_books_when_service_unavailable(self, client, mock_calibre_service):
        """Test quand le service Calibre n'est pas disponible."""
        # Arrange
        mock_calibre_service["get_books"].side_effect = RuntimeError(
            "Calibre service not available"
        )

        # Act
        response = client.get("/api/calibre/books")

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data


class TestCalibreBookDetailEndpoint:
    """Tests pour l'endpoint GET /api/calibre/books/{book_id}."""

    def test_get_book_found(self, client, mock_calibre_service):
        """Test de récupération d'un livre existant."""
        # Arrange
        mock_book = CalibreBook(
            id=3,
            title="Le Silence de la mer",
            authors=["Vercors"],
            isbn="978-2-7011-1234-5",
            rating=8,
            tags=["guillaume", "roman"],
            publisher="Albin Michel",
            read=True,
        )
        mock_calibre_service["get_book"].return_value = mock_book

        # Act
        response = client.get("/api/calibre/books/3")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 3
        assert data["title"] == "Le Silence de la mer"
        assert "Vercors" in data["authors"]
        assert data["isbn"] == "978-2-7011-1234-5"

    def test_get_book_not_found(self, client, mock_calibre_service):
        """Test de récupération d'un livre inexistant."""
        # Arrange
        mock_calibre_service["get_book"].return_value = None

        # Act
        response = client.get("/api/calibre/books/999")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestCalibreAuthorsEndpoint:
    """Tests pour l'endpoint GET /api/calibre/authors."""

    def test_get_authors(self, client, mock_calibre_service):
        """Test de récupération de la liste des auteurs."""
        # Arrange
        mock_authors = [
            CalibreAuthor(id=1, name="Vercors", sort="Vercors", link=None),
            CalibreAuthor(id=2, name="Camus, Albert", sort="Camus, Albert", link=None),
        ]
        mock_calibre_service["get_authors"].return_value = mock_authors

        # Act
        response = client.get("/api/calibre/authors")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Vercors"
        assert data[1]["name"] == "Camus, Albert"


class TestCalibreStatisticsEndpoint:
    """Tests pour l'endpoint GET /api/calibre/statistics."""

    def test_get_statistics(self, client, mock_calibre_service):
        """Test de récupération des statistiques."""
        # Arrange
        mock_stats = CalibreStatistics(
            total_books=516,
            books_with_isbn=221,
            books_with_rating=500,
            books_with_tags=516,
            total_authors=450,
            total_tags=100,
            books_read=299,
        )
        mock_calibre_service["get_statistics"].return_value = mock_stats

        # Act
        response = client.get("/api/calibre/statistics")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_books"] == 516
        assert data["books_with_isbn"] == 221
        assert data["books_read"] == 299
        assert data["total_authors"] == 450
