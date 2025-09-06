"""Tests pour l'endpoint de statistiques."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.services.mongodb_service import mongodb_service


@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)


@pytest.fixture
def mock_mongodb_service():
    """Mock du service MongoDB."""
    with patch.object(mongodb_service, "get_statistics") as mock_stats:
        yield mock_stats


class TestStatisticsEndpoint:
    """Tests pour l'endpoint GET /api/statistics."""

    def test_get_statistics_success(self, client, mock_mongodb_service):
        """Test de récupération des statistiques avec succès."""
        # Données de test
        mock_stats_data = {
            "total_episodes": 142,
            "episodes_with_corrected_titles": 37,
            "episodes_with_corrected_descriptions": 45,
            "last_update_date": "2025-09-06T10:30:00Z",
        }

        mock_mongodb_service.return_value = mock_stats_data

        # Appel de l'API
        response = client.get("/api/statistics")

        # Vérifications
        assert response.status_code == 200
        data = response.json()

        assert data["totalEpisodes"] == 142
        assert data["episodesWithCorrectedTitles"] == 37
        assert data["episodesWithCorrectedDescriptions"] == 45
        assert data["lastUpdateDate"] == "2025-09-06T10:30:00Z"

        # Vérifier que le service a été appelé
        mock_mongodb_service.assert_called_once()

    def test_get_statistics_empty_database(self, client, mock_mongodb_service):
        """Test avec une base de données vide."""
        mock_stats_data = {
            "total_episodes": 0,
            "episodes_with_corrected_titles": 0,
            "episodes_with_corrected_descriptions": 0,
            "last_update_date": None,
        }

        mock_mongodb_service.return_value = mock_stats_data

        response = client.get("/api/statistics")

        assert response.status_code == 200
        data = response.json()

        assert data["totalEpisodes"] == 0
        assert data["episodesWithCorrectedTitles"] == 0
        assert data["episodesWithCorrectedDescriptions"] == 0
        assert data["lastUpdateDate"] is None

    def test_get_statistics_database_error(self, client, mock_mongodb_service):
        """Test de gestion d'erreur de base de données."""
        mock_mongodb_service.side_effect = Exception("Erreur de connexion MongoDB")

        response = client.get("/api/statistics")

        assert response.status_code == 500
        data = response.json()
        assert "Erreur serveur" in data["detail"]
        assert "MongoDB" in data["detail"]

    @patch("back_office_lmelp.utils.memory_guard.memory_guard")
    def test_get_statistics_with_memory_check(
        self, mock_memory_guard, client, mock_mongodb_service
    ):
        """Test que la vérification mémoire est effectuée."""
        mock_memory_guard.check_memory_limit.return_value = None

        mock_stats_data = {
            "total_episodes": 10,
            "episodes_with_corrected_titles": 5,
            "episodes_with_corrected_descriptions": 3,
            "last_update_date": "2025-09-06T10:30:00Z",
        }
        mock_mongodb_service.return_value = mock_stats_data

        response = client.get("/api/statistics")

        assert response.status_code == 200
        mock_memory_guard.check_memory_limit.assert_called_once()

    @patch("back_office_lmelp.utils.memory_guard.memory_guard")
    def test_get_statistics_memory_limit_exceeded(
        self, mock_memory_guard, client, mock_mongodb_service
    ):
        """Test de l'arrêt d'urgence si limite mémoire dépassée."""
        mock_memory_guard.check_memory_limit.return_value = (
            "LIMITE MÉMOIRE DÉPASSÉE: 600MB"
        )
        mock_memory_guard.force_shutdown = MagicMock()

        client.get("/api/statistics")

        # L'endpoint devrait forcer l'arrêt mais ne pas retourner de réponse normale
        mock_memory_guard.force_shutdown.assert_called_once_with(
            "LIMITE MÉMOIRE DÉPASSÉE: 600MB"
        )
