"""La migration vérifie que Babelio est joignable avant de démarrer (Issue #351).

Si l'IP est bannie, la première requête attendrait le timeout de connexion
(10 s) pour rien : un essai TCP d'une seconde suffit à arrêter tout de suite.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from back_office_lmelp.services.babelio_service import PRECHECK_PROBE_TIMEOUT_SEC


@pytest.fixture
def runner():
    from back_office_lmelp.utils.migration_runner import MigrationRunner

    MigrationRunner._instance = None
    return MigrationRunner()


@pytest.mark.asyncio
async def test_start_migration_stops_when_babelio_unreachable(runner):
    from back_office_lmelp.utils import migration_runner

    with (
        patch.object(
            migration_runner.babelio_service,
            "probe_reachability",
            new=AsyncMock(return_value="unreachable"),
        ) as probe,
        patch.object(migration_runner, "migrate_one_book_and_author") as migrate,
    ):
        result = await runner.start_migration()

    probe.assert_awaited_once_with(timeout_sec=PRECHECK_PROBE_TIMEOUT_SEC)
    assert result["status"] == "unreachable"
    assert "IP bannie" in result["message"]
    assert runner.is_running is False
    migrate.assert_not_called()


@pytest.mark.asyncio
async def test_start_migration_runs_when_babelio_reachable(runner, babelio_reachable):
    with patch.object(runner, "_run_python_migration", new=AsyncMock()) as run:
        result = await runner.start_migration()
        await asyncio.sleep(0)

    assert result["status"] == "started"
    babelio_reachable.assert_awaited_once()
    run.assert_awaited_once()
