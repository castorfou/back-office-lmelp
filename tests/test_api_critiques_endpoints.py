"""Tests pour les endpoints API des critiques et émissions."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


@pytest.fixture
def client():
    """Fixture pour le client de test FastAPI."""
    return TestClient(app)


@pytest.fixture
def mock_mongodb_service():
    """Fixture pour mocker le service MongoDB."""
    with patch("back_office_lmelp.app.mongodb_service") as mock:
        # Mock des collections
        mock.avis_critiques_collection = MagicMock()
        mock.critiques_collection = MagicMock()
        mock.emissions_collection = MagicMock()
        yield mock


def test_get_detected_critiques_success(client, mock_mongodb_service):
    """Test de récupération des critiques détectés depuis un épisode.

    Ce test démontre le bug: episode_oid est stocké en STRING dans MongoDB,
    pas en ObjectId. L'endpoint ne doit donc PAS convertir l'episode_id
    en ObjectId avant de faire la requête.
    """
    episode_id = "686bf5e18380ee925ae5e318"

    # Données réelles depuis MongoDB (avis_critiques collection)
    mock_avis_critique = {
        "_id": "686c48b728b9e451c1cee31f",
        "episode_oid": episode_id,  # Stocké en STRING, pas ObjectId!
        "episode_title": "Faut-il lire Raphaël Quenard, Miranda July...",
        "episode_date": "06 juil. 2025",
        "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne |
|--------|-------|---------|------------------------------|--------------|
| Etgar Keret | Correction automatique | Éditions de l'Olivier | **Blandine Rinkel**: "Fantaisiste" - 7 <br> **Arnaud Viviant**: "Échapper au réel" - 8 | 7.5 |
""",
        "created_at": datetime(2025, 7, 7, 22, 22, 47),
        "updated_at": datetime(2025, 7, 7, 22, 22, 47),
    }

    # Mock des critiques existants en base
    mock_existing_critiques = [
        {
            "_id": "65abc0000000000000000001",
            "nom": "Blandine Rinkel",
            "variantes": [],
            "animateur": False,
        },
    ]

    # Configuration des mocks
    mock_mongodb_service.avis_critiques_collection.find_one.return_value = (
        mock_avis_critique
    )
    mock_mongodb_service.critiques_collection.find.return_value = (
        mock_existing_critiques
    )

    # Appel de l'endpoint
    response = client.get(f"/api/episodes/{episode_id}/critiques-detectes")

    # Vérifications
    assert response.status_code == 200
    data = response.json()

    # Vérifier que find_one a été appelé avec episode_id en STRING
    # (pas ObjectId(episode_id))
    mock_mongodb_service.avis_critiques_collection.find_one.assert_called_once_with(
        {"episode_oid": episode_id}  # STRING, pas ObjectId!
    )

    # Vérifier le contenu de la réponse
    assert "episode_id" in data
    assert "avis_critique_id" in data
    assert "detected_critiques" in data

    assert data["episode_id"] == episode_id
    assert len(data["detected_critiques"]) == 2

    # Blandine Rinkel devrait être marquée comme "existing" (match exact)
    blandine = next(
        c for c in data["detected_critiques"] if c["detected_name"] == "Blandine Rinkel"
    )
    assert blandine["status"] == "existing"
    assert blandine["match_type"] == "exact"
    assert blandine["matched_critique"] == "Blandine Rinkel"

    # Arnaud Viviant devrait être marqué comme "new" (pas en base)
    arnaud = next(
        c for c in data["detected_critiques"] if c["detected_name"] == "Arnaud Viviant"
    )
    assert arnaud["status"] == "new"
    assert arnaud["match_type"] is None
    assert arnaud["matched_critique"] is None


def test_get_detected_critiques_no_avis_critique(client, mock_mongodb_service):
    """Test quand aucun avis critique n'est trouvé pour l'épisode."""
    episode_id = "nonexistent_id"

    # Mock retourne None (pas d'avis critique trouvé)
    mock_mongodb_service.avis_critiques_collection.find_one.return_value = None

    # Appel de l'endpoint
    response = client.get(f"/api/episodes/{episode_id}/critiques-detectes")

    # Vérifications
    assert response.status_code == 404
    assert "Aucun avis critique trouvé" in response.json()["detail"]


def test_get_detected_critiques_empty_summary(client, mock_mongodb_service):
    """Test quand le summary est vide (pas de critiques à détecter)."""
    episode_id = "686bf5e18380ee925ae5e318"

    mock_avis_critique = {
        "_id": "686c48b728b9e451c1cee31f",
        "episode_oid": episode_id,
        "episode_title": "Episode sans critiques",
        "episode_date": "06 juil. 2025",
        "summary": "",  # Summary vide
    }

    mock_mongodb_service.avis_critiques_collection.find_one.return_value = (
        mock_avis_critique
    )
    mock_mongodb_service.critiques_collection.find.return_value = []

    # Appel de l'endpoint
    response = client.get(f"/api/episodes/{episode_id}/critiques-detectes")

    # Vérifications
    assert response.status_code == 200
    data = response.json()

    assert "episode_id" in data
    assert "avis_critique_id" in data
    assert "detected_critiques" in data
    assert len(data["detected_critiques"]) == 0
