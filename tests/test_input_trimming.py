"""
Tests pour vérifier le trim des espaces parasites lors de la saisie utilisateur.

Ces tests vérifient que les espaces en début/fin de champ sont supprimés
avant stockage en base de données, évitant les problèmes de matching et
doublons causés par les copier-coller.
"""

from unittest.mock import Mock

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


def create_mocked_service():
    """Crée un service avec les mocks MongoDB configurés."""
    service = CollectionsManagementService()

    mock_mongodb = Mock()
    mock_mongodb.create_author_if_not_exists.return_value = ObjectId(
        "507f1f77bcf86cd799439014"  # pragma: allowlist secret
    )
    mock_mongodb.create_book_if_not_exists.return_value = ObjectId(
        "507f1f77bcf86cd799439015"  # pragma: allowlist secret
    )
    mock_mongodb.update_book_validation.return_value = None
    mock_mongodb.get_avis_critique_by_id.return_value = (
        None  # Pas d'avis critique existant
    )

    service.mongodb_service = mock_mongodb
    service._mock_mongodb = mock_mongodb

    return service


def patch_cache_service():
    """Retourne le patch pour le singleton livres_auteurs_cache_service."""
    from unittest.mock import patch as mock_patch

    return mock_patch(
        "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_as_processed",
        return_value=True,
    )


class TestInputTrimming:
    """Tests de trim des espaces parasites dans les champs utilisateur."""

    def test_should_trim_user_validated_author_spaces(self):
        """Les espaces en début/fin du champ auteur doivent être supprimés."""
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439016",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439017",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439018",  # pragma: allowlist secret
            "auteur": "Guillaume Lebrun",
            "titre": "Ravagés de splendeur",
            "editeur": "Bourgois",
            "user_validated_author": "  Guillaume Lebrun  ",  # Espaces parasites
            "user_validated_title": "Ravagés de splendeur",
            "user_validated_publisher": "Bourgois",
        }

        with patch_cache_service():
            service.handle_book_validation(book_data)

            # Vérifier que l'auteur est créé SANS espaces
            service._mock_mongodb.create_author_if_not_exists.assert_called_once_with(
                "Guillaume Lebrun"  # Pas d'espaces
            )

    def test_should_trim_user_validated_title_spaces(self):
        """Les espaces en début/fin du champ titre doivent être supprimés."""
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439016",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439017",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439018",  # pragma: allowlist secret
            "auteur": "Guillaume Lebrun",
            "titre": "Ravagés de splendeur",
            "editeur": "Bourgois",
            "user_validated_author": "Guillaume Lebrun",
            "user_validated_title": "  Ravagés de splendeur  ",  # Espaces parasites
            "user_validated_publisher": "Bourgois",
        }

        with patch_cache_service():
            service.handle_book_validation(book_data)

            # Vérifier que le livre est créé avec un titre SANS espaces
            book_info_call = service._mock_mongodb.create_book_if_not_exists.call_args[
                0
            ][0]
            assert book_info_call["titre"] == "Ravagés de splendeur"  # Pas d'espaces

    def test_should_trim_user_validated_publisher_spaces(self):
        """Les espaces en début/fin du champ éditeur doivent être supprimés."""
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439016",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439017",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439018",  # pragma: allowlist secret
            "auteur": "Guillaume Lebrun",
            "titre": "Ravagés de splendeur",
            "editeur": "Bourgois",
            "user_validated_author": "Guillaume Lebrun",
            "user_validated_title": "Ravagés de splendeur",
            "user_validated_publisher": "  Bourgois  ",  # Espaces parasites
        }

        with patch_cache_service():
            service.handle_book_validation(book_data)

            # Vérifier que l'éditeur est stocké SANS espaces
            book_info_call = service._mock_mongodb.create_book_if_not_exists.call_args[
                0
            ][0]
            assert book_info_call["editeur"] == "Bourgois"  # Pas d'espaces

    def test_should_trim_suggested_author_and_title(self):
        """Les champs suggested doivent aussi être trimmés."""
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439016",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439017",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439018",  # pragma: allowlist secret
            "auteur": "Guillaume Lebrun",
            "titre": "Ravagés de splendeur",
            "editeur": "Bourgois",
            "suggested_author": "  Guillaume Lebrun  ",  # Espaces parasites
            "suggested_title": "  Ravagés de splendeur  ",  # Espaces parasites
        }

        with patch_cache_service():
            service.handle_book_validation(book_data)

            # Vérifier que les champs suggested sont stockés SANS espaces dans le cache
            # update_book_validation(cache_id, status, metadata) -> accès à metadata = [2]
            metadata = service._mock_mongodb.update_book_validation.call_args[0][2]
            assert metadata["suggested_author"] == "Guillaume Lebrun"  # Pas d'espaces
            assert (
                metadata["suggested_title"] == "Ravagés de splendeur"
            )  # Pas d'espaces

    def test_should_trim_all_fields_simultaneously(self):
        """Tous les champs avec espaces parasites doivent être trimmés en même temps."""
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439016",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439017",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439018",  # pragma: allowlist secret
            "auteur": "  Guillaume Lebrun  ",
            "titre": "  Ravagés de splendeur  ",
            "editeur": "  Bourgois  ",
            "user_validated_author": "  Guillaume Lebrun  ",
            "user_validated_title": "  Ravagés de splendeur  ",
            "user_validated_publisher": "  Bourgois  ",
            "suggested_author": "  Guillaume Lebrun  ",
            "suggested_title": "  Ravagés de splendeur  ",
        }

        with patch_cache_service():
            service.handle_book_validation(book_data)

            # Vérifier l'auteur
            service._mock_mongodb.create_author_if_not_exists.assert_called_once_with(
                "Guillaume Lebrun"
            )

            # Vérifier le livre (titre et éditeur)
            book_info_call = service._mock_mongodb.create_book_if_not_exists.call_args[
                0
            ][0]
            assert book_info_call["titre"] == "Ravagés de splendeur"
            assert book_info_call["editeur"] == "Bourgois"

            # Vérifier les métadonnées suggested
            # update_book_validation(cache_id, status, metadata) -> accès à metadata = [2]
            metadata = service._mock_mongodb.update_book_validation.call_args[0][2]
            assert metadata["suggested_author"] == "Guillaume Lebrun"
            assert metadata["suggested_title"] == "Ravagés de splendeur"

    def test_should_preserve_internal_spaces(self):
        """Les espaces internes doivent être préservés (seuls début/fin sont trimmés)."""
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439016",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439017",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439018",  # pragma: allowlist secret
            "auteur": "Jean-Pierre Martin",
            "titre": "Le livre de la jungle",
            "editeur": "Éditions du Seuil",
            "user_validated_author": "  Jean-Pierre Martin  ",  # Espaces externes
            "user_validated_title": "  Le livre de la jungle  ",  # Espaces externes
            "user_validated_publisher": "  Éditions du Seuil  ",  # Espaces externes
        }

        with patch_cache_service():
            service.handle_book_validation(book_data)

            # Vérifier que les espaces INTERNES sont préservés
            service._mock_mongodb.create_author_if_not_exists.assert_called_once_with(
                "Jean-Pierre Martin"  # Tiret préservé
            )

            book_info_call = service._mock_mongodb.create_book_if_not_exists.call_args[
                0
            ][0]
            assert (
                book_info_call["titre"] == "Le livre de la jungle"
            )  # Espaces internes
            assert (
                book_info_call["editeur"] == "Éditions du Seuil"
            )  # Espace dans "du Seuil"
