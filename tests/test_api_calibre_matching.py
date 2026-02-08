"""Tests pour les endpoints API de matching MongoDB-Calibre (Issue #199)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Client de test FastAPI."""
    from back_office_lmelp.app import app

    return TestClient(app)


class TestCalibreMatchingEndpoint:
    """Tests pour GET /api/calibre/matching."""

    @patch("back_office_lmelp.app.calibre_matching_service")
    def test_returns_matches_and_statistics(self, mock_service, client):
        """Retourne les résultats de matching avec statistiques."""
        mock_service.match_all.return_value = [
            {
                "mongo_livre_id": "abc123",
                "mongo_titre": "Le Lambeau",
                "mongo_auteur": "Philippe Lançon",
                "calibre_id": 42,
                "calibre_title": "Le Lambeau",
                "calibre_authors": ["Lançon, Philippe"],
                "calibre_tags": ["roman"],
                "calibre_read": True,
                "calibre_rating": 8,
                "match_type": "exact",
                "title_differs": False,
                "author_differs": True,
            }
        ]

        response = client.get("/api/calibre/matching")

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "statistics" in data
        assert len(data["matches"]) == 1
        assert data["matches"][0]["match_type"] == "exact"
        assert data["statistics"]["total_matches"] == 1
        assert data["statistics"]["exact_matches"] == 1

    @patch("back_office_lmelp.app.calibre_matching_service")
    def test_returns_empty_when_calibre_unavailable(self, mock_service, client):
        """Retourne des résultats vides si Calibre non disponible."""
        mock_service.match_all.return_value = []

        response = client.get("/api/calibre/matching")

        assert response.status_code == 200
        data = response.json()
        assert data["matches"] == []
        assert data["statistics"]["total_matches"] == 0

    @patch("back_office_lmelp.app.calibre_matching_service")
    def test_handles_error_gracefully(self, mock_service, client):
        """Gère les erreurs sans crash."""
        mock_service.match_all.side_effect = Exception("Database error")

        response = client.get("/api/calibre/matching")

        assert response.status_code == 500


class TestCalibreCorrectionsEndpoint:
    """Tests pour GET /api/calibre/corrections."""

    @patch("back_office_lmelp.app.calibre_matching_service")
    def test_returns_corrections_by_category(self, mock_service, client):
        """Retourne les corrections groupées par catégorie."""
        mock_service.get_corrections.return_value = {
            "author_corrections": [
                {
                    "calibre_id": 42,
                    "calibre_title": "Tropique de la violence",
                    "calibre_authors": ["Appanah| Nathacha"],
                    "mongodb_author": "Nathacha Appanah",
                    "mongo_livre_id": "abc",
                    "match_type": "exact",
                }
            ],
            "title_corrections": [
                {
                    "calibre_id": 100,
                    "calibre_title": "Chanson douce - Prix Goncourt 2016",
                    "mongodb_title": "Chanson douce",
                    "author": "Leïla Slimani",
                    "mongo_livre_id": "def",
                    "match_type": "containment",
                }
            ],
            "missing_lmelp_tags": [
                {
                    "calibre_id": 55,
                    "calibre_title": "La seule histoire",
                    "current_tags": ["roman"],
                    "mongo_livre_id": "ghi",
                    "author": "Julian Barnes",
                }
            ],
            "statistics": {
                "total_author_corrections": 1,
                "total_title_corrections": 1,
                "total_missing_lmelp_tags": 1,
                "total_matches": 3,
            },
        }

        response = client.get("/api/calibre/corrections")

        assert response.status_code == 200
        data = response.json()
        assert len(data["author_corrections"]) == 1
        assert len(data["title_corrections"]) == 1
        assert len(data["missing_lmelp_tags"]) == 1
        assert data["statistics"]["total_matches"] == 3

    @patch("back_office_lmelp.app.calibre_matching_service")
    def test_returns_empty_when_no_corrections(self, mock_service, client):
        """Retourne des listes vides quand tout est correct."""
        mock_service.get_corrections.return_value = {
            "author_corrections": [],
            "title_corrections": [],
            "missing_lmelp_tags": [],
            "statistics": {
                "total_author_corrections": 0,
                "total_title_corrections": 0,
                "total_missing_lmelp_tags": 0,
                "total_matches": 10,
            },
        }

        response = client.get("/api/calibre/corrections")

        assert response.status_code == 200
        data = response.json()
        assert data["author_corrections"] == []
        assert data["title_corrections"] == []
        assert data["missing_lmelp_tags"] == []

    @patch("back_office_lmelp.app.calibre_matching_service")
    def test_handles_error_gracefully(self, mock_service, client):
        """Gère les erreurs sans crash."""
        mock_service.get_corrections.side_effect = Exception("Service error")

        response = client.get("/api/calibre/corrections")

        assert response.status_code == 500


class TestCalibreCacheInvalidateEndpoint:
    """Tests pour POST /api/calibre/cache/invalidate."""

    @patch("back_office_lmelp.app.calibre_matching_service")
    def test_invalidates_cache(self, mock_service, client):
        """Invalide le cache du matching service."""
        response = client.post("/api/calibre/cache/invalidate")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        mock_service.invalidate_cache.assert_called_once()

    @patch("back_office_lmelp.app.calibre_matching_service")
    def test_handles_error_gracefully(self, mock_service, client):
        """Gère les erreurs sans crash."""
        mock_service.invalidate_cache.side_effect = Exception("Error")

        response = client.post("/api/calibre/cache/invalidate")

        assert response.status_code == 500
