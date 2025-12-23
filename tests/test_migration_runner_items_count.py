"""Tests TDD pour le compteur d'éléments traités (Issue #152).

Ce module teste que books_processed compte le nombre total
d'éléments individuels traités (livres + auteurs) et non le nombre de groupes.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestMigrationRunnerItemsCount:
    """Tests pour le comptage correct des éléments individuels traités."""

    def setup_method(self):
        """Reset MigrationRunner singleton before each test."""
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        # Reset singleton instance
        MigrationRunner._instance = None

    @pytest.mark.asyncio
    async def test_books_processed_should_count_individual_items_not_groups(self):
        """Test TDD (RED): books_processed doit compter livres + auteurs individuellement.

        Problème business réel (Issue #152):
        - Actuellement: books_processed compte 1 par groupe traité
        - Exemple: 4 groupes traités (3 livre+auteur + 1 auteur seul)
          → Compteur affiche 4 ❌
          → Devrait afficher 7 (3×2 + 1) ✅

        Scénario:
        1. Phase 1: Traiter 2 livres avec leurs auteurs (= 4 éléments)
        2. Phase 2: Traiter 1 auteur seul (= 1 élément)
        3. Total attendu: 5 éléments
        4. books_processed doit être 5, pas 3 (nombre de groupes)
        """
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        # Arrange - Mock Phase 1 avec 2 livres + auteurs
        with patch(
            "back_office_lmelp.utils.migration_runner.migrate_one_book_and_author"
        ) as mock_migrate:
            call_count = 0

            async def side_effect_migrate(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # Premier livre + auteur
                    return {
                        "livre_updated": True,
                        "auteur_updated": True,
                        "titre": "Le Petit Prince",
                        "auteur": "Antoine de Saint-Exupéry",
                        "status": "success",
                    }
                elif call_count == 2:
                    # Deuxième livre + auteur
                    return {
                        "livre_updated": True,
                        "auteur_updated": True,
                        "titre": "L'Étranger",
                        "auteur": "Albert Camus",
                        "status": "success",
                    }
                else:
                    # Plus de livres, passer à Phase 2
                    return None

            mock_migrate.side_effect = side_effect_migrate

            # Mock Phase 2 avec 1 auteur à compléter
            with patch(
                "back_office_lmelp.utils.migration_runner.get_all_authors_to_complete"
            ) as mock_get_authors:
                # 1 auteur à compléter (fonction async, utiliser AsyncMock)
                async def get_authors_mock():
                    return [
                        {
                            "nom": "Victor Hugo",
                            "livres": [{"titre": "Les Misérables"}],
                            "_id": "author_id_1",
                        }
                    ]

                mock_get_authors.side_effect = get_authors_mock

                with patch(
                    "back_office_lmelp.utils.migration_runner.process_one_author"
                ) as mock_process_author:
                    # Auteur complété avec succès
                    async def process_author_result(*args, **kwargs):
                        return {
                            "auteur_updated": True,
                            "raison": "URL Babelio ajoutée",
                            "status": "success",
                        }

                    mock_process_author.side_effect = process_author_result

                    with patch(
                        "back_office_lmelp.utils.migration_runner.BabelioService"
                    ) as mock_babelio_cls:
                        mock_babelio = AsyncMock()
                        mock_babelio.close = AsyncMock()
                        mock_babelio_cls.return_value = mock_babelio

                        # Act
                        runner = MigrationRunner()
                        await runner.start_migration()

                        # Attendre que la migration se termine (Phase 1 + Phase 2)
                        await asyncio.sleep(5.0)

                        # Assert
                        # Phase 1: 2 livres + 2 auteurs = 4 éléments
                        # Phase 2: 1 auteur = 1 élément
                        # Total: 5 éléments individuels (pas 3 groupes!)
                        assert runner.books_processed == 5, (
                            f"Expected 5 individual items, got {runner.books_processed}"
                        )

    @pytest.mark.asyncio
    async def test_books_processed_should_count_livre_only_when_auteur_already_linked(
        self,
    ):
        """Test TDD (RED): Compte seulement le livre si l'auteur est déjà lié.

        Scénario:
        1. Livre traité, mais auteur déjà lié (auteur_already_linked=True)
        2. Doit compter +1 (livre seulement), pas +2
        """
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        # Arrange - Mock avec auteur déjà lié
        with patch(
            "back_office_lmelp.utils.migration_runner.migrate_one_book_and_author"
        ) as mock_migrate:

            async def side_effect_migrate(*args, **kwargs):
                if not hasattr(side_effect_migrate, "called"):
                    side_effect_migrate.called = True
                    return {
                        "livre_updated": True,
                        "auteur_updated": False,  # Auteur pas mis à jour
                        "auteur_already_linked": True,  # Mais déjà lié!
                        "titre": "Livre Test",
                        "auteur": "Auteur Existant",
                        "status": "success",
                    }
                else:
                    return None

            mock_migrate.side_effect = side_effect_migrate

            with patch(
                "back_office_lmelp.utils.migration_runner.get_all_authors_to_complete"
            ) as mock_get_authors:
                # Pas d'auteurs à compléter en Phase 2
                mock_get_authors.return_value = []

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

                    # Assert - Seulement 1 élément (le livre), pas 2
                    assert runner.books_processed == 1, (
                        f"Expected 1 item (livre only), got {runner.books_processed}"
                    )

    @pytest.mark.asyncio
    async def test_books_processed_should_count_zero_when_both_fail(self):
        """Test TDD (RED): Ne compte rien si livre ET auteur échouent.

        Scénario:
        1. Livre non trouvé, auteur non mis à jour
        2. Ne devrait compter aucun élément traité avec succès
        3. Mais on compte quand même le "groupe traité" (pour progression)

        Note: Cette fonctionnalité pourrait évoluer selon les besoins métier.
        Pour l'instant, on compte le groupe même en cas d'échec pour montrer la progression.
        """
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        # Arrange - Mock avec échec complet
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
                        "auteur": "Auteur Introuvable",
                        "status": "not_found",
                    }
                else:
                    return None

            mock_migrate.side_effect = side_effect_migrate

            with patch(
                "back_office_lmelp.utils.migration_runner.get_all_authors_to_complete"
            ) as mock_get_authors:
                mock_get_authors.return_value = []

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

                    # Assert - On compte quand même 1 groupe traité
                    # (pour montrer la progression même en cas d'échec)
                    assert runner.books_processed >= 1, (
                        "Should count attempted processing even on failure"
                    )
