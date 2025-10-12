"""Test TDD pour le bug éditeur vide.

Bug: Quand l'utilisateur saisit manuellement un éditeur dans le modal de validation,
le backend enregistre l'éditeur original (chaîne vide) au lieu de la valeur saisie
(user_validated_publisher).

Scénario réel:
1. Phase 2.5 trouve "Hannah Assouline - Des visages et des mains"
2. L'éditeur n'est pas dans la suggestion (vide)
3. L'utilisateur saisit manuellement "Herscher"
4. BUG: En base, editeur: "" au lieu de editeur: "Herscher"
"""

from unittest.mock import Mock, patch

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


def test_should_use_user_validated_publisher_when_original_is_empty():
    """
    GIVEN: Un livre avec éditeur original vide
    WHEN: L'utilisateur valide une suggestion en saisissant manuellement l'éditeur
    THEN: Le livre créé doit contenir l'éditeur saisi par l'utilisateur
    """
    # Arrange - Helper function pattern (CLAUDE.md)
    service = CollectionsManagementService()

    # Mock mongodb_service
    mock_mongodb = Mock()
    mock_author_id = ObjectId("68eaccf30e71aa0efaaca069")
    mock_book_id = ObjectId("68eaccf30e71aa0efaaca06a")
    mock_cache_id = ObjectId("68eaccf30e71aa0efaaca06b")

    mock_mongodb.create_author_if_not_exists.return_value = mock_author_id
    mock_mongodb.create_book_if_not_exists.return_value = mock_book_id
    mock_mongodb.update_book_validation = Mock(return_value=None)
    mock_mongodb.get_avis_critique_by_id.return_value = None

    service.mongodb_service = mock_mongodb
    service._mock_mongodb = mock_mongodb

    # Données reçues du frontend (similaire à la requête réelle)
    book_data = {
        "cache_id": str(mock_cache_id),
        "episode_oid": "678cce74a414f229887780cb",  # pragma: allowlist secret
        "avis_critique_id": "686c56e28af289b1d583d1ad",
        "auteur": "Anna Assouline",  # Original (erreur transcription)
        "titre": "Des visages et des mains",  # Original
        "editeur": "",  # ❌ Original VIDE (pas dans transcription)
        "user_validated_author": "Hannah Assouline",  # ✅ Corrigé
        "user_validated_title": "Des visages et des mains: 150 portraits d'écrivains",  # ✅ Enrichi
        "user_validated_publisher": "Herscher",  # ✅ Saisi manuellement par l'utilisateur
    }

    # Act - Mock le cache service pour éviter les appels réels (singleton pattern)
    patches = (
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_as_processed",
            return_value=True,
        ),
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.is_summary_corrected",
            return_value=False,
        ),
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_summary_corrected",
            return_value=True,
        ),
    )
    with patches[0], patches[1], patches[2]:
        service.handle_book_validation(book_data)

    # Assert
    # Vérifier que create_book_if_not_exists a été appelé avec l'éditeur SAISI
    assert mock_mongodb.create_book_if_not_exists.called
    book_info_arg = mock_mongodb.create_book_if_not_exists.call_args[0][0]

    # ✅ Le livre doit contenir l'éditeur saisi par l'utilisateur, PAS l'original vide
    assert book_info_arg["editeur"] == "Herscher", (
        f"Expected editeur='Herscher' (user input), "
        f"but got editeur='{book_info_arg['editeur']}' (original empty)"
    )

    # Vérifier aussi que l'auteur et le titre utilisent les valeurs validées
    assert (
        book_info_arg["titre"] == "Des visages et des mains: 150 portraits d'écrivains"
    )
    assert book_info_arg["auteur_id"] == mock_author_id

    # Vérifier que l'auteur créé utilise user_validated_author
    mock_mongodb.create_author_if_not_exists.assert_called_once_with("Hannah Assouline")


def test_should_fallback_to_original_publisher_if_user_validated_is_empty():
    """
    GIVEN: Un livre avec éditeur original non vide
    WHEN: L'utilisateur ne modifie pas l'éditeur (user_validated_publisher vide ou absent)
    THEN: Le livre doit utiliser l'éditeur original
    """
    # Arrange
    service = CollectionsManagementService()

    mock_mongodb = Mock()
    mock_author_id = ObjectId()
    mock_book_id = ObjectId()
    mock_cache_id = ObjectId()

    mock_mongodb.create_author_if_not_exists.return_value = mock_author_id
    mock_mongodb.create_book_if_not_exists.return_value = mock_book_id
    mock_mongodb.get_avis_critique_by_id.return_value = None

    service.mongodb_service = mock_mongodb

    book_data = {
        "cache_id": str(mock_cache_id),
        "episode_oid": "678cce74a414f229887780cb",  # pragma: allowlist secret
        "avis_critique_id": "686c56e28af289b1d583d1ad",
        "auteur": "Test Author",
        "titre": "Test Book",
        "editeur": "Original Publisher",  # ✅ Original non vide
        "user_validated_author": "Test Author",
        "user_validated_title": "Test Book",
        "user_validated_publisher": "",  # ❌ Utilisateur n'a rien saisi
    }

    # Act - Mock le cache service (singleton pattern)
    patches = (
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_as_processed",
            return_value=True,
        ),
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.is_summary_corrected",
            return_value=False,
        ),
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_summary_corrected",
            return_value=True,
        ),
    )
    with patches[0], patches[1], patches[2]:
        service.handle_book_validation(book_data)

    # Assert
    book_info_arg = mock_mongodb.create_book_if_not_exists.call_args[0][0]
    assert book_info_arg["editeur"] == "Original Publisher", (
        "Should fallback to original publisher when user_validated_publisher is empty"
    )
