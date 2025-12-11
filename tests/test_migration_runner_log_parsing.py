"""Tests TDD pour le parsing des logs bash en logs structurés (Issue #124 - Phase 11.2).

Ce module teste la conversion des logs texte du script bash
vers la structure de données pour le frontend.
"""


class TestMigrationRunnerLogParsing:
    """Tests pour le parsing des logs de migration."""

    def test_parse_book_migration_should_extract_title_and_author(self):
        """Test TDD: Parser les logs d'une migration de livre.

        Problème business réel:
        - Le script bash génère des logs texte non structurés
        - Frontend a besoin de titre, auteur, statuts séparés
        - Il faut parser la sortie pour extraire ces informations

        Exemple de sortie bash pour un livre:
        ```
        📚 Livre: La Cordillère des ondes (Patrice Delbourg)
        🔍 Recherche Babelio...
        ⚠️  Titre ne correspond pas
        ❌ Livre non mis à jour
        ```
        """
        from back_office_lmelp.utils.migration_runner import parse_book_migration_output

        # Arrange - Logs d'une migration qui a échoué
        log_lines = [
            "📚 Livre: La Cordillère des ondes (Patrice Delbourg)",
            "🔍 Recherche Babelio pour 'La Cordillère des ondes'",
            "🔗 URL trouvée: https://www.babelio.com/livres/...",
            "⚠️  Titre ne correspond pas: attendu 'La Cordillère des ondes', trouvé 'Contes...'",
            "❌ Livre non mis à jour",
            "❌ Auteur non migré",
        ]

        # Act
        book_log = parse_book_migration_output(log_lines)

        # Assert
        assert book_log is not None
        assert book_log["titre"] == "La Cordillère des ondes"
        assert book_log["auteur"] == "Patrice Delbourg"
        assert book_log["livre_status"] == "error"
        assert book_log["auteur_status"] == "error"
        assert len(book_log["details"]) == 6

    def test_parse_book_migration_success_should_set_success_status(self):
        """Test TDD: Parser une migration réussie doit retourner status=success."""
        from back_office_lmelp.utils.migration_runner import parse_book_migration_output

        # Arrange - Logs d'une migration réussie
        log_lines = [
            "📚 Livre: Le Petit Prince (Antoine de Saint-Exupéry)",
            "🔍 Recherche Babelio...",
            "✅ Livre mis à jour avec URL Babelio",
            "✅ Auteur mis à jour avec URL Babelio",
        ]

        # Act
        book_log = parse_book_migration_output(log_lines)

        # Assert
        assert book_log["titre"] == "Le Petit Prince"
        assert book_log["auteur"] == "Antoine de Saint-Exupéry"
        assert book_log["livre_status"] == "success"
        assert book_log["auteur_status"] == "success"

    def test_parse_book_migration_not_found_should_set_not_found_status(self):
        """Test TDD: Parser un livre not_found doit retourner status=not_found."""
        from back_office_lmelp.utils.migration_runner import parse_book_migration_output

        # Arrange - Logs d'un livre non trouvé sur Babelio
        log_lines = [
            "📚 Livre: Livre Introuvable (Auteur Inconnu)",
            "🔍 Recherche Babelio...",
            "❌ Livre non trouvé sur Babelio",
            "⚪ Auteur non traité (livre not found)",
        ]

        # Act
        book_log = parse_book_migration_output(log_lines)

        # Assert
        assert book_log["livre_status"] == "not_found"
        assert book_log["auteur_status"] == "none"

    def test_parse_book_migration_with_no_author_should_set_auteur_status_none(self):
        """Test TDD: Un livre sans auteur doit avoir auteur_status=none."""
        from back_office_lmelp.utils.migration_runner import parse_book_migration_output

        # Arrange
        log_lines = [
            "📚 Livre: Anthologie Collective (Collectif)",
            "🔍 Recherche Babelio...",
            "✅ Livre mis à jour avec URL Babelio",
            "⚪ Pas d'auteur à migrer",
        ]

        # Act
        book_log = parse_book_migration_output(log_lines)

        # Assert
        assert book_log["livre_status"] == "success"
        assert book_log["auteur_status"] == "none"

    def test_parse_empty_output_should_return_none(self):
        """Test TDD: Une sortie vide doit retourner None."""
        from back_office_lmelp.utils.migration_runner import parse_book_migration_output

        # Act
        result = parse_book_migration_output([])

        # Assert
        assert result is None

    def test_parse_output_without_book_header_should_return_none(self):
        """Test TDD: Des logs sans header '📚 Livre:' doivent retourner None."""
        from back_office_lmelp.utils.migration_runner import parse_book_migration_output

        # Arrange - Logs incomplets
        log_lines = [
            "🔍 Recherche Babelio...",
            "✅ Quelque chose",
        ]

        # Act
        result = parse_book_migration_output(log_lines)

        # Assert
        assert result is None
