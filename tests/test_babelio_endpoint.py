"""Tests pour l'endpoint /api/verify-babelio."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestBabelioEndpoint:
    """Tests pour l'endpoint de vérification Babelio."""

    @pytest.fixture
    def client(self):
        """Client de test FastAPI."""
        return TestClient(app)

    def test_verify_author_success(self, client):
        """Test de vérification d'auteur réussie."""
        # Mock de la réponse du service
        mock_result = {
            "status": "verified",
            "original": "Michel Houellebecq",
            "babelio_suggestion": "Michel Houellebecq",
            "confidence_score": 1.0,
            "babelio_data": {"id": "2180", "ca_oeuvres": "38"},
            "babelio_url": "https://www.babelio.com/auteur/Michel-Houellebecq/2180",
            "error_message": None,
        }

        with patch(
            "back_office_lmelp.services.babelio_service.babelio_service.verify_author",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/api/verify-babelio",
                json={"type": "author", "name": "Michel Houellebecq"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "verified"
        assert data["original"] == "Michel Houellebecq"
        assert data["confidence_score"] == 1.0

    def test_verify_book_success(self, client):
        """Test de vérification de livre réussie."""
        mock_result = {
            "status": "verified",
            "original_title": "L'Étranger",
            "babelio_suggestion_title": "L'Étranger",
            "original_author": "Albert Camus",
            "babelio_suggestion_author": "Albert Camus",
            "confidence_score": 1.0,
            "babelio_data": {"id_oeuvre": "1234", "ca_copies": "10000"},
            "babelio_url": "https://www.babelio.com/livres/Camus-LEtranger/1234",
            "error_message": None,
        }

        with patch(
            "back_office_lmelp.services.babelio_service.babelio_service.verify_book",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/api/verify-babelio",
                json={"type": "book", "title": "L'Étranger", "author": "Albert Camus"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "verified"
        assert data["original_title"] == "L'Étranger"

    def test_verify_publisher_success(self, client):
        """Test de vérification d'éditeur réussie."""
        mock_result = {
            "status": "verified",
            "original": "Gallimard",
            "babelio_suggestion": "Gallimard",
            "confidence_score": 1.0,
            "babelio_data": {"id": "5678"},
            "babelio_url": "https://www.babelio.com/editeur/Gallimard/5678",
            "error_message": None,
        }

        with patch(
            "back_office_lmelp.services.babelio_service.babelio_service.verify_publisher",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/api/verify-babelio", json={"type": "publisher", "name": "Gallimard"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "verified"
        assert data["original"] == "Gallimard"

    def test_invalid_type(self, client):
        """Test avec un type invalide."""
        response = client.post(
            "/api/verify-babelio", json={"type": "invalid", "name": "Test"}
        )

        assert response.status_code == 400
        assert "Type invalide" in response.json()["detail"]

    def test_missing_author_name(self, client):
        """Test avec nom d'auteur manquant."""
        response = client.post("/api/verify-babelio", json={"type": "author"})

        assert response.status_code == 400
        assert "nom de l'auteur est requis" in response.json()["detail"]

    def test_missing_book_title(self, client):
        """Test avec titre de livre manquant."""
        response = client.post("/api/verify-babelio", json={"type": "book"})

        assert response.status_code == 400
        assert "titre du livre est requis" in response.json()["detail"]

    def test_service_error(self, client):
        """Test avec erreur du service."""
        with patch(
            "back_office_lmelp.services.babelio_service.babelio_service.verify_author",
            new_callable=AsyncMock,
            side_effect=Exception("Erreur réseau"),
        ):
            response = client.post(
                "/api/verify-babelio", json={"type": "author", "name": "Test Author"}
            )

        assert response.status_code == 500
        assert "Erreur serveur" in response.json()["detail"]
