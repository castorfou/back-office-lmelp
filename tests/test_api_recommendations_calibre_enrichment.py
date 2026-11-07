"""Enrichissement Calibre de GET /api/recommendations/me (Issue #325).

Chaque recommandation indique si le livre est déjà dans la bibliothèque
Calibre (`calibre_in_library`, `calibre_read`), pour afficher ◯ / ✓ Lu ou
un lien de téléchargement Anna's Archive dans la page Mes Recommandations.
"""

from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app, calibre_matching_service
from back_office_lmelp.utils.text_utils import normalize_for_matching


@pytest.fixture
def client():
    return TestClient(app)


def make_reco(rank: int, titre: str) -> dict:
    """Structure réelle renvoyée par RecommendationService.get_recommendations()."""
    return {
        "rank": rank,
        "livre_id": str(ObjectId()),
        "titre": titre,
        "auteur_id": str(ObjectId()),
        "auteur_nom": "Auteur Test",
        "score_hybride": 7.5,
        "svd_predict": 7.2,
        "masque_mean": 8.1,
        "masque_count": 3,
    }


def make_calibre_book(title: str, read: bool | None) -> dict:
    """Structure réelle d'un livre de CalibreService.get_all_books_with_tags()."""
    return {
        "id": 42,
        "title": title,
        "authors": ["Auteur Test"],
        "tags": ["guillaume"],
        "read": read,
        "rating": None,
    }


class TestRecommendationsCalibreEnrichment:
    @patch("back_office_lmelp.app.recommendation_service")
    def test_each_recommendation_tells_if_book_is_in_calibre(
        self, mock_reco_service, client
    ):
        mock_reco_service.get_recommendations.return_value = [
            make_reco(1, "L'Œuvre au noir"),
            make_reco(2, "Livre lu"),
            make_reco(3, "Livre absent"),
        ]
        calibre_index = {
            normalize_for_matching("L'Oeuvre au noir"): make_calibre_book(
                "L'Oeuvre au noir", read=None
            ),
            normalize_for_matching("Livre lu"): make_calibre_book(
                "Livre lu", read=True
            ),
        }

        with patch.object(
            calibre_matching_service, "get_calibre_index", return_value=calibre_index
        ) as mock_index:
            response = client.get("/api/recommendations/me")

        assert response.status_code == 200
        data = response.json()
        assert [d["calibre_in_library"] for d in data] == [True, True, False]
        assert [d["calibre_read"] for d in data] == [None, True, None]
        # L'index Calibre n'est construit qu'une fois pour toute la liste
        assert mock_index.call_count == 1

    @patch("back_office_lmelp.app.recommendation_service")
    def test_calibre_failure_does_not_break_recommendations(
        self, mock_reco_service, client
    ):
        mock_reco_service.get_recommendations.return_value = [
            make_reco(1, "Un livre"),
        ]

        with patch.object(
            calibre_matching_service,
            "get_calibre_index",
            side_effect=RuntimeError("Calibre indisponible"),
        ):
            response = client.get("/api/recommendations/me")

        assert response.status_code == 200
        data = response.json()
        assert data[0]["titre"] == "Un livre"
        assert data[0]["calibre_in_library"] is False
        assert data[0]["calibre_read"] is None
