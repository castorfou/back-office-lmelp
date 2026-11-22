"""Compteur « Livrées par pap » dans le payload caché du dashboard (Issue #376).

Le compteur fait partie de GET /api/dashboard/stats (cache 5 min) : le test
des fichiers audio et les logs des fichiers absents ont lieu au plus une fois
par cache, ou à chaque « Actualiser ».
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


client = TestClient(app)


@pytest.fixture
def autres_sources_du_dashboard():
    """Neutralise les autres sources du payload pour isoler le compteur pap."""
    with (
        patch(
            "back_office_lmelp.app.get_critiques_manquants_count",
            new=AsyncMock(return_value=_json_response({"count": 0})),
        ),
        patch("back_office_lmelp.app.get_statistics", new=AsyncMock(return_value={})),
        patch(
            "back_office_lmelp.app.get_livres_auteurs_statistics",
            new=AsyncMock(return_value={}),
        ),
        patch("back_office_lmelp.app.duplicate_books_service") as mock_dup,
        patch("back_office_lmelp.app.orphaned_avis_service") as mock_orphaned,
        patch("back_office_lmelp.app.dashboard_stats_cache_service") as mock_cache,
    ):
        mock_dup.get_duplicate_statistics = AsyncMock(
            return_value={"total_duplicates": 0}
        )
        mock_dup.get_duplicate_authors_statistics = AsyncMock(
            return_value={"total_duplicates": 0}
        )
        mock_orphaned.get_orphaned_statistics = AsyncMock(
            return_value={"orphaned_count": 0}
        )
        mock_cache.get_cached.return_value = None
        yield mock_cache


def _json_response(content):
    from fastapi.responses import JSONResponse

    return JSONResponse(content=content)


def test_le_payload_dashboard_contient_le_nombre_d_emissions_livrees(
    autres_sources_du_dashboard,
):
    with patch("back_office_lmelp.app.count_pap_livrees", return_value=12):
        response = client.get("/api/dashboard/stats")

    assert response.status_code == 200
    assert response.json()["pap_livrees_count"] == 12
    cached_payload = autres_sources_du_dashboard.set_cache.call_args.args[0]
    assert cached_payload["pap_livrees_count"] == 12


def test_un_echec_du_comptage_pap_ne_casse_pas_les_autres_tuiles(
    autres_sources_du_dashboard,
):
    with patch(
        "back_office_lmelp.app.count_pap_livrees",
        side_effect=Exception("Connexion MongoDB non établie"),
    ):
        response = client.get("/api/dashboard/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["pap_livrees_count"] is None
    assert data["orphaned_avis_count"] == 0
