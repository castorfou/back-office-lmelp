"""Tests TDD pour stop_migration - Issue #124.

Le bouton "Arrêter la liaison" ne fonctionne pas car stop_migration()
vérifie self.process qui est toujours None depuis la migration Python directe.
"""

import pytest


class TestMigrationRunnerStop:
    """Tests pour vérifier que stop_migration fonctionne."""

    @pytest.mark.asyncio
    async def test_should_stop_running_migration(self):
        """Test TDD: stop_migration doit arrêter une migration en cours.

        Problème production:
        - Migration en cours (is_running=True)
        - User clique "Arrêter"
        - Reçoit: "No migration is currently running"
        - Raison: self.process is None (plus de subprocess)

        Solution:
        - Ne plus vérifier self.process
        - Vérifier seulement is_running
        """
        # Arrange
        from src.back_office_lmelp.utils.migration_runner import MigrationRunner

        runner = MigrationRunner.get_instance()

        # Simuler une migration en cours (sans subprocess)
        runner.is_running = True
        runner.process = None  # Plus de subprocess en Python direct
        runner.logs = []

        # Act
        result = await runner.stop_migration()

        # Assert
        assert result["status"] == "stopped", (
            "Une migration en cours (is_running=True) doit pouvoir être arrêtée, "
            "même si process=None"
        )
        assert result["message"] == "Migration stopped successfully"
        assert runner.is_running is False, "is_running doit passer à False"
        assert any("stopped" in log.lower() for log in runner.logs), (
            "Un message d'arrêt doit être ajouté aux logs"
        )

    @pytest.mark.asyncio
    async def test_should_return_not_running_when_already_stopped(self):
        """Test TDD: stop_migration sur migration déjà arrêtée doit retourner not_running."""
        # Arrange
        from src.back_office_lmelp.utils.migration_runner import MigrationRunner

        runner = MigrationRunner.get_instance()
        runner.is_running = False
        runner.process = None

        # Act
        result = await runner.stop_migration()

        # Assert
        assert result["status"] == "not_running"
        assert "No migration" in result["message"]
