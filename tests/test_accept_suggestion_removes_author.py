"""Tests TDD pour retirer l'auteur de problematic_cases - Issue #124.

Quand accept_suggestion() met à jour l'URL d'un auteur,
il doit aussi retirer l'auteur de babelio_problematic_cases.
"""

from unittest.mock import MagicMock

from bson import ObjectId


class TestAcceptSuggestionRemovesAuthor:
    """Tests pour retirer l'auteur de problematic_cases."""

    def test_should_remove_author_from_problematic_cases_when_url_updated(self):
        """Test TDD: Retirer l'auteur de problematic_cases après mise à jour.

        Problème UI:
        - L'utilisateur entre l'URL Babelio d'un livre
        - Le système met à jour le livre ET l'auteur
        - Mais l'auteur reste dans les cas problématiques

        Solution:
        - Après avoir mis à jour l'URL de l'auteur
        - Retirer aussi l'auteur de babelio_problematic_cases
        """
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()

        mock_livres = MagicMock()
        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()
        mock_db = {
            "livres": mock_livres,
            "auteurs": mock_auteurs,
            "babelio_problematic_cases": mock_problematic,
        }
        mock_mongodb_service.db = mock_db

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        livre_id = str(ObjectId())
        livre_oid = ObjectId(livre_id)
        auteur_oid = ObjectId()

        # Mock livre avec auteur_id
        mock_livres.find_one.return_value = {
            "_id": livre_oid,
            "titre": "La petite menteuse",
            "auteur_id": auteur_oid,
        }

        # Mock update_one pour le livre
        mock_livres.update_one.return_value = MagicMock(matched_count=1)

        # Mock update_one pour l'auteur (pas d'URL existante, donc matched_count=1)
        mock_auteurs.update_one.return_value = MagicMock(matched_count=1)

        # Mock delete_one
        mock_problematic.delete_one.return_value = MagicMock(deleted_count=1)

        # Act
        service.accept_suggestion(
            livre_id=livre_id,
            babelio_url="https://www.babelio.com/livres/Robert-Diard-La-petite-menteuse/123",
            babelio_author_url="https://www.babelio.com/auteur/Pascale-Robert-Diard/456",
            corrected_title="La petite menteuse",
        )

        # Assert - Vérifier que problematic_cases.delete_one a été appelé 2 fois
        # 1. Pour retirer l'auteur (auteur_id)
        # 2. Pour retirer le livre (livre_id)
        assert mock_problematic.delete_one.call_count == 2, (
            "Doit retirer à la fois l'auteur ET le livre de problematic_cases"
        )

        # Vérifier les appels
        calls = [call[0][0] for call in mock_problematic.delete_one.call_args_list]
        assert {"auteur_id": str(auteur_oid)} in calls, (
            "Doit retirer l'auteur de problematic_cases"
        )
        assert {"livre_id": livre_id} in calls, (
            "Doit retirer le livre de problematic_cases"
        )

    def test_should_not_remove_author_if_url_not_updated(self):
        """Test TDD: Ne pas retirer l'auteur si l'URL n'a pas été mise à jour.

        Si l'auteur a déjà une URL, update_one retourne matched_count=0.
        Dans ce cas, ne pas essayer de retirer l'auteur de problematic_cases.
        """
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()

        mock_livres = MagicMock()
        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()
        mock_db = {
            "livres": mock_livres,
            "auteurs": mock_auteurs,
            "babelio_problematic_cases": mock_problematic,
        }
        mock_mongodb_service.db = mock_db

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        livre_id = str(ObjectId())
        livre_oid = ObjectId(livre_id)
        auteur_oid = ObjectId()

        # Mock livre avec auteur_id
        mock_livres.find_one.return_value = {
            "_id": livre_oid,
            "titre": "Un autre livre",
            "auteur_id": auteur_oid,
        }

        # Mock update_one pour le livre
        mock_livres.update_one.return_value = MagicMock(matched_count=1)

        # Mock update_one pour l'auteur (a déjà une URL, donc matched_count=0)
        mock_auteurs.update_one.return_value = MagicMock(matched_count=0)

        # Mock delete_one
        mock_problematic.delete_one.return_value = MagicMock(deleted_count=1)

        # Act
        service.accept_suggestion(
            livre_id=livre_id,
            babelio_url="https://www.babelio.com/livres/auteur/titre/123",
            babelio_author_url="https://www.babelio.com/auteur/Nom-Auteur/456",
            corrected_title=None,
        )

        # Assert - Vérifier que problematic_cases.delete_one a été appelé 1 seule fois
        # Uniquement pour retirer le livre (pas l'auteur car matched_count=0)
        assert mock_problematic.delete_one.call_count == 1, (
            "Doit retirer uniquement le livre (pas l'auteur car il a déjà une URL)"
        )

        # Vérifier l'appel
        mock_problematic.delete_one.assert_called_once_with({"livre_id": livre_id})

    def test_should_not_remove_author_if_no_author_url_provided(self):
        """Test TDD: Ne pas retirer l'auteur si aucune URL d'auteur fournie."""
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()

        mock_livres = MagicMock()
        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()
        mock_db = {
            "livres": mock_livres,
            "auteurs": mock_auteurs,
            "babelio_problematic_cases": mock_problematic,
        }
        mock_mongodb_service.db = mock_db

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        livre_id = str(ObjectId())
        livre_oid = ObjectId(livre_id)

        # Mock livre
        mock_livres.find_one.return_value = {
            "_id": livre_oid,
            "titre": "Titre",
        }

        # Mock update_one pour le livre
        mock_livres.update_one.return_value = MagicMock(matched_count=1)

        # Mock delete_one
        mock_problematic.delete_one.return_value = MagicMock(deleted_count=1)

        # Act - Pas d'URL auteur fournie
        service.accept_suggestion(
            livre_id=livre_id,
            babelio_url="https://www.babelio.com/livres/auteur/titre/123",
            babelio_author_url=None,
            corrected_title=None,
        )

        # Assert
        mock_problematic.delete_one.assert_called_once_with({"livre_id": livre_id})
        mock_auteurs.update_one.assert_not_called()
