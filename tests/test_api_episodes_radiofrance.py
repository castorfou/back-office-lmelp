"""Tests pour l'endpoint API de fetch RadioFrance episode page URL.

Ce module teste l'endpoint POST /api/episodes/{episode_id}/fetch-page-url
qui permet de récupérer automatiquement l'URL de la page RadioFrance d'un épisode.

Architecture testée:
- Endpoint: POST /api/episodes/{episode_id}/fetch-page-url
- Service: RadioFranceService pour le scraping
- MongoDB: Mise à jour du champ episode_page_url
- Retour: URL de la page ou erreur si non trouvée

Tests TDD avec mocks complets (pas de vraie DB/réseau).
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Fixture pour créer un client de test FastAPI."""
    from back_office_lmelp.app import app

    return TestClient(app)


class TestFetchEpisodePageURL:
    """Tests de l'endpoint POST /api/episodes/{episode_id}/fetch-page-url."""

    def test_fetch_episode_page_url_success(self, client):
        """
        Test de fetch réussi avec mise à jour en base.

        GIVEN: Un episode_id valide dans MongoDB
        WHEN: POST /api/episodes/{episode_id}/fetch-page-url est appelé
        THEN: RadioFranceService trouve l'URL et la persiste en DB
        """
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        episode_title = "Les nouvelles pages de Gaël Faye"
        found_url = "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/episode-123"

        # Mock mongodb_service.get_episode_by_id
        mock_episode = {
            "_id": episode_id,
            "titre": episode_title,
            "emission": "Le Masque et la Plume",
        }

        # Mock RadioFranceService
        with (
            patch(
                "back_office_lmelp.app.mongodb_service.get_episode_by_id",
                return_value=mock_episode,
            ),
            patch(
                "back_office_lmelp.app.mongodb_service.update_episode"
            ) as mock_update,
            patch(
                "back_office_lmelp.services.radiofrance_service.RadioFranceService.search_episode_page_url",
                new_callable=AsyncMock,
                return_value=found_url,
            ),
        ):
            # Act
            response = client.post(f"/api/episodes/{episode_id}/fetch-page-url")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["episode_id"] == episode_id
            assert data["episode_page_url"] == found_url
            assert data["success"] is True

            # Vérifier que update_episode a été appelé avec la bonne URL
            mock_update.assert_called_once()
            call_args = mock_update.call_args[0]
            assert call_args[0] == episode_id
            assert call_args[1]["episode_page_url"] == found_url

    def test_fetch_episode_page_url_not_found_in_radiofrance(self, client):
        """
        Test quand RadioFrance ne trouve pas l'épisode.

        GIVEN: Un episode_id valide mais titre introuvable sur RadioFrance
        WHEN: POST /api/episodes/{episode_id}/fetch-page-url est appelé
        THEN: Retourne 404 avec message explicite
        """
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        episode_title = "Episode inexistant XYZ123"

        mock_episode = {
            "_id": episode_id,
            "titre": episode_title,
            "emission": "Le Masque et la Plume",
        }

        with (
            patch(
                "back_office_lmelp.app.mongodb_service.get_episode_by_id",
                return_value=mock_episode,
            ),
            patch(
                "back_office_lmelp.services.radiofrance_service.RadioFranceService.search_episode_page_url",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            # Act
            response = client.post(f"/api/episodes/{episode_id}/fetch-page-url")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "non trouvée sur RadioFrance" in data["detail"]

    def test_fetch_episode_page_url_episode_not_in_db(self, client):
        """
        Test quand l'épisode n'existe pas en base.

        GIVEN: Un episode_id inexistant
        WHEN: POST /api/episodes/{episode_id}/fetch-page-url est appelé
        THEN: Retourne 404 avec message explicite
        """
        episode_id = "000000000000000000000000"  # pragma: allowlist secret

        with patch(
            "back_office_lmelp.app.mongodb_service.get_episode_by_id",
            return_value=None,
        ):
            # Act
            response = client.post(f"/api/episodes/{episode_id}/fetch-page-url")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "non trouvé" in data["detail"]
