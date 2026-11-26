"""Un auteur créé à la validation reprend une URL Babelio déjà prise (Issue #406).

L'auteur est créé par son nom (`create_author_if_not_exists`), son URL Babelio
n'est connue qu'ensuite (`_enrich_livre_from_babelio_page`). Cas réel :
« Patrick J. Rogers » (nom erroné, 2025) porte déjà l'URL de Patrick Roegiers ;
la validation de « L'autre Simenon » crée « Patrick Roegiers » avec la même URL.
Au lieu de laisser un doublon, l'enrichissement fusionne les deux auteurs avec
la fusion existante (le plus ancien reste, nom officiel Babelio).

Les requêtes tournent sur mongomock ; Babelio est mocké.
"""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import mongomock
import pytest
from bson import ObjectId

from back_office_lmelp import app as app_module


URL = "https://www.babelio.com/auteur/Patrick-Roegiers/6213"


def _app_babelio_service() -> Any:
    """Le singleton Babelio tel que l'utilise app.py.

    test_babelio_service.py recharge le module babelio_service : l'importer
    ici pourrait donner un autre objet que celui qu'appelle le code testé.
    """
    return vars(app_module)["babelio_service"]


BOOK_URL = "https://www.babelio.com/livres/Roegiers-Lautre-Simenon/722392"


@pytest.fixture
def db(monkeypatch):
    database = mongomock.MongoClient().masque_et_la_plume
    service = app_module.mongodb_service
    monkeypatch.setattr(service, "db", database)
    monkeypatch.setattr(service, "auteurs_collection", database.auteurs)
    monkeypatch.setattr(service, "livres_collection", database.livres)
    monkeypatch.setattr(service, "episodes_collection", database.episodes)
    return database


def _seed(db: Any, *, existing_url: str | None) -> tuple[ObjectId, ObjectId, ObjectId]:
    """Auteur ancien (nom erroné) + auteur tout juste créé avec son livre."""
    old_id, old_book = ObjectId(), ObjectId()
    new_id, new_book = ObjectId(), ObjectId()
    db.auteurs.insert_many(
        [
            {
                "_id": old_id,
                "nom": "Patrick J. Rogers",
                "url_babelio": existing_url,
                "livres": [str(old_book)],
                "created_at": datetime(2025, 11, 27, 21, 9, 14),
            },
            {
                "_id": new_id,
                "nom": "Patrick Roegiers",
                "livres": [str(new_book)],
                "created_at": datetime(2026, 11, 25, 6, 58, 25),
            },
        ]
    )
    db.livres.insert_many(
        [
            {"_id": old_book, "titre": "Nouvelle vague", "auteur_id": old_id},
            {
                "_id": new_book,
                "titre": "L'autre Simenon",
                "auteur_id": new_id,
                "url_babelio": BOOK_URL,
                "url_cover": "https://example.org/cover.jpg",
            },
        ]
    )
    return old_id, new_id, new_book


async def _enrich(
    new_id: ObjectId, new_book: ObjectId, official_name: str | None = "Patrick Roegiers"
) -> None:
    babelio = _app_babelio_service()
    with (
        patch.object(
            babelio, "fetch_author_url_from_page", AsyncMock(return_value=URL)
        ),
        patch.object(
            babelio, "fetch_author_name_from_url", AsyncMock(return_value=official_name)
        ),
    ):
        await app_module._enrich_livre_from_babelio_page(
            str(new_book), str(new_id), BOOK_URL, "L'autre Simenon"
        )


@pytest.mark.asyncio
async def test_new_author_with_taken_url_is_merged_into_existing_one(db):
    old_id, new_id, new_book = _seed(db, existing_url=URL)

    await _enrich(new_id, new_book)

    auteurs = list(db.auteurs.find())
    assert [a["_id"] for a in auteurs] == [old_id]
    assert auteurs[0]["nom"] == "Patrick Roegiers"
    assert auteurs[0]["url_babelio"] == URL
    assert set(auteurs[0]["livres"]) == {str(b["_id"]) for b in db.livres.find()}
    assert db.livres.find_one({"_id": new_book})["auteur_id"] == old_id


@pytest.mark.asyncio
async def test_url_taken_with_another_case_is_still_merged(db):
    old_id, new_id, new_book = _seed(db, existing_url=URL.lower())

    await _enrich(new_id, new_book)

    assert [a["_id"] for a in db.auteurs.find()] == [old_id]


@pytest.mark.asyncio
async def test_free_url_is_simply_set_on_the_new_author(db):
    old_id, new_id, new_book = _seed(db, existing_url=None)

    await _enrich(new_id, new_book)

    assert db.auteurs.count_documents({}) == 2
    assert db.auteurs.find_one({"_id": new_id})["url_babelio"] == URL
    assert db.livres.find_one({"_id": new_book})["auteur_id"] == new_id


@pytest.mark.asyncio
async def test_merge_keeps_primary_name_when_babelio_gives_no_name(db):
    old_id, new_id, new_book = _seed(db, existing_url=URL)

    await _enrich(new_id, new_book, official_name=None)

    auteurs = list(db.auteurs.find())
    assert [a["_id"] for a in auteurs] == [old_id]
    assert auteurs[0]["nom"] == "Patrick J. Rogers"


@pytest.mark.asyncio
async def test_apply_refresh_with_taken_url_merges_authors(db):
    """Même doublon par le rafraîchissement manuel d'un livre."""
    from back_office_lmelp.app import ApplyRefreshRequest, apply_livre_refresh

    old_id, new_id, new_book = _seed(db, existing_url=URL)

    with patch.object(
        _app_babelio_service(),
        "fetch_author_name_from_url",
        AsyncMock(return_value="Patrick Roegiers"),
    ):
        await apply_livre_refresh(
            str(new_book), ApplyRefreshRequest(auteur_url_babelio=URL)
        )

    assert [a["_id"] for a in db.auteurs.find()] == [old_id]
    assert db.livres.find_one({"_id": new_book})["auteur_id"] == old_id
