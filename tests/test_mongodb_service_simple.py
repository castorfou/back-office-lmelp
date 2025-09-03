"""Tests simplifiés pour le service MongoDB synchrone."""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


class TestMongoDBServiceSimple:
    """Tests pour le service MongoDB synchrone."""

    @pytest.fixture
    def mongodb_service(self):
        """Create a MongoDB service instance for testing."""
        service = MongoDBService()
        # Mock the collection to avoid real database connections
        service.episodes_collection = MagicMock()
        return service

    def test_update_episode_description_success(self, mongodb_service):
        """Test mise à jour réussie de la description d'un épisode."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        new_description = "Nouvelle description corrigée"
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mongodb_service.episodes_collection.update_one = MagicMock(
            return_value=mock_result
        )

        # Act
        result = mongodb_service.update_episode_description(episode_id, new_description)

        # Assert
        assert result is True
        mongodb_service.episodes_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)},
            {"$set": {"description_corrigee": new_description}},
        )

    def test_update_episode_title_success(self, mongodb_service):
        """Test mise à jour réussie du titre d'un épisode."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        new_title = "Nouveau titre corrigé"
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mongodb_service.episodes_collection.update_one = MagicMock(
            return_value=mock_result
        )

        # Act
        result = mongodb_service.update_episode_title(episode_id, new_title)

        # Assert
        assert result is True
        mongodb_service.episodes_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)},
            {"$set": {"titre_corrige": new_title}},
        )

    def test_update_episode_title_failure(self, mongodb_service):
        """Test échec de mise à jour du titre d'un épisode."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        new_title = "Nouveau titre corrigé"
        mock_result = MagicMock()
        mock_result.modified_count = 0  # No document modified
        mongodb_service.episodes_collection.update_one = MagicMock(
            return_value=mock_result
        )

        # Act
        result = mongodb_service.update_episode_title(episode_id, new_title)

        # Assert
        assert result is False

    def test_insert_episode_success(self, mongodb_service):
        """Test insertion réussie d'un épisode."""
        # Arrange
        episode_data = {"titre": "Test Episode", "description": "Test description"}
        mock_result = MagicMock()
        inserted_id = ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret
        mock_result.inserted_id = inserted_id
        mongodb_service.episodes_collection.insert_one = MagicMock(
            return_value=mock_result
        )

        # Act
        result = mongodb_service.insert_episode(episode_data)

        # Assert
        assert result == str(inserted_id)
        mongodb_service.episodes_collection.insert_one.assert_called_once_with(
            episode_data
        )
