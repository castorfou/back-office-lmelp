"""Tests TDD pour la validation de create_book_log - Issue #124.

La Phase 2 utilise livre_status='none' car elle ne modifie pas les livres.
"""

import pytest


class TestCreateBookLogValidation:
    """Tests pour vérifier la validation des statuts dans create_book_log."""

    def test_should_accept_none_as_valid_livre_status(self):
        """Test TDD: livre_status='none' doit être accepté.

        En Phase 2, on complète les auteurs mais on ne modifie PAS les livres.
        Le livre_status doit donc être 'none' pour indiquer qu'aucune action
        n'a été effectuée sur le livre.

        Erreur production:
        ValueError: livre_status must be one of {'success', 'not_found', 'error'},
        got 'none'
        """
        # Arrange
        from src.back_office_lmelp.utils.migration_runner import create_book_log

        # Act & Assert - ne doit PAS lever d'exception
        result = create_book_log(
            titre="Jean-Daniel Beauvallet",
            auteur="",
            livre_status="none",  # Phase 2: livre pas modifié
            auteur_status="success",
            details=["Via livre: Rock City Guide", "✅ Auteur complété"],
        )

        # Vérifier la structure du résultat
        assert result["livre_status"] == "none"
        assert result["auteur_status"] == "success"
        assert result["titre"] == "Jean-Daniel Beauvallet"

    def test_should_reject_invalid_livre_status(self):
        """Test TDD: Un livre_status invalide doit être rejeté."""
        # Arrange
        from src.back_office_lmelp.utils.migration_runner import create_book_log

        # Act & Assert
        with pytest.raises(ValueError, match="livre_status must be one of"):
            create_book_log(
                titre="Test",
                auteur="Author",
                livre_status="invalid_status",
                auteur_status="success",
                details=["test"],
            )

    def test_should_accept_all_valid_livre_statuses(self):
        """Test TDD: Tous les statuts valides doivent être acceptés."""
        # Arrange
        from src.back_office_lmelp.utils.migration_runner import create_book_log

        valid_statuses = ["success", "error", "not_found", "none"]

        # Act & Assert
        for status in valid_statuses:
            result = create_book_log(
                titre="Test",
                auteur="Author",
                livre_status=status,
                auteur_status="success",
                details=["test"],
            )
            assert result["livre_status"] == status, (
                f"Status '{status}' should be accepted"
            )
