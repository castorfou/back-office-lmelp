"""Service pour gérer la migration des URL Babelio.

Ce service gère:
- Lecture des cas problématiques depuis MongoDB
- Actions manuelles (accepter suggestion, marquer not found, retry)
- Suppression de cas de MongoDB après traitement
"""

import logging
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from back_office_lmelp.services.babelio_service import BabelioService
from back_office_lmelp.services.mongodb_service import MongoDBService


logger = logging.getLogger(__name__)


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
        auteurs_collection = self.mongodb_service.db["auteurs"]

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

        # Statistiques pour les auteurs
        total_authors = auteurs_collection.count_documents({})
        authors_with_url = auteurs_collection.count_documents(
            {"url_babelio": {"$exists": True, "$ne": None}}
        )
        authors_without_url = total_authors - authors_with_url

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
            # Statistiques auteurs
            "total_authors": total_authors,
            "authors_with_url": authors_with_url,
            "authors_without_url_babelio": authors_without_url,
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

            # Convertir ObjectId et datetime en strings pour Pydantic/FastAPI
            serializable_case = {}
            for key, value in case.items():
                if isinstance(value, ObjectId):
                    serializable_case[key] = str(value)
                elif isinstance(value, datetime):
                    serializable_case[key] = value.isoformat()
                else:
                    serializable_case[key] = value

            cases.append(serializable_case)

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

        # Retirer de la collection MongoDB babelio_problematic_cases
        problematic_collection = self.mongodb_service.db["babelio_problematic_cases"]
        problematic_collection.delete_one({"livre_id": livre_id})

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

        # Retirer de la collection MongoDB babelio_problematic_cases
        problematic_collection = self.mongodb_service.db["babelio_problematic_cases"]
        problematic_collection.delete_one({"livre_id": livre_id})

        logger.info(f"❌ Livre {livre_id} marqué comme not found: {reason}")
        return True

    def correct_title(self, livre_id: str, new_title: str) -> bool:
        """Corrige le titre d'un livre et le retire des cas problématiques.

        Le livre redevient éligible pour la migration automatique.

        Args:
            livre_id: ID du livre MongoDB (string hex)
            new_title: Nouveau titre corrigé

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

        # Mettre à jour le titre du livre
        result = livres_collection.update_one(
            {"_id": livre_oid},
            {
                "$set": {
                    "titre": new_title,
                    "updated_at": datetime.now(UTC),
                }
            },
        )

        if result.matched_count == 0:
            logger.error(f"Livre {livre_id} non trouvé dans MongoDB")
            return False

        # Retirer de la collection MongoDB babelio_problematic_cases
        problematic_collection = self.mongodb_service.db["babelio_problematic_cases"]
        problematic_collection.delete_one({"livre_id": livre_id})

        logger.info(f"✏️  Titre corrigé pour livre {livre_id}: '{new_title}'")
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
