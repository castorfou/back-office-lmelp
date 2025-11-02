"""Tests pour la persistance de babelio_publisher dans le cache MongoDB (Issue #85).

Ce module teste que le champ `babelio_publisher` enrichi par verify_book()
est correctement persisté dans le cache MongoDB (livresauteurs_cache).

Fonctionnalités testées :
1. Persistence de babelio_publisher lors de handle_book_validation()
2. Mise à jour du cache avec babelio_publisher via mark_as_processed()
3. Traçabilité et réutilisation des données enrichies

Architecture :
- babelio_publisher est reçu du frontend dans book_data
- handle_book_validation() l'utilise pour créer le livre
- mark_as_processed() persiste babelio_publisher dans le cache
"""

from unittest.mock import Mock

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


def create_mocked_service():
    """Crée un service avec tous les mocks configurés.

    Pattern recommandé pour tester des services avec dépendances injectées.
    Évite les problèmes de pytest fixtures avec patch.object().
    """
    service = CollectionsManagementService()

    # Mock mongodb_service directement sur l'instance
    mock_mongodb = Mock()
    mock_mongodb.create_author_if_not_exists.return_value = ObjectId(
        "507f1f77bcf86cd799439014"
    )
    mock_mongodb.create_book_if_not_exists.return_value = ObjectId(
        "507f1f77bcf86cd799439015"
    )
    mock_mongodb.update_book_validation.return_value = None
    mock_mongodb.update_avis_critique = Mock(return_value=True)
    mock_mongodb.get_avis_critique_by_id.return_value = None

    # Injection directe (bypass du __init__)
    service.mongodb_service = mock_mongodb
    service._mock_mongodb = mock_mongodb  # Pour accès dans les tests

    return service


def patch_cache_service(is_already_corrected=False):
    """Retourne un tuple de patches pour l'instance globale livres_auteurs_cache_service.

    IMPORTANT: Utiliser avec le pattern de patch multiple:
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # code...

    Args:
        is_already_corrected: Si True, is_summary_corrected() retourne True

    Returns:
        Tuple de 3 context managers pour patcher les méthodes du cache service
    """
    from unittest.mock import patch as mock_patch

    return (
        mock_patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_as_processed",
            return_value=True,
        ),
        mock_patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.is_summary_corrected",
            return_value=is_already_corrected,
        ),
        mock_patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_summary_corrected",
            return_value=True,
        ),
    )


class TestBabelioPublisherPersistence:
    """Tests de la persistance de babelio_publisher dans le cache MongoDB."""

    def test_should_persist_babelio_publisher_to_cache_when_provided(self):
        """GIVEN: Validation d'un livre avec babelio_publisher enrichi par Babelio
        WHEN: handle_book_validation() est appelé
        THEN: babelio_publisher est persisté dans le cache MongoDB via mark_as_processed()
        """
        # Arrange
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439016",
            "avis_critique_id": "507f1f77bcf86cd799439017",
            "episode_oid": "507f1f77bcf86cd799439018",
            "auteur": "Hannah Assouline",
            "titre": "Des visages et des mains",
            "editeur": "",  # Éditeur vide (transcription Whisper)
            "user_validated_author": "Hannah Assouline",
            "user_validated_title": "Des visages et des mains: 150 portraits d'écrivain",
            "babelio_publisher": "Herscher",  # ✅ Enrichi par verify_book()
        }

        # Patcher l'instance globale de livres_auteurs_cache_service

        patches = patch_cache_service()
        with (
            patches[0] as mock_mark_processed,
            patches[1],
            patches[2],
        ):
            # Act
            service.handle_book_validation(book_data)

            # Assert - Vérifier que mark_as_processed est appelé avec babelio_publisher
            assert mock_mark_processed.called
            call_args = mock_mark_processed.call_args

            # Vérifier les arguments positionnels (cache_id, author_id, book_id)
            assert call_args[0][0] == ObjectId("507f1f77bcf86cd799439016")  # cache_id
            assert call_args[0][1] == ObjectId("507f1f77bcf86cd799439014")  # author_id
            assert call_args[0][2] == ObjectId("507f1f77bcf86cd799439015")  # book_id

            # ✅ VÉRIFIER QUE babelio_publisher est dans les metadata
            metadata = call_args[1].get("metadata", {})
            assert "babelio_publisher" in metadata, (
                "babelio_publisher doit être dans metadata"
            )
            assert metadata["babelio_publisher"] == "Herscher"

    def test_should_use_babelio_publisher_when_creating_book(self):
        """GIVEN: book_data contient babelio_publisher mais pas user_validated_publisher
        WHEN: handle_book_validation() est appelé
        THEN: Le livre est créé avec babelio_publisher comme éditeur
        """
        # Arrange
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439016",
            "avis_critique_id": "507f1f77bcf86cd799439017",
            "episode_oid": "507f1f77bcf86cd799439018",
            "auteur": "Hannah Assouline",
            "titre": "Des visages et des mains",
            "editeur": "",  # Éditeur vide
            "user_validated_author": "Hannah Assouline",
            "user_validated_title": "Des visages et des mains",
            "babelio_publisher": "Herscher",  # ✅ Doit être utilisé
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert - Vérifier que create_book_if_not_exists est appelé avec Herscher
            assert service._mock_mongodb.create_book_if_not_exists.called
            book_info = service._mock_mongodb.create_book_if_not_exists.call_args[0][0]

            assert book_info["editeur"] == "Herscher"

    def test_should_not_persist_babelio_publisher_when_not_provided(self):
        """GIVEN: Validation d'un livre sans babelio_publisher (confidence < 0.90)
        WHEN: handle_book_validation() est appelé
        THEN: babelio_publisher n'est PAS dans les metadata du cache
        """
        # Arrange
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439016",
            "avis_critique_id": "507f1f77bcf86cd799439017",
            "episode_oid": "507f1f77bcf86cd799439018",
            "auteur": "Auteur Inconnu",
            "titre": "Titre vague",
            "editeur": "",
            "user_validated_author": "Auteur Inconnu",
            "user_validated_title": "Titre vague",
            # Pas de babelio_publisher (confidence < 0.90)
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with (
            patches[0] as mock_mark_processed,
            patches[1],
            patches[2],
        ):
            # Act
            service.handle_book_validation(book_data)

            # Assert - Vérifier que babelio_publisher n'est PAS dans metadata
            call_args = mock_mark_processed.call_args
            metadata = call_args[1].get("metadata", {})
            assert "babelio_publisher" not in metadata, (
                "babelio_publisher ne doit PAS être dans metadata si absent"
            )

    def test_should_prioritize_user_validated_publisher_over_babelio(self):
        """GIVEN: book_data contient user_validated_publisher ET babelio_publisher
        WHEN: handle_book_validation() est appelé
        THEN: user_validated_publisher est prioritaire pour créer le livre
        """
        # Arrange
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439016",
            "avis_critique_id": "507f1f77bcf86cd799439017",
            "episode_oid": "507f1f77bcf86cd799439018",
            "auteur": "Hannah Assouline",
            "titre": "Des visages et des mains",
            "editeur": "",
            "user_validated_author": "Hannah Assouline",
            "user_validated_title": "Des visages et des mains",
            "user_validated_publisher": "Herscher (édition spéciale)",  # ✅ Priorité
            "babelio_publisher": "Herscher",  # Doit être ignoré pour le livre
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with (
            patches[0] as mock_mark_processed,
            patches[1],
            patches[2],
        ):
            # Act
            service.handle_book_validation(book_data)

            # Assert - Vérifier que create_book_if_not_exists utilise user_validated
            book_info = service._mock_mongodb.create_book_if_not_exists.call_args[0][0]
            assert book_info["editeur"] == "Herscher (édition spéciale)"

            # Assert - Mais babelio_publisher doit quand même être persisté dans cache
            call_args = mock_mark_processed.call_args
            metadata = call_args[1].get("metadata", {})
            assert metadata.get("babelio_publisher") == "Herscher"
