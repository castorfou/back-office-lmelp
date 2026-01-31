"""Tests for GET /api/livre/{livre_id} endpoint (Issue #96 - Phase 2, updated Issue #190)."""

from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestGetLivreDetail:
    """Tests pour l'endpoint GET /api/livre/{livre_id}."""

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_livre_returns_book_with_emissions(self, mock_mongodb_service, client):
        """Test que GET /api/livre/{id} retourne les détails d'un livre avec ses émissions."""
        # GIVEN: Un livre avec plusieurs émissions en base
        livre_id = str(ObjectId())
        auteur_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = {
            "livre_id": livre_id,
            "titre": "L'Adversaire",
            "auteur_id": auteur_id,
            "auteur_nom": "Emmanuel Carrère",
            "editeur": "Gallimard",
            "note_moyenne": 7.5,
            "nombre_emissions": 2,
            "emissions": [
                {
                    "emission_id": str(ObjectId()),
                    "date": "2000-09-15",
                    "note_moyenne": 8.0,
                    "nombre_avis": 3,
                },
                {
                    "emission_id": str(ObjectId()),
                    "date": "2000-03-12",
                    "note_moyenne": 7.0,
                    "nombre_avis": 2,
                },
            ],
        }

        # WHEN: On appelle GET /api/livre/{id}
        response = client.get(f"/api/livre/{livre_id}")

        # THEN: On reçoit un 200 avec les données du livre
        assert response.status_code == 200
        data = response.json()
        assert data["livre_id"] == livre_id
        assert data["titre"] == "L'Adversaire"
        assert data["auteur_nom"] == "Emmanuel Carrère"
        assert data["editeur"] == "Gallimard"
        assert data["note_moyenne"] == 7.5
        assert data["nombre_emissions"] == 2
        assert len(data["emissions"]) == 2
        assert data["emissions"][0]["date"] == "2000-09-15"
        assert data["emissions"][1]["date"] == "2000-03-12"

        # Vérifier que le service a été appelé avec le bon ID
        mock_mongodb_service.get_livre_with_episodes.assert_called_once_with(livre_id)

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_livre_returns_404_when_not_found(self, mock_mongodb_service, client):
        """Test que GET /api/livre/{id} retourne 404 si le livre n'existe pas."""
        # GIVEN: Un livre inexistant
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = None

        # WHEN: On appelle GET /api/livre/{id}
        response = client.get(f"/api/livre/{livre_id}")

        # THEN: On reçoit un 404
        assert response.status_code == 404
        assert "Livre non trouvé" in response.json()["detail"]

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_livre_returns_book_with_no_emissions(
        self, mock_mongodb_service, client
    ):
        """Test qu'un livre sans émissions retourne une liste vide."""
        # GIVEN: Un livre sans émissions
        livre_id = str(ObjectId())
        auteur_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = {
            "livre_id": livre_id,
            "titre": "Nouveau Livre",
            "auteur_id": auteur_id,
            "auteur_nom": "Nouvel Auteur",
            "editeur": "Nouveau Editeur",
            "note_moyenne": None,
            "nombre_emissions": 0,
            "emissions": [],
        }

        # WHEN: On appelle GET /api/livre/{id}
        response = client.get(f"/api/livre/{livre_id}")

        # THEN: On reçoit un 200 avec une liste d'émissions vide
        assert response.status_code == 200
        data = response.json()
        assert data["nombre_emissions"] == 0
        assert data["emissions"] == []

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_livre_validates_objectid_format(self, mock_mongodb_service, client):
        """Test que l'endpoint valide le format ObjectId."""
        # GIVEN: Un ID invalide
        invalid_id = "invalid_id_format"

        # WHEN: On appelle GET /api/livre/{invalid_id}
        response = client.get(f"/api/livre/{invalid_id}")

        # THEN: On reçoit une erreur 404 avec un message simple
        assert response.status_code == 404
        assert "Livre non trouvé" in response.json()["detail"]

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_livre_returns_url_babelio_when_present(
        self, mock_mongodb_service, client
    ):
        """Test que GET /api/livre/{id} retourne url_babelio quand disponible (Issue #124)."""
        # GIVEN: Un livre avec URL Babelio en base
        livre_id = str(ObjectId())
        auteur_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = {
            "livre_id": livre_id,
            "titre": "Simone Émonet",
            "auteur_id": auteur_id,
            "auteur_nom": "Catherine Millet",
            "editeur": "Flammarion",
            "url_babelio": "https://www.babelio.com/livres/Millet-Simone-monet/1870367",
            "note_moyenne": 6.5,
            "nombre_emissions": 1,
            "emissions": [
                {
                    "emission_id": str(ObjectId()),
                    "date": "2025-09-28",
                    "note_moyenne": 6.5,
                    "nombre_avis": 4,
                }
            ],
        }

        # WHEN: On appelle GET /api/livre/{id}
        response = client.get(f"/api/livre/{livre_id}")

        # THEN: On reçoit un 200 avec url_babelio
        assert response.status_code == 200
        data = response.json()
        assert data["livre_id"] == livre_id
        assert data["titre"] == "Simone Émonet"
        assert (
            data["url_babelio"]
            == "https://www.babelio.com/livres/Millet-Simone-monet/1870367"
        )

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_livre_handles_missing_url_babelio(self, mock_mongodb_service, client):
        """Test que GET /api/livre/{id} gère l'absence de url_babelio (Issue #124)."""
        # GIVEN: Un livre SANS URL Babelio en base
        livre_id = str(ObjectId())
        auteur_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = {
            "livre_id": livre_id,
            "titre": "Livre sans URL",
            "auteur_id": auteur_id,
            "auteur_nom": "Auteur Test",
            "editeur": "Editeur Test",
            "note_moyenne": None,
            "nombre_emissions": 0,
            "emissions": [],
        }

        # WHEN: On appelle GET /api/livre/{id}
        response = client.get(f"/api/livre/{livre_id}")

        # THEN: On reçoit un 200 sans url_babelio (ou avec None/null)
        assert response.status_code == 200
        data = response.json()
        assert data["livre_id"] == livre_id
        # url_babelio peut être absent ou None
        assert data.get("url_babelio") is None or "url_babelio" not in data
