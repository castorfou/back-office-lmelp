"""Tests for GET /api/auteur/{auteur_id} endpoint (Issue #96 - Phase 1)."""

from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestGetAuteurDetail:
    """Tests pour l'endpoint GET /api/auteur/{auteur_id}."""

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_auteur_returns_author_with_books(self, mock_mongodb_service, client):
        """Test que GET /api/auteur/{id} retourne les détails d'un auteur avec ses livres."""
        # GIVEN: Un auteur avec plusieurs livres en base
        auteur_id = str(ObjectId())
        mock_mongodb_service.get_auteur_with_livres.return_value = {
            "auteur_id": auteur_id,
            "nom": "Emmanuel Carrère",
            "nombre_oeuvres": 3,
            "livres": [
                {
                    "livre_id": str(ObjectId()),
                    "titre": "L'Adversaire",
                    "editeur": "Gallimard",
                },
                {
                    "livre_id": str(ObjectId()),
                    "titre": "Limonov",
                    "editeur": "P.O.L",
                },
                {
                    "livre_id": str(ObjectId()),
                    "titre": "Yoga",
                    "editeur": "P.O.L",
                },
            ],
        }

        # WHEN: On appelle GET /api/auteur/{id}
        response = client.get(f"/api/auteur/{auteur_id}")

        # THEN: On reçoit un 200 avec les données de l'auteur
        assert response.status_code == 200
        data = response.json()
        assert data["auteur_id"] == auteur_id
        assert data["nom"] == "Emmanuel Carrère"
        assert data["nombre_oeuvres"] == 3
        assert len(data["livres"]) == 3
        assert data["livres"][0]["titre"] == "L'Adversaire"
        assert data["livres"][1]["titre"] == "Limonov"
        assert data["livres"][2]["titre"] == "Yoga"

        # Vérifier que le service a été appelé avec le bon ID
        mock_mongodb_service.get_auteur_with_livres.assert_called_once_with(auteur_id)

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_auteur_returns_404_when_not_found(self, mock_mongodb_service, client):
        """Test que GET /api/auteur/{id} retourne 404 si l'auteur n'existe pas."""
        # GIVEN: Un auteur inexistant
        auteur_id = str(ObjectId())
        mock_mongodb_service.get_auteur_with_livres.return_value = None

        # WHEN: On appelle GET /api/auteur/{id}
        response = client.get(f"/api/auteur/{auteur_id}")

        # THEN: On reçoit un 404
        assert response.status_code == 404
        assert "Auteur non trouvé" in response.json()["detail"]

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_auteur_returns_author_with_no_books(
        self, mock_mongodb_service, client
    ):
        """Test qu'un auteur sans livres retourne une liste vide."""
        # GIVEN: Un auteur sans livres
        auteur_id = str(ObjectId())
        mock_mongodb_service.get_auteur_with_livres.return_value = {
            "auteur_id": auteur_id,
            "nom": "Nouvel Auteur",
            "nombre_oeuvres": 0,
            "livres": [],
        }

        # WHEN: On appelle GET /api/auteur/{id}
        response = client.get(f"/api/auteur/{auteur_id}")

        # THEN: On reçoit un 200 avec une liste de livres vide
        assert response.status_code == 200
        data = response.json()
        assert data["nombre_oeuvres"] == 0
        assert data["livres"] == []

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_auteur_validates_objectid_format(self, mock_mongodb_service, client):
        """Test que l'endpoint valide le format ObjectId."""
        # GIVEN: Un ID invalide
        invalid_id = "invalid_id_format"

        # WHEN: On appelle GET /api/auteur/{invalid_id}
        response = client.get(f"/api/auteur/{invalid_id}")

        # THEN: On reçoit une erreur 400 ou 422
        assert response.status_code in [400, 422]
