"""Tests pour l'acceptation des cas groupés livre-auteur.

Vérifie que lorsqu'on accepte une suggestion pour un cas groupé,
BOTH le livre ET l'auteur sont supprimés de problematic_cases.
"""

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


def test_accept_suggestion_should_remove_both_book_and_author_from_problematic_cases(
    babelio_migration_service, mock_mongodb_service, mock_babelio_service
):
    """Test RED: Accepter une suggestion doit supprimer BOTH livre ET auteur de problematic_cases."""
    # GIVEN: Un livre avec son auteur dans problematic_cases
    livre_id = str(ObjectId())
    auteur_id = str(ObjectId())
    babelio_url = "https://www.babelio.com/livres/Goscinny-Romance/1416257"
    auteur_url = "https://www.babelio.com/auteur/Anne-Goscinny/12345"

    # Mock des collections
    mock_livres_collection = MagicMock()
    mock_auteurs_collection = MagicMock()
    mock_problematic_collection = MagicMock()

    # Le livre a un auteur_id
    mock_livres_collection.find_one.return_value = {
        "_id": ObjectId(livre_id),
        "titre": "Romance",
        "auteur_id": ObjectId(auteur_id),
    }

    # Mock update_one pour le livre
    mock_livres_collection.update_one.return_value = MagicMock(matched_count=1)

    # Mock find_one pour l'auteur (url_babelio est None, pas absent)
    mock_auteurs_collection.find_one.return_value = {
        "_id": ObjectId(auteur_id),
        "nom": "Anne Goscinny",
        "url_babelio": None,  # IMPORTANT: None, pas absent!
    }

    # Mock update_one pour l'auteur
    # Après correction: La condition avec $or matche aussi url_babelio: None
    # Donc matched_count = 1 (l'auteur est mis à jour)
    mock_auteurs_collection.update_one.return_value = MagicMock(matched_count=1)

    mock_mongodb_service.db.__getitem__.side_effect = lambda key: {
        "livres": mock_livres_collection,
        "auteurs": mock_auteurs_collection,
        "babelio_problematic_cases": mock_problematic_collection,
    }[key]

    # Mock fetch methods
    mock_babelio_service.fetch_full_title_from_url.return_value = "Romance"
    mock_babelio_service.fetch_author_url_from_page.return_value = auteur_url

    # WHEN: On accepte la suggestion (via update_from_babelio_url qui appelle accept_suggestion)
    result = babelio_migration_service.accept_suggestion(
        livre_id=livre_id,
        babelio_url=babelio_url,
        babelio_author_url=auteur_url,
        corrected_title="Romance",
    )

    assert result is True

    # THEN: L'entrée LIVRE doit être supprimée de problematic_cases
    livre_delete_calls = [
        call
        for call in mock_problematic_collection.delete_one.call_args_list
        if call[0][0].get("livre_id") == livre_id
    ]
    assert len(livre_delete_calls) == 1, (
        "Le livre doit être supprimé de problematic_cases"
    )

    # THEN: L'entrée AUTEUR doit AUSSI être supprimée de problematic_cases
    auteur_delete_calls = [
        call
        for call in mock_problematic_collection.delete_one.call_args_list
        if call[0][0].get("auteur_id") == auteur_id
    ]
    assert len(auteur_delete_calls) == 1, (
        "L'auteur doit AUSSI être supprimé de problematic_cases "
        "car il était groupé avec le livre"
    )

    # THEN: Le champ updated_at doit être mis à jour pour l'auteur
    auteur_update_call = mock_auteurs_collection.update_one.call_args
    assert auteur_update_call is not None, "L'auteur doit être mis à jour"
    update_data = auteur_update_call[0][1]["$set"]
    assert "updated_at" in update_data, (
        "Le champ updated_at doit être mis à jour lors de la modification de l'auteur"
    )
