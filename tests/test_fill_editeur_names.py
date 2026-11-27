"""Tests de MongoDBService.fill_editeur_names (Issue #404).

Un livre porte soit un champ texte `editeur` (livres anciens), soit un
`editeur_id` (ObjectId, réf. collection `editeurs`) sans champ texte. Toute
lecture qui affiche l'éditeur doit résoudre les deux formes.

Les requêtes tournent sur mongomock : un mock de `find()` ne verrait pas une
confusion ObjectId / str dans le `$in`.
"""

from datetime import datetime
from typing import Any

import mongomock
from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


def _service_with_editeurs(editeurs: list[dict]) -> MongoDBService:
    service = MongoDBService()
    db: Any = mongomock.MongoClient().db
    if editeurs:
        db.editeurs.insert_many(editeurs)
    service.editeurs_collection = db.editeurs
    return service


def test_fills_editeur_name_from_editeur_id():
    editeur_id = ObjectId()
    service = _service_with_editeurs([{"_id": editeur_id, "nom": "Conférence"}])
    livre = {"_id": ObjectId(), "titre": "Conférence, n°40", "editeur_id": editeur_id}

    service.fill_editeur_names([livre])

    assert livre["editeur"] == "Conférence"


def test_accepts_editeur_id_as_string():
    editeur_id = ObjectId()
    service = _service_with_editeurs([{"_id": editeur_id, "nom": "Minuit"}])
    livre = {"_id": ObjectId(), "editeur_id": str(editeur_id)}

    service.fill_editeur_names([livre])

    assert livre["editeur"] == "Minuit"


def test_keeps_existing_editeur_text():
    editeur_id = ObjectId()
    service = _service_with_editeurs([{"_id": editeur_id, "nom": "Autre"}])
    livre = {"_id": ObjectId(), "editeur": "P.O.L.", "editeur_id": editeur_id}

    service.fill_editeur_names([livre])

    assert livre["editeur"] == "P.O.L."


def test_resolves_a_batch_with_one_query():
    ids = [ObjectId(), ObjectId()]
    service = _service_with_editeurs(
        [{"_id": ids[0], "nom": "Minuit"}, {"_id": ids[1], "nom": "Gallimard"}]
    )
    calls = []
    collection: Any = service.editeurs_collection
    real_find = collection.find

    def counting_find(*args, **kwargs):
        calls.append(args)
        return real_find(*args, **kwargs)

    collection.find = counting_find
    livres = [
        {"_id": ObjectId(), "editeur_id": ids[0]},
        {"_id": ObjectId(), "editeur_id": ids[1]},
        {"_id": ObjectId(), "editeur_id": ids[0]},
        {"_id": ObjectId(), "editeur": "Folio"},
    ]

    service.fill_editeur_names(livres)

    assert [livre["editeur"] for livre in livres] == [
        "Minuit",
        "Gallimard",
        "Minuit",
        "Folio",
    ]
    assert len(calls) == 1


def test_unknown_editeur_id_leaves_livre_untouched():
    service = _service_with_editeurs([])
    livre = {"_id": ObjectId(), "editeur_id": ObjectId()}

    service.fill_editeur_names([livre])

    assert "editeur" not in livre


def test_no_query_when_nothing_to_resolve():
    service = _service_with_editeurs([])
    service.editeurs_collection = None  # ne doit pas être touchée
    livres = [{"_id": ObjectId(), "editeur": "Seuil"}, {"_id": ObjectId()}]

    service.fill_editeur_names(livres)

    assert livres[0]["editeur"] == "Seuil"
    assert "editeur" not in livres[1]


def test_without_editeurs_collection_does_not_raise():
    service = MongoDBService()
    livre = {"_id": ObjectId(), "editeur_id": ObjectId()}

    service.fill_editeur_names([livre])

    assert "editeur" not in livre


# --- Lectures qui affichent l'éditeur d'un livre ---------------------------


def _db_with_livre_a_editeur_id() -> tuple[Any, ObjectId, ObjectId]:
    """Base mongomock : un auteur, un livre post-#189 (editeur_id seul)."""
    db: Any = mongomock.MongoClient().db
    auteur_id, livre_id, editeur_id = ObjectId(), ObjectId(), ObjectId()
    db.editeurs.insert_one({"_id": editeur_id, "nom": "Conférence"})
    db.auteurs.insert_one({"_id": auteur_id, "nom": "Livres de Revue Conférence"})
    db.livres.insert_one(
        {
            "_id": livre_id,
            "titre": "Conférence, n°40",
            "auteur_id": auteur_id,
            "editeur_id": editeur_id,
            "episodes": [],
        }
    )
    return db, auteur_id, livre_id


def _service_on(db: Any) -> MongoDBService:
    service = MongoDBService()
    service.db = db
    service.auteurs_collection = db.auteurs
    service.livres_collection = db.livres
    service.editeurs_collection = db.editeurs
    service.avis_collection = db.avis
    service.emissions_collection = db.emissions
    service.critiques_collection = db.critiques
    return service


def test_auteur_page_shows_editeur_of_livre_with_editeur_id():
    db, auteur_id, _ = _db_with_livre_a_editeur_id()
    service = _service_on(db)

    auteur = service.get_auteur_with_livres(str(auteur_id))

    assert auteur is not None
    assert auteur["livres"][0]["editeur"] == "Conférence"


def test_search_livres_returns_editeur_of_livre_with_editeur_id():
    db, _, _ = _db_with_livre_a_editeur_id()
    service = _service_on(db)

    result = service.search_livres("Conférence")

    assert result["livres"][0]["editeur"] == "Conférence"


def _add_avis(
    db: Any, livre_id: ObjectId, emission_id: ObjectId, critique_id: ObjectId
) -> None:
    db.emissions.insert_one({"_id": emission_id, "date": datetime(2026, 11, 22)})
    db.critiques.insert_one({"_id": critique_id, "nom": "Michel Crépu"})
    db.avis.insert_one(
        {
            "_id": ObjectId(),
            "emission_oid": str(emission_id),
            "livre_oid": str(livre_id),
            "critique_oid": str(critique_id),
            "commentaire": "Plus belle revue, discrète",
            "note": 8,
            "section": "programme",
            "livre_titre_extrait": "Conférence, n°40",
            "auteur_nom_extrait": "Revue Conférence",
            "editeur_extrait": "Revue Conférence",
        }
    )


def test_critique_page_shows_editeur_of_livre_not_extracted_one():
    db, _, livre_id = _db_with_livre_a_editeur_id()
    critique_id = ObjectId()
    _add_avis(db, livre_id, ObjectId(), critique_id)
    service = _service_on(db)

    detail = service.get_critique_detail(str(critique_id))

    assert detail is not None
    assert detail["oeuvres"][0]["editeur"] == "Conférence"


def test_critique_page_keeps_extracted_editeur_for_unresolved_livre():
    db: Any = mongomock.MongoClient().db
    critique_id = ObjectId()
    _add_avis(db, ObjectId(), ObjectId(), critique_id)  # livre absent de la base
    service = _service_on(db)

    detail = service.get_critique_detail(str(critique_id))

    assert detail is not None
    assert detail["oeuvres"][0]["editeur"] == "Revue Conférence"


def test_search_emissions_finds_livre_by_editeur_id_name():
    db, _, livre_id = _db_with_livre_a_editeur_id()
    emission_id = ObjectId()
    _add_avis(db, livre_id, emission_id, ObjectId())
    # L'éditeur extrait ne contient pas le terme : seul editeur_id peut matcher
    db.avis.update_many({}, {"$set": {"editeur_extrait": "-"}})
    db.editeurs.update_many({}, {"$set": {"nom": "Éditions Zulma"}})
    service = _service_on(db)

    result = service.search_emissions("zulma")

    assert [e["_id"] for e in result["emissions"]] == [str(emission_id)]


def test_episode_books_carry_editeur_of_livre_with_editeur_id():
    """get_livres_from_collections alimente l'extraction et la page Émission."""
    import asyncio
    from unittest.mock import patch

    from back_office_lmelp import app as app_module

    db, auteur_id, livre_id = _db_with_livre_a_editeur_id()
    episode_oid = str(ObjectId())
    db.livresauteurs_cache.insert_one(
        {
            "episode_oid": episode_oid,
            "status": "mongo",
            "book_id": livre_id,
            "author_id": auteur_id,
        }
    )
    service = _service_on(db)

    with patch.object(app_module, "mongodb_service", service):
        books = asyncio.run(app_module.get_livres_from_collections(episode_oid))

    assert books[0]["editeur"] == "Conférence"
