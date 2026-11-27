"""Un livre déjà en base n'est pas recréé sous un titre plus complet (Issue #411).

Cas réel (émission du 28/06/2015) : « Quand vous viendrez me voir aux antipodes »
est en base ; la revalidation reçoit de Babelio le titre complet « … : Lettres à
Pierre Boncenne », avec la même URL Babelio. La recherche par titre normalisé ne
le reconnaissait pas et créait une seconde fiche. Même URL Babelio = même livre.

Les requêtes tournent sur mongomock (vrais filtres, vrais types).
"""

from typing import Any

import mongomock
import pytest
from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


URL = (
    "https://www.babelio.com/livres/"
    "Leys-Quand-vous-viendrez-me-voir-aux-Antipodes--Lettre/720681"
)
# episodes : identifiants d'épisodes en String, comme en base
E1 = "6b061fd73a756aaf913fe936"  # pragma: allowlist secret
E2 = "678ccfada414f229887782a7"  # pragma: allowlist secret


@pytest.fixture
def db() -> Any:
    return mongomock.MongoClient().masque_et_la_plume


@pytest.fixture
def service(db: Any) -> MongoDBService:
    svc = MongoDBService()
    svc.db = db
    svc.livres_collection = db.livres
    svc.auteurs_collection = db.auteurs
    svc.editeurs_collection = db.editeurs
    return svc


def _seed(db: Any, *, url: str | None = URL) -> tuple[ObjectId, ObjectId]:
    """Simon Leys et son livre au titre court, déjà validé pour l'épisode E1."""
    auteur_id = db.auteurs.insert_one({"nom": "Simon Leys", "livres": []}).inserted_id
    livre_id = db.livres.insert_one(
        {
            "titre": "Quand vous viendrez me voir aux antipodes",
            "auteur_id": auteur_id,
            "url_babelio": url,
            "episodes": [E1],
            "avis_critiques": [],
        }
    ).inserted_id
    db.auteurs.update_one({"_id": auteur_id}, {"$set": {"livres": [str(livre_id)]}})
    return auteur_id, livre_id


def _book_data(auteur_id: ObjectId, url: str | None = URL) -> dict[str, Any]:
    data: dict[str, Any] = {
        "titre": "Quand vous viendrez me voir aux Antipodes : Lettres à Pierre Boncenne",
        "auteur_id": auteur_id,
        "editeur": "",
        "episodes": [E2],
        "avis_critiques": [],
    }
    if url is not None:
        data["url_babelio"] = url
    return data


def test_same_babelio_url_reuses_existing_book_despite_longer_title(db, service):
    auteur_id, livre_id = _seed(db)

    book_id = service.create_book_if_not_exists(_book_data(auteur_id))

    assert book_id == livre_id
    assert db.livres.count_documents({}) == 1
    livre = db.livres.find_one({"_id": livre_id})
    assert livre["episodes"] == [E1, E2]
    assert livre["titre"] == "Quand vous viendrez me voir aux antipodes"


def test_babelio_url_with_another_case_still_matches(db, service):
    auteur_id, livre_id = _seed(db, url=URL.lower())

    assert service.create_book_if_not_exists(_book_data(auteur_id)) == livre_id
    assert db.livres.count_documents({}) == 1


def test_same_url_from_a_duplicate_author_keeps_book_on_its_own_author(db, service):
    """L'auteur passé peut être un doublon créé par son nom (fusionné ensuite, #406)."""
    auteur_id, livre_id = _seed(db)
    doublon_id = db.auteurs.insert_one({"nom": "S. Leys", "livres": []}).inserted_id

    book_id = service.create_book_if_not_exists(_book_data(doublon_id))

    assert book_id == livre_id
    assert db.livres.find_one({"_id": livre_id})["auteur_id"] == auteur_id
    assert db.auteurs.find_one({"_id": doublon_id})["livres"] == []
    assert db.auteurs.find_one({"_id": auteur_id})["livres"] == [str(livre_id)]


def test_without_babelio_url_a_different_title_is_a_new_book(db, service):
    auteur_id, livre_id = _seed(db, url=None)

    book_id = service.create_book_if_not_exists(_book_data(auteur_id, url=None))

    assert book_id != livre_id
    assert db.livres.count_documents({}) == 2
