"""
Service de détection et fusion des doublons de livres (Issue #178).

Ce service permet de :
1. Détecter les livres en doublon (même url_babelio)
2. Valider les groupes de doublons (auteur_id identique)
3. Fusionner les doublons en scrapant Babelio pour données officielles
4. Traiter en batch avec possibilité de skip
"""

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from back_office_lmelp.services.babelio_service import BabelioService
from back_office_lmelp.services.mongodb_service import MongoDBService


logger = logging.getLogger(__name__)


class DuplicateBooksService:
    """Service de gestion des doublons de livres."""

    def __init__(
        self, mongodb_service: MongoDBService, babelio_service: BabelioService
    ):
        """
        Initialise le service.

        Args:
            mongodb_service: Service MongoDB pour accès aux collections
            babelio_service: Service Babelio pour scraping données officielles
        """
        self.mongodb_service = mongodb_service
        self.babelio_service = babelio_service

    async def find_duplicate_groups_by_url(self) -> list[dict[str, Any]]:
        """
        Trouve tous les groupes de doublons par url_babelio.

        Utilise une aggregation MongoDB pour grouper les livres
        ayant la même url_babelio.

        Returns:
            Liste de groupes de doublons avec détails complets:
            [{
                "url_babelio": str,
                "count": int,
                "book_ids": list[ObjectId],
                "titres": list[str],
                "auteur_ids": list[ObjectId],
                ...
            }]
        """
        assert self.mongodb_service.livres_collection is not None, (
            "livres_collection must be initialized"
        )

        pipeline: list[dict[str, Any]] = [
            # Étape 1: Ne garder que les livres avec url_babelio
            {"$match": {"url_babelio": {"$ne": None, "$exists": True}}},
            # Étape 2: Grouper par url_babelio
            {
                "$group": {
                    "_id": "$url_babelio",
                    "count": {"$sum": 1},
                    "book_ids": {"$push": "$_id"},
                    "titres": {"$push": "$titre"},
                    "auteur_ids": {"$push": "$auteur_id"},
                }
            },
            # Étape 3: Ne garder que les groupes avec count > 1 (doublons)
            {"$match": {"count": {"$gt": 1}}},
            # Étape 4: Trier par count décroissant (groupes les plus gros d'abord)
            {"$sort": {"count": -1}},
        ]

        results = list(self.mongodb_service.livres_collection.aggregate(pipeline))

        # Transformer le résultat pour correspondre au format attendu
        formatted_results = []
        for group in results:
            formatted_results.append(
                {
                    "url_babelio": group["_id"],
                    "count": group["count"],
                    "book_ids": group["book_ids"],
                    "titres": group["titres"],
                    "auteur_ids": group["auteur_ids"],
                }
            )

        return formatted_results

    async def validate_duplicate_group(
        self, url_babelio: str, book_ids: list[str]
    ) -> dict[str, Any]:
        """
        Valide un groupe de doublons avant fusion.

        CRITICAL: Vérifie que tous les livres ont le MÊME auteur_id.

        Args:
            url_babelio: URL Babelio du groupe
            book_ids: Liste des IDs de livres (strings)

        Returns:
            {
                "valid": bool,
                "errors": list[str],
                "warnings": list[str],
                "auteur_id": ObjectId | None,
                "book_data": list[dict]
            }
        """
        # Récupérer les livres de la base
        object_ids = [ObjectId(book_id) for book_id in book_ids]
        assert self.mongodb_service.livres_collection is not None, (
            "livres_collection must be initialized"
        )
        books = list(
            self.mongodb_service.livres_collection.find({"_id": {"$in": object_ids}})
        )

        if not books:
            return {
                "valid": False,
                "errors": ["No books found with given IDs"],
                "warnings": [],
                "auteur_id": None,
                "book_data": [],
            }

        # Vérifier que tous les auteur_id sont identiques
        auteur_ids = [book["auteur_id"] for book in books]
        unique_auteur_ids = list(set(auteur_ids))

        if len(unique_auteur_ids) > 1:
            return {
                "valid": False,
                "errors": [
                    f"auteur_id mismatch: Expected {unique_auteur_ids[0]}, "
                    f"found {unique_auteur_ids[1]}"
                ],
                "warnings": [],
                "auteur_id": None,
                "book_data": books,
            }

        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "auteur_id": unique_auteur_ids[0],
            "book_data": books,
        }

    async def merge_duplicate_group(
        self, url_babelio: str, book_ids: list[str]
    ) -> dict[str, Any]:
        """
        Fusionne un groupe de doublons.

        Algorithme:
        1. Valider le groupe (auteur_id identique)
        2. Scraper Babelio pour données officielles
        3. Sélectionner livre primaire (oldest created_at)
        4. Fusionner episodes et avis_critiques (union)
        5. Mettre à jour livre primaire
        6. Supprimer doublons
        7. Cascading updates (auteurs, cache)
        8. Logger dans merge_history

        Args:
            url_babelio: URL Babelio du groupe
            book_ids: Liste des IDs de livres à fusionner

        Returns:
            {
                "success": bool,
                "primary_book_id": str,
                "deleted_book_ids": list[str],
                "merged_data": {"titre": str, "editeur": str},
                "episodes_merged": int,
                "avis_critiques_merged": int,
                "logs": list[str],
                "error": str | None
            }
        """
        # Étape 1: Validation
        validation = await self.validate_duplicate_group(url_babelio, book_ids)
        if not validation["valid"]:
            return {
                "success": False,
                "error": "; ".join(validation["errors"]),
                "primary_book_id": None,
                "deleted_book_ids": [],
                "merged_data": {},
                "episodes_merged": 0,
                "avis_critiques_merged": 0,
                "logs": [],
            }

        books = validation["book_data"]

        # Étape 2: Scraper Babelio pour données officielles
        official_titre = await self.babelio_service.fetch_full_title_from_url(
            url_babelio
        )
        official_editeur = await self.babelio_service.fetch_publisher_from_url(
            url_babelio
        )

        # Étape 3: Sélectionner livre primaire (plus ancien)
        books.sort(key=lambda b: b["created_at"])
        primary_book = books[0]
        duplicates = books[1:]

        # Étape 4: Fusionner episodes et avis_critiques (union, déduplication)
        all_episodes = []
        all_avis = []
        for book in books:
            all_episodes.extend(book.get("episodes", []))
            all_avis.extend(book.get("avis_critiques", []))

        unique_episodes = list(set(all_episodes))  # Déduplication
        unique_avis = list(set(all_avis))

        # Étape 5: Mettre à jour livre primaire avec données Babelio
        assert self.mongodb_service.livres_collection is not None, (
            "livres_collection must be initialized"
        )
        self.mongodb_service.livres_collection.update_one(
            {"_id": primary_book["_id"]},
            {
                "$set": {
                    "titre": official_titre,
                    "editeur": official_editeur,
                    "updated_at": datetime.now(UTC),
                },
                "$addToSet": {
                    "episodes": {"$each": unique_episodes},
                    "avis_critiques": {"$each": unique_avis},
                },
            },
        )

        # Étape 6: Supprimer doublons
        duplicate_ids = [book["_id"] for book in duplicates]
        if duplicate_ids:
            assert self.mongodb_service.livres_collection is not None, (
                "livres_collection must be initialized"
            )
            self.mongodb_service.livres_collection.delete_many(
                {"_id": {"$in": duplicate_ids}}
            )

        # Étape 7: Cascading update - auteurs collection
        duplicate_ids_str = [str(book_id) for book_id in duplicate_ids]
        if duplicate_ids_str:
            assert self.mongodb_service.auteurs_collection is not None, (
                "auteurs_collection must be initialized"
            )
            self.mongodb_service.auteurs_collection.update_one(
                {"_id": validation["auteur_id"]},
                {"$pull": {"livres": {"$in": duplicate_ids_str}}},
            )

        # Étape 8: Logger dans merge_history
        history_collection = self.mongodb_service.get_collection(
            "duplicate_books_merge_history"
        )
        history_collection.insert_one(
            {
                "url_babelio": url_babelio,
                "primary_book_id": primary_book["_id"],
                "deleted_book_ids": duplicate_ids,
                "merged_episodes_count": len(unique_episodes),
                "merged_avis_critiques_count": len(unique_avis),
                "babelio_data": {"titre": official_titre, "editeur": official_editeur},
                "timestamp": datetime.now(UTC),
            }
        )

        return {
            "success": True,
            "primary_book_id": str(primary_book["_id"]),
            "deleted_book_ids": [str(book_id) for book_id in duplicate_ids],
            "merged_data": {"titre": official_titre, "editeur": official_editeur},
            "episodes_merged": len(unique_episodes),
            "avis_critiques_merged": len(unique_avis),
            "logs": [
                f"Primary book: {primary_book['_id']}",
                f"Deleted: {len(duplicate_ids)} duplicates",
                f"Merged: {len(unique_episodes)} episodes, {len(unique_avis)} avis",
            ],
            "error": None,
        }

    async def get_duplicate_statistics(self) -> dict[str, Any]:
        """
        Récupère les statistiques des doublons pour le dashboard.

        Returns:
            {
                "total_groups": int,
                "total_duplicates": int,
                "merged_count": int,
                "skipped_count": int,
                "pending_count": int
            }
        """
        assert self.mongodb_service.livres_collection is not None, (
            "livres_collection must be initialized"
        )

        # Compter les groupes de doublons
        pipeline: list[dict[str, Any]] = [
            {"$match": {"url_babelio": {"$ne": None, "$exists": True}}},
            {"$group": {"_id": "$url_babelio", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
        ]

        duplicate_groups = list(
            self.mongodb_service.livres_collection.aggregate(pipeline)
        )

        total_groups = len(duplicate_groups)

        # Calculer le nombre total de doublons
        # Pour chaque groupe, le nombre de doublons = count - 1
        # (on ne compte pas le livre principal)
        total_duplicates = sum(group["count"] - 1 for group in duplicate_groups)

        # Compter les groupes fusionnés
        history_collection = self.mongodb_service.get_collection(
            "duplicate_books_merge_history"
        )
        merged_count = history_collection.count_documents({})

        # Compter les groupes en attente
        pending_count = total_groups - merged_count

        return {
            "total_groups": total_groups,
            "total_duplicates": total_duplicates,
            "merged_count": merged_count,
            "skipped_count": 0,  # TODO: Implémenter skip list persistante
            "pending_count": pending_count,
        }

    async def merge_batch(
        self, skip_list: list[str] | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Fusionne en batch tous les groupes de doublons.

        Args:
            skip_list: Liste d'URLs Babelio à ignorer

        Yields:
            Événements de progression pour Server-Sent Events:
            {
                "type": "progress" | "group_result" | "error" | "complete",
                "current": int,
                "total": int,
                "url_babelio": str,
                "result": dict,
                "timestamp": str
            }
        """
        if skip_list is None:
            skip_list = []

        # TODO: Implémenter batch processing
        yield {
            "type": "complete",
            "message": "Batch processing not yet implemented",
            "timestamp": datetime.now(UTC).isoformat(),
        }
