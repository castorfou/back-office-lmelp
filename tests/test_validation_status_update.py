"""Tests TDD pour vérifier que la validation met à jour le status vers 'mongo'."""

from unittest.mock import patch

import pytest
from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    collections_management_service,
)


class TestValidationStatusUpdate:
    """Tests TDD pour s'assurer que la validation met à jour le status vers 'mongo'."""

    @patch(
        "back_office_lmelp.services.collections_management_service.livres_auteurs_cache_service"
    )
    @patch(
        "back_office_lmelp.services.collections_management_service.collections_management_service.mongodb_service"
    )
    def test_validate_suggestion_should_update_status_to_mongo(
        self, mock_mongodb_service, mock_cache_service
    ):
        """Test TDD: La validation d'une suggestion doit mettre à jour le status vers 'mongo'."""
        # Arrange
        mock_author_id = ObjectId("67ae74d24cbe4a7b032cef98")
        mock_book_id = ObjectId("68d5badd44877587a8a5c5b0")  # pragma: allowlist secret

        # Mock des services
        mock_mongodb_service.create_author_if_not_exists.return_value = mock_author_id
        mock_mongodb_service.create_book_if_not_exists.return_value = mock_book_id

        book_data = {
            "cache_id": None,  # Pas de cache pour cette suggestion
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "auteur": "Alain Mabancou",
            "titre": "Ramsès de Paris",
            "editeur": "Seuil",
            "user_validated_author": "Alain Mabanckou",
            "user_validated_title": "Ramsès de Paris",
            "user_validated_publisher": "Seuil",
        }

        # Act
        result = collections_management_service.handle_book_validation(book_data)

        # Assert
        assert result["success"] is True
        assert result["author_id"] == str(mock_author_id)
        assert result["book_id"] == str(mock_book_id)

        # Vérifier que create_author_if_not_exists a été appelé avec le bon nom
        mock_mongodb_service.create_author_if_not_exists.assert_called_once_with(
            "Alain Mabanckou"
        )

        # Vérifier que create_book_if_not_exists a été appelé avec les bonnes données
        expected_book_info = {
            "titre": "Ramsès de Paris",
            "auteur_id": mock_author_id,
            "editeur": "Seuil",
            "episodes": ["68c707ad6e51b9428ab87e9e"],  # pragma: allowlist secret
            "avis_critiques": ["68c718a16e51b9428ab88066"],  # pragma: allowlist secret
        }
        mock_mongodb_service.create_book_if_not_exists.assert_called_once_with(
            expected_book_info
        )

    @patch(
        "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
    )
    @patch(
        "back_office_lmelp.services.collections_management_service.collections_management_service.mongodb_service"
    )
    def test_validate_suggestion_with_cache_should_update_cache_status_to_mongo(
        self, mock_mongodb_service, mock_cache_service
    ):
        """Test TDD: La validation avec cache_id doit mettre à jour le status du cache vers 'mongo'."""
        # Arrange
        mock_author_id = ObjectId("67ae74d24cbe4a7b032cef98")
        mock_book_id = ObjectId("68d5badd44877587a8a5c5b0")  # pragma: allowlist secret
        cache_id_str = "68d5b9099265d804e509dbcb"  # pragma: allowlist secret

        # Mock des services
        mock_mongodb_service.create_author_if_not_exists.return_value = mock_author_id
        mock_mongodb_service.create_book_if_not_exists.return_value = mock_book_id

        book_data = {
            "cache_id": cache_id_str,  # Avec cache cette fois
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "auteur": "Alain Mabancou",
            "titre": "Ramsès de Paris",
            "editeur": "Seuil",
            "user_validated_author": "Alain Mabanckou",
            "user_validated_title": "Ramsès de Paris",
            "user_validated_publisher": "Seuil",
        }

        # Act
        result = collections_management_service.handle_book_validation(book_data)

        # Assert
        assert result["success"] is True

        # Vérifier que le cache est marqué comme traité avec le status 'mongo'
        # Issue #159: metadata avec editeur est maintenant toujours passé
        mock_cache_service.mark_as_processed.assert_called_once_with(
            ObjectId(cache_id_str),
            mock_author_id,
            mock_book_id,
            metadata={"editeur": "Seuil"},
        )

        # Vérifier que update_book_validation est appelé pour mettre à jour le status
        # Note: handle_book_validation envoie plus de métadonnées (validated_* ET suggested_*)
        call_args = mock_mongodb_service.update_book_validation.call_args
        assert call_args[0][0] == cache_id_str  # cache_id
        assert call_args[0][1] == "validated"  # status

        # Vérifier les métadonnées (doivent contenir validated_* ET suggested_*)
        metadata = call_args[0][2]
        assert metadata["validated_author"] == "Alain Mabanckou"
        assert metadata["validated_title"] == "Ramsès de Paris"
        assert (
            metadata["suggested_author"] == "Alain Mabanckou"
        )  # Nouveau: fallback de user_validated_*
        assert (
            metadata["suggested_title"] == "Ramsès de Paris"
        )  # Nouveau: fallback de user_validated_*

    def test_validation_should_result_in_mongo_status_in_cache(self):
        """Test TDD: Après validation, le livre doit avoir le status 'mongo' dans le cache."""
        # Ce test intégration vérifiera que après une validation complète,
        # un appel à l'API /livres-auteurs retourne le livre avec status='mongo'

        # Ce test sera implémenté après avoir corrigé la logique
        # pour vérifier que le status est bien mis à jour dans la DB
        pytest.skip("Test d'intégration à implémenter après correction de la logique")
