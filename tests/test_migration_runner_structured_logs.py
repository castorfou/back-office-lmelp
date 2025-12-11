"""Tests TDD pour les logs structurés de MigrationRunner (Issue #124 - Phase 11).

Ce module teste la génération de logs structurés pour le frontend,
permettant un affichage compact avec expand/collapse par livre traité.
"""

import pytest


class TestMigrationRunnerStructuredLogs:
    """Tests pour la structure des logs de migration."""

    def test_book_log_should_have_structured_format(self):
        """Test TDD: Un log de livre doit avoir une structure précise.

        Problème business réel:
        - Frontend veut afficher 1 ligne compacte par livre traité
        - Besoin de statuts séparés pour livre et auteur
        - Besoin de détails expandables

        Format attendu:
        {
            "titre": "La Cordillère des ondes",
            "auteur": "Patrice Delbourg",
            "livre_status": "error",  # success | error | not_found
            "auteur_status": "error",  # success | error | not_found | none
            "details": [
                "📚 Recherche Babelio...",
                "⚠️ Titre ne correspond pas"
            ]
        }
        """
        # Arrange - Structure attendue
        expected_structure = {
            "titre": str,
            "auteur": str,
            "livre_status": str,
            "auteur_status": str,
            "details": list,
        }

        # Act - Créer un log de livre (fonction à implémenter)
        from back_office_lmelp.utils.migration_runner import create_book_log

        book_log = create_book_log(
            titre="La Cordillère des ondes",
            auteur="Patrice Delbourg",
            livre_status="error",
            auteur_status="error",
            details=[
                "📚 Recherche Babelio pour 'La Cordillère des ondes'",
                "🔍 URL trouvée: https://www.babelio.com/livres/...",
                "⚠️ Titre ne correspond pas",
                "❌ Livre marqué comme problématique",
            ],
        )

        # Assert - Vérifier la structure
        assert isinstance(book_log, dict)
        assert set(book_log.keys()) == set(expected_structure.keys())

        # Vérifier les types
        assert isinstance(book_log["titre"], str)
        assert isinstance(book_log["auteur"], str)
        assert isinstance(book_log["livre_status"], str)
        assert isinstance(book_log["auteur_status"], str)
        assert isinstance(book_log["details"], list)

        # Vérifier les valeurs
        assert book_log["titre"] == "La Cordillère des ondes"
        assert book_log["auteur"] == "Patrice Delbourg"
        assert book_log["livre_status"] == "error"
        assert book_log["auteur_status"] == "error"
        assert len(book_log["details"]) == 4

    def test_livre_status_should_be_valid_enum(self):
        """Test TDD: livre_status doit être success, error, ou not_found."""
        from back_office_lmelp.utils.migration_runner import create_book_log

        # Test valeurs valides
        for status in ["success", "error", "not_found"]:
            log = create_book_log(
                titre="Test",
                auteur="Test",
                livre_status=status,
                auteur_status="none",
                details=[],
            )
            assert log["livre_status"] == status

        # Test valeur invalide
        with pytest.raises(ValueError, match="livre_status must be one of"):
            create_book_log(
                titre="Test",
                auteur="Test",
                livre_status="invalid",
                auteur_status="none",
                details=[],
            )

    def test_auteur_status_should_be_valid_enum(self):
        """Test TDD: auteur_status doit être success, error, not_found, ou none."""
        from back_office_lmelp.utils.migration_runner import create_book_log

        # Test valeurs valides
        for status in ["success", "error", "not_found", "none"]:
            log = create_book_log(
                titre="Test",
                auteur="Test",
                livre_status="success",
                auteur_status=status,
                details=[],
            )
            assert log["auteur_status"] == status

        # Test valeur invalide
        with pytest.raises(ValueError, match="auteur_status must be one of"):
            create_book_log(
                titre="Test",
                auteur="Test",
                livre_status="success",
                auteur_status="invalid",
                details=[],
            )

    def test_get_status_should_return_book_logs_list(self):
        """Test TDD: get_status() doit retourner une liste de book_logs.

        Problème business réel:
        - MigrationRunner accumule les logs de tous les livres traités
        - Frontend veut afficher tous les livres dans l'ordre de traitement
        - Chaque livre = 1 entrée structurée dans la liste

        Format attendu:
        {
            "is_running": true,
            "books_processed": 2,
            "book_logs": [
                { "titre": "Livre 1", ... },
                { "titre": "Livre 2", ... }
            ]
        }
        """
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        # Arrange - Créer un MigrationRunner
        runner = MigrationRunner()

        # Initialiser manuellement pour le test
        runner.book_logs = [
            {
                "titre": "La Cordillère des ondes",
                "auteur": "Patrice Delbourg",
                "livre_status": "error",
                "auteur_status": "error",
                "details": ["Test"],
            },
            {
                "titre": "Le Petit Prince",
                "auteur": "Antoine de Saint-Exupéry",
                "livre_status": "success",
                "auteur_status": "success",
                "details": ["Test"],
            },
        ]

        # Act
        status = runner.get_status()

        # Assert
        assert "book_logs" in status
        assert isinstance(status["book_logs"], list)
        assert len(status["book_logs"]) == 2

        # Premier livre (traité en premier = en haut)
        assert status["book_logs"][0]["titre"] == "La Cordillère des ondes"
        assert status["book_logs"][1]["titre"] == "Le Petit Prince"
