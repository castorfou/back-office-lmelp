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

        # Compter les cas problématiques par type
        problematic_collection = self.mongodb_service.db["babelio_problematic_cases"]
        problematic_count = problematic_collection.count_documents({"type": "livre"})
        problematic_authors_count = problematic_collection.count_documents(
            {"type": "auteur"}
        )

        # Statistiques pour les auteurs
        total_authors = auteurs_collection.count_documents({})
        authors_with_url = auteurs_collection.count_documents(
            {"url_babelio": {"$exists": True, "$ne": None}}
        )
        authors_not_found_count = auteurs_collection.count_documents(
            {"babelio_not_found": True}
        )
        authors_without_url = (
            total_authors
            - authors_with_url
            - authors_not_found_count
            - problematic_authors_count
        )

        # Chercher la dernière date de mise à jour
        last_migration = None
        latest_book = livres_collection.find_one(
            {"url_babelio": {"$exists": True, "$ne": None}},
            sort=[("_id", -1)],
        )
        if latest_book:
            # Extraire timestamp de l'ObjectId
            last_migration = latest_book["_id"].generation_time.isoformat()

        # Statistiques couvertures
        covers_with_url = livres_collection.count_documents(
            {"url_cover": {"$exists": True, "$ne": None}}
        )
        covers_not_applicable = (
            not_found_count  # Livres sans Babelio → pas de couverture
        )
        covers_mismatch_count = livres_collection.count_documents(
            {"cover_mismatch_page_title": {"$exists": True, "$ne": None}}
        )
        covers_pending = livres_collection.count_documents(
            {
                "url_babelio": {"$exists": True, "$ne": None},
                "cover_mismatch_page_title": {"$exists": False},
                "$or": [
                    {"url_cover": {"$exists": False}},
                    {"url_cover": None},
                ],
            }
        )

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
            "authors_not_found_count": authors_not_found_count,
            "problematic_authors_count": problematic_authors_count,
            "authors_without_url_babelio": authors_without_url,
            # Statistiques couvertures
            "covers_total": migrated_count,  # Livres avec url_babelio (seuls candidats pour une couverture)
            "covers_with_url": covers_with_url,
            "covers_not_applicable": covers_not_applicable,
            "covers_mismatch_count": covers_mismatch_count,
            "covers_pending": covers_pending,
        }

    def get_books_pending_covers(self) -> list[dict[str, Any]]:
        """Retourne les livres ayant une url_babelio mais pas encore de url_cover.

        Returns:
            Liste de livres avec _id (string), titre, url_babelio
        """
        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")
        livres_collection = self.mongodb_service.db["livres"]

        books = list(
            livres_collection.find(
                {
                    "url_babelio": {"$exists": True, "$ne": None},
                    "$or": [
                        {"url_cover": {"$exists": False}},
                        {"url_cover": None},
                    ],
                },
                {"_id": 1, "titre": 1, "url_babelio": 1},
            )
        )

        # Sérialiser les ObjectId en string pour JSON
        result = []
        for book in books:
            result.append(
                {
                    "_id": str(book["_id"]),
                    "titre": book.get("titre", ""),
                    "url_babelio": book.get("url_babelio", ""),
                }
            )
        return result

    def save_cover_url(self, livre_id: str, url_cover: str) -> bool:
        """Sauvegarde l'URL de couverture dans MongoDB pour un livre.

        Args:
            livre_id: ID du livre MongoDB (string hex)
            url_cover: URL de la couverture Babelio

        Returns:
            True si succès, False sinon
        """
        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")
        livres_collection = self.mongodb_service.db["livres"]

        try:
            livre_oid = ObjectId(livre_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId format: {livre_id} - {e}")
            return False

        result = livres_collection.update_one(
            {"_id": livre_oid},
            {"$set": {"url_cover": url_cover, "updated_at": datetime.now(UTC)}},
        )

        if result.matched_count == 0:
            logger.error(f"Livre {livre_id} non trouvé dans MongoDB")
            return False

        logger.info(f"✅ Couverture sauvegardée pour livre {livre_id}: {url_cover}")
        return True

    def save_cover_mismatch(
        self, livre_id: str, page_title: str, cover_url_found: str | None = None
    ) -> bool:
        """Stocke le titre de page Babelio erronée sur le livre pour traitement manuel.

        Appelé quand la page Babelio redirige vers un autre livre (TITLE_MISMATCH).

        Args:
            livre_id: ID du livre MongoDB (string hex)
            page_title: Titre affiché sur la page Babelio (mauvais livre)
            cover_url_found: URL cover trouvée sur la page (peut être proposée à l'utilisateur)

        Returns:
            True si succès, False sinon
        """
        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")
        livres_collection = self.mongodb_service.db["livres"]

        try:
            livre_oid = ObjectId(livre_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId format: {livre_id} - {e}")
            return False

        fields: dict[str, Any] = {
            "cover_mismatch_page_title": page_title,
            "updated_at": datetime.now(UTC),
        }
        if cover_url_found:
            fields["cover_mismatch_url_found"] = cover_url_found

        result = livres_collection.update_one({"_id": livre_oid}, {"$set": fields})

        if result.matched_count == 0:
            logger.error(f"Livre {livre_id} non trouvé dans MongoDB")
            return False

        logger.warning(
            f"⚠️ Cover mismatch sauvegardé pour livre {livre_id}: page='{page_title}'"
        )
        return True

    def get_cover_mismatch_cases(self) -> list[dict[str, Any]]:
        """Retourne les livres avec cover_mismatch_page_title (à traiter manuellement).

        Returns:
            Liste de livres avec _id (string), titre, url_babelio, cover_mismatch_page_title
        """
        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")
        livres_collection = self.mongodb_service.db["livres"]

        books = list(
            livres_collection.find(
                {"cover_mismatch_page_title": {"$exists": True, "$ne": None}},
                {
                    "_id": 1,
                    "titre": 1,
                    "url_babelio": 1,
                    "cover_mismatch_page_title": 1,
                    "cover_mismatch_url_found": 1,
                },
            )
        )

        result = []
        for book in books:
            result.append(
                {
                    "_id": str(book["_id"]),
                    "titre": book.get("titre", ""),
                    "url_babelio": book.get("url_babelio", ""),
                    "cover_mismatch_page_title": book.get(
                        "cover_mismatch_page_title", ""
                    ),
                    "cover_mismatch_url_found": book.get(
                        "cover_mismatch_url_found", ""
                    ),
                }
            )
        return result

    def clear_cover_mismatch(self, livre_id: str) -> bool:
        """Supprime cover_mismatch_page_title du livre (cas traité manuellement).

        Args:
            livre_id: ID du livre MongoDB (string hex)

        Returns:
            True si succès, False sinon
        """
        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")
        livres_collection = self.mongodb_service.db["livres"]

        try:
            livre_oid = ObjectId(livre_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId format: {livre_id} - {e}")
            return False

        result = livres_collection.update_one(
            {"_id": livre_oid},
            {
                "$unset": {"cover_mismatch_page_title": ""},
                "$set": {"updated_at": datetime.now(UTC)},
            },
        )

        if result.matched_count == 0:
            logger.error(f"Livre {livre_id} non trouvé dans MongoDB")
            return False

        logger.info(f"✅ Cover mismatch effacé pour livre {livre_id}")
        return True

    def get_problematic_cases(self) -> list[dict[str, Any]]:
        """Récupère la liste des cas problématiques depuis MongoDB.

        Exclut les livres qui ont déjà été marqués avec babelio_not_found=true
        ou qui ont déjà une url_babelio (déjà résolus).

        Groupe les entrées livre + auteur lorsque les deux sont problématiques.

        Returns:
            Liste des cas problématiques non résolus (avec groupement livre+auteur)
        """
        cases: list[dict[str, Any]] = []

        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")

        problematic_collection = self.mongodb_service.db["babelio_problematic_cases"]
        livres_collection = self.mongodb_service.db["livres"]

        # Récupérer tous les cas problématiques depuis MongoDB
        all_cases = list(problematic_collection.find())

        # Créer un index des cas auteur par auteur_id pour lookup rapide
        auteur_cases_index: dict[str, dict[str, Any]] = {}
        for case in all_cases:
            if case.get("type") == "auteur":
                auteur_id = case.get("auteur_id")
                if auteur_id:
                    auteur_cases_index[auteur_id] = case

        # Traiter les cas livre et auteur
        grouped_auteur_ids: set[str] = set()  # Track auteurs déjà groupés

        for case in all_cases:
            case_type = case.get("type")

            # Traiter les cas livre
            if case_type == "livre":
                livre_id = case.get("livre_id")
                livre = None
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

                # Vérifier si l'auteur est aussi problématique
                # IMPORTANT: Récupérer auteur_id depuis le document livre, pas depuis le cas
                auteur_id = None
                if livre and livre.get("auteur_id"):
                    auteur_id = str(livre["auteur_id"])

                if auteur_id and auteur_id in auteur_cases_index:
                    # Grouper livre + auteur
                    auteur_case = auteur_cases_index[auteur_id]
                    grouped_case = self._create_grouped_case(case, auteur_case)
                    cases.append(grouped_case)
                    grouped_auteur_ids.add(auteur_id)
                else:
                    # Cas livre seul (pas de groupement)
                    serializable_case = self._serialize_case(case)
                    cases.append(serializable_case)

            # Traiter les cas auteur (uniquement si non groupés)
            elif case_type == "auteur":
                auteur_id = case.get("auteur_id")
                if auteur_id and auteur_id not in grouped_auteur_ids:
                    # Auteur problématique sans livre problématique associé
                    serializable_case = self._serialize_case(case)
                    cases.append(serializable_case)

        # Trier: livres groupés d'abord, puis livres seuls, puis auteurs
        def sort_key(c: dict[str, Any]) -> tuple[int, str]:
            case_type = c.get("type", "")
            if case_type == "livre_auteur_groupe":
                return (0, case_type)
            if case_type == "livre":
                return (1, case_type)
            return (2, case_type)

        cases.sort(key=sort_key)

        return cases

    def _serialize_case(self, case: dict[str, Any]) -> dict[str, Any]:
        """Sérialise un cas en convertissant ObjectId et datetime en strings.

        Args:
            case: Cas problématique brut depuis MongoDB

        Returns:
            Cas sérialisé pour JSON/FastAPI
        """
        serializable_case = {}
        for key, value in case.items():
            if isinstance(value, ObjectId):
                serializable_case[key] = str(value)
            elif isinstance(value, datetime):
                serializable_case[key] = value.isoformat()
            else:
                serializable_case[key] = value
        return serializable_case

    def _create_grouped_case(
        self, livre_case: dict[str, Any], auteur_case: dict[str, Any]
    ) -> dict[str, Any]:
        """Crée un cas groupé livre + auteur.

        Args:
            livre_case: Cas problématique du livre
            auteur_case: Cas problématique de l'auteur

        Returns:
            Cas groupé avec type "livre_auteur_groupe"
        """
        # Sérialiser les deux cas
        livre_serialized = self._serialize_case(livre_case)
        auteur_serialized = self._serialize_case(auteur_case)

        # Créer le cas groupé avec les informations combinées
        grouped = {
            "type": "livre_auteur_groupe",
            "livre_id": livre_serialized.get("livre_id"),
            "auteur_id": auteur_serialized.get("auteur_id"),
            "titre_attendu": livre_serialized.get("titre_attendu"),
            "nom_auteur": auteur_serialized.get("nom_auteur"),
            "auteur": livre_serialized.get("auteur"),  # Pour compatibilité
            "raison": livre_serialized.get("raison"),  # Raison du livre
            "raison_auteur": auteur_serialized.get("raison"),  # Raison de l'auteur
            "url_babelio": livre_serialized.get("url_babelio", "N/A"),
            "timestamp": livre_serialized.get("timestamp"),
            "_id": livre_serialized.get("_id"),  # Garder l'ID du livre
        }

        return grouped

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
                # Ne pas écraser si l'auteur a déjà une URL valide
                # IMPORTANT: Matcher aussi url_babelio: None (pas seulement $exists: False)
                result = auteurs_collection.update_one(
                    {
                        "_id": auteur_id,
                        "$or": [
                            {"url_babelio": {"$exists": False}},
                            {"url_babelio": None},
                        ],
                    },
                    {
                        "$set": {
                            "url_babelio": babelio_author_url,
                            "updated_at": datetime.now(UTC),
                        }
                    },
                )

                # Si l'auteur a été mis à jour, retirer aussi de problematic_cases
                if result.matched_count > 0:
                    problematic_collection = self.mongodb_service.db[
                        "babelio_problematic_cases"
                    ]
                    problematic_collection.delete_one({"auteur_id": str(auteur_id)})

        # Retirer de la collection MongoDB babelio_problematic_cases
        problematic_collection = self.mongodb_service.db["babelio_problematic_cases"]
        problematic_collection.delete_one({"livre_id": livre_id})

        logger.info(f"✅ Suggestion acceptée pour livre {livre_id}: {babelio_url}")
        return True

    def mark_as_not_found(
        self, item_id: str, reason: str, item_type: str = "livre"
    ) -> bool:
        """Marque un livre ou auteur comme non trouvé sur Babelio.

        Args:
            item_id: ID du livre ou auteur MongoDB (string hex)
            reason: Raison du not found
            item_type: Type d'item ('livre' ou 'auteur')

        Returns:
            True si succès, False sinon
        """
        if self.mongodb_service.db is None:
            raise RuntimeError("MongoDB not connected")

        # Convertir item_id en ObjectId
        try:
            item_oid = ObjectId(item_id)
        except Exception as e:
            logger.error(f"Invalid ObjectId format: {item_id} - {e}")
            return False

        # Déterminer la collection à mettre à jour
        if item_type == "livre":
            collection = self.mongodb_service.db["livres"]
            problematic_key = "livre_id"
            log_label = "Livre"
        elif item_type == "auteur":
            collection = self.mongodb_service.db["auteurs"]
            problematic_key = "auteur_id"
            log_label = "Auteur"
        else:
            logger.error(f"Type invalide: {item_type}. Doit être 'livre' ou 'auteur'.")
            return False

        result = collection.update_one(
            {"_id": item_oid},
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
            logger.error(f"{log_label} {item_id} non trouvé dans MongoDB")
            return False

        # Retirer de la collection MongoDB babelio_problematic_cases
        problematic_collection = self.mongodb_service.db["babelio_problematic_cases"]
        problematic_collection.delete_one({problematic_key: item_id})

        logger.info(f"❌ {log_label} {item_id} marqué comme not found: {reason}")
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

    async def extract_from_babelio_url(
        self,
        babelio_url: str,
        babelio_cookies: str | None = None,
    ) -> dict[str, Any]:
        """Extrait les données depuis une URL Babelio sans mise à jour (Issue #159).

        Args:
            babelio_url: URL Babelio complète
            babelio_cookies: Valeur du header Cookie copiée depuis les DevTools du
                navigateur sur babelio.com. Permet de contourner le captcha Babelio
                (Issue #245).

        Returns:
            Dict avec les données extraites (titre, auteur, editeur, url_livre, url_auteur)

        Raises:
            ValueError: Si l'URL n'est pas valide
            Exception: En cas d'erreur de scraping
        """
        # Valider l'URL Babelio
        if not babelio_url or "babelio.com" not in babelio_url.lower():
            raise ValueError("URL invalide: doit être une URL Babelio")

        # Scraper les données de la page livre (toutes les méthodes sont async)
        titre = await self.babelio_service.fetch_full_title_from_url(
            babelio_url, babelio_cookies=babelio_cookies
        )
        auteur_url = await self.babelio_service.fetch_author_url_from_page(
            babelio_url, babelio_cookies=babelio_cookies
        )
        editeur = await self.babelio_service.fetch_publisher_from_url(
            babelio_url, babelio_cookies=babelio_cookies
        )

        # Extraire le nom de l'auteur depuis son URL
        auteur = None
        if auteur_url:
            auteur = await self.babelio_service._scrape_author_from_book_page(
                babelio_url, babelio_cookies=babelio_cookies
            )

        return {
            "titre": titre,
            "auteur": auteur,
            "editeur": editeur,
            "url_livre": babelio_url,
            "url_auteur": auteur_url,
        }

    async def update_from_babelio_url(
        self, item_id: str, babelio_url: str, item_type: str = "livre"
    ) -> dict[str, Any]:
        """Met à jour un livre/auteur depuis une URL Babelio manuelle.

        Scrape la page Babelio et réutilise la logique existante (accept_suggestion).

        Args:
            item_id: ID du livre ou auteur MongoDB
            babelio_url: URL Babelio complète
            item_type: Type d'item ('livre' ou 'auteur')

        Returns:
            Dict avec success, scraped_data, ou error
        """
        if self.mongodb_service.db is None:
            return {"success": False, "error": "MongoDB not connected"}

        # Valider l'URL Babelio
        if not babelio_url or "babelio.com" not in babelio_url.lower():
            return {
                "success": False,
                "error": "URL invalide: doit être une URL Babelio",
            }

        try:
            if item_type == "livre":
                # Scraper les données de la page livre
                titre = await self.babelio_service.fetch_full_title_from_url(
                    babelio_url
                )
                auteur_url = await self.babelio_service.fetch_author_url_from_page(
                    babelio_url
                )

                if not titre:
                    return {
                        "success": False,
                        "error": "Impossible de scraper le titre depuis l'URL",
                    }

                # Réutiliser accept_suggestion pour la mise à jour
                success = self.accept_suggestion(
                    livre_id=item_id,
                    babelio_url=babelio_url,
                    babelio_author_url=auteur_url,
                    corrected_title=titre,
                )

                if success:
                    return {
                        "success": True,
                        "scraped_data": {
                            "titre": titre,
                            "url_babelio": babelio_url,
                            "auteur_url_babelio": auteur_url,
                        },
                    }
                return {"success": False, "error": "Échec de la mise à jour"}

            if item_type == "auteur":
                # Pour un auteur, mise à jour simple de l'URL
                auteurs_collection = self.mongodb_service.db["auteurs"]
                try:
                    auteur_oid = ObjectId(item_id)
                except Exception as e:
                    return {"success": False, "error": f"ID invalide: {e}"}

                auteur = auteurs_collection.find_one({"_id": auteur_oid})
                if not auteur:
                    return {"success": False, "error": "Auteur non trouvé dans MongoDB"}

                # Mise à jour de l'auteur
                auteurs_collection.update_one(
                    {"_id": auteur_oid},
                    {
                        "$set": {
                            "url_babelio": babelio_url,
                            "updated_at": datetime.now(UTC),
                        }
                    },
                )

                # Retirer de problematic_cases
                problematic_collection = self.mongodb_service.db[
                    "babelio_problematic_cases"
                ]
                problematic_collection.delete_one({"auteur_id": item_id})

                logger.info(f"✅ Auteur {item_id} mis à jour depuis URL: {babelio_url}")
                return {
                    "success": True,
                    "scraped_data": {
                        "nom": auteur.get("nom", ""),
                        "url_babelio": babelio_url,
                    },
                }

            return {"success": False, "error": f"Type invalide: {item_type}"}

        except Exception as e:
            logger.error(f"Erreur update_from_babelio_url pour {item_id}: {e}")
            return {"success": False, "error": str(e)}
