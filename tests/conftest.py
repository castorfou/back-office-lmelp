"""Configuration pytest pour les tests du Back-Office LMELP."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from back_office_lmelp.app import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_mongodb_service():
    """Create a mock MongoDB service for tests."""
    with patch(
        "back_office_lmelp.services.mongodb_service.mongodb_service"
    ) as mock_service:
        mock_service.connect = MagicMock(return_value=True)
        mock_service.disconnect = MagicMock()
        mock_service.create_author_if_not_exists = MagicMock()
        mock_service.create_book_if_not_exists = MagicMock()
        yield mock_service


@pytest.fixture
def client(mock_mongodb_service):
    """Create a test client for the FastAPI app."""
    yield TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_episode_data() -> dict[str, Any]:
    """Sample episode data for testing."""
    return {
        "titre": "Test Episode Title",
        "date": "2025-08-30T10:59:59.000+00:00",
        "description": "Original test description",
        "description_corrigee": None,
        "url": "https://example.com/test-episode",
        "audio_rel_filename": "test/episode.mp3",
        "transcription": "Test transcription content",
        "type": "test",
        "duree": 1800,
    }


@pytest.fixture
def sample_episode_id() -> str:
    """Sample episode ID for testing."""
    return "507f1f77bcf86cd799439011"  # pragma: allowlist secret
