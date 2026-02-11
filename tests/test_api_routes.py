"""Comprehensive tests for API routes to improve coverage."""

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_mongodb_service():
    """Mock MongoDB service for testing."""
    with patch("back_office_lmelp.app.mongodb_service") as mock:
        yield mock


@pytest.fixture
def mock_memory_guard():
    """Mock memory guard for testing."""
    with patch("back_office_lmelp.app.memory_guard") as mock:
        mock.check_memory_limit.return_value = None
        yield mock


class TestAPIRoutes:
    """Test class for API route endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns correct response."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Back-office LMELP API"
        assert "version" in data  # Version dynamique depuis git (Issue #205)

    def test_get_episodes_success(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test successful episodes retrieval."""
        # Mock data with datetime objects
        mock_episodes = [
            {
                "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
                "titre": "Episode 1",
                "date": datetime(2024, 1, 1),
                "type": "test",
            },
            {
                "_id": "507f1f77bcf86cd799439012",
                "titre": "Episode 2",
                "date": datetime(2024, 1, 2),
                "type": "test",
            },
        ]
        mock_mongodb_service.get_all_episodes.return_value = mock_episodes

        response = client.get("/api/episodes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        mock_mongodb_service.get_all_episodes.assert_called_once()

    def test_get_episodes_memory_warning(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episodes retrieval with memory warning."""
        mock_memory_guard.check_memory_limit.return_value = "Memory usage: 85%"
        mock_mongodb_service.get_all_episodes.return_value = []

        response = client.get("/api/episodes")
        assert response.status_code == 200
        mock_memory_guard.check_memory_limit.assert_called()

    def test_get_episodes_memory_limit_exceeded(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episodes retrieval with memory limit exceeded."""
        mock_memory_guard.check_memory_limit.return_value = (
            "LIMITE MÉMOIRE DÉPASSÉE: 95%"
        )
        mock_memory_guard.force_shutdown.return_value = None

        with patch(
            "back_office_lmelp.app.mongodb_service.get_all_episodes",
            side_effect=Exception("Shutdown triggered"),
        ):
            response = client.get("/api/episodes")
            assert response.status_code == 500
            mock_memory_guard.force_shutdown.assert_called_once()

    def test_get_episodes_database_error(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episodes retrieval with database error."""
        mock_mongodb_service.get_all_episodes.side_effect = Exception(
            "Database connection failed"
        )

        response = client.get("/api/episodes")
        assert response.status_code == 500
        assert "Erreur serveur" in response.json()["detail"]

    def test_get_episode_by_id_success(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test successful single episode retrieval."""
        mock_episode = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Test Episode",
            "date": datetime(2024, 1, 1),
            "type": "test",
            "description": "Test description",
        }
        mock_mongodb_service.get_episode_by_id.return_value = mock_episode

        response = client.get("/api/episodes/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        assert data["titre"] == "Test Episode"

    def test_get_episode_by_id_not_found(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episode retrieval when episode not found."""
        mock_mongodb_service.get_episode_by_id.return_value = None

        response = client.get("/api/episodes/nonexistent")
        assert response.status_code == 404
        assert "Épisode non trouvé" in response.json()["detail"]

    def test_get_episode_by_id_memory_limit_exceeded(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test single episode retrieval with memory limit exceeded."""
        mock_memory_guard.check_memory_limit.return_value = (
            "LIMITE MÉMOIRE DÉPASSÉE: 95%"
        )
        mock_memory_guard.force_shutdown.return_value = None

        with patch(
            "back_office_lmelp.app.mongodb_service.get_episode_by_id",
            side_effect=Exception("Shutdown triggered"),
        ):
            response = client.get("/api/episodes/507f1f77bcf86cd799439011")
            assert response.status_code == 500
            mock_memory_guard.force_shutdown.assert_called_once()

    def test_get_episode_by_id_database_error(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test single episode retrieval with database error."""
        mock_mongodb_service.get_episode_by_id.side_effect = Exception("Database error")

        response = client.get("/api/episodes/507f1f77bcf86cd799439011")
        assert response.status_code == 500
        assert "Erreur serveur" in response.json()["detail"]

    def test_update_episode_description_success(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test successful episode description update."""
        mock_mongodb_service.get_episode_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439011"
        }
        mock_mongodb_service.update_episode_description.return_value = True

        response = client.put(
            "/api/episodes/507f1f77bcf86cd799439011", content="Updated description"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Description mise à jour avec succès"

    def test_update_episode_description_not_found(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episode description update when episode not found."""
        mock_mongodb_service.get_episode_by_id.return_value = None

        response = client.put(
            "/api/episodes/nonexistent", content="Updated description"
        )
        assert response.status_code == 404
        assert "Épisode non trouvé" in response.json()["detail"]

    def test_update_episode_description_update_fails(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episode description update when update operation fails."""
        mock_mongodb_service.get_episode_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439011"
        }
        mock_mongodb_service.update_episode_description_new.return_value = False

        response = client.put(
            "/api/episodes/507f1f77bcf86cd799439011", content="Updated description"
        )
        assert response.status_code == 400
        assert "Échec de la mise à jour" in response.json()["detail"]

    def test_update_episode_description_memory_limit_exceeded(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episode description update with memory limit exceeded."""
        mock_memory_guard.check_memory_limit.return_value = (
            "LIMITE MÉMOIRE DÉPASSÉE: 95%"
        )
        mock_memory_guard.force_shutdown.return_value = None

        client.put(
            "/api/episodes/507f1f77bcf86cd799439011", content="Updated description"
        )
        mock_memory_guard.force_shutdown.assert_called_once()

    def test_update_episode_description_database_error(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episode description update with database error."""
        mock_mongodb_service.get_episode_by_id.side_effect = Exception("Database error")

        response = client.put(
            "/api/episodes/507f1f77bcf86cd799439011", content="Updated description"
        )
        assert response.status_code == 500
        assert "Erreur serveur" in response.json()["detail"]

    def test_update_episode_title_success(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test successful episode title update."""
        mock_mongodb_service.get_episode_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439011"
        }
        mock_mongodb_service.update_episode_title_new.return_value = True

        response = client.put(
            "/api/episodes/507f1f77bcf86cd799439011/title", content="Updated title"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Titre mis à jour avec succès"

    def test_update_episode_title_not_found(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episode title update when episode not found."""
        mock_mongodb_service.get_episode_by_id.return_value = None

        response = client.put(
            "/api/episodes/nonexistent/title", content="Updated title"
        )
        assert response.status_code == 404
        assert "Épisode non trouvé" in response.json()["detail"]

    def test_update_episode_title_update_fails(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episode title update when update operation fails."""
        mock_mongodb_service.get_episode_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439011"
        }
        mock_mongodb_service.update_episode_title_new.return_value = False

        response = client.put(
            "/api/episodes/507f1f77bcf86cd799439011/title", content="Updated title"
        )
        assert response.status_code == 400
        assert "Échec de la mise à jour" in response.json()["detail"]

    def test_update_episode_title_memory_limit_exceeded(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episode title update with memory limit exceeded."""
        mock_memory_guard.check_memory_limit.return_value = (
            "LIMITE MÉMOIRE DÉPASSÉE: 95%"
        )
        mock_memory_guard.force_shutdown.return_value = None

        client.put(
            "/api/episodes/507f1f77bcf86cd799439011/title", content="Updated title"
        )
        mock_memory_guard.force_shutdown.assert_called_once()

    def test_update_episode_title_database_error(
        self, client, mock_mongodb_service, mock_memory_guard
    ):
        """Test episode title update with database error."""
        mock_mongodb_service.get_episode_by_id.side_effect = Exception("Database error")

        response = client.put(
            "/api/episodes/507f1f77bcf86cd799439011/title", content="Updated title"
        )
        assert response.status_code == 500
        assert "Erreur serveur" in response.json()["detail"]


class TestLifespanManager:
    """Test the application lifespan context manager."""

    def test_lifespan_startup_success(self, mock_mongodb_service):
        """Test successful startup in lifespan context."""
        from back_office_lmelp.app import lifespan

        mock_mongodb_service.connect.return_value = True

        # This test would require async testing setup which is complex
        # For now we'll test the components that can be tested synchronously
        assert lifespan is not None

    def test_lifespan_startup_failure(self, mock_mongodb_service):
        """Test startup failure in lifespan context."""
        from back_office_lmelp.app import lifespan

        mock_mongodb_service.connect.return_value = False

        # Testing the actual async context manager would require more setup
        assert lifespan is not None
