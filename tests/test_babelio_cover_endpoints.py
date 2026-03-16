"""Tests TDD pour les endpoints de couvertures (Issue #238).

Tests pour :
- GET /api/babelio-migration/covers/pending
- POST /api/babelio-migration/covers/save
- POST /api/babelio/extract-cover-url (proxy backend)
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_babelio_migration_service():
    """Mock du service de migration Babelio pour les tests."""
    with patch("back_office_lmelp.app.babelio_migration_service") as mock:
        yield mock


@pytest.fixture
def client():
    """Client de test FastAPI."""
    from back_office_lmelp.app import app

    return TestClient(app)


def test_get_pending_covers_endpoint_returns_list(
    client, mock_babelio_migration_service
):
    """RED Test: GET /api/babelio-migration/covers/pending retourne une liste de livres."""
    mock_babelio_migration_service.get_books_pending_covers.return_value = [
        {
            "_id": "674e9a8f1234567890abcde1",
            "titre": "Simone Émonet",
            "url_babelio": "https://www.babelio.com/livres/Millet-Simone-monet/1870367",
        },
        {
            "_id": "674e9a8f1234567890abcde2",
            "titre": "Le Couteau",
            "url_babelio": "https://www.babelio.com/livres/Rushdie-Le-Couteau/1234567",
        },
    ]

    response = client.get("/api/babelio-migration/covers/pending")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["titre"] == "Simone Émonet"
    assert data[0]["url_babelio"].startswith("https://www.babelio.com")


def test_get_pending_covers_endpoint_returns_empty_list_when_no_pending(
    client, mock_babelio_migration_service
):
    """RED Test: GET /api/babelio-migration/covers/pending retourne [] si aucun livre en attente."""
    mock_babelio_migration_service.get_books_pending_covers.return_value = []

    response = client.get("/api/babelio-migration/covers/pending")

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_save_cover_url_endpoint_returns_success(
    client, mock_babelio_migration_service
):
    """RED Test: POST /api/babelio-migration/covers/save retourne succès si livre trouvé."""
    mock_babelio_migration_service.save_cover_url.return_value = True

    response = client.post(
        "/api/babelio-migration/covers/save",
        json={
            "livre_id": "674e9a8f1234567890abcde1",
            "url_cover": "https://www.babelio.com/couv/CVT_Simone-monet_42.jpg",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_save_cover_url_endpoint_returns_404_if_not_found(
    client, mock_babelio_migration_service
):
    """RED Test: POST /api/babelio-migration/covers/save retourne 404 si livre non trouvé."""
    mock_babelio_migration_service.save_cover_url.return_value = False

    response = client.post(
        "/api/babelio-migration/covers/save",
        json={
            "livre_id": "674e9a8f1234567890abcde1",
            "url_cover": "https://www.babelio.com/couv/CVT_test_42.jpg",
        },
    )

    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"


def test_save_cover_url_endpoint_calls_service_with_correct_args(
    client, mock_babelio_migration_service
):
    """RED Test: POST /api/babelio-migration/covers/save appelle save_cover_url avec les bons args."""
    mock_babelio_migration_service.save_cover_url.return_value = True

    livre_id = "674e9a8f1234567890abcde1"
    url_cover = "https://www.babelio.com/couv/CVT_Simone-monet_42.jpg"

    client.post(
        "/api/babelio-migration/covers/save",
        json={"livre_id": livre_id, "url_cover": url_cover},
    )

    mock_babelio_migration_service.save_cover_url.assert_called_once_with(
        livre_id=livre_id, url_cover=url_cover
    )


@pytest.fixture
def mock_babelio_service():
    """Mock du service Babelio pour les tests de couverture."""
    with patch("back_office_lmelp.app.babelio_service") as mock:
        yield mock


def test_extract_cover_url_endpoint_returns_cover_url(client, mock_babelio_service):
    """RED Test: POST /api/babelio/extract-cover-url retourne l'URL de couverture."""
    mock_babelio_service.fetch_cover_url_from_babelio_page = AsyncMock(
        return_value="https://www.babelio.com/couv/CVT_Simone-monet_42.jpg"
    )

    response = client.post(
        "/api/babelio/extract-cover-url",
        json={
            "babelio_url": "https://www.babelio.com/livres/Millet-Simone-monet/1870367"
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["url_cover"] == "https://www.babelio.com/couv/CVT_Simone-monet_42.jpg"
    assert data["title_mismatch"] is False


def test_extract_cover_url_endpoint_returns_none_when_not_found(
    client, mock_babelio_service
):
    """RED Test: POST /api/babelio/extract-cover-url retourne url_cover=null si non trouvé."""
    mock_babelio_service.fetch_cover_url_from_babelio_page = AsyncMock(
        return_value=None
    )

    response = client.post(
        "/api/babelio/extract-cover-url",
        json={"babelio_url": "https://www.babelio.com/livres/NoImage/999999"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["url_cover"] is None
    assert data["title_mismatch"] is False


def test_extract_cover_url_endpoint_returns_title_mismatch(
    client, mock_babelio_service
):
    """Test: POST /api/babelio/extract-cover-url retourne title_mismatch=True si redirection Babelio."""
    mock_babelio_service.fetch_cover_url_from_babelio_page = AsyncMock(
        return_value="TITLE_MISMATCH:Fauves"
    )

    response = client.post(
        "/api/babelio/extract-cover-url",
        json={
            "babelio_url": "https://www.babelio.com/livres/X/999",
            "expected_title": "On ne sait rien de toi",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["url_cover"] is None
    assert data["title_mismatch"] is True
    assert data["page_title"] == "Fauves"
