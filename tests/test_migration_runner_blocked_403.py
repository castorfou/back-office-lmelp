"""Tests TDD pour l'arrêt anticipé du MigrationRunner sur blocked_403 (Issue #304).

Bug racine: une fois qu'un blocage 403 n'est plus loggé dans
babelio_problematic_cases (fix migrate_url_babelio.py), le livre bloqué
n'est plus exclu de la requête de sélection du prochain livre à traiter.
Résultat: si le cookie Babelio est expiré (circuit breaker ouvert), TOUTE
tentative suivante échoue aussi en blocked_403, et le runner retombe sur le
MÊME livre à chaque itération jusqu'à épuiser max_iterations (1000) — une
boucle infinie inutile plutôt qu'un arrêt propre.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestMigrationRunnerBlocked403:
    """Tests pour l'arrêt anticipé de la migration sur blocage 403 Babelio."""

    def setup_method(self):
        """Reset MigrationRunner singleton before each test."""
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        MigrationRunner._instance = None

    @pytest.mark.asyncio
    async def test_should_stop_migration_loop_on_first_blocked_403(self):
        """Test TDD: la boucle doit s'arrêter dès le premier blocked_403.

        Problème business réel:
        - Le cookie Babelio est expiré (circuit breaker ouvert côté serveur)
        - migrate_one_book_and_author() retourne status='blocked_403' pour
          CHAQUE appel (le même livre, puisqu'il n'est plus exclu)
        - Continuer la boucle est inutile: tous les appels échoueront pareil
          tant que le cookie n'est pas corrigé
        - Le runner doit détecter ce cas et arrêter la Phase 1 immédiatement
          plutôt que de consommer les 1000 itérations pour rien
        """
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        call_count = 0

        async def side_effect_migrate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "livre_updated": False,
                "auteur_updated": False,
                "titre": "Livre Bloqué",
                "auteur": "Auteur Bloqué",
                "status": "blocked_403",
            }

        real_sleep = asyncio.sleep

        async def fast_sleep(_seconds):
            await real_sleep(0)

        with (
            patch(
                "back_office_lmelp.utils.migration_runner.migrate_one_book_and_author"
            ) as mock_migrate,
            patch(
                "back_office_lmelp.utils.migration_runner.asyncio.sleep",
                new=fast_sleep,
            ),
        ):
            mock_migrate.side_effect = side_effect_migrate

            runner = MigrationRunner()
            await runner.start_migration()

            # Laisser la boucle tourner sans le vrai délai de 1s/itération
            for _ in range(50):
                await real_sleep(0.01)
                if not runner.is_running or call_count > 1:
                    break

            # La boucle doit s'être arrêtée après UN SEUL appel bloqué,
            # pas avoir continué à retenter indéfiniment sur le même livre
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_should_stop_migration_loop_on_first_error_status(self):
        """Test TDD (Issue #304): la boucle doit aussi s'arrêter dès le premier
        status='error' (pas seulement 'blocked_403').

        Problème business réel observé:
        - Un timeout réseau (Babelio ou connexion) fait échouer verify_book()
        - migrate_one_book_and_author() catche l'exception et retourne
          status='error' (volontairement PAS loggé dans
          babelio_problematic_cases — cf. commentaire ligne ~317, un timeout
          est transitoire, pas un problème de données)
        - Mais ce livre n'étant jamais exclu, MigrationRunner le retrouve
          identique à l'itération suivante et retente indéfiniment le même
          livre en timeout jusqu'à épuiser max_iterations — même symptôme
          que blocked_403, juste avec un statut différent en sortie.
        """
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        call_count = 0

        async def side_effect_migrate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "livre_updated": False,
                "auteur_updated": False,
                "titre": "Livre En Timeout",
                "auteur": "Auteur Inconnu",
                "status": "error",
            }

        real_sleep = asyncio.sleep

        async def fast_sleep(_seconds):
            await real_sleep(0)

        with (
            patch(
                "back_office_lmelp.utils.migration_runner.migrate_one_book_and_author"
            ) as mock_migrate,
            patch(
                "back_office_lmelp.utils.migration_runner.asyncio.sleep",
                new=fast_sleep,
            ),
        ):
            mock_migrate.side_effect = side_effect_migrate

            runner = MigrationRunner()
            await runner.start_migration()

            for _ in range(50):
                await real_sleep(0.01)
                if not runner.is_running or call_count > 1:
                    break

            # La boucle doit s'être arrêtée après UN SEUL appel en erreur,
            # pas avoir continué à retenter indéfiniment sur le même livre
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_should_use_shared_babelio_service_singleton_not_new_instance(self):
        """Test TDD (Issue #304): le runner doit réutiliser le singleton partagé
        babelio_service, pas créer une nouvelle instance BabelioService().

        Bug racine: MigrationRunner créait `BabelioService()` (une nouvelle
        instance à chaque migration), complètement isolée du singleton utilisé
        par app.py pour /api/babelio/status et /api/babelio/cookie. Résultat:
        - Le cookie enregistré via la page Contrôle Babelio (ou le panneau
          inline) n'était jamais vu par cette instance de migration.
        - Le circuit breaker ouvert pendant la migration (après un 403)
          n'était jamais visible sur la page Contrôle Babelio, qui affichait
          "Fermé" alors que la migration était bel et bien bloquée.
        """
        from back_office_lmelp.services.babelio_service import (
            babelio_service as shared_babelio_service,
        )
        from back_office_lmelp.utils.migration_runner import MigrationRunner

        with (
            patch(
                "back_office_lmelp.utils.migration_runner.migrate_one_book_and_author",
                new=AsyncMock(return_value=None),
            ) as mock_migrate,
            patch.object(
                shared_babelio_service, "close", new=AsyncMock()
            ) as mock_close,
        ):
            runner = MigrationRunner()
            await runner.start_migration()

            for _ in range(50):
                await asyncio.sleep(0.01)
                if not runner.is_running:
                    break

            # Le singleton partagé doit être celui passé à migrate_one_book_and_author
            mock_migrate.assert_called_once_with(
                babelio_service=shared_babelio_service, dry_run=False
            )

            # Le singleton partagé ne doit JAMAIS être fermé par la migration
            # (il continue à vivre pour le reste de l'application)
            mock_close.assert_not_called()
