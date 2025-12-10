"""Tests TDD pour MigrationRunner avec appels Python directs (Issue #124 - Phase 12).

Ce module teste la nouvelle implémentation de MigrationRunner
qui appelle directement migrate_one_book_and_author() au lieu du script bash.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestMigrationRunnerPythonDirect:
    """Tests pour MigrationRunner avec appels Python directs."""

    def setup_method(self):
        """Reset MigrationRunner singleton before each test."""
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        # Reset singleton instance
        MigrationRunner._instance = None

    @pytest.mark.asyncio
    async def test_start_migration_should_call_python_function_not_bash(self):
        """Test TDD: start_migration() doit appeler migrate_one_book_and_author().

        Problème business réel:
        - Avant: MigrationRunner lançait un script bash via subprocess
        - Après: Il doit appeler directement la fonction Python
        - Raison: Contrôle total sur les logs structurés, pas de parsing nécessaire

        Scénario:
        1. Lancer start_migration()
        2. Vérifier qu'aucun subprocess n'est créé
        3. Vérifier que migrate_one_book_and_author() est appelée
        4. Vérifier que book_logs est peuplé avec les résultats structurés
        """
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        # Arrange - Mock migrate_one_book_and_author
        with patch(
            "back_office_lmelp.utils.migration_runner.migrate_one_book_and_author"
        ) as mock_migrate:
            # First call: return success, second call: return None (no more books)
            async def side_effect_migrate(*args, **kwargs):
                if not hasattr(side_effect_migrate, "called"):
                    side_effect_migrate.called = True
                    return {
                        "livre_updated": True,
                        "auteur_updated": True,
                        "titre": "Le Petit Prince",
                        "auteur": "Antoine de Saint-Exupéry",
                        "status": "success",
                    }
                else:
                    return None  # No more books

            mock_migrate.side_effect = side_effect_migrate

            # Mock BabelioService
            with patch(
                "back_office_lmelp.utils.migration_runner.BabelioService"
            ) as mock_babelio_cls:
                mock_babelio = AsyncMock()
                mock_babelio.close = AsyncMock()
                mock_babelio_cls.return_value = mock_babelio

                # Act - Lancer la migration
                runner = MigrationRunner()
                result = await runner.start_migration()

                # Assert - Vérifier que le statut est started
                assert result["status"] == "started"

                # Vérifier qu'aucun subprocess n'est créé
                assert runner.process is None

                # Attendre un peu pour que la tâche background s'exécute
                await asyncio.sleep(0.5)

                # Vérifier que migrate_one_book_and_author a été appelée
                assert mock_migrate.called

    @pytest.mark.asyncio
    async def test_migration_should_populate_book_logs_directly(self):
        """Test TDD: La migration doit peupler book_logs directement.

        Problème business réel:
        - migrate_one_book_and_author() retourne déjà les données structurées
        - On doit les transformer en book_log et les ajouter à book_logs

        Scénario:
        1. migrate_one_book_and_author() retourne un résultat
        2. MigrationRunner transforme ce résultat en book_log
        3. book_logs contient une entrée structurée
        """
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        # Arrange - Mock avec un livre migré
        with patch(
            "back_office_lmelp.utils.migration_runner.migrate_one_book_and_author"
        ) as mock_migrate:
            # First call: return success, second call: return None
            async def side_effect_migrate(*args, **kwargs):
                if not hasattr(side_effect_migrate, "called"):
                    side_effect_migrate.called = True
                    return {
                        "livre_updated": True,
                        "auteur_updated": True,
                        "titre": "Le Petit Prince",
                        "auteur": "Antoine de Saint-Exupéry",
                        "status": "success",
                    }
                else:
                    return None

            mock_migrate.side_effect = side_effect_migrate

            with patch(
                "back_office_lmelp.utils.migration_runner.BabelioService"
            ) as mock_babelio_cls:
                mock_babelio = AsyncMock()
                mock_babelio.close = AsyncMock()
                mock_babelio_cls.return_value = mock_babelio

                # Act
                runner = MigrationRunner()
                await runner.start_migration()

                # Attendre que la migration traite au moins 1 livre
                await asyncio.sleep(0.5)

                # Assert - Vérifier que book_logs est peuplé
                status = runner.get_status()
                assert len(status["book_logs"]) >= 1

                # Vérifier la structure du premier book_log
                first_log = status["book_logs"][0]
                assert first_log["titre"] == "Le Petit Prince"
                assert first_log["auteur"] == "Antoine de Saint-Exupéry"
                assert first_log["livre_status"] == "success"
                assert first_log["auteur_status"] == "success"

    @pytest.mark.asyncio
    async def test_migration_should_stop_when_no_more_books(self):
        """Test TDD: La migration doit s'arrêter quand il n'y a plus de livres.

        Scénario:
        1. migrate_one_book_and_author() retourne None (plus de livres)
        2. MigrationRunner arrête la boucle
        3. is_running passe à False
        """
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        # Arrange - Mock qui retourne None (pas de livres)
        with (
            patch(
                "back_office_lmelp.utils.migration_runner.migrate_one_book_and_author"
            ) as mock_migrate,
            patch(
                "back_office_lmelp.utils.migration_runner.get_all_books_to_complete"
            ) as mock_get_all_books,
        ):

            async def side_effect_migrate(*args, **kwargs):
                return None

            mock_migrate.side_effect = side_effect_migrate

            # Mock get_all_books_to_complete to return empty list (no books to complete)
            async def side_effect_get_all_books():
                return []

            mock_get_all_books.side_effect = side_effect_get_all_books

            with patch(
                "back_office_lmelp.utils.migration_runner.BabelioService"
            ) as mock_babelio_cls:
                mock_babelio = AsyncMock()
                mock_babelio.close = AsyncMock()
                mock_babelio_cls.return_value = mock_babelio

                # Act
                runner = MigrationRunner()
                await runner.start_migration()

                # Attendre que la migration se termine
                await asyncio.sleep(1.0)

                # Assert - La migration doit être terminée
                assert runner.is_running is False

    @pytest.mark.asyncio
    async def test_migration_should_map_error_status_correctly(self):
        """Test TDD: Les erreurs doivent être mappées correctement.

        Scénario:
        1. migrate_one_book_and_author() retourne livre_updated=False, auteur_updated=False
        2. book_log doit avoir livre_status="error", auteur_status="error"
        """
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        # Arrange - Mock avec échec
        with patch(
            "back_office_lmelp.utils.migration_runner.migrate_one_book_and_author"
        ) as mock_migrate:

            async def side_effect_migrate(*args, **kwargs):
                if not hasattr(side_effect_migrate, "called"):
                    side_effect_migrate.called = True
                    return {
                        "livre_updated": False,
                        "auteur_updated": False,
                        "titre": "Livre Introuvable",
                        "auteur": "Auteur Inconnu",
                        "status": "not_found",
                    }
                else:
                    return None

            mock_migrate.side_effect = side_effect_migrate

            with patch(
                "back_office_lmelp.utils.migration_runner.BabelioService"
            ) as mock_babelio_cls:
                mock_babelio = AsyncMock()
                mock_babelio.close = AsyncMock()
                mock_babelio_cls.return_value = mock_babelio

                # Act
                runner = MigrationRunner()
                await runner.start_migration()
                await asyncio.sleep(1.0)

                # Assert
                status = runner.get_status()
                assert len(status["book_logs"]) > 0, (
                    "book_logs should contain at least one entry"
                )
                first_log = status["book_logs"][0]
                assert first_log["livre_status"] in ["error", "not_found"]
                assert first_log["auteur_status"] in ["error", "none"]
