"""Service pour gérer la migration des URL Babelio.

Ce service gère:
- Lecture des cas problématiques depuis le fichier JSONL
- Actions manuelles (accepter suggestion, marquer not found, retry)
- Suppression de cas du fichier JSONL après traitement
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bson import ObjectId

from back_office_lmelp.services.babelio_service import BabelioService
from back_office_lmelp.services.mongodb_service import MongoDBService


logger = logging.getLogger(__name__)

# Chemin vers le fichier JSONL des cas problématiques
PROBLEMATIC_CASES_FILE = (
    Path(__file__).parent.parent.parent.parent
    / "scripts"
    / "migration_donnees"
    / "migration_problematic_cases.jsonl"
)


class BabelioMigrationService:
    """Service de gestion de la migration Babelio."""

    def __init__(
        self,
        mongodb_service: MongoDBService,
        babelio_service: BabelioService,
    ):
        """Initialise le service de migration.

        Args:
            mongodb_service: Service MongoDB
            babelio_service: Service Babelio
        """
        self.mongodb_service = mongodb_service
        self.babelio_service = babelio_service

    def get_migration_status(self) -> dict[str, Any]:
        """Récupère le statut de la migration.

        Returns:
            Statut avec compteurs et dernière mise à jour
        """
        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")
        livres_collection = self.mongodb_service.db["livres"]

        # Compter les livres total
        total_books = livres_collection.count_documents({})

        # Compter les livres avec URL Babelio
        migrated_count = livres_collection.count_documents(
            {"url_babelio": {"$exists": True, "$ne": None}}
        )

        # Compter les livres marqués "not found"
        not_found_count = livres_collection.count_documents({"babelio_not_found": True})

        # Compter les cas problématiques dans le fichier
        problematic_cases = self.get_problematic_cases()
        problematic_count = len(problematic_cases)

        # Chercher la dernière date de mise à jour
        last_migration = None
        latest_book = livres_collection.find_one(
            {"url_babelio": {"$exists": True, "$ne": None}},
            sort=[("_id", -1)],
        )
        if latest_book:
            # Extraire timestamp de l'ObjectId
            last_migration = latest_book["_id"].generation_time.isoformat()

        return {
            "total_books": total_books,
            "migrated_count": migrated_count,
            "not_found_count": not_found_count,
            "problematic_count": problematic_count,
            "pending_count": total_books
            - migrated_count
            - not_found_count
            - problematic_count,
            "last_migration": last_migration,
        }

    def get_problematic_cases(self) -> list[dict[str, Any]]:
        """Récupère la liste des cas problématiques depuis MongoDB.

        Exclut les livres qui ont déjà été marqués avec babelio_not_found=true
        ou qui ont déjà une url_babelio (déjà résolus).

        Returns:
            Liste des cas problématiques non résolus
        """
        cases: list[dict[str, Any]] = []

        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")

        problematic_collection = self.mongodb_service.db["babelio_problematic_cases"]
        livres_collection = self.mongodb_service.db["livres"]

        # Récupérer tous les cas problématiques depuis MongoDB
        for case in problematic_collection.find():
            # Vérifier si ce livre est déjà résolu dans la collection livres
            livre_id = case.get("livre_id")
            if livre_id:
                livre = livres_collection.find_one({"_id": ObjectId(livre_id)})
                # Exclure si déjà marqué "not found" ou si a déjà une URL
                if livre and (
                    livre.get("babelio_not_found") or livre.get("url_babelio")
                ):
                    logger.debug(
                        f"Livre {livre_id} déjà résolu, exclu des cas problématiques"
                    )
                    continue

            cases.append(case)

        return cases

    def accept_suggestion(
        self,
        livre_id: str,
        babelio_url: str,
        babelio_author_url: str | None = None,
        corrected_title: str | None = None,
    ) -> bool:
        """Accepte la suggestion Babelio et met à jour MongoDB.

        Args:
            livre_id: ID du livre MongoDB (string hex)
            babelio_url: URL Babelio du livre
            babelio_author_url: URL Babelio de l'auteur (optionnel)
            corrected_title: Titre corrigé (optionnel)

        Returns:
            True si succès, False sinon
        """
        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")
        livres_collection = self.mongodb_service.db["livres"]
        auteurs_collection = self.mongodb_service.db["auteurs"]

        # Convertir livre_id en ObjectId
        try:
            livre_oid = ObjectId(livre_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId format: {livre_id} - {e}")
            return False

        # Mettre à jour le livre
        update_data: dict[str, Any] = {
            "url_babelio": babelio_url,
            "updated_at": datetime.now(UTC),
        }
        if corrected_title:
            update_data["titre"] = corrected_title

        result = livres_collection.update_one({"_id": livre_oid}, {"$set": update_data})

        if result.matched_count == 0:
            logger.error(f"Livre {livre_id} non trouvé dans MongoDB")
            return False

        # Mettre à jour l'auteur si URL fournie
        if babelio_author_url:
            livre = livres_collection.find_one({"_id": livre_oid})
            if livre and livre.get("auteur_id"):
                auteur_id = livre["auteur_id"]
                # Ne pas écraser si l'auteur a déjà une URL
                auteurs_collection.update_one(
                    {"_id": auteur_id, "url_babelio": {"$exists": False}},
                    {"$set": {"url_babelio": babelio_author_url}},
                )

        # Retirer du fichier JSONL
        self._remove_from_problematic(livre_id)

        logger.info(f"✅ Suggestion acceptée pour livre {livre_id}: {babelio_url}")
        return True

    def mark_as_not_found(self, livre_id: str, reason: str) -> bool:
        """Marque un livre comme non trouvé sur Babelio.

        Args:
            livre_id: ID du livre MongoDB (string hex)
            reason: Raison du not found

        Returns:
            True si succès, False sinon
        """
        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")
        livres_collection = self.mongodb_service.db["livres"]

        # Convertir livre_id en ObjectId
        try:
            livre_oid = ObjectId(livre_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId format: {livre_id} - {e}")
            return False

        result = livres_collection.update_one(
            {"_id": livre_oid},
            {
                "$set": {
                    "babelio_not_found": True,
                    "babelio_not_found_reason": reason,
                    "babelio_not_found_date": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            },
        )

        if result.matched_count == 0:
            logger.error(f"Livre {livre_id} non trouvé dans MongoDB")
            return False

        # Retirer du fichier JSONL
        self._remove_from_problematic(livre_id)

        logger.info(f"❌ Livre {livre_id} marqué comme not found: {reason}")
        return True

    async def retry_with_new_title(
        self, livre_id: str, new_title: str, author: str | None = None
    ) -> dict[str, Any]:
        """Réessaie la recherche Babelio avec un nouveau titre.

        Args:
            livre_id: ID du livre MongoDB
            new_title: Nouveau titre à rechercher
            author: Nom de l'auteur (optionnel)

        Returns:
            Résultat de verify_book()
        """
        logger.info(
            f"🔄 Retry pour livre {livre_id}: titre='{new_title}' auteur='{author}'"
        )

        result = await self.babelio_service.verify_book(new_title, author)

        logger.info(f"📊 Résultat retry: status={result.get('status')}")
        return result

    def _remove_from_problematic(self, livre_id: str) -> None:
        """Retire un livre du fichier JSONL des cas problématiques.

        Args:
            livre_id: ID du livre à retirer
        """
        if not PROBLEMATIC_CASES_FILE.exists():
            return

        # Lire toutes les lignes sauf celle du livre_id
        lines_to_keep = []
        with open(PROBLEMATIC_CASES_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    case = json.loads(line)
                    if case.get("livre_id") != livre_id:
                        lines_to_keep.append(line)
                except json.JSONDecodeError:
                    # Garder les lignes invalides pour ne pas les perdre
                    lines_to_keep.append(line)

        # Réécrire le fichier
        with open(PROBLEMATIC_CASES_FILE, "w", encoding="utf-8") as f:
            for line in lines_to_keep:
                f.write(line + "\n")

        logger.debug(f"Livre {livre_id} retiré du fichier JSONL")
