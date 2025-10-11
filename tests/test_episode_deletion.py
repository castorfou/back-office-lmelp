"""Tests pour la suppression d'épisodes (Issue #82)."""

from unittest.mock import Mock, patch

import pytest
from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


@pytest.fixture
def mock_mongodb_service():
    """Crée un service MongoDB mocké pour les tests."""
    service = MongoDBService()

    # Mock database and collections
    mock_db = Mock()
    mock_episodes_collection = Mock()
    mock_avis_critiques_collection = Mock()
    mock_livres_collection = Mock()
    mock_auteurs_collection = Mock()

    service.db = mock_db
    service.episodes_collection = mock_episodes_collection
    service.avis_critiques_collection = mock_avis_critiques_collection
    service.livres_collection = mock_livres_collection
    service.auteurs_collection = mock_auteurs_collection

    return service


class TestEpisodeDeletion:
    """Tests pour la suppression d'épisodes."""

    def test_delete_episode_should_remove_episode_from_collection(
        self, mock_mongodb_service
    ):
        """Test que l'épisode est supprimé de la collection episodes."""
        # Arrange
        episode_id = "680c97e15a667de306e42042"
        mock_mongodb_service.episodes_collection.delete_one.return_value = Mock(
            deleted_count=1
        )

        # Act
        result = mock_mongodb_service.delete_episode(episode_id)

        # Assert
        assert result is True
        mock_mongodb_service.episodes_collection.delete_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)}
        )

    def test_delete_episode_should_return_false_when_episode_not_found(
        self, mock_mongodb_service
    ):
        """Test que la méthode retourne False si l'épisode n'existe pas."""
        # Arrange
        episode_id = "680c97e15a667de306e42042"
        mock_mongodb_service.episodes_collection.delete_one.return_value = Mock(
            deleted_count=0
        )

        # Act
        result = mock_mongodb_service.delete_episode(episode_id)

        # Assert
        assert result is False

    def test_delete_episode_should_delete_related_avis_critiques(
        self, mock_mongodb_service
    ):
        """Test que les avis critiques liés sont supprimés."""
        # Arrange
        episode_id = "680c97e15a667de306e42042"
        mock_mongodb_service.episodes_collection.delete_one.return_value = Mock(
            deleted_count=1
        )
        mock_mongodb_service.avis_critiques_collection.delete_many.return_value = Mock(
            deleted_count=5
        )

        # Act
        result = mock_mongodb_service.delete_episode(episode_id)

        # Assert
        assert result is True
        mock_mongodb_service.avis_critiques_collection.delete_many.assert_called_once_with(
            {"episode_oid": episode_id}
        )

    def test_delete_episode_should_remove_episode_reference_from_books(
        self, mock_mongodb_service
    ):
        """Test que les références à l'épisode sont retirées des livres."""
        # Arrange
        episode_id = "680c97e15a667de306e42042"
        mock_mongodb_service.episodes_collection.delete_one.return_value = Mock(
            deleted_count=1
        )
        mock_mongodb_service.livres_collection.update_many.return_value = Mock(
            modified_count=3
        )

        # Act
        result = mock_mongodb_service.delete_episode(episode_id)

        # Assert
        assert result is True
        # Vérifier que les références à l'épisode sont retirées du tableau episodes
        mock_mongodb_service.livres_collection.update_many.assert_called_once_with(
            {"episodes": episode_id}, {"$pull": {"episodes": episode_id}}
        )

    def test_delete_episode_should_handle_invalid_object_id(self, mock_mongodb_service):
        """Test que la méthode gère les ObjectId invalides."""
        from bson.errors import InvalidId

        # Arrange
        invalid_episode_id = "invalid_id"

        # Act & Assert
        with pytest.raises((InvalidId, Exception)):
            mock_mongodb_service.delete_episode(invalid_episode_id)

    def test_delete_episode_should_work_with_cascade_deletes(
        self, mock_mongodb_service
    ):
        """Test complet avec suppression en cascade."""
        # Arrange
        episode_id = "680c97e15a667de306e42042"

        # Mock successful deletions
        mock_mongodb_service.episodes_collection.delete_one.return_value = Mock(
            deleted_count=1
        )
        mock_mongodb_service.avis_critiques_collection.delete_many.return_value = Mock(
            deleted_count=2
        )
        mock_mongodb_service.livres_collection.update_many.return_value = Mock(
            modified_count=3
        )

        # Act
        result = mock_mongodb_service.delete_episode(episode_id)

        # Assert
        assert result is True

        # Vérifier toutes les opérations de cascade
        mock_mongodb_service.episodes_collection.delete_one.assert_called_once()
        mock_mongodb_service.avis_critiques_collection.delete_many.assert_called_once()
        mock_mongodb_service.livres_collection.update_many.assert_called_once()


class TestEpisodeDeletionAPI:
    """Tests pour l'endpoint API DELETE /api/episodes/{episode_id}."""

    @pytest.mark.asyncio
    async def test_delete_episode_endpoint_should_return_success(self):
        """Test que l'endpoint retourne un succès quand l'épisode est supprimé."""
        from fastapi.testclient import TestClient

        from back_office_lmelp.app import app

        episode_id = "680c97e15a667de306e42042"

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.delete_episode.return_value = True

            client = TestClient(app)
            response = client.delete(f"/api/episodes/{episode_id}")

            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["episode_id"] == episode_id

    @pytest.mark.asyncio
    async def test_delete_episode_endpoint_should_return_404_when_not_found(self):
        """Test que l'endpoint retourne 404 si l'épisode n'existe pas."""
        from fastapi.testclient import TestClient

        from back_office_lmelp.app import app

        episode_id = "680c97e15a667de306e42042"

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.delete_episode.return_value = False

            client = TestClient(app)
            response = client.delete(f"/api/episodes/{episode_id}")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_episode_endpoint_should_handle_invalid_id(self):
        """Test que l'endpoint gère les ID invalides."""
        from fastapi.testclient import TestClient

        from back_office_lmelp.app import app

        invalid_id = "invalid_id"

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.delete_episode.side_effect = Exception("Invalid ObjectId")

            client = TestClient(app)
            response = client.delete(f"/api/episodes/{invalid_id}")

            assert response.status_code == 500
