"""Tests pour l'endpoint d'extraction depuis URL Babelio (Issue #159).

Ce module teste l'endpoint /api/babelio/extract-from-url qui permet d'extraire
les informations d'un livre depuis une URL Babelio sans faire de mise à jour en base.
"""

from unittest.mock import patch

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


def test_extract_from_url_returns_book_data(client, mock_babelio_migration_service):
    """RED Test: L'endpoint devrait retourner les données extraites d'une URL Babelio."""
    # Arrange: Simuler les données scrapées (méthode async)
    from unittest.mock import AsyncMock

    mock_babelio_migration_service.extract_from_babelio_url = AsyncMock(
        return_value={
            "titre": "Les Particules élémentaires",
            "auteur": "Michel Houellebecq",
            "editeur": "Flammarion",
            "url_livre": "https://www.babelio.com/livres/Houellebecq-Les-Particules-elementaires/2172",
            "url_auteur": "https://www.babelio.com/auteur/Michel-Houellebecq/2342",
        }
    )

    # Act: Appeler l'endpoint
    response = client.post(
        "/api/babelio/extract-from-url",
        json={
            "babelio_url": "https://www.babelio.com/livres/Houellebecq-Les-Particules-elementaires/2172"
        },
    )

    # Assert: Vérifier la réponse
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["titre"] == "Les Particules élémentaires"
    assert data["data"]["auteur"] == "Michel Houellebecq"
    assert data["data"]["editeur"] == "Flammarion"


def test_extract_from_url_handles_invalid_url(client, mock_babelio_migration_service):
    """L'endpoint devrait retourner une erreur pour une URL invalide."""
    # Arrange: Simuler une erreur de scraping (méthode async)
    from unittest.mock import AsyncMock

    mock_babelio_migration_service.extract_from_babelio_url = AsyncMock(
        side_effect=ValueError("URL invalide")
    )

    # Act: Appeler l'endpoint avec une URL invalide
    response = client.post(
        "/api/babelio/extract-from-url",
        json={"babelio_url": "https://example.com/invalid"},
    )

    # Assert: Vérifier l'erreur
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"


def test_extract_from_url_handles_scraping_error(
    client, mock_babelio_migration_service
):
    """L'endpoint devrait gérer les erreurs de scraping gracieusement."""
    # Arrange: Simuler une erreur de scraping (méthode async)
    from unittest.mock import AsyncMock

    mock_babelio_migration_service.extract_from_babelio_url = AsyncMock(
        side_effect=Exception("Erreur de scraping")
    )

    # Act: Appeler l'endpoint
    response = client.post(
        "/api/babelio/extract-from-url",
        json={"babelio_url": "https://www.babelio.com/livres/Test/123"},
    )

    # Assert: Vérifier la gestion d'erreur
    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
