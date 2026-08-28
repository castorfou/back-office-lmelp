"""
Service de détection et nettoyage des avis orphelins (Issue #271).

Un avis est orphelin si son livre_oid (String) ne correspond à aucun
document livres._id (ObjectId) existant — typiquement après une fusion
de doublons qui n'a pas repointé un avis (bug historique corrigé dans
merge_duplicate_group, ou avis créés avant le fix).
"""

import logging
from typing import Any

from back_office_lmelp.services.mongodb_service import MongoDBService
from back_office_lmelp.utils.text_utils import normalize_for_matching


logger = logging.getLogger(__name__)


class OrphanedAvisService:
    """Service de gestion des avis orphelins."""

    def __init__(self, mongodb_service: MongoDBService):
        """
        Initialise le service.

        Args:
            mongodb_service: Service MongoDB pour accès à la collection avis
        """
        self.mongodb_service = mongodb_service

    def _orphaned_pipeline(self) -> list[dict[str, Any]]:
        """Pipeline d'agrégation commun: avis dont livre_oid ne matche aucun livre."""
        return [
            {"$match": {"livre_oid": {"$ne": None, "$exists": True}}},
            {
                "$lookup": {
                    "from": "livres",
                    "let": {"livre_id": {"$toObjectId": "$livre_oid"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", "$$livre_id"]}}}
                    ],
                    "as": "matched_livre",
                }
            },
            {"$match": {"matched_livre": {"$size": 0}}},
        ]

    async def get_orphaned_statistics(self) -> dict[str, Any]:
        """Compte les avis orphelins (livre_oid sans livre correspondant)."""
        assert self.mongodb_service.avis_collection is not None, (
            "avis_collection must be initialized"
        )
        pipeline = [*self._orphaned_pipeline(), {"$count": "count"}]
        result = list(self.mongodb_service.avis_collection.aggregate(pipeline))
        return {"orphaned_count": result[0]["count"] if result else 0}

    def _build_titre_index(self) -> dict[str, tuple[str, str]]:
        """Index {titre_normalisé: (livre_id, titre_original)} pour suggestion (Issue #271).

        Un avis orphelin est presque toujours dû à une fusion de doublons dont
        le livre survivant existe encore, sous un autre titre normalisé identique.
        """
        assert self.mongodb_service.livres_collection is not None, (
            "livres_collection must be initialized"
        )
        index: dict[str, tuple[str, str]] = {}
        for livre in self.mongodb_service.livres_collection.find({}, {"titre": 1}):
            titre = livre.get("titre")
            if not titre:
                continue
            index[normalize_for_matching(titre)] = (str(livre["_id"]), titre)
        return index

    async def list_orphaned_avis(self) -> list[dict[str, Any]]:
        """
        Liste tous les avis orphelins avec contexte pour affichage/correction manuelle.

        Pour chaque avis, suggère un livre existant correspondant (matching par
        titre normalisé) — permet à l'UI de distinguer "livre déplacé" (repointage
        sûr) de "livre disparu" (suppression seule option pertinente), afin
        d'éviter de supprimer un avis dont le livre existe encore (Issue #271).

        Returns:
            Liste de dicts: id, livre_oid, livre_titre_extrait, auteur_nom_extrait,
            critique_nom_extrait, emission_oid, commentaire, note,
            suggested_livre_id, suggested_livre_titre
        """
        assert self.mongodb_service.avis_collection is not None, (
            "avis_collection must be initialized"
        )
        pipeline = self._orphaned_pipeline()
        orphaned = list(self.mongodb_service.avis_collection.aggregate(pipeline))
        titre_index = self._build_titre_index()

        result = []
        for avis in orphaned:
            titre_extrait = avis.get("livre_titre_extrait", "")
            suggestion = titre_index.get(normalize_for_matching(titre_extrait))

            result.append(
                {
                    "id": str(avis["_id"]),
                    "livre_oid": avis.get("livre_oid"),
                    "livre_titre_extrait": titre_extrait,
                    "auteur_nom_extrait": avis.get("auteur_nom_extrait", ""),
                    "critique_nom_extrait": avis.get("critique_nom_extrait", ""),
                    "emission_oid": avis.get("emission_oid"),
                    "commentaire": avis.get("commentaire", ""),
                    "note": avis.get("note"),
                    "suggested_livre_id": suggestion[0] if suggestion else None,
                    "suggested_livre_titre": suggestion[1] if suggestion else None,
                }
            )
        return result
