"""Tests TDD pour le endpoint /api/calibre/onkindle (Issue #216)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Client de test FastAPI."""
    from back_office_lmelp.app import app

    return TestClient(app)


# ============================================================
# Tests for MongoDBService.get_notes_for_livres()
# ============================================================


class TestGetNotesForLivres:
    """Tests pour MongoDBService.get_notes_for_livres().

    Les notes sont dans la collection 'avis' (champs: livre_oid String, note Number),
    PAS dans 'avis_critiques' (qui est la collection des résumés LLM sans notes).
    """

    def test_uses_avis_collection_not_avis_critiques(self):
        """Doit interroger avis_collection, pas avis_critiques_collection."""
        from unittest.mock import MagicMock

        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)

        # avis_collection a les données
        mock_avis = MagicMock()
        service.avis_collection = mock_avis
        mock_avis.aggregate.return_value = iter(
            [{"_id": "livre_abc", "note_moyenne": 8.5}]
        )

        # avis_critiques_collection ne doit PAS être appelée
        mock_avis_critiques = MagicMock()
        service.avis_critiques_collection = mock_avis_critiques

        result = service.get_notes_for_livres(["livre_abc"])

        assert result["livre_abc"] == 8.5
        mock_avis.aggregate.assert_called_once()
        mock_avis_critiques.aggregate.assert_not_called()

    def test_returns_dict_by_livre_id(self):
        """Retourne un dict {livre_id: note_moyenne} pour une liste d'IDs."""
        from unittest.mock import MagicMock

        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)

        mock_collection = MagicMock()
        service.avis_collection = mock_collection

        # Simuler le résultat de l'agrégation
        mock_collection.aggregate.return_value = iter(
            [
                {"_id": "livre_abc", "note_moyenne": 8.5},
                {"_id": "livre_def", "note_moyenne": 7.0},
            ]
        )

        result = service.get_notes_for_livres(["livre_abc", "livre_def"])

        assert isinstance(result, dict)
        assert result["livre_abc"] == 8.5
        assert result["livre_def"] == 7.0

    def test_returns_empty_dict_when_no_collection(self):
        """Retourne un dict vide si la collection n'est pas disponible."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)
        service.avis_collection = None

        result = service.get_notes_for_livres(["livre_abc"])

        assert result == {}

    def test_returns_empty_dict_for_empty_input(self):
        """Retourne un dict vide pour une liste d'IDs vide."""
        from unittest.mock import MagicMock

        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)
        service.avis_collection = MagicMock()
        service.avis_collection.aggregate.return_value = iter([])

        result = service.get_notes_for_livres([])

        assert result == {}


# ============================================================
# Tests for CalibreMatchingService.get_onkindle_books()
# ============================================================


class TestGetOnkindleBooks:
    """Tests pour CalibreMatchingService.get_onkindle_books()."""

    def test_returns_only_onkindle_tagged_books(self):
        """Retourne uniquement les livres avec le tag 'onkindle'."""
        from unittest.mock import MagicMock

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_mongodb = MagicMock()

        service = CalibreMatchingService(mock_calibre, mock_mongodb)

        # Calibre books: 2 livres, 1 avec onkindle, 1 sans
        mock_calibre.get_all_books_with_tags.return_value = [
            {
                "id": 1,
                "title": "Le Lambeau",
                "authors": ["Philippe Lançon"],
                "tags": ["guillaume", "onkindle"],
                "rating": 10,
                "read": True,
            },
            {
                "id": 2,
                "title": "La Serpe",
                "authors": ["Philippe Jaenada"],
                "tags": ["guillaume"],
                "rating": 8,
                "read": False,
            },
        ]
        # MongoDB books
        mock_mongodb.get_all_books.return_value = [
            {
                "_id": "abc123",
                "titre": "Le Lambeau",
                "auteur_id": "aut1",
                "url_babelio": "https://babelio.com/lambeau",
            }
        ]
        mock_mongodb.get_all_authors.return_value = [
            {"_id": "aut1", "nom": "Philippe Lançon"}
        ]
        mock_mongodb.get_notes_for_livres.return_value = {"abc123": 9.5}

        result = service.get_onkindle_books()

        # Should return only 1 book (with onkindle tag)
        assert len(result) == 1
        assert result[0]["titre"] == "Le Lambeau"
        assert result[0]["calibre_id"] == 1

    def test_enriches_with_mongodb_data_when_matched(self):
        """Enrichit avec les données MongoDB quand le livre est dans la base."""
        from unittest.mock import MagicMock

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_mongodb = MagicMock()

        service = CalibreMatchingService(mock_calibre, mock_mongodb)

        mock_calibre.get_all_books_with_tags.return_value = [
            {
                "id": 1,
                "title": "Le Lambeau",
                "authors": ["Lançon, Philippe"],
                "tags": ["onkindle"],
                "rating": 10,
                "read": True,
            }
        ]
        mock_mongodb.get_all_books.return_value = [
            {
                "_id": "abc123",
                "titre": "Le Lambeau",
                "auteur_id": "aut1",
                "url_babelio": "https://babelio.com/lambeau",
            }
        ]
        mock_mongodb.get_all_authors.return_value = [
            {"_id": "aut1", "nom": "Philippe Lançon"}
        ]
        mock_mongodb.get_notes_for_livres.return_value = {"abc123": 9.5}

        result = service.get_onkindle_books()

        assert len(result) == 1
        book = result[0]
        assert book["mongo_livre_id"] == "abc123"
        assert book["auteur_id"] == "aut1"
        assert book["url_babelio"] == "https://babelio.com/lambeau"
        assert book["note_moyenne"] == 9.5

    def test_returns_empty_mongo_fields_when_not_matched(self):
        """Retourne des champs MongoDB vides pour les livres non matchés."""
        from unittest.mock import MagicMock

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_mongodb = MagicMock()

        service = CalibreMatchingService(mock_calibre, mock_mongodb)

        mock_calibre.get_all_books_with_tags.return_value = [
            {
                "id": 5,
                "title": "Livre Inconnu",
                "authors": ["Auteur Inconnu"],
                "tags": ["onkindle"],
                "rating": None,
                "read": None,
            }
        ]
        mock_mongodb.get_all_books.return_value = []
        mock_mongodb.get_all_authors.return_value = []
        mock_mongodb.get_notes_for_livres.return_value = {}

        result = service.get_onkindle_books()

        assert len(result) == 1
        book = result[0]
        assert book["mongo_livre_id"] is None
        assert book["auteur_id"] is None
        assert book["url_babelio"] is None
        assert book["note_moyenne"] is None

    def test_returns_empty_list_when_calibre_unavailable(self):
        """Retourne une liste vide si Calibre n'est pas disponible."""
        from unittest.mock import MagicMock

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        mock_calibre = MagicMock()
        mock_calibre._available = False
        mock_mongodb = MagicMock()

        service = CalibreMatchingService(mock_calibre, mock_mongodb)

        result = service.get_onkindle_books()

        assert result == []

    def test_sorted_by_title(self):
        """Les livres sont triés par titre."""
        from unittest.mock import MagicMock

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_mongodb = MagicMock()

        service = CalibreMatchingService(mock_calibre, mock_mongodb)

        mock_calibre.get_all_books_with_tags.return_value = [
            {
                "id": 3,
                "title": "Zola",
                "authors": ["A"],
                "tags": ["onkindle"],
                "rating": None,
                "read": None,
            },
            {
                "id": 1,
                "title": "Arnaud",
                "authors": ["B"],
                "tags": ["onkindle"],
                "rating": None,
                "read": None,
            },
        ]
        mock_mongodb.get_all_books.return_value = []
        mock_mongodb.get_all_authors.return_value = []
        mock_mongodb.get_notes_for_livres.return_value = {}

        result = service.get_onkindle_books()

        assert result[0]["titre"] == "Arnaud"
        assert result[1]["titre"] == "Zola"


# ============================================================
# Tests for GET /api/calibre/onkindle endpoint
# ============================================================


class TestOnKindleEndpoint:
    """Tests pour GET /api/calibre/onkindle."""

    @patch("back_office_lmelp.app.calibre_service")
    @patch("back_office_lmelp.app.calibre_matching_service")
    def test_returns_books_and_total(
        self, mock_matching_service, mock_calibre_service, client
    ):
        """Retourne une liste de livres avec le total."""
        mock_calibre_service.is_available.return_value = True
        mock_matching_service.get_onkindle_books.return_value = [
            {
                "calibre_id": 1,
                "titre": "Le Lambeau",
                "auteurs": ["Philippe Lançon"],
                "calibre_rating": 10,
                "calibre_read": True,
                "mongo_livre_id": "abc123",
                "auteur_id": "aut1",
                "note_moyenne": 9.5,
                "url_babelio": "https://babelio.com/lambeau",
            }
        ]

        response = client.get("/api/calibre/onkindle")

        assert response.status_code == 200
        data = response.json()
        assert "books" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["books"]) == 1
        book = data["books"][0]
        assert book["titre"] == "Le Lambeau"
        assert book["mongo_livre_id"] == "abc123"
        assert book["note_moyenne"] == 9.5
        assert book["url_babelio"] == "https://babelio.com/lambeau"

    @patch("back_office_lmelp.app.calibre_service")
    def test_returns_503_when_calibre_unavailable(self, mock_calibre_service, client):
        """Retourne 503 si Calibre n'est pas disponible."""
        mock_calibre_service.is_available.return_value = False

        response = client.get("/api/calibre/onkindle")

        assert response.status_code == 503
        data = response.json()
        assert "error" in data

    @patch("back_office_lmelp.app.calibre_service")
    @patch("back_office_lmelp.app.calibre_matching_service")
    def test_returns_empty_list_when_no_onkindle_books(
        self, mock_matching_service, mock_calibre_service, client
    ):
        """Retourne une liste vide si aucun livre n'a le tag onkindle."""
        mock_calibre_service.is_available.return_value = True
        mock_matching_service.get_onkindle_books.return_value = []

        response = client.get("/api/calibre/onkindle")

        assert response.status_code == 200
        data = response.json()
        assert data["books"] == []
        assert data["total"] == 0
