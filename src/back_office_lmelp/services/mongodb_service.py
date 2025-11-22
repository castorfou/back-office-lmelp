"""Service MongoDB pour la gestion des épisodes."""

import os
from datetime import datetime
from typing import Any

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


load_dotenv()


class MongoDBService:
    """Service pour interagir avec la base MongoDB."""

    def __init__(self) -> None:
        """Initialise la connexion MongoDB."""
        self.mongo_url = os.getenv(
            "MONGODB_URL", "mongodb://localhost:27017/masque_et_la_plume"
        )
        self.client: MongoClient | None = None
        self.db: Database | None = None
        self.episodes_collection: Collection | None = None
        self.avis_critiques_collection: Collection | None = None
        self.auteurs_collection: Collection | None = None
        self.livres_collection: Collection | None = None
        self.editeurs_collection: Collection | None = None

    def connect(self) -> bool:
        """Établit la connexion à MongoDB."""
        try:
            self.client = MongoClient(self.mongo_url)
            # Test de connexion
            self.client.admin.command("ping")
            self.db = self.client.get_default_database()
            self.episodes_collection = self.db.episodes
            self.avis_critiques_collection = self.db.avis_critiques
            self.auteurs_collection = self.db.auteurs
            self.livres_collection = self.db.livres
            self.editeurs_collection = self.db.editeurs
            return True
        except Exception as e:
            print(f"Erreur de connexion MongoDB: {e}")
            # Clean up on connection failure
            self.client = None
            self.db = None
            self.episodes_collection = None
            self.avis_critiques_collection = None
            self.auteurs_collection = None
            self.livres_collection = None
            self.editeurs_collection = None
            return False

    def disconnect(self) -> None:
        """Ferme la connexion MongoDB."""
        if self.client:
            self.client.close()

    def get_collection(self, collection_name: str) -> Collection:
        """Récupère une collection MongoDB par son nom."""
        if self.db is None:
            raise Exception("Connexion MongoDB non établie")
        return self.db[collection_name]

    def get_all_episodes(self, include_masked: bool = False) -> list[dict[str, Any]]:
        """Récupère tous les épisodes avec tri par date décroissante.

        Args:
            include_masked: Si False (défaut), exclut les épisodes masqués.
                          Si True, inclut tous les épisodes.

        Returns:
            Liste des épisodes
        """
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Issue #107: Filtrer les épisodes masqués par défaut
            query_filter: dict[str, Any] = {}
            if not include_masked:
                query_filter["masked"] = {"$ne": True}

            episodes = list(
                self.episodes_collection.find(
                    query_filter,
                    {
                        "titre": 1,
                        "titre_corrige": 1,
                        "date": 1,
                        "type": 1,
                        "duree": 1,
                        "masked": 1,
                        "_id": 1,
                    },
                ).sort([("date", -1)])
            )

            # Conversion ObjectId en string pour JSON
            for episode in episodes:
                episode["_id"] = str(episode["_id"])

            return episodes
        except Exception as e:
            print(f"Erreur lors de la récupération des épisodes: {e}")
            return []

    def get_episode_by_id(self, episode_id: str) -> dict[str, Any] | None:
        """Récupère un épisode par son ID."""
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            episode = self.episodes_collection.find_one({"_id": ObjectId(episode_id)})
            if episode:
                # Cast pour satisfaire MyPy
                episode_dict: dict[str, Any] = dict(episode)
                episode_dict["_id"] = str(episode_dict["_id"])
                return episode_dict
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération de l'épisode {episode_id}: {e}")
            return None

    def delete_episode(self, episode_id: str) -> bool:
        """Supprime un épisode et toutes ses données associées.

        Effectue les opérations suivantes :
        1. Supprime les avis critiques liés à l'épisode
        2. Retire les références à l'épisode des livres
        3. Supprime l'épisode lui-même

        Args:
            episode_id: L'ID de l'épisode à supprimer (chaîne ObjectId)

        Returns:
            True si la suppression a réussi, False si l'épisode n'existe pas

        Raises:
            Exception: Si la connexion MongoDB n'est pas établie ou si l'ObjectId est invalide
        """
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")
        if self.avis_critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")
        if self.livres_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Convertir en ObjectId (peut lever bson.errors.InvalidId)
            episode_oid = ObjectId(episode_id)

            # 1. Supprimer les avis critiques liés (episode_oid est stocké comme string)
            avis_delete_result = self.avis_critiques_collection.delete_many(
                {"episode_oid": episode_id}
            )
            print(
                f"Suppression de {avis_delete_result.deleted_count} avis critiques pour l'épisode {episode_id}"
            )

            # 2. Retirer les références à l'épisode des livres (episodes est un tableau de strings)
            livres_update_result = self.livres_collection.update_many(
                {"episodes": episode_id}, {"$pull": {"episodes": episode_id}}
            )
            print(
                f"Mise à jour de {livres_update_result.modified_count} livres pour retirer l'épisode {episode_id}"
            )

            # 3. Supprimer l'épisode lui-même
            episode_delete_result = self.episodes_collection.delete_one(
                {"_id": episode_oid}
            )

            if episode_delete_result.deleted_count == 0:
                print(f"Épisode {episode_id} non trouvé")
                return False

            print(f"Épisode {episode_id} supprimé avec succès")
            return True

        except Exception as e:
            print(f"Erreur lors de la suppression de l'épisode {episode_id}: {e}")
            raise

    def update_episode_description(
        self, episode_id: str, description_corrigee: str
    ) -> bool:
        """Met à jour la description corrigée d'un épisode."""
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            result = self.episodes_collection.update_one(
                {"_id": ObjectId(episode_id)},
                {"$set": {"description_corrigee": description_corrigee}},
            )
            return bool(result.modified_count > 0)
        except Exception as e:
            print(f"Erreur lors de la mise à jour de l'épisode {episode_id}: {e}")
            return False

    def update_episode(self, episode_id: str, update_data: dict[str, Any]) -> bool:
        """Met à jour un épisode avec les champs fournis.

        Args:
            episode_id: ID de l'épisode à mettre à jour
            update_data: Dictionnaire des champs à mettre à jour

        Returns:
            True si la mise à jour a réussi, False sinon
        """
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            result = self.episodes_collection.update_one(
                {"_id": ObjectId(episode_id)},
                {"$set": update_data},
            )
            return bool(result.modified_count > 0 or result.matched_count > 0)
        except Exception as e:
            print(f"Erreur lors de la mise à jour de l'épisode {episode_id}: {e}")
            return False

    def update_episode_title(self, episode_id: str, titre_corrige: str) -> bool:
        """Met à jour le titre corrigé d'un épisode."""
        return self.update_episode(episode_id, {"titre_corrige": titre_corrige})

    def update_episode_masked_status(self, episode_id: str, masked: bool) -> bool:
        """Met à jour le statut masked d'un épisode (Issue #107).

        Cette méthode est idempotente : elle retourne True si l'épisode existe,
        même s'il est déjà dans l'état demandé (principe REST).

        Args:
            episode_id: ID de l'épisode
            masked: True pour masquer, False pour afficher

        Returns:
            True si l'épisode existe (même si déjà dans l'état voulu), False sinon
        """
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            result = self.episodes_collection.update_one(
                {"_id": ObjectId(episode_id)},
                {"$set": {"masked": masked}},
            )
            # Utilise matched_count au lieu de modified_count pour l'idempotence
            return bool(result.matched_count > 0)
        except Exception as e:
            print(
                f"Erreur lors de la mise à jour du statut masked de l'épisode {episode_id}: {e}"
            )
            return False

    def insert_episode(self, episode_data: dict[str, Any]) -> str:
        """Insère un nouvel épisode."""
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            result = self.episodes_collection.insert_one(episode_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Erreur lors de l'insertion de l'épisode: {e}")
            raise

    def get_all_critical_reviews(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Récupère tous les avis critiques avec tri par date de création décroissante."""
        if self.avis_critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            query = self.avis_critiques_collection.find({}).sort("created_at", -1)

            if limit:
                query = query.limit(limit)

            avis_critiques = list(query)

            # Conversion ObjectId en string pour JSON
            for avis in avis_critiques:
                avis["_id"] = str(avis["_id"])

            return avis_critiques
        except Exception as e:
            print(f"Erreur lors de la récupération des avis critiques: {e}")
            return []

    def get_critical_reviews_by_episode_oid(
        self, episode_oid: str
    ) -> list[dict[str, Any]]:
        """Récupère les avis critiques pour un épisode spécifique."""
        if self.avis_critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            avis_critiques = list(
                self.avis_critiques_collection.find({"episode_oid": episode_oid}).sort(
                    "created_at", -1
                )
            )

            # Conversion ObjectId en string pour JSON
            for avis in avis_critiques:
                avis["_id"] = str(avis["_id"])

            return avis_critiques
        except Exception as e:
            print(
                f"Erreur lors de la récupération des avis critiques pour l'épisode {episode_oid}: {e}"
            )
            return []

    def get_avis_critique_by_id(self, avis_critique_id: str) -> dict[str, Any] | None:
        """
        Récupère un avis critique par son ID.

        Args:
            avis_critique_id: ID de l'avis critique (ObjectId ou string)

        Returns:
            Dictionnaire de l'avis critique ou None si non trouvé
        """
        if self.avis_critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            from bson import ObjectId

            # Convertir en ObjectId
            oid = ObjectId(avis_critique_id)

            avis = self.avis_critiques_collection.find_one({"_id": oid})

            if avis:
                avis["_id"] = str(avis["_id"])
                return dict(avis)  # Type cast pour mypy
            return None
        except Exception as e:
            print(
                f"Erreur lors de la récupération de l'avis critique {avis_critique_id}: {e}"
            )
            return None

    def update_avis_critique(
        self, avis_critique_id: str, updates: dict[str, Any]
    ) -> bool:
        """
        Met à jour un avis critique.

        Args:
            avis_critique_id: ID de l'avis critique
            updates: Dictionnaire des champs à mettre à jour

        Returns:
            True si la mise à jour a réussi, False sinon
        """
        if self.avis_critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            from bson import ObjectId

            # Convertir en ObjectId
            oid = ObjectId(avis_critique_id)

            result = self.avis_critiques_collection.update_one(
                {"_id": oid}, {"$set": updates}
            )

            return bool(result.modified_count > 0 or result.matched_count > 0)
        except Exception as e:
            print(
                f"Erreur lors de la mise à jour de l'avis critique {avis_critique_id}: {e}"
            )
            return False

    def get_statistics(self) -> dict[str, Any]:
        """Récupère les statistiques de la base de données."""
        if self.episodes_collection is None or self.avis_critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Total des épisodes
            total_episodes = self.episodes_collection.count_documents({})

            # Épisodes avec titres corrigés (maintenant dans titre_origin)
            episodes_with_corrected_titles = self.episodes_collection.count_documents(
                {"titre_origin": {"$ne": None, "$exists": True}}
            )

            # Épisodes avec descriptions corrigées (maintenant dans description_origin)
            episodes_with_corrected_descriptions = (
                self.episodes_collection.count_documents(
                    {"description_origin": {"$ne": None, "$exists": True}}
                )
            )

            # Nombre total d'avis critiques
            critical_reviews_count = self.avis_critiques_collection.count_documents({})

            # Dernière date de mise à jour (basée sur l'épisode le plus récent)
            # Utilisation de l'aggregation pour trouver la plus récente date
            pipeline: list[dict[str, Any]] = [
                {"$sort": {"date": -1}},
                {"$limit": 1},
                {"$project": {"date": 1}},
            ]

            last_update_result = list(self.episodes_collection.aggregate(pipeline))
            last_update_date = None
            if last_update_result:
                date_obj = last_update_result[0].get("date")
                if date_obj:
                    # Convertir en format ISO string pour JSON
                    last_update_date = (
                        date_obj.isoformat()
                        if hasattr(date_obj, "isoformat")
                        else str(date_obj)
                    )

            return {
                "total_episodes": total_episodes,
                "episodes_with_corrected_titles": episodes_with_corrected_titles,
                "episodes_with_corrected_descriptions": episodes_with_corrected_descriptions,
                "critical_reviews_count": critical_reviews_count,
                "last_update_date": last_update_date,
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des statistiques: {e}")
            raise

    def search_episodes(
        self, query: str, limit: int = 10, offset: int = 0
    ) -> dict[str, Any]:
        """Recherche textuelle dans les épisodes."""
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        if not query or len(query.strip()) == 0:
            return {"episodes": [], "total_count": 0}

        try:
            # Recherche simple avec regex pour insensibilité à la casse uniquement
            query_escaped = query.strip()

            # Recherche dans les champs titre, description et transcription
            search_query = {
                "$or": [
                    {"titre": {"$regex": query_escaped, "$options": "i"}},
                    {"titre_corrige": {"$regex": query_escaped, "$options": "i"}},
                    {"description": {"$regex": query_escaped, "$options": "i"}},
                    {
                        "description_corrigee": {
                            "$regex": query_escaped,
                            "$options": "i",
                        }
                    },
                    {"transcription": {"$regex": query_escaped, "$options": "i"}},
                ]
            }

            # Compter le nombre total de résultats
            total_count = self.episodes_collection.count_documents(search_query)

            # Récupérer les résultats avec skip et limit
            episodes = list(
                self.episodes_collection.find(search_query)
                .sort([("date", -1)])
                .skip(offset)
                .limit(limit)
            )

            # Conversion ObjectId simple - score minimal pour compatibility frontend
            results = []
            for episode in episodes:
                episode["_id"] = str(episode["_id"])

                # Assigner un score minimal (MongoDB a trouvé l'épisode donc il est pertinent)
                episode["score"] = 1.0
                episode["match_type"] = "found"

                # Extraire le contexte de recherche
                episode["search_context"] = self._extract_search_context(query, episode)

                results.append(episode)

            return {"episodes": results, "total_count": total_count}
        except Exception as e:
            print(f"Erreur lors de la recherche d'épisodes: {e}")
            return {"episodes": [], "total_count": 0}

    def search_critical_reviews_for_authors_books(
        self, query: str, limit: int = 10
    ) -> dict[str, list[dict[str, Any]]]:
        """Recherche textuelle dans les avis critiques pour auteurs, livres et éditeurs."""
        if self.avis_critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")

        if not query or len(query.strip()) == 0:
            return {"auteurs": [], "livres": [], "editeurs": []}

        try:
            query_escaped = query.strip()

            # Recherche dans les avis critiques
            search_query = {
                "$or": [
                    {"auteur": {"$regex": query_escaped, "$options": "i"}},
                    {"titre_livre": {"$regex": query_escaped, "$options": "i"}},
                    {"editeur": {"$regex": query_escaped, "$options": "i"}},
                ]
            }

            reviews = list(
                self.avis_critiques_collection.find(search_query).limit(limit * 3)
            )

            # Séparer par catégories et dédupliquer
            auteurs_set = set()
            livres_set = set()
            editeurs_set = set()

            for review in reviews:
                review["_id"] = str(review["_id"])

                # Auteurs
                if review.get("auteur"):
                    auteurs_set.add(review["auteur"])

                # Livres
                if review.get("titre_livre"):
                    livres_set.add(review["titre_livre"])

                # Éditeurs
                if review.get("editeur"):
                    editeurs_set.add(review["editeur"])

            # Convertir en listes simples (pas de score)
            auteurs = [{"nom": nom} for nom in sorted(auteurs_set)][:limit]
            livres = [{"titre": titre} for titre in sorted(livres_set)][:limit]
            editeurs = [{"nom": nom} for nom in sorted(editeurs_set)][:limit]

            return {
                "auteurs": auteurs,
                "livres": livres,
                "editeurs": editeurs,
            }

        except Exception as e:
            print(f"Erreur lors de la recherche dans les avis critiques: {e}")
            return {"auteurs": [], "livres": [], "editeurs": []}

    def search_auteurs(
        self, query: str, limit: int = 10, offset: int = 0
    ) -> dict[str, Any]:
        """Recherche textuelle insensible aux accents dans la collection auteurs.

        Args:
            query: Terme de recherche (ex: "carrere" trouvera "Carrère")
            limit: Nombre maximum de résultats à retourner
            offset: Offset pour la pagination

        Returns:
            Dict avec clés "auteurs" (liste de résultats) et "total_count"
        """
        if self.auteurs_collection is None:
            raise Exception("Connexion MongoDB non établie")

        if not query or len(query.strip()) == 0:
            return {"auteurs": [], "total_count": 0}

        try:
            from ..utils.text_utils import create_accent_insensitive_regex

            query_stripped = query.strip()

            # Créer un regex insensible aux accents (Issue #92)
            regex_pattern = create_accent_insensitive_regex(query_stripped)

            # Recherche dans le champ nom avec regex insensible aux accents
            search_query = {"nom": {"$regex": regex_pattern, "$options": "i"}}

            # Compter le nombre total de résultats
            total_count = self.auteurs_collection.count_documents(search_query)

            # Récupérer les résultats avec skip et limit
            auteurs = list(
                self.auteurs_collection.find(search_query).skip(offset).limit(limit)
            )

            # Conversion ObjectId en string
            results = []
            for auteur in auteurs:
                auteur["_id"] = str(auteur["_id"])
                results.append(auteur)

            return {"auteurs": results, "total_count": total_count}
        except Exception as e:
            print(f"Erreur lors de la recherche d'auteurs: {e}")
            return {"auteurs": [], "total_count": 0}

    def search_livres(
        self, query: str, limit: int = 10, offset: int = 0
    ) -> dict[str, Any]:
        """Recherche textuelle insensible aux accents dans la collection livres.

        Args:
            query: Terme de recherche (ex: "emonet" trouvera "Émonet")
            limit: Nombre maximum de résultats à retourner
            offset: Offset pour la pagination

        Returns:
            Dict avec clés "livres" (liste de résultats) et "total_count"
        """
        if self.livres_collection is None:
            raise Exception("Connexion MongoDB non établie")

        if not query or len(query.strip()) == 0:
            return {"livres": [], "total_count": 0}

        try:
            from ..utils.text_utils import create_accent_insensitive_regex

            query_stripped = query.strip()

            # Créer un regex insensible aux accents (Issue #92)
            regex_pattern = create_accent_insensitive_regex(query_stripped)

            # Recherche uniquement dans le champ titre avec regex insensible aux accents
            search_query = {"titre": {"$regex": regex_pattern, "$options": "i"}}

            # Compter le nombre total de résultats
            total_count = self.livres_collection.count_documents(search_query)

            # Récupérer les résultats avec skip et limit
            livres = list(
                self.livres_collection.find(search_query).skip(offset).limit(limit)
            )

            # Conversion ObjectId en string et enrichissement avec nom auteur
            results = []
            for livre in livres:
                livre["_id"] = str(livre["_id"])

                # Récupérer le nom de l'auteur si auteur_id existe
                if (
                    "auteur_id" in livre
                    and livre["auteur_id"]
                    and self.auteurs_collection is not None
                ):
                    try:
                        auteur = self.auteurs_collection.find_one(
                            {"_id": livre["auteur_id"]}
                        )
                        if auteur:
                            livre["auteur_nom"] = auteur.get("nom", "")
                    except Exception:
                        livre["auteur_nom"] = ""

                    # Convertir auteur_id en string
                    livre["auteur_id"] = str(livre["auteur_id"])

                results.append(livre)

            return {"livres": results, "total_count": total_count}
        except Exception as e:
            print(f"Erreur lors de la recherche de livres: {e}")
            return {"livres": [], "total_count": 0}

    def get_auteur_with_livres(self, auteur_id: str) -> dict[str, Any] | None:
        """Récupère un auteur avec la liste de ses livres (Issue #96 - Phase 1).

        Args:
            auteur_id: ID de l'auteur (MongoDB ObjectId en string)

        Returns:
            Dict avec auteur_id, nom, nombre_oeuvres, et livres (triés alphabétiquement)
            None si l'auteur n'existe pas
        """
        if self.auteurs_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Agrégation MongoDB pour joindre l'auteur avec ses livres
            pipeline: list[dict[str, Any]] = [
                # Match l'auteur par ID
                {"$match": {"_id": ObjectId(auteur_id)}},
                # Lookup pour récupérer les livres de cet auteur
                {
                    "$lookup": {
                        "from": "livres",
                        "localField": "_id",
                        "foreignField": "auteur_id",
                        "as": "livres",
                    }
                },
                # Projection pour formater les données
                {
                    "$project": {
                        "_id": 1,
                        "nom": 1,
                        "livres": {
                            "_id": 1,
                            "titre": 1,
                            "editeur": 1,
                        },
                    }
                },
            ]

            result = list(self.auteurs_collection.aggregate(pipeline))

            if not result:
                return None

            auteur_data = result[0]

            # Trier les livres par ordre alphabétique du titre
            livres = sorted(auteur_data.get("livres", []), key=lambda x: x["titre"])

            # Formater les livres pour le frontend
            livres_formatted = [
                {
                    "livre_id": str(livre["_id"]),
                    "titre": livre["titre"],
                    "editeur": livre.get("editeur", ""),
                }
                for livre in livres
            ]

            return {
                "auteur_id": str(auteur_data["_id"]),
                "nom": auteur_data["nom"],
                "nombre_oeuvres": len(livres_formatted),
                "livres": livres_formatted,
            }

        except Exception as e:
            print(f"Erreur lors de la récupération de l'auteur {auteur_id}: {e}")
            return None

    def get_livre_with_episodes(self, livre_id: str) -> dict[str, Any] | None:
        """Récupère un livre avec ses informations et la liste des épisodes (Issue #96 - Phase 2).

        Args:
            livre_id: ID du livre (MongoDB ObjectId en string)

        Returns:
            Dict avec livre_id, titre, auteur_id, auteur_nom, editeur, nombre_episodes,
            et episodes (triés par date décroissante, avec champ programme pour chaque épisode)
            None si le livre n'existe pas
        """
        if self.livres_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Agrégation MongoDB pour joindre le livre avec son auteur et ses épisodes
            pipeline: list[dict[str, Any]] = [
                # Match le livre par ID
                {"$match": {"_id": ObjectId(livre_id)}},
                # Lookup pour récupérer l'auteur
                {
                    "$lookup": {
                        "from": "auteurs",
                        "localField": "auteur_id",
                        "foreignField": "_id",
                        "as": "auteur",
                    }
                },
                # Lookup pour récupérer les épisodes
                # Les épisodes sont stockés comme un tableau de strings dans livre.episodes
                {
                    "$lookup": {
                        "from": "episodes",
                        "let": {"episode_ids": "$episodes", "livre_id": "$_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$in": [
                                            {"$toString": "$_id"},
                                            "$$episode_ids",
                                        ]
                                    }
                                }
                            },
                            # Lookup pour récupérer le champ programme depuis livresauteurs_cache
                            {
                                "$lookup": {
                                    "from": "livresauteurs_cache",
                                    "let": {"episode_oid": {"$toString": "$_id"}},
                                    "pipeline": [
                                        {
                                            "$match": {
                                                "$expr": {
                                                    "$and": [
                                                        {
                                                            "$eq": [
                                                                "$episode_oid",
                                                                "$$episode_oid",
                                                            ]
                                                        },
                                                        {
                                                            "$eq": [
                                                                "$book_id",
                                                                "$$livre_id",
                                                            ]
                                                        },
                                                    ]
                                                }
                                            }
                                        },
                                        {
                                            "$project": {
                                                "programme": 1,
                                            }
                                        },
                                    ],
                                    "as": "cache_data",
                                }
                            },
                            {
                                "$project": {
                                    "_id": 1,
                                    "titre": 1,
                                    "date": 1,
                                    "programme": {
                                        "$cond": {
                                            "if": {
                                                "$gt": [{"$size": "$cache_data"}, 0]
                                            },
                                            "then": {
                                                "$arrayElemAt": [
                                                    "$cache_data.programme",
                                                    0,
                                                ]
                                            },
                                            "else": None,
                                        }
                                    },
                                }
                            },
                        ],
                        "as": "episodes_data",
                    }
                },
                # Projection pour formater les données
                {
                    "$project": {
                        "_id": 1,
                        "titre": 1,
                        "auteur_id": 1,
                        "editeur": 1,
                        "auteur": 1,
                        "episodes_data": 1,
                    }
                },
            ]

            result = list(self.livres_collection.aggregate(pipeline))

            if not result:
                return None

            livre_data = result[0]

            # Récupérer le nom de l'auteur
            auteur_nom = ""
            if livre_data.get("auteur") and len(livre_data["auteur"]) > 0:
                auteur_nom = livre_data["auteur"][0].get("nom", "")

            # Trier les épisodes par date (plus récent d'abord)
            episodes = livre_data.get("episodes_data", [])
            episodes_sorted = sorted(
                episodes,
                key=lambda x: x.get("date", ""),
                reverse=True,
            )

            # Formater les épisodes pour le frontend
            episodes_formatted = [
                {
                    "episode_id": str(episode["_id"]),
                    "titre": episode.get("titre", ""),
                    "date": (
                        episode["date"].strftime("%Y-%m-%d")
                        if isinstance(episode.get("date"), datetime)
                        else str(episode.get("date", ""))[:10]
                    ),
                    "programme": episode.get("programme"),
                }
                for episode in episodes_sorted
            ]

            return {
                "livre_id": str(livre_data["_id"]),
                "titre": livre_data["titre"],
                "auteur_id": str(livre_data["auteur_id"]),
                "auteur_nom": auteur_nom,
                "editeur": livre_data.get("editeur", ""),
                "nombre_episodes": len(episodes_formatted),
                "episodes": episodes_formatted,
            }

        except Exception as e:
            print(f"Erreur lors de la récupération du livre {livre_id}: {e}")
            return None

    def search_editeurs(
        self, query: str, limit: int = 10, offset: int = 0
    ) -> dict[str, Any]:
        """Recherche textuelle insensible aux accents dans editeurs.nom ET livres.editeur.

        Args:
            query: Terme de recherche (ex: "flammarion")
            limit: Nombre maximum de résultats à retourner
            offset: Offset pour la pagination

        Returns:
            Dict avec clés "editeurs" (liste de résultats) et "total_count"
        """
        if self.editeurs_collection is None or self.livres_collection is None:
            raise Exception("Connexion MongoDB non établie")

        if not query or len(query.strip()) == 0:
            return {"editeurs": [], "total_count": 0}

        try:
            from ..utils.text_utils import create_accent_insensitive_regex

            query_stripped = query.strip()

            # Créer un regex insensible aux accents (Issue #92)
            regex_pattern = create_accent_insensitive_regex(query_stripped)

            search_query = {"nom": {"$regex": regex_pattern, "$options": "i"}}

            # 1. Recherche dans collection editeurs
            editeurs_from_collection = list(
                self.editeurs_collection.find(search_query).skip(offset).limit(limit)
            )

            # 2. Recherche dans livres.editeur
            livres_search_query = {
                "editeur": {"$regex": regex_pattern, "$options": "i"}
            }
            livres_with_editeur = list(
                self.livres_collection.find(livres_search_query)
                .skip(offset)
                .limit(limit)
            )

            # 3. Combiner et dédupliquer
            editeurs_set = set()
            results = []

            # Ajouter éditeurs de la collection editeurs
            for editeur in editeurs_from_collection:
                editeur["_id"] = str(editeur["_id"])
                editeur_nom = editeur.get("nom")
                if editeur_nom and editeur_nom not in editeurs_set:
                    editeurs_set.add(editeur_nom)
                    results.append(editeur)

            # Ajouter éditeurs depuis livres.editeur
            for livre in livres_with_editeur:
                editeur_nom = livre.get("editeur")
                if editeur_nom and editeur_nom not in editeurs_set:
                    editeurs_set.add(editeur_nom)
                    results.append({"nom": editeur_nom})

            # Total = nombre d'éditeurs UNIQUES après déduplication
            # (pas la somme brute des deux collections)
            total_count = len(editeurs_set)

            # Respecter la limite
            results = results[:limit]

            return {"editeurs": results, "total_count": total_count}
        except Exception as e:
            print(f"Erreur lors de la recherche d'éditeurs: {e}")
            return {"editeurs": [], "total_count": 0}

    def calculate_search_score(self, query: str, text: str) -> tuple[float, str]:
        """Calcule le score de pertinence et le type de match - STRICT: terme doit être présent."""
        if not text or not query:
            return 0.0, "none"

        query_lower = query.lower().strip()
        text_lower = text.lower().strip()

        # Match exact (insensible à la casse)
        if query_lower == text_lower:
            return 1.0, "exact"

        # Match exact partiel - LE TERME DOIT ÊTRE PRÉSENT
        if query_lower in text_lower:
            # Score basé sur la position et la longueur relative
            position = text_lower.find(query_lower)
            length_ratio = len(query_lower) / len(text_lower)

            # Bonus si le match est au début
            position_bonus = 0.1 if position == 0 else 0
            score = 0.5 + length_ratio * 0.3 + position_bonus

            return min(score, 0.9), "partial"

        # PAS de recherche floue - si le terme n'est pas présent, score = 0
        return 0.0, "none"

    def _create_fuzzy_regex_pattern(self, query: str) -> str:
        """Crée un pattern regex simple : insensible à la casse et aux accents."""
        # Échapper les caractères spéciaux regex
        import re

        escaped_query = re.escape(query.strip())

        # Permettre des variations d'accents seulement (pas de recherche floue complexe)
        variations = {
            "e": "[eéèê]",
            "a": "[aàâ]",
            "i": "[iîï]",
            "o": "[oôö]",
            "u": "[uûü]",
            "c": "[cç]",
        }

        pattern = escaped_query.lower()
        for char, variation in variations.items():
            pattern = pattern.replace(char, variation)

        return pattern

    def _calculate_episode_search_score(
        self, query: str, episode: dict[str, Any]
    ) -> tuple[float, str]:
        """Calcule le score de pertinence pour un épisode."""
        # Champs à analyser avec leurs poids
        fields_weights = {
            "titre": 0.4,
            "titre_corrige": 0.4,
            "description": 0.3,
            "description_corrigee": 0.3,
            "transcription": 0.2,
        }

        best_score = 0.0
        best_match_type = "none"

        for field, weight in fields_weights.items():
            text = episode.get(field, "")
            if text:
                score, match_type = self.calculate_search_score(query, text)
                weighted_score = score * weight

                if weighted_score > best_score:
                    best_score = weighted_score
                    best_match_type = match_type

        return best_score, best_match_type

    def _calculate_fuzzy_score(self, query: str, text: str) -> float:
        """Calcule un score de correspondance stricte (le terme doit être présent)."""
        if not text or not query:
            return 0.0

        query_lower = query.lower()
        text_lower = text.lower()

        # Le terme de recherche doit être présent dans le texte (pas juste des caractères similaires)
        if query_lower in text_lower:
            # Score basé sur la position et la longueur relative
            position = text_lower.find(query_lower)
            text_length = len(text_lower)

            # Bonus si le terme est au début
            position_bonus = max(0.1, 1.0 - (position / text_length)) * 0.3

            # Bonus selon la proportion du terme dans le texte total
            coverage = len(query_lower) / text_length
            coverage_bonus = min(1.0, coverage * 2) * 0.7

            return position_bonus + coverage_bonus

        return 0.0

    def _extract_search_context(self, query: str, episode: dict[str, Any]) -> str:
        """Extrait le contexte de recherche avec 10 mots avant et après le terme trouvé."""

        query_lower = query.lower().strip()

        # Chercher dans titre, description, transcription par ordre de priorité
        fields_to_search = [
            episode.get("titre", ""),
            episode.get("description", ""),
            episode.get("transcription", ""),
        ]

        for text in fields_to_search:
            if not text or not isinstance(text, str):
                continue

            text_lower = text.lower()

            # Vérifier si le terme est présent
            if query_lower in text_lower:
                # Trouver la position du terme
                pos = text_lower.find(query_lower)

                # Diviser en mots
                words = text.split()

                # Trouver l'index du mot contenant le terme
                char_count = 0
                word_index = -1

                for i, word in enumerate(words):
                    word_end = char_count + len(word)
                    if char_count <= pos < word_end:
                        word_index = i
                        break
                    char_count += len(word) + 1  # +1 pour l'espace

                if word_index >= 0:
                    # Extraire 10 mots avant et après
                    start_word = max(0, word_index - 10)
                    end_word = min(len(words), word_index + 11)

                    context_words = words[start_word:end_word]
                    context = " ".join(context_words)

                    # Ajouter des ellipses si nécessaire
                    if start_word > 0:
                        context = "..." + context
                    if end_word < len(words):
                        context = context + "..."

                    return context

        return ""

    def _fuzzy_match_simple(self, query: str, word: str) -> bool:
        """Correspondance floue simple pour l'extraction de contexte."""
        if len(query) < 3 or len(word) < 3:
            return False

        # Compter les caractères communs dans l'ordre
        query_chars = list(query)
        word_chars = list(word)

        matches = 0
        query_idx = 0

        for char in word_chars:
            if query_idx < len(query_chars) and char == query_chars[query_idx]:
                matches += 1
                query_idx += 1

        # Correspondance si au moins 60% des caractères sont trouvés
        return matches >= len(query) * 0.6

    def update_episode_title_new(self, episode_id: str, titre_corrige: str) -> bool:
        """Met à jour le titre avec la nouvelle logique (titre_origin)."""
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Récupérer l'épisode existant pour sauvegarder l'original
            existing_episode = self.episodes_collection.find_one(
                {"_id": ObjectId(episode_id)}
            )

            if not existing_episode:
                return False

            # Préparer les données à mettre à jour
            update_data = {"titre": titre_corrige}

            # Sauvegarder l'original seulement s'il n'existe pas déjà
            if (
                "titre_origin" not in existing_episode
                or existing_episode["titre_origin"] is None
            ):
                update_data["titre_origin"] = existing_episode.get("titre")

            # Effectuer la mise à jour
            result = self.episodes_collection.update_one(
                {"_id": ObjectId(episode_id)},
                {"$set": update_data},
            )
            return bool(result.modified_count > 0)
        except Exception as e:
            print(f"Erreur lors de la mise à jour du titre {episode_id}: {e}")
            return False

    def update_episode_description_new(
        self, episode_id: str, description_corrigee: str
    ) -> bool:
        """Met à jour la description avec la nouvelle logique (description_origin)."""
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Récupérer l'épisode existant pour sauvegarder l'original
            existing_episode = self.episodes_collection.find_one(
                {"_id": ObjectId(episode_id)}
            )

            if not existing_episode:
                return False

            # Préparer les données à mettre à jour
            update_data = {"description": description_corrigee}

            # Sauvegarder l'original seulement s'il n'existe pas déjà
            if (
                "description_origin" not in existing_episode
                or existing_episode["description_origin"] is None
            ):
                update_data["description_origin"] = existing_episode.get("description")

            # Effectuer la mise à jour
            result = self.episodes_collection.update_one(
                {"_id": ObjectId(episode_id)},
                {"$set": update_data},
            )
            return bool(result.modified_count > 0)
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la description {episode_id}: {e}")
            return False

    # Nouvelles méthodes pour la gestion des collections auteurs/livres (Issue #66)

    def get_untreated_episodes_count(self) -> int:
        """Récupère le nombre d'épisodes non-traités (avec au moins un livre pas en base)."""
        # TODO: Implémenter la logique pour identifier les épisodes non-traités
        # Pour l'instant, retourner une valeur mockée pour les tests
        return 0

    def get_books_in_collections_count(self) -> int:
        """Récupère le nombre de couples auteur-livre en base."""
        if self.livres_collection is None:
            raise Exception("Connexion MongoDB non établie")
        try:
            return int(self.livres_collection.count_documents({}))
        except Exception as e:
            print(f"Erreur lors du comptage des livres: {e}")
            return 0

    def create_author_if_not_exists(self, nom: str) -> ObjectId:
        """Crée un auteur s'il n'existe pas déjà."""
        if self.auteurs_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Vérifier si l'auteur existe déjà
            existing_author = self.auteurs_collection.find_one({"nom": nom})
            if existing_author:
                return ObjectId(existing_author["_id"])

            # Créer le nouvel auteur
            from ..models.author import Author

            author_data = Author.for_mongodb_insert({"nom": nom})
            result = self.auteurs_collection.insert_one(author_data)
            return ObjectId(result.inserted_id)

        except Exception as e:
            print(f"Erreur lors de la création de l'auteur {nom}: {e}")
            raise

    def _add_book_to_author(self, author_id: ObjectId, book_id: ObjectId) -> None:
        """Ajoute la référence d'un livre au tableau livres[] de l'auteur."""
        if self.auteurs_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Utiliser $addToSet pour éviter les doublons
            self.auteurs_collection.update_one(
                {"_id": author_id},
                {
                    "$addToSet": {"livres": str(book_id)},
                    "$set": {"updated_at": datetime.now()},
                },
            )
        except Exception as e:
            print(
                f"Erreur lors de la mise à jour de l'auteur {author_id} avec le livre {book_id}: {e}"
            )
            # Ne pas raise pour ne pas bloquer la création du livre

    def create_book_if_not_exists(self, book_data: dict[str, Any]) -> ObjectId:
        """Crée un livre s'il n'existe pas déjà."""
        if self.livres_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Vérifier si le livre existe déjà (même titre + même auteur)
            existing_book = self.livres_collection.find_one(
                {"titre": book_data["titre"], "auteur_id": book_data["auteur_id"]}
            )
            if existing_book:
                book_id = ObjectId(existing_book["_id"])

                # Préparer les mises à jour
                update_ops: dict[str, Any] = {}

                # Issue #85: Si l'éditeur a changé (ex: enrichissement Babelio), mettre à jour
                if existing_book.get("editeur") != book_data.get("editeur"):
                    update_ops["$set"] = {
                        "editeur": book_data["editeur"],
                        "updated_at": datetime.now(),
                    }

                # Issue #96 Bug Fix: Ajouter les nouveaux épisodes/avis_critiques avec $addToSet
                # $addToSet évite les doublons automatiquement
                addtoset_ops: dict[str, Any] = {}

                if book_data.get("episodes"):
                    # Ajouter chaque épisode individuellement pour éviter les doublons
                    for episode_id in book_data["episodes"]:
                        if episode_id:  # Vérifier que l'ID n'est pas vide
                            addtoset_ops.setdefault("episodes", {"$each": []})
                            addtoset_ops["episodes"]["$each"].append(episode_id)

                if book_data.get("avis_critiques"):
                    # Ajouter chaque avis_critique individuellement pour éviter les doublons
                    for avis_id in book_data["avis_critiques"]:
                        if avis_id:  # Vérifier que l'ID n'est pas vide
                            addtoset_ops.setdefault("avis_critiques", {"$each": []})
                            addtoset_ops["avis_critiques"]["$each"].append(avis_id)

                if addtoset_ops:
                    update_ops["$addToSet"] = addtoset_ops

                # Appliquer les mises à jour si nécessaire
                if update_ops:
                    self.livres_collection.update_one({"_id": book_id}, update_ops)

                # S'assurer que l'auteur a la référence au livre existant
                self._add_book_to_author(book_data["auteur_id"], book_id)
                return book_id

            # Créer le nouveau livre
            from ..models.book import Book

            formatted_data = Book.for_mongodb_insert(book_data)
            result = self.livres_collection.insert_one(formatted_data)
            book_id = ObjectId(result.inserted_id)

            # Ajouter la référence du livre à l'auteur
            self._add_book_to_author(book_data["auteur_id"], book_id)

            return book_id

        except Exception as e:
            print(
                f"Erreur lors de la création du livre {book_data.get('titre', '')}: {e}"
            )
            raise

    def get_books_by_validation_status(self, status: str) -> list[dict[str, Any]]:
        """Récupère les livres par statut de validation depuis le cache livresauteurs_cache."""
        cache_collection = self.get_collection("livresauteurs_cache")

        # Déterminer le filtre selon le statut demandé
        if status in ["mongo", "pending", "rejected"]:
            # Statuts directs de validation_status
            query_filter = {"validation_status": status}
        elif status in ["verified", "suggested", "not_found"]:
            # Statuts de biblio_verification_status pour les livres pending
            query_filter = {
                "validation_status": "pending",
                "biblio_verification_status": status,
            }
        elif status == "babelio_enriched":
            # Issue #85: Livres enrichis par Babelio (avec babelio_publisher)
            # Cherche dans tous les statuts qui ont babelio_publisher
            query_filter = {"babelio_publisher": {"$exists": True, "$ne": None}}  # type: ignore[dict-item]
        else:
            # Statut inconnu, retourner une liste vide
            query_filter = {"validation_status": status}

        # Récupérer les documents
        books = list(cache_collection.find(query_filter))

        # Convertir les ObjectId en string pour la sérialisation
        for book in books:
            if "_id" in book and hasattr(book["_id"], "__str__"):
                book["_id"] = str(book["_id"])
            if "episode_oid" in book and hasattr(book["episode_oid"], "__str__"):
                book["episode_oid"] = str(book["episode_oid"])

        return books

    def update_book_validation(
        self, book_id: str, status: str, metadata: dict[str, Any]
    ) -> bool:
        """
        Met à jour le statut de validation d'un livre dans la collection cache.

        Args:
            book_id: ID du livre (cache_id) dans livresauteurs_cache
            status: Nouveau statut de validation
            metadata: Métadonnées supplémentaires à sauvegarder (suggested_author, etc.)

        Returns:
            True si la mise à jour a réussi
        """
        try:
            from bson import ObjectId

            # Obtenir la collection cache
            cache_collection = self.get_collection("livresauteurs_cache")
            if cache_collection is None:
                raise Exception(
                    "Impossible d'accéder à la collection livresauteurs_cache"
                )

            # Préparer les données de mise à jour
            update_data = {"validation_status": status, "updated_at": datetime.now()}

            # Ajouter toutes les métadonnées (suggested_author, suggested_title, etc.)
            update_data.update(metadata)

            # Mettre à jour le document dans la collection cache
            result = cache_collection.update_one(
                {"_id": ObjectId(book_id)}, {"$set": update_data}
            )

            if result.modified_count > 0:
                return True
            else:
                print(f"⚠️ Aucun document modifié pour cache_id={book_id}")
                return False

        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour: {e}")
            return False

    def get_all_authors(self) -> list[dict[str, Any]]:
        """Récupère tous les auteurs."""
        if self.auteurs_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            authors = list(self.auteurs_collection.find({}))
            # Conversion ObjectId en string pour JSON
            for author in authors:
                author["_id"] = str(author["_id"])
                # Convertir les ObjectIds dans la liste des livres
                if "livres" in author:
                    author["livres"] = [str(livre_id) for livre_id in author["livres"]]
            return authors
        except Exception as e:
            print(f"Erreur lors de la récupération des auteurs: {e}")
            return []

    def get_all_books(self) -> list[dict[str, Any]]:
        """Récupère tous les livres."""
        if self.livres_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            books = list(self.livres_collection.find({}))
            # Conversion ObjectId en string pour JSON
            for book in books:
                book["_id"] = str(book["_id"])
                book["auteur_id"] = str(book["auteur_id"])
                # Convertir les ObjectIds dans les listes
                if "episodes" in book:
                    book["episodes"] = [
                        str(episode_id) for episode_id in book["episodes"]
                    ]
                if "avis_critiques" in book:
                    book["avis_critiques"] = [
                        str(avis_id) for avis_id in book["avis_critiques"]
                    ]
            return books
        except Exception as e:
            print(f"Erreur lors de la récupération des livres: {e}")
            return []

    def get_critical_review_by_episode_oid(
        self, episode_oid: str
    ) -> dict[str, Any] | None:
        """Récupère l'avis critique correspondant à un épisode."""
        try:
            if self.avis_critiques_collection is None:
                return None

            review = self.avis_critiques_collection.find_one(
                {"episode_oid": episode_oid}
            )
            return dict(review) if review else None
        except Exception as e:
            print(
                f"Erreur lors de la récupération de l'avis critique pour l'épisode {episode_oid}: {e}"
            )
            return None


# Instance globale du service
mongodb_service = MongoDBService()
