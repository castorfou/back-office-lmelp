"""Integration tests for MongoDB service to improve coverage."""

from unittest.mock import Mock, patch

import pytest
from bson import ObjectId
from pymongo.errors import ConnectionFailure, PyMongoError

from back_office_lmelp.services.mongodb_service import MongoDBService


@pytest.fixture
def mongodb_service():
    """Create a fresh MongoDB service instance for testing."""
    return MongoDBService()


@pytest.fixture
def mock_mongo_client():
    """Mock MongoDB client."""
    with patch("back_office_lmelp.services.mongodb_service.MongoClient") as mock:
        yield mock


class TestMongoDBService:
    """Test class for MongoDB service operations."""

    def test_init(self, mongodb_service):
        """Test MongoDB service initialization."""
        # Verify MongoDB URL is set (either from .env or default)
        assert mongodb_service.mongo_url is not None
        assert mongodb_service.mongo_url.startswith("mongodb://")
        assert mongodb_service.client is None
        assert mongodb_service.db is None
        assert mongodb_service.episodes_collection is None

    def test_init_with_env_url(self, mock_mongo_client):
        """Test MongoDB service initialization with environment URL."""
        with patch.dict("os.environ", {"MONGODB_URL": "mongodb://test:27017/testdb"}):
            service = MongoDBService()
            assert service.mongo_url == "mongodb://test:27017/testdb"

    def test_connect_success(self, mongodb_service, mock_mongo_client):
        """Test successful MongoDB connection."""
        mock_client = Mock()
        mock_mongo_client.return_value = mock_client
        mock_client.admin.command.return_value = {"ok": 1}
        mock_db = Mock()
        mock_client.get_default_database.return_value = mock_db
        mock_collection = Mock()
        mock_db.episodes = mock_collection

        result = mongodb_service.connect()

        assert result is True
        assert mongodb_service.client == mock_client
        assert mongodb_service.db == mock_db
        assert mongodb_service.episodes_collection == mock_collection
        mock_client.admin.command.assert_called_once_with("ping")

    def test_connect_failure(self, mongodb_service, mock_mongo_client):
        """Test MongoDB connection failure."""
        mock_client = Mock()
        mock_mongo_client.return_value = mock_client
        mock_client.admin.command.side_effect = ConnectionFailure("Connection failed")

        result = mongodb_service.connect()

        assert result is False
        assert mongodb_service.client is None

    def test_connect_generic_exception(self, mongodb_service, mock_mongo_client):
        """Test MongoDB connection with generic exception."""
        mock_mongo_client.side_effect = Exception("Unexpected error")

        result = mongodb_service.connect()

        assert result is False

    def test_disconnect(self, mongodb_service):
        """Test MongoDB disconnection."""
        mock_client = Mock()
        mongodb_service.client = mock_client

        mongodb_service.disconnect()

        mock_client.close.assert_called_once()

    def test_disconnect_no_client(self, mongodb_service):
        """Test MongoDB disconnection when no client exists."""
        mongodb_service.disconnect()  # Should not raise exception

    def test_get_all_episodes_success(self, mongodb_service):
        """Test successful retrieval of all episodes."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection

        mock_cursor = Mock()
        mock_collection.find.return_value = mock_cursor
        mock_cursor.sort.return_value = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "titre": "Episode 1",
                "titre_corrige": "Episode 1 corrigé",
                "date": "2024-01-01",
                "type": "test",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "titre": "Episode 2",
                "titre_corrige": None,
                "date": "2024-01-02",
                "type": "test",
            },
        ]

        result = mongodb_service.get_all_episodes()

        assert len(result) == 2
        assert result[0]["_id"] == "507f1f77bcf86cd799439011"
        assert result[1]["_id"] == "507f1f77bcf86cd799439012"
        mock_collection.find.assert_called_once_with(
            {"masked": {"$ne": True}},
            {
                "titre": 1,
                "titre_corrige": 1,
                "date": 1,
                "type": 1,
                "duree": 1,
                "masked": 1,
                "_id": 1,
            },
        )

    def test_get_all_episodes_no_connection(self, mongodb_service):
        """Test get all episodes when no connection established."""
        with pytest.raises(Exception, match="Connexion MongoDB non établie"):
            mongodb_service.get_all_episodes()

    def test_get_all_episodes_database_error(self, mongodb_service):
        """Test get all episodes with database error."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection
        mock_collection.find.side_effect = PyMongoError("Database error")

        result = mongodb_service.get_all_episodes()

        assert result == []

    def test_get_episode_by_id_success(self, mongodb_service):
        """Test successful retrieval of episode by ID."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection

        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        mock_episode = {
            "_id": ObjectId(episode_id),
            "titre": "Test Episode",
            "description": "Test",
        }
        mock_collection.find_one.return_value = mock_episode

        result = mongodb_service.get_episode_by_id(episode_id)

        assert result is not None
        assert result["_id"] == episode_id
        assert result["titre"] == "Test Episode"
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(episode_id)})

    def test_get_episode_by_id_not_found(self, mongodb_service):
        """Test get episode by ID when episode not found."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection
        mock_collection.find_one.return_value = None

        result = mongodb_service.get_episode_by_id("nonexistent")

        assert result is None

    def test_get_episode_by_id_no_connection(self, mongodb_service):
        """Test get episode by ID when no connection established."""
        with pytest.raises(Exception, match="Connexion MongoDB non établie"):
            mongodb_service.get_episode_by_id(
                "507f1f77bcf86cd799439011"  # pragma: allowlist secret
            )  # pragma: allowlist secret

    def test_get_episode_by_id_database_error(self, mongodb_service):
        """Test get episode by ID with database error."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection
        mock_collection.find_one.side_effect = PyMongoError("Database error")

        result = mongodb_service.get_episode_by_id("507f1f77bcf86cd799439011")

        assert result is None

    def test_update_episode_description_success(self, mongodb_service):
        """Test successful episode description update."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection

        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result

        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        description = "Updated description"
        result = mongodb_service.update_episode_description(episode_id, description)

        assert result is True
        mock_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)},
            {"$set": {"description_corrigee": description}},
        )

    def test_update_episode_description_no_modification(self, mongodb_service):
        """Test episode description update with no modification."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection

        mock_result = Mock()
        mock_result.modified_count = 0
        mock_collection.update_one.return_value = mock_result

        result = mongodb_service.update_episode_description(
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "description",
        )

        assert result is False

    def test_update_episode_description_no_connection(self, mongodb_service):
        """Test update episode description when no connection established."""
        with pytest.raises(Exception, match="Connexion MongoDB non établie"):
            mongodb_service.update_episode_description(
                "507f1f77bcf86cd799439011",  # pragma: allowlist secret
                "description",
            )

    def test_update_episode_description_database_error(self, mongodb_service):
        """Test update episode description with database error."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection
        mock_collection.update_one.side_effect = PyMongoError("Database error")

        result = mongodb_service.update_episode_description(
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "description",
        )

        assert result is False

    def test_update_episode_title_success(self, mongodb_service):
        """Test successful episode title update."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection

        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result

        episode_id = "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        title = "Updated title"
        result = mongodb_service.update_episode_title(episode_id, title)

        assert result is True
        mock_collection.update_one.assert_called_once_with(
            {"_id": ObjectId(episode_id)}, {"$set": {"titre_corrige": title}}
        )

    def test_update_episode_title_no_modification(self, mongodb_service):
        """Test episode title update with no modification."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection

        mock_result = Mock()
        mock_result.modified_count = 0
        mock_collection.update_one.return_value = mock_result

        result = mongodb_service.update_episode_title(
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "title",
        )

        assert result is False

    def test_update_episode_title_no_connection(self, mongodb_service):
        """Test update episode title when no connection established."""
        with pytest.raises(Exception, match="Connexion MongoDB non établie"):
            mongodb_service.update_episode_title(
                "507f1f77bcf86cd799439011",  # pragma: allowlist secret
                "title",
            )

    def test_update_episode_title_database_error(self, mongodb_service):
        """Test update episode title with database error."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection
        mock_collection.update_one.side_effect = PyMongoError("Database error")

        result = mongodb_service.update_episode_title(
            "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "title",
        )

        assert result is False

    def test_insert_episode_success(self, mongodb_service):
        """Test successful episode insertion."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection

        inserted_id = ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret
        mock_result = Mock()
        mock_result.inserted_id = inserted_id
        mock_collection.insert_one.return_value = mock_result

        episode_data = {"titre": "New Episode", "description": "Test"}
        result = mongodb_service.insert_episode(episode_data)

        assert result == str(inserted_id)
        mock_collection.insert_one.assert_called_once_with(episode_data)

    def test_insert_episode_no_connection(self, mongodb_service):
        """Test insert episode when no connection established."""
        with pytest.raises(Exception, match="Connexion MongoDB non établie"):
            mongodb_service.insert_episode({"titre": "Test"})

    def test_insert_episode_database_error(self, mongodb_service):
        """Test insert episode with database error."""
        mock_collection = Mock()
        mongodb_service.episodes_collection = mock_collection
        mock_collection.insert_one.side_effect = PyMongoError("Database error")

        episode_data = {"titre": "New Episode"}
        with pytest.raises(PyMongoError):
            mongodb_service.insert_episode(episode_data)


class TestGlobalMongoDBServiceInstance:
    """Test the global mongodb_service instance."""

    def test_global_instance_exists(self):
        """Test that global mongodb_service instance exists."""
        from back_office_lmelp.services.mongodb_service import mongodb_service

        assert mongodb_service is not None
        assert isinstance(mongodb_service, MongoDBService)
