"""« En attente de liaison » ne doit jamais être négatif (Issue #341).

Problème business réel (13/11/2026) : une liaison lancée avant le repli
« titre + auteur » a classé L'Héritage, Je et Le génie en cas problématiques
(not_found). La validation de l'épisode les a ensuite liés à Babelio (L'Héritage
et Je), sans retirer leur cas problématique. Le statut les comptait à la fois
« liés » et « à traiter manuellement » : « En attente de liaison » = -2.

get_problematic_cases() ignore déjà les livres résolus : le compteur doit faire
de même. Données : documents réels de babelio_problematic_cases.
"""

from typing import Any
from unittest.mock import MagicMock

from bson import ObjectId

from back_office_lmelp.services.babelio_migration_service import (
    BabelioMigrationService,
)


HERITAGE_ID = "6af62a007de3c738c888a90c"
JE_ID = "6af62a467de3c738c888a913"
GENIE_ID = "6af62a5e7de3c738c888a916"

PROBLEMATIC_LIVRE_IDS = [HERITAGE_ID, JE_ID, GENIE_ID]  # livre_id : String


def _service() -> tuple[BabelioMigrationService, MagicMock, MagicMock]:
    livres = MagicMock()
    auteurs = MagicMock()
    problematic = MagicMock()
    collections = {
        "livres": livres,
        "auteurs": auteurs,
        "babelio_problematic_cases": problematic,
    }
    db = MagicMock()
    db.__getitem__.side_effect = collections.__getitem__
    mongodb_service = MagicMock()
    mongodb_service.db = db

    total, migrated, not_found = 1735, 1716, 18

    def count_livres(query: dict[str, Any]) -> int:
        if query == {}:
            return total
        if query == {"url_babelio": {"$exists": True, "$ne": None}}:
            return migrated
        if query == {"babelio_not_found": True}:
            return not_found
        return 0

    livres.count_documents.side_effect = count_livres
    livres.find_one.return_value = None
    auteurs.count_documents.return_value = 0
    problematic.count_documents.side_effect = lambda q: (
        3 if q == {"type": "livre"} else 0
    )
    problematic.distinct.return_value = PROBLEMATIC_LIVRE_IDS

    def find_livres(query: dict[str, Any], *args: Any) -> list[dict[str, Any]]:
        # L'Héritage et Je ont été liés par la validation de l'épisode
        assert all(isinstance(i, ObjectId) for i in query["_id"]["$in"])
        return [{"_id": ObjectId(HERITAGE_ID)}, {"_id": ObjectId(JE_ID)}]

    livres.find.side_effect = find_livres

    return BabelioMigrationService(mongodb_service, MagicMock()), livres, problematic


def test_linked_books_are_not_counted_as_problematic() -> None:
    service, _, _ = _service()

    status = service.get_migration_status()

    assert status["problematic_count"] == 1  # Le génie seul
    assert status["pending_count"] == 0  # 1735 - 1716 - 18 - 1
