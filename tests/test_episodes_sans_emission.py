"""Compteur « Épisodes sans émission » du dashboard (Issue #403).

Un épisode compte comme « sans émission » seulement s'il est déjà passé dans
Livres et Auteurs (entrées dans ``livresauteurs_cache``) sans avoir encore
d'émission. Un épisode pas encore traité relève du seul compteur
« Épisodes non traités » : les deux compteurs ne doivent pas se recouvrir.

Les requêtes tournent sur mongomock (vrais filtres, vrais types) plutôt que sur
des retours mockés, qui ne verraient pas une jointure ratée String/ObjectId.
"""

from typing import Any
from unittest.mock import MagicMock

import mongomock
import pytest

from back_office_lmelp.services.livres_auteurs_cache_service import (
    LivresAuteursCacheService,
)


@pytest.fixture
def db():
    return mongomock.MongoClient().db


@pytest.fixture
def service(db):
    mongodb = MagicMock()
    mongodb.get_collection.side_effect = lambda name: db[name]
    svc = LivresAuteursCacheService()
    svc.mongodb_service = mongodb
    return svc


def _add_episode(db: Any, *, traite: bool, emission: bool, masked: bool = False) -> Any:
    """Ajoute un épisode avec son avis critique, aux types de la base réelle."""
    episode_id = db.episodes.insert_one({"masked": masked}).inserted_id
    # avis_critiques.episode_oid est une String
    avis_id = db.avis_critiques.insert_one({"episode_oid": str(episode_id)}).inserted_id
    if traite:
        # livresauteurs_cache : episode_oid String, avis_critique_id ObjectId
        db.livresauteurs_cache.insert_one(
            {
                "episode_oid": str(episode_id),
                "avis_critique_id": avis_id,
                "status": "mongo",
            }
        )
    if emission:
        # emissions.episode_id est un ObjectId
        db.emissions.insert_one({"episode_id": episode_id})
    return episode_id


def test_episode_not_yet_treated_is_not_counted_as_sans_emission(db, service):
    _add_episode(db, traite=True, emission=False)  # sans émission
    _add_episode(db, traite=False, emission=False)  # non traité seulement
    _add_episode(db, traite=True, emission=True)  # complet

    stats = service.get_statistics_from_cache()

    assert stats["episodes_non_traites"] == 1
    assert stats["episodes_sans_emission"] == 1


def test_masked_episode_is_never_counted_as_sans_emission(db, service):
    _add_episode(db, traite=True, emission=False, masked=True)

    stats = service.get_statistics_from_cache()

    assert stats["episodes_sans_emission"] == 0


def test_episode_with_unvalidated_books_still_counts_as_sans_emission(db, service):
    """Être passé dans Livres et Auteurs suffit, quel que soit le statut Babelio."""
    episode_id = _add_episode(db, traite=False, emission=False)
    avis = db.avis_critiques.find_one({"episode_oid": str(episode_id)})
    db.livresauteurs_cache.insert_one(
        {
            "episode_oid": str(episode_id),
            "avis_critique_id": avis["_id"],
            "status": "suggested",
        }
    )

    stats = service.get_statistics_from_cache()

    assert stats["episodes_sans_emission"] == 1
