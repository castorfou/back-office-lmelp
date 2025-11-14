"""Test TDD: auto_process_verified_books persiste babelio_publisher dans livres (Issue #85).

GREEN: auto_process_verified_books met à jour editeur avec babelio_publisher

GIVEN:
- Cache avec livre enrichi (babelio_publisher = "P.O.L", editeur original = "POL")
- Livres collection avec livre existant ayant editeur = "POL" (ancien)

WHEN: auto_process_verified_books() est appelée

THEN:
- Le livre est trouvé via get_books_by_validation_status("babelio_enriched")
- La différence entre cache.babelio_publisher et livres.editeur est détectée
- livres.editeur est mis à jour de "POL" à "P.O.L"
"""

from unittest.mock import Mock, patch

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)
from back_office_lmelp.services.mongodb_service import MongoDBService


def test_auto_process_enriched_books_updates_editeur():
    """
    GREEN: auto_process_verified_books détecte et met à jour l'éditeur enrichi par Babelio.

    Vérifie que:
    1. Les livres enrichis par Babelio (avec babelio_publisher) sont trouvés
    2. La différence d'éditeur est détectée
    3. livres.editeur est mis à jour avec la valeur Babelio
    """

    author_id = ObjectId(
        "68e47439f4ac0655e1de7d6e"  # pragma: allowlist secret
    )
    book_id = ObjectId(
        "68e47439f4ac0655e1de7d6f"  # pragma: allowlist secret
    )
    episode_oid = "68bd9ed3582cf994fb66f1d6"  # pragma: allowlist secret
    avis_critique_id = ObjectId(
        "68bddf38d79eae6a485abdaf"  # pragma: allowlist secret
    )

    # Livre dans le cache avec enrichissement Babelio
    cache_book_enriched = {
        "episode_oid": episode_oid,
        "auteur": "Emmanuel Carrère",
        "titre": "Kolkhoze",
        "editeur": "POL",  # Valeur originale du cache
        "babelio_publisher": "P.O.L.",  # Valeur enrichie depuis Babelio
        "status": "mongo",
        "avis_critique_id": avis_critique_id,
    }

    # Livre existant dans collection livres avec l'ancien éditeur
    livres_doc = {
        "_id": book_id,
        "titre": "Kolkhoze",
        "auteur_id": author_id,
        "editeur": "POL",  # ❌ Ancien (à mettre à jour)
        "episodes": [episode_oid],
        "avis_critiques": [avis_critique_id],
    }

    # Setup MongoDB service avec collections mockées
    mongodb_service = MongoDBService()
    mock_livres_collection = Mock()
    mock_auteurs_collection = Mock()

    mongodb_service.livres_collection = mock_livres_collection
    mongodb_service.auteurs_collection = mock_auteurs_collection

    # Mock find_one pour retourner le livre existant
    mock_livres_collection.find_one.return_value = livres_doc

    # Mock update_one pour mettre à jour le doc in-memory (simulation MongoDB)
    def update_livres_doc(_filter_dict, update_dict):
        if "$set" in update_dict:
            livres_doc.update(update_dict["$set"])
        return Mock(modified_count=1)

    mock_livres_collection.update_one.side_effect = update_livres_doc

    # Mock auteurs_collection (pour _add_book_to_author)
    mock_auteurs_collection.update_one = Mock()

    # Setup service
    service = CollectionsManagementService()
    service.mongodb_service = mongodb_service

    # Mock les dépendances externes
    with (
        patch.object(
            mongodb_service,
            "get_books_by_validation_status",
            return_value=[cache_book_enriched],
        ) as mock_get_books,
        patch.object(
            mongodb_service, "create_author_if_not_exists", return_value=author_id
        ),
        patch.object(
            mongodb_service,
            "get_critical_review_by_episode_oid",
            return_value={"_id": avis_critique_id},
        ),
    ):
        # Act
        result = service.auto_process_verified_books()

        # Assert 1: Vérifier que get_books_by_validation_status a été appelé avec "verified"
        # Note: L'enrichissement Babelio est stocké dans le champ babelio_publisher,
        # pas dans un statut séparé. Les livres enrichis restent "verified".
        mock_get_books.assert_called_once_with("verified")

        # Assert 2: Vérifier que le livre a été trouvé et traité
        assert result["processed_count"] == 1, "Un livre devrait être traité"

        # Assert 3: Vérifier que livres.editeur a été mis à jour
        assert livres_doc["editeur"] == "P.O.L.", (
            f"Expected livres.editeur='P.O.L.' but got '{livres_doc['editeur']}'"
        )

        # Assert 4: Vérifier que update_one a été appelé
        mock_livres_collection.update_one.assert_called_once()
        call_args = mock_livres_collection.update_one.call_args
        assert call_args[0][0] == {"_id": book_id}, "Filter doit chercher par _id"
        assert "editeur" in call_args[0][1]["$set"], "$set doit contenir editeur"
        assert call_args[0][1]["$set"]["editeur"] == "P.O.L.", (
            "Editeur doit être P.O.L."
        )


def test_auto_process_no_update_when_editeur_same():
    """
    Vérifier que quand l'éditeur du cache et de livres est identique ET que
    l'épisode existe déjà dans episodes array, update_one est appelé avec
    $addToSet (qui ne modifiera rien grâce à la déduplication automatique).
    """

    author_id = ObjectId("68e47439f4ac0655e1de7d6e")  # pragma: allowlist secret
    book_id = ObjectId("68e47439f4ac0655e1de7d6f")  # pragma: allowlist secret
    episode_oid = "68bd9ed3582cf994fb66f1d6"  # pragma: allowlist secret

    cache_book = {
        "episode_oid": episode_oid,
        "auteur": "Test Author",
        "titre": "Test Book",
        "editeur": "Gallimard",
        "babelio_publisher": "Gallimard",  # Même éditeur
        "status": "mongo",
    }

    livres_doc = {
        "_id": book_id,
        "titre": "Test Book",
        "auteur_id": author_id,
        "editeur": "Gallimard",  # Déjà correct
        "episodes": [episode_oid],  # Épisode déjà présent
    }

    mongodb_service = MongoDBService()
    mock_livres_collection = Mock()
    mock_auteurs_collection = Mock()

    mongodb_service.livres_collection = mock_livres_collection
    mongodb_service.auteurs_collection = mock_auteurs_collection

    mock_livres_collection.find_one.return_value = livres_doc
    mock_livres_collection.update_one = Mock()
    mock_auteurs_collection.update_one = Mock()

    service = CollectionsManagementService()
    service.mongodb_service = mongodb_service

    with (
        patch.object(
            mongodb_service, "get_books_by_validation_status", return_value=[cache_book]
        ),
        patch.object(
            mongodb_service, "create_author_if_not_exists", return_value=author_id
        ),
        patch.object(
            mongodb_service, "get_critical_review_by_episode_oid", return_value=None
        ),
    ):
        # Act
        service.auto_process_verified_books()

        # Assert: Issue #96 Fix - update_one EST appelé pour ajouter l'épisode avec $addToSet
        # MongoDB ne créera pas de doublon grâce à $addToSet
        mock_livres_collection.update_one.assert_called_once()
        call_args = mock_livres_collection.update_one.call_args[0]
        assert call_args[0] == {"_id": book_id}
        # Vérifier que $addToSet est utilisé pour éviter les doublons
        assert "$addToSet" in call_args[1]
        assert "episodes" in call_args[1]["$addToSet"]
