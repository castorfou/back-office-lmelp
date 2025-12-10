"""Tests TDD pour la Phase 2 du MigrationRunner (Issue #124).

Ce module teste que la Phase 2 (complétion des auteurs) s'exécute
même quand la Phase 1 (migration des livres) se termine car il n'y a
plus de livres en attente (pending_count = 0).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMigrationRunnerPhase2:
    """Tests pour l'exécution de la Phase 2 du MigrationRunner."""

    @pytest.mark.asyncio
    async def test_should_run_phase2_when_phase1_completes_with_no_pending_books(self):
        """Test TDD: Phase 2 doit s'exécuter même si Phase 1 termine sans livres.

        Problème business réel (Issue #124):
        - pending_count = 0 (plus de livres à migrer)
        - authors_without_url_babelio = 15 (auteurs à compléter)
        - L'utilisateur clique sur "Lancer liaison automatique"
        - La Phase 1 se termine immédiatement (pas de livres)
        - La Phase 2 doit quand même s'exécuter pour compléter les 15 auteurs
        - Mais actuellement, is_running = False empêche Phase 2 de démarrer

        Scénario:
        1. migrate_one_book_and_author retourne None (pas de livres)
        2. Phase 1 se termine
        3. Phase 2 doit s'exécuter quand même
        4. complete_missing_authors doit être appelé
        5. Au moins un auteur doit être complété
        """
        # Arrange
        from src.back_office_lmelp.utils.migration_runner import MigrationRunner

        runner = MigrationRunner.get_instance()
        # Réinitialiser l'état manuellement
        runner.is_running = False
        runner.logs = []
        runner.book_logs = []
        runner.books_processed = 0

        # Mock migrate_one_book_and_author pour retourner None (pas de livres)
        mock_migrate = AsyncMock(return_value=None)

        # Mock get_all_books_to_complete pour retourner une liste avec un livre
        from bson import ObjectId

        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_get_all_books = AsyncMock(
            return_value=[
                {
                    "livre_id": livre_id,
                    "titre": "1984",
                    "auteur": "George Orwell",
                    "auteur_id": auteur_id,
                    "url_babelio": "https://www.babelio.com/livres/Orwell-1984/1234",
                }
            ]
        )

        # Mock process_one_book_author pour simuler la complétion d'un auteur
        mock_process_one = AsyncMock(
            return_value={
                "auteur_updated": True,
                "titre": "1984",
                "auteur": "George Orwell",
                "status": "success",
            }
        )

        # Mock BabelioService
        mock_babelio_service = MagicMock()
        mock_babelio_service.close = AsyncMock()

        with (
            patch(
                "src.back_office_lmelp.utils.migration_runner.migrate_one_book_and_author",
                mock_migrate,
            ),
            patch(
                "src.back_office_lmelp.utils.migration_runner.get_all_authors_to_complete",
                mock_get_all_books,
            ),
            patch(
                "src.back_office_lmelp.utils.migration_runner.process_one_author",
                mock_process_one,
            ),
            patch(
                "src.back_office_lmelp.utils.migration_runner.BabelioService",
                return_value=mock_babelio_service,
            ),
        ):
            # Act
            await runner.start_migration()

            # Attendre que la migration async se termine
            import asyncio

            await asyncio.sleep(3)  # Laisser le temps à la Phase 2 de s'exécuter

            # Assert
            # Vérifier que migrate_one_book_and_author a été appelé (Phase 1)
            assert mock_migrate.call_count >= 1, (
                "Phase 1 doit être appelée au moins une fois"
            )

            # Vérifier que get_all_authors_to_complete a été appelé (Phase 2)
            assert mock_get_all_books.call_count >= 1, (
                "Phase 2 doit charger la liste des auteurs à traiter"
            )

            # Vérifier que process_one_author a été appelé (Phase 2)
            assert mock_process_one.call_count >= 1, (
                "Phase 2 doit traiter au moins un auteur"
            )

            # Vérifier que le runner a traité l'auteur
            assert runner.books_processed >= 1, (
                "Au moins un auteur doit être traité en Phase 2"
            )

            # Vérifier que le runner s'est arrêté proprement
            assert runner.is_running is False, "Runner doit être arrêté après Phase 2"
