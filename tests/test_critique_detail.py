"""Tests for GET /api/critique/{critique_id} endpoint (Issue #191)."""

from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestGetCritiqueDetail:
    """Tests pour l'endpoint GET /api/critique/{critique_id}."""

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_critique_returns_info_with_stats_and_oeuvres(
        self, mock_mongodb_service, client
    ):
        """Test que GET /api/critique/{id} retourne les détails avec stats et oeuvres."""
        # GIVEN: Un critique avec des avis en base
        critique_id = str(ObjectId())
        mock_mongodb_service.get_critique_detail.return_value = {
            "critique_id": critique_id,
            "nom": "Arnaud Viviant",
            "animateur": False,
            "variantes": ["Arnaud Vivian"],
            "nombre_avis": 2,
            "note_moyenne": 8.5,
            "note_distribution": {
                "2": 0,
                "3": 0,
                "4": 0,
                "5": 0,
                "6": 0,
                "7": 0,
                "8": 1,
                "9": 1,
                "10": 0,
            },
            "coups_de_coeur": [
                {
                    "livre_oid": str(ObjectId()),
                    "livre_titre": "Combats de filles",
                    "auteur_nom": "Rita Bullwinkel",
                    "auteur_oid": str(ObjectId()),
                    "editeur": "La Croisée",
                    "note": 9,
                    "commentaire": "Très belle découverte",
                    "section": "programme",
                    "emission_date": "2026-01-18",
                    "emission_oid": str(ObjectId()),
                }
            ],
            "oeuvres": [
                {
                    "livre_oid": str(ObjectId()),
                    "livre_titre": "Combats de filles",
                    "auteur_nom": "Rita Bullwinkel",
                    "auteur_oid": str(ObjectId()),
                    "editeur": "La Croisée",
                    "note": 9,
                    "commentaire": "Très belle découverte",
                    "section": "programme",
                    "emission_date": "2026-01-18",
                    "emission_oid": str(ObjectId()),
                },
                {
                    "livre_oid": str(ObjectId()),
                    "livre_titre": "Le Grand Vertige",
                    "auteur_nom": "Pierre Ducrozet",
                    "auteur_oid": str(ObjectId()),
                    "editeur": "Actes Sud",
                    "note": 8,
                    "commentaire": "Roman ambitieux",
                    "section": "programme",
                    "emission_date": "2025-12-14",
                    "emission_oid": str(ObjectId()),
                },
            ],
        }

        # WHEN: On appelle GET /api/critique/{id}
        response = client.get(f"/api/critique/{critique_id}")

        # THEN: On reçoit un 200 avec les données enrichies
        assert response.status_code == 200
        data = response.json()
        assert data["critique_id"] == critique_id
        assert data["nom"] == "Arnaud Viviant"
        assert data["animateur"] is False
        assert data["variantes"] == ["Arnaud Vivian"]
        assert data["nombre_avis"] == 2
        assert data["note_moyenne"] == 8.5
        assert "note_distribution" in data
        assert data["note_distribution"]["9"] == 1
        assert data["note_distribution"]["8"] == 1
        assert len(data["coups_de_coeur"]) == 1
        assert data["coups_de_coeur"][0]["note"] >= 9
        assert len(data["oeuvres"]) == 2

        # Vérifier que le service a été appelé avec le bon ID
        mock_mongodb_service.get_critique_detail.assert_called_once_with(critique_id)

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_critique_returns_404_when_not_found(
        self, mock_mongodb_service, client
    ):
        """Test que GET /api/critique/{id} retourne 404 si le critique n'existe pas."""
        # GIVEN: Un critique inexistant
        critique_id = str(ObjectId())
        mock_mongodb_service.get_critique_detail.return_value = None

        # WHEN: On appelle GET /api/critique/{id}
        response = client.get(f"/api/critique/{critique_id}")

        # THEN: On reçoit un 404
        assert response.status_code == 404
        assert "Critique non trouvé" in response.json()["detail"]

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_critique_validates_objectid_format(self, mock_mongodb_service, client):
        """Test que l'endpoint valide le format ObjectId."""
        # GIVEN: Un ID invalide (trop court)
        invalid_id = "invalid_id_format"

        # WHEN: On appelle GET /api/critique/{invalid_id}
        response = client.get(f"/api/critique/{invalid_id}")

        # THEN: On reçoit une erreur 404
        assert response.status_code == 404
        assert "Critique non trouvé" in response.json()["detail"]

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_critique_returns_critique_with_no_avis(
        self, mock_mongodb_service, client
    ):
        """Test qu'un critique sans avis retourne des listes vides et stats null."""
        # GIVEN: Un critique sans aucun avis
        critique_id = str(ObjectId())
        mock_mongodb_service.get_critique_detail.return_value = {
            "critique_id": critique_id,
            "nom": "Nouveau Critique",
            "animateur": False,
            "variantes": [],
            "nombre_avis": 0,
            "note_moyenne": None,
            "note_distribution": {
                "2": 0,
                "3": 0,
                "4": 0,
                "5": 0,
                "6": 0,
                "7": 0,
                "8": 0,
                "9": 0,
                "10": 0,
            },
            "coups_de_coeur": [],
            "oeuvres": [],
        }

        # WHEN: On appelle GET /api/critique/{id}
        response = client.get(f"/api/critique/{critique_id}")

        # THEN: On reçoit un 200 avec des listes vides
        assert response.status_code == 200
        data = response.json()
        assert data["nombre_avis"] == 0
        assert data["note_moyenne"] is None
        assert data["coups_de_coeur"] == []
        assert data["oeuvres"] == []

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_critique_returns_animateur_flag(self, mock_mongodb_service, client):
        """Test que le flag animateur est correctement retourné."""
        # GIVEN: Un critique qui est aussi animateur
        critique_id = str(ObjectId())
        mock_mongodb_service.get_critique_detail.return_value = {
            "critique_id": critique_id,
            "nom": "Jérôme Garcin",
            "animateur": True,
            "variantes": [],
            "nombre_avis": 100,
            "note_moyenne": 7.0,
            "note_distribution": {str(i): 0 for i in range(2, 11)},
            "coups_de_coeur": [],
            "oeuvres": [],
        }

        # WHEN: On appelle GET /api/critique/{id}
        response = client.get(f"/api/critique/{critique_id}")

        # THEN: Le flag animateur est True
        assert response.status_code == 200
        data = response.json()
        assert data["animateur"] is True
        assert data["nom"] == "Jérôme Garcin"
