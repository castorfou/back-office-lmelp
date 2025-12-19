"""Tests pour le groupement des cas problématiques livre-auteur.

Tests pour l'issue #146: regroupement des entrées livre + auteur
dans les cas problématiques nécessitant un traitement manuel.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from back_office_lmelp.services.babelio_migration_service import BabelioMigrationService


@pytest.fixture
def mock_mongodb_service():
    """Crée un mock du service MongoDB."""
    service = MagicMock()
    service.db = MagicMock()
    return service


@pytest.fixture
def mock_babelio_service():
    """Crée un mock du service Babelio."""
    return MagicMock()


@pytest.fixture
def babelio_migration_service(mock_mongodb_service, mock_babelio_service):
    """Crée une instance du service de migration."""
    return BabelioMigrationService(mock_mongodb_service, mock_babelio_service)


def test_get_problematic_cases_should_group_book_and_author_when_both_problematic(
    babelio_migration_service, mock_mongodb_service
):
    """Test: Les cas livre + auteur problématiques doivent être groupés en une seule entrée."""
    # GIVEN: Un livre et son auteur dans babelio_problematic_cases
    livre_id = str(ObjectId())
    auteur_id = str(ObjectId())
    timestamp = datetime.now(UTC)

    # Mock de la collection problematic_cases avec livre + auteur
    mock_problematic_collection = MagicMock()
    mock_problematic_collection.find.return_value = [
        {
            "_id": ObjectId(),
            "type": "livre",
            "livre_id": livre_id,
            "titre_attendu": "Romance",
            "auteur": "Anne Goscinny",
            # Note: auteur_id n'est PAS dans le cas problématique,
            # il est récupéré depuis la collection livres
            "raison": "Livre non trouvé",
            "url_babelio": "N/A",
            "timestamp": timestamp,
        },
        {
            "_id": ObjectId(),
            "type": "auteur",
            "auteur_id": auteur_id,
            "nom_auteur": "Anne Goscinny",
            "nb_livres": 1,
            "raison": "Livres problématiques: ['Romance']",
            "timestamp": timestamp,
        },
    ]

    # Mock de la collection livres (pas encore résolu)
    mock_livres_collection = MagicMock()
    mock_livres_collection.find_one.return_value = {
        "_id": ObjectId(livre_id),
        "titre": "Romance",
        "auteur_id": ObjectId(auteur_id),
        # Pas de url_babelio ni babelio_not_found
    }

    mock_mongodb_service.db.__getitem__.side_effect = lambda key: {
        "babelio_problematic_cases": mock_problematic_collection,
        "livres": mock_livres_collection,
    }[key]

    # WHEN: On récupère les cas problématiques
    result = babelio_migration_service.get_problematic_cases()

    # THEN: On devrait avoir une seule entrée groupée
    assert len(result) == 1
    grouped_case = result[0]

    # Vérifier le type groupé
    assert grouped_case["type"] == "livre_auteur_groupe"

    # Vérifier les IDs
    assert grouped_case["livre_id"] == livre_id
    assert grouped_case["auteur_id"] == auteur_id

    # Vérifier les informations affichées
    assert grouped_case["titre_attendu"] == "Romance"
    assert grouped_case["nom_auteur"] == "Anne Goscinny"
    assert grouped_case["auteur"] == "Anne Goscinny"

    # Vérifier les métadonnées
    assert "raison" in grouped_case
    assert "timestamp" in grouped_case


def test_get_problematic_cases_should_not_group_when_only_book_is_problematic(
    babelio_migration_service, mock_mongodb_service
):
    """Test: Un livre problématique sans auteur problématique ne doit PAS être groupé."""
    # GIVEN: Seulement un livre problématique (pas l'auteur)
    livre_id = str(ObjectId())
    auteur_id = str(ObjectId())
    timestamp = datetime.now(UTC)

    # Mock de la collection problematic_cases avec seulement le livre
    mock_problematic_collection = MagicMock()
    mock_problematic_collection.find.return_value = [
        {
            "_id": ObjectId(),
            "type": "livre",
            "livre_id": livre_id,
            "titre_attendu": "Un autre livre",
            "auteur": "Auteur Normal",
            "raison": "Livre non trouvé",
            "url_babelio": "N/A",
            "timestamp": timestamp,
        }
        # Pas d'entrée auteur dans problematic_cases
    ]

    # Mock de la collection livres
    mock_livres_collection = MagicMock()
    mock_livres_collection.find_one.return_value = {
        "_id": ObjectId(livre_id),
        "titre": "Un autre livre",
        "auteur_id": ObjectId(auteur_id),
    }

    mock_mongodb_service.db.__getitem__.side_effect = lambda key: {
        "babelio_problematic_cases": mock_problematic_collection,
        "livres": mock_livres_collection,
    }[key]

    # WHEN: On récupère les cas problématiques
    result = babelio_migration_service.get_problematic_cases()

    # THEN: On devrait avoir une entrée normale (pas groupée)
    assert len(result) == 1
    case = result[0]

    # Vérifier que ce n'est PAS groupé
    assert case["type"] == "livre"
    assert case["livre_id"] == livre_id


def test_get_problematic_cases_should_handle_mixed_cases(
    babelio_migration_service, mock_mongodb_service
):
    """Test: Mélange de cas groupés et non groupés."""
    # GIVEN: 2 livres problématiques, dont 1 avec auteur problématique
    livre1_id = str(ObjectId())
    auteur1_id = str(ObjectId())
    livre2_id = str(ObjectId())
    auteur2_id = str(ObjectId())
    timestamp = datetime.now(UTC)

    mock_problematic_collection = MagicMock()
    mock_problematic_collection.find.return_value = [
        # Livre 1 + auteur 1 (à grouper)
        {
            "_id": ObjectId(),
            "type": "livre",
            "livre_id": livre1_id,
            "titre_attendu": "Romance",
            "auteur": "Anne Goscinny",
            "raison": "Livre non trouvé",
            "url_babelio": "N/A",
            "timestamp": timestamp,
        },
        {
            "_id": ObjectId(),
            "type": "auteur",
            "auteur_id": auteur1_id,
            "nom_auteur": "Anne Goscinny",
            "nb_livres": 1,
            "raison": "Livres problématiques",
            "timestamp": timestamp,
        },
        # Livre 2 seul (pas de groupement)
        {
            "_id": ObjectId(),
            "type": "livre",
            "livre_id": livre2_id,
            "titre_attendu": "Autre livre",
            "auteur": "Auteur OK",
            "raison": "Titre ambigu",
            "url_babelio": "https://...",
            "timestamp": timestamp,
        },
    ]

    mock_livres_collection = MagicMock()

    def find_one_side_effect(query):
        livre_id_query = str(query["_id"])
        if livre_id_query == livre1_id:
            return {
                "_id": ObjectId(livre1_id),
                "titre": "Romance",
                "auteur_id": ObjectId(auteur1_id),
            }
        elif livre_id_query == livre2_id:
            return {
                "_id": ObjectId(livre2_id),
                "titre": "Autre livre",
                "auteur_id": ObjectId(auteur2_id),
            }
        return None

    mock_livres_collection.find_one.side_effect = find_one_side_effect

    mock_mongodb_service.db.__getitem__.side_effect = lambda key: {
        "babelio_problematic_cases": mock_problematic_collection,
        "livres": mock_livres_collection,
    }[key]

    # WHEN: On récupère les cas problématiques
    result = babelio_migration_service.get_problematic_cases()

    # THEN: On devrait avoir 2 entrées (1 groupée, 1 normale)
    assert len(result) == 2

    # Trouver l'entrée groupée et l'entrée normale
    grouped = [c for c in result if c.get("type") == "livre_auteur_groupe"]
    normal = [c for c in result if c.get("type") == "livre"]

    assert len(grouped) == 1
    assert len(normal) == 1

    # Vérifier l'entrée groupée
    assert grouped[0]["livre_id"] == livre1_id
    assert grouped[0]["auteur_id"] == auteur1_id

    # Vérifier l'entrée normale
    assert normal[0]["livre_id"] == livre2_id
