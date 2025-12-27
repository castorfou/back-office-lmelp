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
        mock.episodes_collection = MagicMock()
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


def test_get_episodes_with_avis_critiques_success(client, mock_mongodb_service):
    """Test de récupération des épisodes avec avis critiques."""
    from datetime import datetime

    # Mock des épisodes AVEC LES VRAIS NOMS DE CHAMPS depuis MongoDB
    # (vérifié avec mcp__MongoDB__find sur collection episodes)
    mock_episodes = [
        {
            "_id": "686bf5e18380ee925ae5e318",
            "titre": "Épisode 1",  # Nom réel dans MongoDB
            "date": datetime(2025, 7, 6),  # Type réel: datetime, pas string
            "url": "https://example.com/episode1.mp3",  # Nom réel dans MongoDB
            "type": "normal",
            "duree": "28:00",
            "masked": False,
        },
        {
            "_id": "686bf5e18380ee925ae5e319",
            "titre": "Épisode 2",
            "date": datetime(2025, 7, 13),
            "url": "https://example.com/episode2.mp3",
            "type": "normal",
            "duree": "30:00",
            "masked": False,
        },
    ]

    # Configuration des mocks
    mock_mongodb_service.episodes_collection.find.return_value = mock_episodes
    mock_mongodb_service.avis_critiques_collection.distinct.return_value = [
        "686bf5e18380ee925ae5e318",  # pragma: allowlist secret
        "686bf5e18380ee925ae5e319",  # pragma: allowlist secret
    ]

    # Mock du service d'extraction de critiques pour les pastilles
    with patch(
        "back_office_lmelp.app.critiques_extraction_service"
    ) as mock_critiques_service:
        # Mock des avis critiques pour vérifier les critiques "new"
        # Premier épisode: a des critiques dont au moins un "new" (Bernard Poiret)
        # Deuxième épisode: tous les critiques existent déjà (Elisabeth Philippe)
        def mock_find_one(query):
            episode_oid = query.get("episode_oid")
            if episode_oid == "686bf5e18380ee925ae5e318":  # pragma: allowlist secret
                return {
                    "_id": "avis1",
                    "episode_oid": episode_oid,
                    "summary": "**Bernard Poiret**: avis critique",
                }
            elif episode_oid == "686bf5e18380ee925ae5e319":  # pragma: allowlist secret
                return {
                    "_id": "avis2",
                    "episode_oid": episode_oid,
                    "summary": "**Elisabeth Philippe**: avis critique",
                }
            return None

        mock_mongodb_service.avis_critiques_collection.find_one.side_effect = (
            mock_find_one
        )

        # Mock du service d'extraction de critiques
        mock_critiques_service.extract_critiques_from_summary.side_effect = (
            lambda summary: (
                ["Bernard Poiret"]
                if "Bernard Poiret" in summary
                else ["Elisabeth Philippe"]
            )
        )

        # Mock find_matching_critique: Bernard Poiret n'existe pas (new), Elisabeth Philippe existe
        mock_critiques_service.find_matching_critique.side_effect = lambda name, _: (
            None
            if name == "Bernard Poiret"
            else {"nom": "Elisabeth Philippe", "match_type": "exact"}
        )

        # Appel de l'endpoint
        response = client.get("/api/episodes-with-avis-critiques")

    # Vérifications
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 2

    # Vérifier que distinct() a été appelé
    mock_mongodb_service.avis_critiques_collection.distinct.assert_called_once_with(
        "episode_oid"
    )

    # Vérifier que find() a été appelé avec les bons IDs (convertis en ObjectId)
    from bson import ObjectId

    call_args = mock_mongodb_service.episodes_collection.find.call_args[0][0]
    assert "_id" in call_args
    assert "$in" in call_args["_id"]
    # Vérifier que les IDs ont été convertis en ObjectId
    ids_list = call_args["_id"]["$in"]
    assert all(isinstance(id_val, ObjectId) for id_val in ids_list)
    assert len(ids_list) == 2

    # Vérifier la structure de la réponse (compatible avec EpisodeDropdown)
    # Le endpoint utilise to_summary_dict() qui retourne: id, titre, date (ISO), type, duree, masked
    first_episode = data[0]
    assert "id" in first_episode  # Episode.to_summary_dict() retourne 'id', pas '_id'
    assert "titre" in first_episode
    assert "date" in first_episode  # ISO string
    assert "type" in first_episode
    assert "duree" in first_episode
    assert "masked" in first_episode

    # Vérifier les flags pour les pastilles de couleur (Issue #164)
    assert "has_cached_books" in first_episode
    assert "has_incomplete_books" in first_episode
    assert isinstance(first_episode["has_cached_books"], bool)
    assert isinstance(first_episode["has_incomplete_books"], bool)

    # Issue #154: Vérifier que les épisodes sont triés par date décroissante
    # (le plus récent en premier)
    assert data[0]["date"] == "2025-07-13T00:00:00"  # Épisode 2 (plus récent)
    assert data[1]["date"] == "2025-07-06T00:00:00"  # Épisode 1 (plus ancien)

    # Vérifier les valeurs des flags pour chaque épisode
    # Les pastilles reflètent UNIQUEMENT le statut des critiques (pas des livres)
    episode_2 = data[0]  # Épisode le plus récent (2025-07-13)
    episode_1 = data[1]  # Épisode le plus ancien (2025-07-06)

    # Épisode 2: Tous les critiques existent (Elisabeth Philippe)
    # → Vert (has_cached_books=True, has_incomplete_books=False)
    assert episode_2["has_cached_books"] is True
    assert episode_2["has_incomplete_books"] is False

    # Épisode 1: Au moins un critique "new" (Bernard Poiret)
    # → Rouge (has_cached_books=True, has_incomplete_books=True)
    assert episode_1["has_cached_books"] is True
    assert episode_1["has_incomplete_books"] is True


def test_get_episodes_with_avis_critiques_no_collection(client, mock_mongodb_service):
    """Test quand les collections ne sont pas disponibles."""
    # Mock retourne None pour les collections
    mock_mongodb_service.episodes_collection = None
    mock_mongodb_service.avis_critiques_collection = None

    # Appel de l'endpoint
    response = client.get("/api/episodes-with-avis-critiques")

    # Vérifications
    assert response.status_code == 500
    assert "Service MongoDB non disponible" in response.json()["detail"]


def test_create_critique_success(client, mock_mongodb_service):
    """Test de création d'un nouveau critique."""
    from bson import ObjectId

    mock_inserted_id = ObjectId()

    # Mock insert_one
    mock_mongodb_service.critiques_collection.insert_one.return_value = MagicMock(
        inserted_id=mock_inserted_id
    )

    # Mock critique créé
    mock_critique = {
        "_id": mock_inserted_id,
        "nom": "Nouveau Critique",
        "variantes": ["Variante 1"],
        "animateur": False,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    # Configurer le mock pour retourner None (pas de critique existant) puis le critique créé
    mock_mongodb_service.critiques_collection.find_one.side_effect = [
        None,  # Premier appel: vérifier si existe
        mock_critique,  # Deuxième appel: récupérer après insert
    ]

    # Appel de l'endpoint
    response = client.post(
        "/api/critiques",
        json={
            "nom": "Nouveau Critique",
            "variantes": ["Variante 1"],
            "animateur": False,
        },
    )

    # Vérifications
    assert response.status_code == 201
    data = response.json()
    assert data["nom"] == "Nouveau Critique"
    assert "Variante 1" in data["variantes"]


def test_create_critique_with_animateur_true(client, mock_mongodb_service):
    """Test de création d'un critique avec animateur=True (Issue #154)."""
    from bson import ObjectId

    mock_inserted_id = ObjectId()

    # Mock insert_one
    mock_mongodb_service.critiques_collection.insert_one.return_value = MagicMock(
        inserted_id=mock_inserted_id
    )

    # Mock critique créé (animateur)
    mock_critique = {
        "_id": mock_inserted_id,
        "nom": "Jérôme Garcin",
        "variantes": [],
        "animateur": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    # Configurer le mock pour retourner None (pas de critique existant) puis le critique créé
    mock_mongodb_service.critiques_collection.find_one.side_effect = [
        None,  # Premier appel: vérifier si existe
        mock_critique,  # Deuxième appel: récupérer après insert
    ]

    # Appel de l'endpoint avec animateur=True
    response = client.post(
        "/api/critiques",
        json={"nom": "Jérôme Garcin", "variantes": [], "animateur": True},
    )

    # Vérifications
    assert response.status_code == 201
    data = response.json()
    assert data["nom"] == "Jérôme Garcin"
    assert data["animateur"] is True

    # Vérifier que insert_one a été appelé avec animateur=True
    insert_call = mock_mongodb_service.critiques_collection.insert_one.call_args[0][0]
    assert insert_call["animateur"] is True


def test_create_critique_adds_variante_to_existing(client, mock_mongodb_service):
    """Test: quand un critique existe déjà, ajouter la variante au lieu de rejeter."""
    from bson import ObjectId

    critique_id = ObjectId()

    # Mock: critique existant avec ce nom
    existing_critique = {
        "_id": critique_id,
        "nom": "Philippe Trétiack",
        "variantes": ["Philippe T."],
        "animateur": False,
        "created_at": datetime(2025, 1, 1),
        "updated_at": datetime(2025, 1, 1),
    }

    # Mock find_one: retourne le critique existant
    mock_mongodb_service.critiques_collection.find_one.return_value = existing_critique

    # Mock update_one
    mock_mongodb_service.critiques_collection.update_one.return_value = MagicMock(
        matched_count=1
    )

    # Mock find_one après update: critique avec la nouvelle variante ajoutée
    updated_critique = {
        "_id": critique_id,
        "nom": "Philippe Trétiack",
        "variantes": ["Philippe T.", "Philippe Trétiac"],  # Nouvelle variante ajoutée
        "animateur": False,
        "created_at": datetime(2025, 1, 1),
        "updated_at": datetime.now(),
    }

    # Configurer le mock pour retourner le critique existant puis le critique mis à jour
    mock_mongodb_service.critiques_collection.find_one.side_effect = [
        existing_critique,  # Premier appel: vérifier si existe
        updated_critique,  # Deuxième appel: récupérer après update
    ]

    # Appel de l'endpoint avec une nouvelle variante
    response = client.post(
        "/api/critiques",
        json={
            "nom": "Philippe Trétiack",
            "variantes": ["Philippe Trétiac"],  # Nouvelle variante
            "animateur": False,
        },
    )

    # Vérifications
    assert response.status_code == 200  # 200 au lieu de 201 (mise à jour)
    data = response.json()
    assert data["nom"] == "Philippe Trétiack"
    assert "Philippe T." in data["variantes"]  # Ancienne variante conservée
    assert "Philippe Trétiac" in data["variantes"]  # Nouvelle variante ajoutée
    assert "message" in data
    assert "Variantes ajoutées" in data["message"]

    # Vérifier que update_one a été appelé avec les bonnes variantes
    mock_mongodb_service.critiques_collection.update_one.assert_called_once()
    call_args = mock_mongodb_service.critiques_collection.update_one.call_args
    assert call_args[0][0] == {"_id": critique_id}
    updated_variantes = call_args[0][1]["$set"]["variantes"]
    assert set(updated_variantes) == {"Philippe T.", "Philippe Trétiac"}


def test_get_critiques_manquants_count(client, mock_mongodb_service):
    """Test du comptage des épisodes avec critiques manquants."""
    from bson import ObjectId

    # Mock des épisodes (avec statut masqué)
    mock_episode1_id = ObjectId("507f1f77bcf86cd799439011")
    mock_episode2_id = ObjectId("507f1f77bcf86cd799439012")

    # Mock: 2 épisodes avec avis critiques
    mock_mongodb_service.avis_critiques_collection.distinct.return_value = [
        str(mock_episode1_id),
        str(mock_episode2_id),
    ]

    mock_episodes_data = [
        {"_id": mock_episode1_id, "masked": False},  # Non masqué
        {"_id": mock_episode2_id, "masked": False},  # Non masqué
    ]
    mock_mongodb_service.episodes_collection.find.return_value = mock_episodes_data

    # Mock des critiques existants
    mock_existing_critiques = [
        {"_id": "crit1", "nom": "Patricia Martin", "variantes": []},
        {"_id": "crit2", "nom": "Arnaud Viviant", "variantes": []},
    ]
    mock_mongodb_service.critiques_collection.find.return_value = (
        mock_existing_critiques
    )

    # Mock des avis critiques
    def mock_find_one(query):
        episode_oid = query.get("episode_oid")
        if episode_oid == str(mock_episode1_id):
            # Épisode 1: a un critique "new" (Bernard Poiret)
            return {
                "_id": "avis1",
                "episode_oid": episode_oid,
                "summary": "**Bernard Poiret**: avis critique <br> **Patricia Martin**: autre avis",
            }
        elif episode_oid == str(mock_episode2_id):
            # Épisode 2: tous les critiques existent (Patricia Martin + Arnaud Viviant)
            return {
                "_id": "avis2",
                "episode_oid": episode_oid,
                "summary": "**Patricia Martin**: avis <br> **Arnaud Viviant**: avis",
            }
        return None

    mock_mongodb_service.avis_critiques_collection.find_one.side_effect = mock_find_one

    # Mock du service d'extraction de critiques
    with patch(
        "back_office_lmelp.app.critiques_extraction_service"
    ) as mock_critiques_service:
        mock_critiques_service.extract_critiques_from_summary.side_effect = (
            lambda summary: (
                ["Bernard Poiret", "Patricia Martin"]
                if "Bernard Poiret" in summary
                else ["Patricia Martin", "Arnaud Viviant"]
            )
        )

        # Mock find_matching_critique:
        # Bernard Poiret n'existe pas (new)
        # Patricia Martin et Arnaud Viviant existent
        critique_matches = {
            "Patricia Martin": {"nom": "Patricia Martin", "match_type": "exact"},
            "Arnaud Viviant": {"nom": "Arnaud Viviant", "match_type": "exact"},
        }

        def mock_find_matching(name, _):
            return critique_matches.get(name)

        mock_critiques_service.find_matching_critique.side_effect = mock_find_matching

        # Appel de l'endpoint
        response = client.get("/api/stats/critiques-manquants")

    # Vérifications
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    # Seul episode1 a un critique "new" (Bernard Poiret)
    assert data["count"] == 1


def test_get_critiques_manquants_count_filters_masked_episodes(
    client, mock_mongodb_service
):
    """Test que les épisodes masqués sont exclus du comptage."""
    from bson import ObjectId

    # Mock des épisodes
    mock_episode1_id = ObjectId("507f1f77bcf86cd799439011")
    mock_episode2_id = ObjectId("507f1f77bcf86cd799439012")

    # Mock: 2 épisodes avec avis critiques
    mock_mongodb_service.avis_critiques_collection.distinct.return_value = [
        str(mock_episode1_id),
        str(mock_episode2_id),
    ]

    # Episode 1: masqué (ne devrait PAS être compté)
    # Episode 2: non masqué avec critique manquant (devrait être compté)
    mock_episodes_data = [
        {"_id": mock_episode1_id, "masked": True},  # Masqué
        {"_id": mock_episode2_id, "masked": False},  # Non masqué
    ]
    mock_mongodb_service.episodes_collection.find.return_value = mock_episodes_data

    # Mock des critiques existants
    mock_existing_critiques = [
        {"_id": "crit1", "nom": "Patricia Martin", "variantes": []},
    ]
    mock_mongodb_service.critiques_collection.find.return_value = (
        mock_existing_critiques
    )

    # Mock des avis critiques
    def mock_find_one(query):
        episode_oid = query.get("episode_oid")
        if episode_oid == str(mock_episode1_id):
            # Épisode masqué avec critique "new"
            return {
                "_id": "avis1",
                "episode_oid": episode_oid,
                "summary": "**Bernard Poiret**: avis critique",
            }
        elif episode_oid == str(mock_episode2_id):
            # Épisode non masqué avec critique "new"
            return {
                "_id": "avis2",
                "episode_oid": episode_oid,
                "summary": "**Arnaud Viviant**: avis critique",
            }
        return None

    mock_mongodb_service.avis_critiques_collection.find_one.side_effect = mock_find_one

    # Mock du service d'extraction
    with patch(
        "back_office_lmelp.app.critiques_extraction_service"
    ) as mock_critiques_service:
        mock_critiques_service.extract_critiques_from_summary.side_effect = (
            lambda summary: (
                ["Bernard Poiret"]
                if "Bernard Poiret" in summary
                else ["Arnaud Viviant"]
            )
        )

        # Les deux critiques n'existent pas (sont "new")
        mock_critiques_service.find_matching_critique.return_value = None

        # Appel de l'endpoint
        response = client.get("/api/stats/critiques-manquants")

    # Vérifications
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    # Seul episode2 (non masqué) devrait être compté
    # Episode1 (masqué) est exclu même s'il a un critique manquant
    assert data["count"] == 1
