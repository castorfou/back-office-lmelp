"""Tests for the Palmares API endpoint (Issue #195).

Tests the GET /api/palmares endpoint which returns books ranked by
average rating (descending), with minimum 2 reviews required.
Includes Calibre matching integration tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from back_office_lmelp.app import app

    return TestClient(app)


@pytest.fixture
def mock_palmares_data():
    """Mock data matching real MongoDB aggregation structure.

    Based on real data: Le Lambeau (10.0/4 avis), La Serpe (10.0/4 avis),
    Feu (10.0/4 avis).
    """
    return {
        "items": [
            {
                "livre_id": "6956ba2affd13096430f9cb9",
                "titre": "Le Lambeau",
                "auteur_id": "6950027a26f38eb0ca5aabed",
                "auteur_nom": "Philippe Lançon",
                "note_moyenne": 10.0,
                "nombre_avis": 4,
                "url_babelio": "https://www.babelio.com/livres/Lancon-Le-Lambeau/1036944",
            },
            {
                "livre_id": "6956cb23ffd13096430f9d2c",
                "titre": "La Serpe",
                "auteur_id": "68e9729e7f7c718a5b6200f9",
                "auteur_nom": "Philippe Jaenada",
                "note_moyenne": 10.0,
                "nombre_avis": 4,
                "url_babelio": "https://www.babelio.com/livres/Jaenada-La-Serpe/1357073",
            },
            {
                "livre_id": "694a538a7f4fb7d4a62077dc",
                "titre": "Feu",
                "auteur_id": "68e2c3ba1391489c77ccdee5",
                "auteur_nom": "Maria Pourchet",
                "note_moyenne": 10.0,
                "nombre_avis": 4,
                "url_babelio": "https://www.babelio.com/livres/Pourchet-Feu/1331996",
            },
        ],
        "total": 861,
        "page": 1,
        "limit": 30,
        "total_pages": 29,
    }


class TestPalmaresEndpoint:
    """Tests for GET /api/palmares endpoint."""

    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_returns_200(self, mock_service, client, mock_palmares_data):
        """Test that the endpoint returns 200 with valid data."""
        mock_service.get_palmares.return_value = mock_palmares_data

        response = client.get("/api/palmares")

        assert response.status_code == 200

    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_response_structure(
        self, mock_service, client, mock_palmares_data
    ):
        """Test that response has correct structure with items and pagination."""
        mock_service.get_palmares.return_value = mock_palmares_data

        response = client.get("/api/palmares")
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)

    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_item_structure(self, mock_service, client, mock_palmares_data):
        """Test that each item has all required fields."""
        mock_service.get_palmares.return_value = mock_palmares_data

        response = client.get("/api/palmares")
        data = response.json()
        item = data["items"][0]

        assert "livre_id" in item
        assert "titre" in item
        assert "auteur_id" in item
        assert "auteur_nom" in item
        assert "note_moyenne" in item
        assert "nombre_avis" in item
        assert "url_babelio" in item

    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_sorted_by_note_descending(
        self, mock_service, client, mock_palmares_data
    ):
        """Test that items are sorted by note_moyenne descending."""
        # Add items with different notes
        mock_palmares_data["items"] = [
            {
                "livre_id": "id1",
                "titre": "Best Book",
                "auteur_id": "a1",
                "auteur_nom": "Author 1",
                "note_moyenne": 9.5,
                "nombre_avis": 3,
                "url_babelio": None,
            },
            {
                "livre_id": "id2",
                "titre": "Good Book",
                "auteur_id": "a2",
                "auteur_nom": "Author 2",
                "note_moyenne": 8.0,
                "nombre_avis": 2,
                "url_babelio": None,
            },
            {
                "livre_id": "id3",
                "titre": "Average Book",
                "auteur_id": "a3",
                "auteur_nom": "Author 3",
                "note_moyenne": 6.5,
                "nombre_avis": 4,
                "url_babelio": None,
            },
        ]
        mock_service.get_palmares.return_value = mock_palmares_data

        response = client.get("/api/palmares")
        data = response.json()
        notes = [item["note_moyenne"] for item in data["items"]]

        assert notes == sorted(notes, reverse=True)

    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_pagination_params(self, mock_service, client, mock_palmares_data):
        """Test that page and limit query params are passed to service."""
        mock_service.get_palmares.return_value = mock_palmares_data

        client.get("/api/palmares?page=2&limit=10")

        mock_service.get_palmares.assert_called_once_with(page=2, limit=10)

    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_default_pagination(
        self, mock_service, client, mock_palmares_data
    ):
        """Test default pagination values (page=1, limit=30)."""
        mock_service.get_palmares.return_value = mock_palmares_data

        client.get("/api/palmares")

        mock_service.get_palmares.assert_called_once_with(page=1, limit=30)

    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_error_handling(self, mock_service, client):
        """Test that endpoint handles service errors gracefully."""
        mock_service.get_palmares.side_effect = Exception("Database error")

        response = client.get("/api/palmares")

        assert response.status_code == 500


class TestPalmaresService:
    """Tests for the MongoDB service get_palmares method."""

    def test_get_palmares_returns_dict_with_items(self):
        """Test that get_palmares returns expected structure."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)
        # Mock the avis collection with aggregation
        mock_collection = MagicMock()
        service.avis_collection = mock_collection

        # Mock aggregation result matching real MongoDB structure
        mock_collection.aggregate.return_value = iter(
            [
                {
                    "metadata": [{"total": 2}],
                    "data": [
                        {
                            "_id": "6956ba2affd13096430f9cb9",
                            "note_moyenne": 10.0,
                            "nombre_avis": 4,
                            "titre": "Le Lambeau",
                            "auteur_id": "6950027a26f38eb0ca5aabed",
                            "auteur_nom": "Philippe Lançon",
                            "url_babelio": "https://www.babelio.com/livres/Lancon-Le-Lambeau/1036944",
                        },
                        {
                            "_id": "694a538a7f4fb7d4a62077dc",
                            "note_moyenne": 10.0,
                            "nombre_avis": 4,
                            "titre": "Feu",
                            "auteur_id": "68e2c3ba1391489c77ccdee5",
                            "auteur_nom": "Maria Pourchet",
                            "url_babelio": "https://www.babelio.com/livres/Pourchet-Feu/1331996",
                        },
                    ],
                }
            ]
        )

        result = service.get_palmares(page=1, limit=30)

        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "limit" in result
        assert "total_pages" in result
        assert len(result["items"]) == 2

    def test_get_palmares_item_has_correct_fields(self):
        """Test that each palmares item has all required fields."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)
        mock_collection = MagicMock()
        service.avis_collection = mock_collection

        mock_collection.aggregate.return_value = iter(
            [
                {
                    "metadata": [{"total": 1}],
                    "data": [
                        {
                            "_id": "6956ba2affd13096430f9cb9",
                            "note_moyenne": 10.0,
                            "nombre_avis": 4,
                            "titre": "Le Lambeau",
                            "auteur_id": "6950027a26f38eb0ca5aabed",
                            "auteur_nom": "Philippe Lançon",
                            "url_babelio": "https://www.babelio.com/livres/Lancon-Le-Lambeau/1036944",
                        },
                    ],
                }
            ]
        )

        result = service.get_palmares(page=1, limit=30)
        item = result["items"][0]

        assert item["livre_id"] == "6956ba2affd13096430f9cb9"
        assert item["titre"] == "Le Lambeau"
        assert item["auteur_id"] == "6950027a26f38eb0ca5aabed"
        assert item["auteur_nom"] == "Philippe Lançon"
        assert item["note_moyenne"] == 10.0
        assert item["nombre_avis"] == 4
        assert (
            item["url_babelio"]
            == "https://www.babelio.com/livres/Lancon-Le-Lambeau/1036944"
        )

    def test_get_palmares_empty_result(self):
        """Test that get_palmares handles empty results."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)
        mock_collection = MagicMock()
        service.avis_collection = mock_collection

        mock_collection.aggregate.return_value = iter([{"metadata": [], "data": []}])

        result = service.get_palmares(page=1, limit=30)

        assert result["items"] == []
        assert result["total"] == 0
        assert result["total_pages"] == 0

    def test_get_palmares_pagination_calculation(self):
        """Test correct total_pages calculation."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)
        mock_collection = MagicMock()
        service.avis_collection = mock_collection

        mock_collection.aggregate.return_value = iter(
            [
                {
                    "metadata": [{"total": 65}],
                    "data": [
                        {
                            "_id": "id1",
                            "note_moyenne": 8.0,
                            "nombre_avis": 3,
                            "titre": "Book",
                            "auteur_id": "a1",
                            "auteur_nom": "Author",
                            "url_babelio": None,
                        },
                    ],
                }
            ]
        )

        result = service.get_palmares(page=1, limit=30)

        assert result["total"] == 65
        assert result["total_pages"] == 3  # ceil(65/30) = 3


class TestPalmaresWithCalibre:
    """Tests for Calibre enrichment in palmares endpoint."""

    @patch("back_office_lmelp.app.calibre_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_items_include_calibre_fields(
        self, mock_mongodb, mock_calibre, client
    ):
        """Test that items include calibre_* fields when Calibre is available."""
        mock_mongodb.get_palmares.return_value = {
            "items": [
                {
                    "livre_id": "id1",
                    "titre": "Le Lambeau",
                    "auteur_id": "a1",
                    "auteur_nom": "Philippe Lançon",
                    "note_moyenne": 10.0,
                    "nombre_avis": 4,
                    "url_babelio": None,
                },
            ],
            "total": 1,
            "page": 1,
            "limit": 30,
            "total_pages": 1,
        }
        # Mock Calibre available with matching book
        mock_calibre._available = True
        mock_calibre.get_all_books_summary.return_value = [
            {
                "id": 42,
                "title": "Le lambeau",
                "authors": ["Philippe Lançon"],
                "read": True,
                "rating": 10,
            }
        ]

        response = client.get("/api/palmares")
        data = response.json()
        item = data["items"][0]

        assert "calibre_in_library" in item
        assert "calibre_read" in item
        assert "calibre_rating" in item

    @patch("back_office_lmelp.app.calibre_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_calibre_match_by_normalized_title(
        self, mock_mongodb, mock_calibre, client
    ):
        """Test that matching works with case/accent differences."""
        mock_mongodb.get_palmares.return_value = {
            "items": [
                {
                    "livre_id": "id1",
                    "titre": "L'Ordre du jour",
                    "auteur_id": "a1",
                    "auteur_nom": "Éric Vuillard",
                    "note_moyenne": 9.5,
                    "nombre_avis": 3,
                    "url_babelio": None,
                },
            ],
            "total": 1,
            "page": 1,
            "limit": 30,
            "total_pages": 1,
        }
        mock_calibre._available = True
        mock_calibre.get_all_books_summary.return_value = [
            {
                "id": 100,
                "title": "L'ordre du jour",
                "authors": ["Eric Vuillard"],
                "read": True,
                "rating": 8,
            }
        ]

        response = client.get("/api/palmares")
        data = response.json()
        item = data["items"][0]

        assert item["calibre_in_library"] is True
        assert item["calibre_read"] is True
        assert item["calibre_rating"] == 8

    @patch("back_office_lmelp.app.calibre_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_no_calibre_match(self, mock_mongodb, mock_calibre, client):
        """Test items without Calibre match have null calibre fields."""
        mock_mongodb.get_palmares.return_value = {
            "items": [
                {
                    "livre_id": "id1",
                    "titre": "Unknown Book",
                    "auteur_id": "a1",
                    "auteur_nom": "Author",
                    "note_moyenne": 7.0,
                    "nombre_avis": 2,
                    "url_babelio": None,
                },
            ],
            "total": 1,
            "page": 1,
            "limit": 30,
            "total_pages": 1,
        }
        mock_calibre._available = True
        mock_calibre.get_all_books_summary.return_value = [
            {
                "id": 1,
                "title": "Other Book",
                "authors": ["Other Author"],
                "read": True,
                "rating": 6,
            }
        ]

        response = client.get("/api/palmares")
        data = response.json()
        item = data["items"][0]

        assert item["calibre_in_library"] is False
        assert item["calibre_read"] is None
        assert item["calibre_rating"] is None

    @patch("back_office_lmelp.app.calibre_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_calibre_unavailable(self, mock_mongodb, mock_calibre, client):
        """Test that palmares works when Calibre is not available."""
        mock_mongodb.get_palmares.return_value = {
            "items": [
                {
                    "livre_id": "id1",
                    "titre": "A Book",
                    "auteur_id": "a1",
                    "auteur_nom": "Author",
                    "note_moyenne": 8.0,
                    "nombre_avis": 3,
                    "url_babelio": None,
                },
            ],
            "total": 1,
            "page": 1,
            "limit": 30,
            "total_pages": 1,
        }
        mock_calibre._available = False

        response = client.get("/api/palmares")
        data = response.json()
        item = data["items"][0]

        assert item["calibre_in_library"] is False
        assert item["calibre_read"] is None
        assert item["calibre_rating"] is None

    @patch("back_office_lmelp.app.calibre_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_palmares_calibre_rating_ignored_when_not_read(
        self, mock_mongodb, mock_calibre, client
    ):
        """Test that calibre_rating is None when book is in Calibre but not read."""
        mock_mongodb.get_palmares.return_value = {
            "items": [
                {
                    "livre_id": "id1",
                    "titre": "La seule histoire",
                    "auteur_id": "a1",
                    "auteur_nom": "Julian Barnes",
                    "note_moyenne": 10.0,
                    "nombre_avis": 4,
                    "url_babelio": None,
                },
            ],
            "total": 1,
            "page": 1,
            "limit": 30,
            "total_pages": 1,
        }
        mock_calibre._available = True
        mock_calibre.get_all_books_summary.return_value = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Julian Barnes"],
                "read": False,
                "rating": 10,
            }
        ]

        response = client.get("/api/palmares")
        data = response.json()
        item = data["items"][0]

        assert item["calibre_in_library"] is True
        assert item["calibre_read"] is False
        assert item["calibre_rating"] is None  # Rating ignored when not read
