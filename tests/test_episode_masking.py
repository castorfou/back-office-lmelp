"""Tests pour la fonctionnalité de masquage d'épisodes (Issue #107)."""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from back_office_lmelp.models.episode import Episode
from back_office_lmelp.services.mongodb_service import MongoDBService


class TestEpisodeMasking:
    """Tests pour le masquage d'épisodes."""

    @pytest.fixture
    def mongodb_service(self):
        """Create a MongoDB service instance for testing."""
        service = MongoDBService()
        # Mock the collection to avoid real database connections
        service.episodes_collection = MagicMock()
        return service

    def test_update_episode_masked_status_to_true(self, mongodb_service):
        """Test masquage d'un épisode (masked=True)."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mongodb_service.episodes_collection.update_one = MagicMock(
            return_value=mock_result
        )

        # Act
        result = mongodb_service.update_episode_masked_status(episode_id, True)

        # Assert
        assert result is True
        mongodb_service.episodes_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)},
            {"$set": {"masked": True}},
        )

    def test_update_episode_masked_status_to_false(self, mongodb_service):
        """Test démasquage d'un épisode (masked=False)."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_result.modified_count = 1
        mongodb_service.episodes_collection.update_one = MagicMock(
            return_value=mock_result
        )

        # Act
        result = mongodb_service.update_episode_masked_status(episode_id, False)

        # Assert
        assert result is True
        mongodb_service.episodes_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)},
            {"$set": {"masked": False}},
        )

    def test_update_episode_masked_status_not_found(self, mongodb_service):
        """Test masquage d'un épisode inexistant."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mock_result = MagicMock()
        mock_result.matched_count = 0
        mock_result.modified_count = 0
        mongodb_service.episodes_collection.update_one = MagicMock(
            return_value=mock_result
        )

        # Act
        result = mongodb_service.update_episode_masked_status(episode_id, True)

        # Assert
        assert result is False

    def test_update_episode_masked_status_idempotent(self, mongodb_service):
        """Test que le masquage est idempotent (succès même si déjà dans l'état voulu)."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mock_result = MagicMock()
        mock_result.matched_count = 1  # L'épisode existe
        mock_result.modified_count = 0  # Mais aucune modification (déjà dans l'état)
        mongodb_service.episodes_collection.update_one = MagicMock(
            return_value=mock_result
        )

        # Act
        result = mongodb_service.update_episode_masked_status(episode_id, False)

        # Assert - Doit retourner True car l'épisode existe et est dans l'état voulu
        assert result is True
        mongodb_service.episodes_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)},
            {"$set": {"masked": False}},
        )

    def test_get_all_episodes_excludes_masked_by_default(self, mongodb_service):
        """Test que get_all_episodes exclut les épisodes masqués par défaut."""
        # Arrange - créer des épisodes simulés (un masqué, un non-masqué)
        mock_episodes = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),  # pragma: allowlist secret
                "titre": "Episode visible",
                "date": "2024-01-01",
                "type": "livre",
                "masked": False,
            },
            # L'épisode masqué ne devrait pas être retourné
        ]

        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter(mock_episodes))
        mock_find = MagicMock(return_value=mock_cursor)
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mongodb_service.episodes_collection.find = mock_find

        # Act
        result = mongodb_service.get_all_episodes()

        # Assert
        # Vérifier que le filtre {"masked": {"$ne": True}} est appliqué
        mongodb_service.episodes_collection.find.assert_called_once()
        call_args = mongodb_service.episodes_collection.find.call_args
        filter_query = call_args[0][0]
        assert "masked" in filter_query
        assert filter_query["masked"] == {"$ne": True}
        assert len(result) == 1
        assert result[0]["titre"] == "Episode visible"

    def test_get_all_episodes_with_include_masked_true(self, mongodb_service):
        """Test que get_all_episodes peut inclure les épisodes masqués."""
        # Arrange
        mock_episodes = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),  # pragma: allowlist secret
                "titre": "Episode visible",
                "date": "2024-01-01",
                "type": "livre",
                "masked": False,
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),  # pragma: allowlist secret
                "titre": "Episode masque",
                "date": "2024-01-02",
                "type": "livre",
                "masked": True,
            },
        ]

        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter(mock_episodes))
        mock_find = MagicMock(return_value=mock_cursor)
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mongodb_service.episodes_collection.find = mock_find

        # Act
        result = mongodb_service.get_all_episodes(include_masked=True)

        # Assert
        # Vérifier qu'aucun filtre masked n'est appliqué
        mongodb_service.episodes_collection.find.assert_called_once()
        call_args = mongodb_service.episodes_collection.find.call_args
        filter_query = call_args[0][0]
        assert "masked" not in filter_query
        assert len(result) == 2


class TestEpisodeModel:
    """Tests pour le modèle Episode avec le champ masked."""

    def test_episode_model_with_masked_true(self):
        """Test que le modèle Episode gère le champ masked=True."""
        # Arrange
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Episode masque",
            "date": None,
            "type": "livre",
            "description": "Description",
            "masked": True,
        }

        # Act
        episode = Episode(data)

        # Assert
        assert episode.masked is True
        assert episode.titre == "Episode masque"

    def test_episode_model_with_masked_false(self):
        """Test que le modèle Episode gère le champ masked=False."""
        # Arrange
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Episode visible",
            "date": None,
            "type": "livre",
            "description": "Description",
            "masked": False,
        }

        # Act
        episode = Episode(data)

        # Assert
        assert episode.masked is False

    def test_episode_model_without_masked_defaults_to_false(self):
        """Test que le modèle Episode définit masked=False par défaut."""
        # Arrange
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Episode sans champ masked",
            "date": None,
            "type": "livre",
            "description": "Description",
        }

        # Act
        episode = Episode(data)

        # Assert
        assert episode.masked is False

    def test_episode_to_dict_includes_masked(self):
        """Test que to_dict() inclut le champ masked."""
        # Arrange
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Episode",
            "date": None,
            "type": "livre",
            "description": "Description",
            "masked": True,
        }
        episode = Episode(data)

        # Act
        result = episode.to_dict()

        # Assert
        assert "masked" in result
        assert result["masked"] is True

    def test_episode_to_summary_dict_includes_masked(self):
        """Test que to_summary_dict() inclut le champ masked."""
        # Arrange
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Episode",
            "date": None,
            "type": "livre",
            "description": "Description",
            "masked": True,
        }
        episode = Episode(data)

        # Act
        result = episode.to_summary_dict()

        # Assert
        assert "masked" in result
        assert result["masked"] is True

    def test_episode_to_summary_dict_includes_duree(self):
        """Test que to_summary_dict() inclut le champ duree (Issue #107)."""
        # Arrange
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Episode avec duree",
            "date": None,
            "type": "livre",
            "description": "Description",
            "duree": 2763,  # Durée en secondes
            "masked": False,
        }
        episode = Episode(data)

        # Act
        result = episode.to_summary_dict()

        # Assert
        assert "duree" in result
        assert result["duree"] == 2763

    def test_episode_to_summary_dict_with_duree_none(self):
        """Test que to_summary_dict() gère duree=None."""
        # Arrange
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Episode sans duree",
            "date": None,
            "type": "livre",
            "description": "Description",
            "masked": False,
        }
        episode = Episode(data)

        # Act
        result = episode.to_summary_dict()

        # Assert
        assert "duree" in result
        assert result["duree"] is None
