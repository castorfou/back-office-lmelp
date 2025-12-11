"""Tests TDD pour marquer un auteur comme absent de Babelio - Issue #124.

mark_as_not_found() doit supporter item_type='auteur' en plus de 'livre'.
"""

from datetime import datetime
from unittest.mock import MagicMock

from bson import ObjectId


class TestMarkAuthorNotFound:
    """Tests pour marquer un auteur comme absent de Babelio."""

    def test_should_mark_author_as_not_found_in_mongodb(self):
        """Test TDD: Marquer un auteur avec babelio_not_found=True.

        Problème UI:
        - L'utilisateur veut marquer un auteur comme "Pas sur Babelio"
        - mark_as_not_found() ne supporte que les livres

        Solution:
        - Étendre mark_as_not_found() pour supporter item_type='auteur'
        - Marquer l'auteur avec babelio_not_found=True dans collection auteurs
        - Retirer l'auteur de babelio_problematic_cases
        """
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()

        # Mock collections
        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()
        mock_db = {
            "auteurs": mock_auteurs,
            "babelio_problematic_cases": mock_problematic,
        }
        mock_mongodb_service.db = mock_db

        auteur_id = str(ObjectId())
        auteur_oid = ObjectId(auteur_id)

        # Mock update_one pour retourner succès
        mock_auteurs.update_one.return_value = MagicMock(matched_count=1)
        mock_problematic.delete_one.return_value = MagicMock(deleted_count=1)

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Act
        result = service.mark_as_not_found(
            item_id=auteur_id, reason="Auteur introuvable", item_type="auteur"
        )

        # Assert
        assert result is True, "Doit retourner True si succès"

        # Vérifier l'appel update_one sur collection auteurs
        mock_auteurs.update_one.assert_called_once()
        call_args = mock_auteurs.update_one.call_args
        query = call_args[0][0]
        update = call_args[0][1]

        assert query == {"_id": auteur_oid}, "Doit filtrer par ObjectId de l'auteur"
        assert update["$set"]["babelio_not_found"] is True
        assert update["$set"]["babelio_not_found_reason"] == "Auteur introuvable"
        assert isinstance(update["$set"]["babelio_not_found_date"], datetime)
        assert isinstance(update["$set"]["updated_at"], datetime)

        # Vérifier le retrait de problematic_cases
        mock_problematic.delete_one.assert_called_once_with({"auteur_id": auteur_id})

    def test_should_return_false_if_author_not_found_in_db(self):
        """Test TDD: Retourner False si l'auteur n'existe pas dans MongoDB."""
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()

        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()
        mock_db = {
            "auteurs": mock_auteurs,
            "babelio_problematic_cases": mock_problematic,
        }
        mock_mongodb_service.db = mock_db

        auteur_id = str(ObjectId())

        # Mock update_one pour retourner matched_count=0 (auteur non trouvé)
        mock_auteurs.update_one.return_value = MagicMock(matched_count=0)

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Act
        result = service.mark_as_not_found(
            item_id=auteur_id, reason="Test", item_type="auteur"
        )

        # Assert
        assert result is False, "Doit retourner False si l'auteur n'existe pas"
        mock_problematic.delete_one.assert_not_called()

    def test_should_support_livre_type_for_backward_compatibility(self):
        """Test TDD: Doit toujours supporter item_type='livre' (compatibilité)."""
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()

        mock_livres = MagicMock()
        mock_problematic = MagicMock()
        mock_db = {
            "livres": mock_livres,
            "babelio_problematic_cases": mock_problematic,
        }
        mock_mongodb_service.db = mock_db

        livre_id = str(ObjectId())

        # Mock update_one pour retourner succès
        mock_livres.update_one.return_value = MagicMock(matched_count=1)
        mock_problematic.delete_one.return_value = MagicMock(deleted_count=1)

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Act
        result = service.mark_as_not_found(
            item_id=livre_id, reason="Livre introuvable", item_type="livre"
        )

        # Assert
        assert result is True, "Doit toujours supporter item_type='livre'"
        mock_livres.update_one.assert_called_once()
        mock_problematic.delete_one.assert_called_once_with({"livre_id": livre_id})
