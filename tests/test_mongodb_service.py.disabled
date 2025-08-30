"""Tests pour le service MongoDB du Back-Office LMELP."""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from bson.errors import InvalidId

from back_office_lmelp.services.mongodb_service import MongoDBService


class TestMongoDBService:
    """Tests pour le service MongoDB."""

    @pytest.fixture
    def mongodb_service(self):
        """Create a MongoDB service instance for testing."""
        service = MongoDBService()
        # Mock the collection to avoid real database connections
        service.episodes_collection = MagicMock()
        return service

    def test_get_all_episodes(self, mongodb_service):
        """Test récupération de tous les épisodes."""
        # Arrange
        mock_episodes = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "titre": "Episode 1",
            },  # pragma: allowlist secret
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "titre": "Episode 2",
            },  # pragma: allowlist secret
        ]
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_episodes
        mongodb_service.episodes_collection.find.return_value = mock_cursor

        # Act
        result = mongodb_service.get_all_episodes()

        # Assert
        assert len(result) == 2
        assert result[0]["titre"] == "Episode 1"
        assert result[1]["titre"] == "Episode 2"
        mongodb_service.episodes_collection.find.assert_called_once()

    def test_get_episode_by_id_valid(self, mongodb_service):
        """Test récupération d'un épisode par ID valide."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mock_episode = {"_id": ObjectId(episode_id), "titre": "Test Episode"}
        mongodb_service.episodes_collection.find_one = MagicMock(
            return_value=mock_episode
        )

        # Act
        result = mongodb_service.get_episode_by_id(episode_id)

        # Assert
        assert result is not None
        assert result["titre"] == "Test Episode"
        mongodb_service.episodes_collection.find_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)}
        )

    def test_get_episode_by_id_not_found(self, mongodb_service):
        """Test récupération d'un épisode inexistant."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mongodb_service.collection.find_one = MagicMock(return_value=None)

        # Act
        result = mongodb_service.get_episode_by_id(episode_id)

        # Assert
        assert result is None
        mongodb_service.collection.find_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)}
        )

    def test_get_episode_by_id_invalid_id(self, mongodb_service):
        """Test récupération avec ID MongoDB invalide."""
        # Arrange
        invalid_id = "invalid_object_id"
        mongodb_service.collection.find_one = MagicMock(
            side_effect=InvalidId("Invalid ObjectId")
        )

        # Act
        result = mongodb_service.get_episode_by_id(invalid_id)

        # Assert
        assert result is None
        # L'exception InvalidId devrait être gérée gracieusement

    def test_update_episode_description_success(self, mongodb_service):
        """Test mise à jour réussie de la description d'un épisode."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        new_description = "Nouvelle description corrigée"
        mock_result = MagicMock()
        mock_result.modified_count = 1
        mongodb_service.collection.update_one = MagicMock(return_value=mock_result)

        # Act
        result = mongodb_service.update_episode_description(episode_id, new_description)

        # Assert
        assert result is True
        mongodb_service.collection.update_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)},
            {"$set": {"description_corrigee": new_description}},
        )

    def test_update_episode_description_no_modification(self, mongodb_service):
        """Test mise à jour qui ne modifie aucun document."""
        # Arrange
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        new_description = "Nouvelle description"
        mock_result = MagicMock()
        mock_result.modified_count = 0
        mongodb_service.collection.update_one = MagicMock(return_value=mock_result)

        # Act
        result = mongodb_service.update_episode_description(episode_id, new_description)

        # Assert
        assert result is False
        mongodb_service.collection.update_one.assert_called_once()

    def test_update_episode_description_invalid_id(self, mongodb_service):
        """Test mise à jour avec ID invalide."""
        # Arrange
        invalid_id = "invalid_id"
        new_description = "Test description"
        mongodb_service.collection.update_one = MagicMock(
            side_effect=InvalidId("Invalid ObjectId")
        )

        # Act & Assert
        with pytest.raises(InvalidId):
            mongodb_service.update_episode_description(invalid_id, new_description)

    @patch("back_office_lmelp.services.mongodb_service.AsyncIOMotorClient")
    def test_connect_success(self, mock_client_class):
        """Test connexion réussie à MongoDB."""
        # Arrange
        service = MongoDBService()
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.admin.command = MagicMock(return_value={"ok": 1})

        # Act
        service.connect()

        # Assert
        assert service.client is not None
        assert service.database is not None
        assert service.collection is not None
        mock_client.admin.command.assert_called_once_with("ismaster")

    @patch("back_office_lmelp.services.mongodb_service.AsyncIOMotorClient")
    def test_connect_failure(self, mock_client_class):
        """Test échec de connexion à MongoDB."""
        # Arrange
        service = MongoDBService()
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.admin.command = MagicMock(
            side_effect=Exception("Connection failed")
        )

        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            service.connect()

    def test_disconnect(self):
        """Test déconnexion de MongoDB."""
        # Arrange
        service = MongoDBService()
        mock_client = MagicMock()
        service.client = mock_client

        # Act
        service.disconnect()

        # Assert
        mock_client.close.assert_called_once()


class TestMongoDBServiceIntegration:
    """Tests d'intégration pour le service MongoDB."""

    @pytest.fixture
    def mongodb_service_with_mock_db(self):
        """Create a MongoDB service with mocked database operations."""
        service = MongoDBService()

        # Mock the entire database chain
        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_collection = MagicMock()

        service.client = mock_client
        service.database = mock_database
        service.collection = mock_collection

        return service

    def test_episode_lifecycle(self, mongodb_service_with_mock_db):
        """Test du cycle de vie complet d'un épisode."""
        service = mongodb_service_with_mock_db

        # Arrange
        episode_data = {
            "titre": "Test Episode",
            "description": "Original description",
            "type": "test",
            "duree": 1800,
        }
        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret

        # Mock responses
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId(episode_id)
        service.collection.insert_one = MagicMock(return_value=mock_insert_result)

        created_episode = {**episode_data, "_id": ObjectId(episode_id)}
        service.collection.find_one = MagicMock(return_value=created_episode)

        mock_update_result = MagicMock()
        mock_update_result.modified_count = 1
        service.collection.update_one = MagicMock(return_value=mock_update_result)

        # Act & Assert
        # 1. Insérer un épisode
        inserted_id = service.insert_episode(episode_data)
        assert inserted_id == episode_id

        # 2. Récupérer l'épisode
        retrieved_episode = service.get_episode_by_id(episode_id)
        assert retrieved_episode["titre"] == episode_data["titre"]

        # 3. Mettre à jour la description
        new_description = "Description corrigée"
        update_success = service.update_episode_description(episode_id, new_description)
        assert update_success is True

    def test_error_handling_database_failure(self, mongodb_service_with_mock_db):
        """Test gestion d'erreurs lors d'échecs base de données."""
        service = mongodb_service_with_mock_db

        # Arrange - Simuler une panne de base de données
        service.collection.find.side_effect = Exception("Database connection lost")

        # Act & Assert
        with pytest.raises(Exception, match="Database connection lost"):
            service.get_all_episodes()

    def test_concurrent_operations(self, mongodb_service_with_mock_db):
        """Test opérations concurrentes sur MongoDB."""
        service = mongodb_service_with_mock_db

        # Arrange
        episode_ids = [
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "507f1f77bcf86cd799439012",  # pragma: allowlist secret
        ]  # pragma: allowlist secret
        mock_episodes = [
            {"_id": ObjectId(eid), "titre": f"Episode {i}"}
            for i, eid in enumerate(episode_ids)
        ]

        # Simuler des réponses pour chaque get_episode_by_id
        service.collection.find_one = MagicMock(side_effect=mock_episodes)

        # Act - Opérations concurrentes
        import asyncio

        tasks = [service.get_episode_by_id(eid) for eid in episode_ids]
        results = asyncio.gather(*tasks)

        # Assert
        assert len(results) == 2
        assert all(result is not None for result in results)
        assert service.collection.find_one.call_count == 2
