"""Service MongoDB pour la gestion des épisodes."""

import contextlib
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
        self.critiques_collection: Collection | None = None
        self.emissions_collection: Collection | None = None
        self.avis_collection: Collection | None = None
        self.livresauteurs_cache_collection: Collection | None = None

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
            self.critiques_collection = self.db.critiques
            self.emissions_collection = self.db.emissions
            self.avis_collection = self.db.avis
            self.livresauteurs_cache_collection = self.db.livresauteurs_cache
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
            self.critiques_collection = None
            self.emissions_collection = None
            self.avis_collection = None
            self.livresauteurs_cache_collection = None
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

            # 1.5 Supprimer le cache livres-auteurs lié (Issue #107 - Fix ghost stats)
            try:
                cache_collection = self.get_collection("livresauteurs_cache")
                cache_delete_result = cache_collection.delete_many(
                    {"episode_oid": episode_id}
                )
                print(
                    f"Suppression de {cache_delete_result.deleted_count} entrées de cache pour l'épisode {episode_id}"
                )
            except Exception as e:
                print(
                    f"Erreur lors de la suppression du cache pour l'épisode {episode_id}: {e}"
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

    def get_avis_critique_by_episode_oid(
        self, episode_oid: str
    ) -> dict[str, Any] | None:
        """
        Récupère un avis critique par son episode_oid (fallback si avis_critique_id orphelin).

        Args:
            episode_oid: ID de l'épisode associé (string)

        Returns:
            Dictionnaire de l'avis critique ou None si non trouvé
        """
        if self.avis_critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            avis = self.avis_critiques_collection.find_one({"episode_oid": episode_oid})

            if avis:
                avis["_id"] = str(avis["_id"])
                return dict(avis)
            return None
        except Exception as e:
            print(
                f"Erreur lors de la récupération de l'avis critique par episode_oid {episode_oid}: {e}"
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
            # Total des épisodes (visibles uniquement)
            total_episodes = self.episodes_collection.count_documents(
                {"masked": {"$ne": True}}
            )

            # Nombre d'épisodes masqués
            masked_episodes_count = self.episodes_collection.count_documents(
                {"masked": True}
            )

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

            # Nombre total d'avis critiques (excluant les épisodes masqués)
            # Récupérer les IDs des épisodes masqués
            masked_episodes = list(
                self.episodes_collection.find({"masked": True}, {"_id": 1})
            )
            masked_episode_oids = [str(ep["_id"]) for ep in masked_episodes]

            critical_reviews_count = self.avis_critiques_collection.count_documents(
                {"episode_oid": {"$nin": masked_episode_oids}}
            )

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
                "masked_episodes_count": masked_episodes_count,
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
        """Recherche textuelle insensible aux accents et caractères typographiques dans les épisodes.

        Args:
            query: Terme de recherche (ex: "etranger" trouvera "L'Étranger")
            limit: Nombre maximum de résultats à retourner
            offset: Offset pour la pagination

        Returns:
            Dict avec clés "episodes" (liste de résultats) et "total_count"

        Note:
            Issue #173: Recherche insensible aux accents et caractères typographiques
        """
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        if not query or len(query.strip()) == 0:
            return {"episodes": [], "total_count": 0}

        try:
            from ..utils.text_utils import create_accent_insensitive_regex

            query_stripped = query.strip()

            # Créer un regex insensible aux accents et caractères typographiques (Issue #173)
            regex_pattern = create_accent_insensitive_regex(query_stripped)

            # Recherche dans les champs titre, description et transcription
            search_query = {
                "$or": [
                    {"titre": {"$regex": regex_pattern, "$options": "i"}},
                    {"titre_corrige": {"$regex": regex_pattern, "$options": "i"}},
                    {"description": {"$regex": regex_pattern, "$options": "i"}},
                    {
                        "description_corrigee": {
                            "$regex": regex_pattern,
                            "$options": "i",
                        }
                    },
                    {"transcription": {"$regex": regex_pattern, "$options": "i"}},
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
                episode_original_id = episode["_id"]
                episode["_id"] = str(episode["_id"])

                # Assigner un score minimal (MongoDB a trouvé l'épisode donc il est pertinent)
                episode["score"] = 1.0
                episode["match_type"] = "found"

                # Extraire le contexte de recherche
                episode["search_context"] = self._extract_search_context(query, episode)

                # Enrichir avec emission_date pour lien cliquable vers /emissions/YYYYMMDD
                emission_date_str = None
                if self.emissions_collection is not None:
                    emission = self.emissions_collection.find_one(
                        {"episode_id": episode_original_id}
                    )
                    if emission and emission.get("date"):
                        emission_date_str = emission["date"].strftime("%Y%m%d")
                episode["emission_date"] = emission_date_str

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

                # Convertir editeur_id en string si présent
                if "editeur_id" in livre and livre["editeur_id"]:
                    livre["editeur_id"] = str(livre["editeur_id"])

                results.append(livre)

            return {"livres": results, "total_count": total_count}
        except Exception as e:
            print(f"Erreur lors de la recherche de livres: {e}")
            return {"livres": [], "total_count": 0}

    def get_auteur_with_livres(self, auteur_id: str) -> dict[str, Any] | None:
        """Récupère un auteur avec ses livres, notes et émissions (Issue #190).

        Args:
            auteur_id: ID de l'auteur (MongoDB ObjectId en string)

        Returns:
            Dict avec auteur_id, nom, url_babelio, nombre_oeuvres, et livres
            (triés par émission la plus récente, avec note_moyenne et
            liste d'émissions par livre). None si l'auteur n'existe pas
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
                        "url_babelio": 1,
                        "livres": {
                            "_id": 1,
                            "titre": 1,
                            "editeur": 1,
                            "episodes": 1,  # Issue #190
                        },
                    }
                },
            ]

            result = list(self.auteurs_collection.aggregate(pipeline))

            if not result:
                return None

            auteur_data = result[0]
            livres = auteur_data.get("livres", [])

            # Issue #190: Pour chaque livre, récupérer les avis et émissions
            livres_formatted = []
            for livre in livres:
                livre_id_str = str(livre["_id"])

                # Récupérer les avis pour ce livre
                livre_notes: list[float] = []
                if self.avis_collection is not None:
                    livre_avis = list(
                        self.avis_collection.find({"livre_oid": livre_id_str})
                    )
                    livre_notes = [
                        float(a["note"])
                        for a in livre_avis
                        if a.get("note") is not None
                    ]

                note_moyenne = (
                    round(sum(livre_notes) / len(livre_notes), 1)
                    if livre_notes
                    else None
                )

                # Récupérer les émissions via les épisodes du livre
                episode_strs = livre.get("episodes", [])
                emissions_formatted: list[dict[str, Any]] = []
                max_emission_date = ""

                if episode_strs and self.emissions_collection is not None:
                    episode_oids = [ObjectId(ep_id) for ep_id in episode_strs if ep_id]
                    if episode_oids:
                        emissions_docs = list(
                            self.emissions_collection.find(
                                {"episode_id": {"$in": episode_oids}}
                            )
                        )
                        for em in emissions_docs:
                            em_date = em.get("date")
                            if isinstance(em_date, datetime):
                                date_str = em_date.strftime("%Y-%m-%d")
                            else:
                                date_str = str(em_date or "")[:10]

                            emissions_formatted.append(
                                {
                                    "emission_id": str(em["_id"]),
                                    "date": date_str,
                                }
                            )

                            if date_str > max_emission_date:
                                max_emission_date = date_str

                # Trier les émissions par date décroissante
                emissions_formatted.sort(key=lambda x: x.get("date", ""), reverse=True)

                livres_formatted.append(
                    {
                        "livre_id": livre_id_str,
                        "titre": livre["titre"],
                        "editeur": livre.get("editeur", ""),
                        "note_moyenne": note_moyenne,
                        "emissions": emissions_formatted,
                        "_max_emission_date": max_emission_date,
                    }
                )

            # Issue #190: Trier par émission la plus récente (desc)
            livres_formatted.sort(
                key=lambda x: x.get("_max_emission_date", ""), reverse=True
            )

            # Supprimer le champ interne _max_emission_date
            for livre in livres_formatted:
                livre.pop("_max_emission_date", None)

            return {
                "auteur_id": str(auteur_data["_id"]),
                "nom": auteur_data["nom"],
                "url_babelio": auteur_data.get("url_babelio"),
                "nombre_oeuvres": len(livres_formatted),
                "livres": livres_formatted,
            }

        except Exception as e:
            print(f"Erreur lors de la récupération de l'auteur {auteur_id}: {e}")
            return None

    def get_livre_with_episodes(self, livre_id: str) -> dict[str, Any] | None:
        """Récupère un livre avec ses émissions et notes moyennes (Issue #190).

        Args:
            livre_id: ID du livre (MongoDB ObjectId en string)

        Returns:
            Dict avec livre_id, titre, auteur_id, auteur_nom, editeur, url_babelio,
            note_moyenne (moyenne globale des avis), nombre_emissions, et emissions
            (triées par date décroissante, avec note_moyenne et nombre_avis par émission).
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
                        "editeur_id": 1,  # Issue #189
                        "url_babelio": 1,  # Issue #124
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

            # Issue #190: Récupérer les émissions pour chaque épisode
            episodes = livre_data.get("episodes_data", [])
            episode_ids = [ep["_id"] for ep in episodes]

            # Mapper épisode -> émission
            emissions_by_episode: dict[str, dict[str, Any]] = {}
            if episode_ids and self.emissions_collection is not None:
                emissions_docs = list(
                    self.emissions_collection.find({"episode_id": {"$in": episode_ids}})
                )
                for em in emissions_docs:
                    ep_id_str = str(em["episode_id"])
                    emissions_by_episode[ep_id_str] = em

            # Issue #190: Récupérer les avis pour ce livre
            all_avis: list[dict[str, Any]] = []
            if self.avis_collection is not None:
                all_avis = list(self.avis_collection.find({"livre_oid": livre_id}))

            # Grouper les avis par emission_oid
            avis_by_emission: dict[str, list[float]] = {}
            all_notes: list[float] = []
            for avis in all_avis:
                note = avis.get("note")
                if note is not None:
                    all_notes.append(float(note))
                    em_oid = avis.get("emission_oid", "")
                    if em_oid not in avis_by_emission:
                        avis_by_emission[em_oid] = []
                    avis_by_emission[em_oid].append(float(note))

            # Note moyenne globale
            note_moyenne = (
                round(sum(all_notes) / len(all_notes), 1) if all_notes else None
            )

            # Construire la liste des émissions triées par date décroissante
            emissions_list = []
            for episode in episodes:
                ep_id_str = str(episode["_id"])
                emission = emissions_by_episode.get(ep_id_str)
                if emission:
                    em_id_str = str(emission["_id"])
                    em_date = emission.get("date")
                    # Formater la date
                    if isinstance(em_date, datetime):
                        date_str = em_date.strftime("%Y-%m-%d")
                    else:
                        date_str = str(em_date or "")[:10]

                    # Notes pour cette émission
                    em_notes = avis_by_emission.get(em_id_str, [])
                    em_note_moyenne = (
                        round(sum(em_notes) / len(em_notes), 1) if em_notes else None
                    )

                    emissions_list.append(
                        {
                            "emission_id": em_id_str,
                            "date": date_str,
                            "note_moyenne": em_note_moyenne,
                            "nombre_avis": len(em_notes),
                        }
                    )

            # Trier par date décroissante
            emissions_list.sort(key=lambda x: str(x.get("date", "")), reverse=True)

            # Issue #200: Build Calibre-style tags from avis data
            # Build emissions_by_id map for tag generation
            emissions_by_id: dict[str, dict[str, Any]] = {}
            for em in emissions_by_episode.values():
                em_id_str = str(em["_id"])
                emissions_by_id[em_id_str] = em

            # Build critiques_by_id for official critic names
            # critique_oid is String in avis, but _id is ObjectId in critiques
            critiques_by_id: dict[str, str] = {}
            critique_oid_strs = {
                a.get("critique_oid", "") for a in all_avis if a.get("critique_oid")
            }
            if critique_oid_strs and self.critiques_collection is not None:
                from bson import ObjectId as BsonObjectId

                critique_object_ids = []
                for oid in critique_oid_strs:
                    with contextlib.suppress(Exception):
                        critique_object_ids.append(BsonObjectId(oid))

                if critique_object_ids:
                    critiques_docs = list(
                        self.critiques_collection.find(
                            {"_id": {"$in": critique_object_ids}}
                        )
                    )
                    for c in critiques_docs:
                        critiques_by_id[str(c["_id"])] = c.get("nom", "")

            calibre_tags = self._build_calibre_tags(
                all_avis, emissions_by_id, critiques_by_id=critiques_by_id
            )

            # Issue #189: Résoudre editeur - soit string, soit via editeur_id
            editeur_nom = livre_data.get("editeur", "")
            if (
                not editeur_nom
                and livre_data.get("editeur_id")
                and self.editeurs_collection is not None
            ):
                editeur_doc = self.editeurs_collection.find_one(
                    {"_id": livre_data["editeur_id"]}
                )
                if editeur_doc:
                    editeur_nom = editeur_doc.get("nom", "")

            return {
                "livre_id": str(livre_data["_id"]),
                "titre": livre_data["titre"],
                "auteur_id": str(livre_data["auteur_id"]),
                "auteur_nom": auteur_nom,
                "editeur": editeur_nom,
                "url_babelio": livre_data.get("url_babelio"),
                "note_moyenne": note_moyenne,
                "nombre_emissions": len(emissions_list),
                "emissions": emissions_list,
                "calibre_tags": calibre_tags,
            }

        except Exception as e:
            print(f"Erreur lors de la récupération du livre {livre_id}: {e}")
            return None

    def _build_calibre_tags(
        self,
        all_avis: list[dict[str, Any]],
        emissions_by_id: dict[str, dict[str, Any]],
        critiques_by_id: dict[str, str] | None = None,
    ) -> list[str]:
        """Build Calibre-style tags from avis data (Issue #200).

        Returns list of tags:
        - lmelp_yyMMdd for each emission date (chronological order)
        - lmelp_prenom_nom for each coup de coeur critic (alphabetical order)

        When critiques_by_id is provided, uses the official critique name
        (resolved via critique_oid) instead of critique_nom_extrait (LLM name).
        """
        date_tags: set[str] = set()
        critic_tags: set[str] = set()

        for avis in all_avis:
            # Get emission date for lmelp_yyMMdd tag
            em_oid = avis.get("emission_oid", "")
            emission = emissions_by_id.get(em_oid)
            if emission:
                em_date = emission.get("date")
                if isinstance(em_date, datetime):
                    date_tag = f"lmelp_{em_date.strftime('%y%m%d')}"
                    date_tags.add(date_tag)

            # Get critic name for coup_de_coeur → lmelp_prenom_nom
            if avis.get("section") == "coup_de_coeur":
                # Prefer official name via critique_oid over LLM-extracted name
                critic_name = ""
                critique_oid = avis.get("critique_oid", "")
                if critique_oid and critiques_by_id:
                    critic_name = critiques_by_id.get(critique_oid, "")
                if not critic_name:
                    critic_name = avis.get("critique_nom_extrait", "")
                if critic_name:
                    from ..utils.text_utils import normalize_for_matching

                    normalized = normalize_for_matching(critic_name)
                    tag = "lmelp_" + normalized.replace(" ", "_")
                    critic_tags.add(tag)

        # Sort: dates chronologically, critics alphabetically
        return sorted(date_tags) + sorted(critic_tags)

    def get_expected_calibre_tags(self, livre_ids: list[str]) -> dict[str, list[str]]:
        """Compute expected Calibre lmelp_ tags for multiple livres in bulk.

        Uses the same logic as _build_calibre_tags() but for multiple livres.

        Args:
            livre_ids: List of livre _id strings.

        Returns:
            Dict mapping livre_id → list of expected lmelp_ tags.
        """
        if not livre_ids or self.avis_collection is None:
            return {}

        try:
            # Bulk fetch all avis for these livres
            all_avis = list(
                self.avis_collection.find({"livre_oid": {"$in": livre_ids}})
            )
            if not all_avis:
                return {}

            # Collect all emission_oid references
            emission_oids = {
                avis.get("emission_oid", "")
                for avis in all_avis
                if avis.get("emission_oid")
            }

            # Bulk fetch emissions
            from bson import ObjectId as BsonObjectId

            emissions_by_id: dict[str, dict[str, Any]] = {}
            if emission_oids and self.emissions_collection is not None:
                emission_object_ids = []
                for oid in emission_oids:
                    with contextlib.suppress(Exception):
                        emission_object_ids.append(BsonObjectId(oid))

                if emission_object_ids:
                    emissions = list(
                        self.emissions_collection.find(
                            {"_id": {"$in": emission_object_ids}}
                        )
                    )
                    for em in emissions:
                        emissions_by_id[str(em["_id"])] = em

            # Bulk fetch critiques for official critic names
            # critique_oid is String in avis, but _id is ObjectId in critiques
            critiques_by_id: dict[str, str] = {}
            critique_oid_strs = {
                avis.get("critique_oid", "")
                for avis in all_avis
                if avis.get("critique_oid")
            }
            if critique_oid_strs and self.critiques_collection is not None:
                critique_object_ids = []
                for oid in critique_oid_strs:
                    with contextlib.suppress(Exception):
                        critique_object_ids.append(BsonObjectId(oid))

                if critique_object_ids:
                    critiques_docs = list(
                        self.critiques_collection.find(
                            {"_id": {"$in": critique_object_ids}}
                        )
                    )
                    for c in critiques_docs:
                        critiques_by_id[str(c["_id"])] = c.get("nom", "")

            # Group avis by livre_oid
            avis_by_livre: dict[str, list[dict[str, Any]]] = {}
            for avis in all_avis:
                livre_oid = avis.get("livre_oid", "")
                if livre_oid:
                    avis_by_livre.setdefault(livre_oid, []).append(avis)

            # Build tags for each livre using existing _build_calibre_tags
            result: dict[str, list[str]] = {}
            for livre_id in livre_ids:
                livre_avis = avis_by_livre.get(livre_id, [])
                if livre_avis:
                    tags = self._build_calibre_tags(
                        livre_avis,
                        emissions_by_id,
                        critiques_by_id=critiques_by_id,
                    )
                    if tags:
                        result[livre_id] = tags

            return result

        except Exception as e:
            print(f"Erreur get_expected_calibre_tags: {e}")
            return {}

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

    def search_emissions(
        self, query: str, limit: int = 10, offset: int = 0
    ) -> dict[str, Any]:
        """Recherche textuelle dans les émissions via la collection avis.

        Cherche dans les champs propres et structurés de la collection avis :
        livre_titre_extrait, auteur_nom_extrait, editeur_extrait, commentaire.
        Sections "programme" et "coup_de_coeur" uniquement (sans noms de critiques).

        Args:
            query: Terme de recherche (ex: "Camus" trouvera "Albert Camus")
            limit: Nombre maximum de résultats à retourner
            offset: Offset pour la pagination

        Returns:
            Dict avec clés "emissions" (liste de résultats) et "total_count"
        """
        if self.avis_collection is None or self.emissions_collection is None:
            raise Exception("Connexion MongoDB non établie")

        if not query or len(query.strip()) == 0:
            return {"emissions": [], "total_count": 0}

        try:
            from bson import ObjectId

            from ..utils.text_utils import create_accent_insensitive_regex

            query_stripped = query.strip()
            regex_pattern = create_accent_insensitive_regex(query_stripped)

            # Chercher dans les champs propres de la collection avis
            search_query = {
                "$or": [
                    {
                        "livre_titre_extrait": {
                            "$regex": regex_pattern,
                            "$options": "i",
                        }
                    },
                    {
                        "auteur_nom_extrait": {
                            "$regex": regex_pattern,
                            "$options": "i",
                        }
                    },
                    {
                        "editeur_extrait": {
                            "$regex": regex_pattern,
                            "$options": "i",
                        }
                    },
                    {
                        "commentaire": {
                            "$regex": regex_pattern,
                            "$options": "i",
                        }
                    },
                ]
            }

            # Compter les avis correspondants (avant déduplication)
            matching_avis = list(self.avis_collection.find(search_query))
            total_avis_count = len(matching_avis)

            if total_avis_count == 0:
                return {"emissions": [], "total_count": 0}

            # Dédupliquer par emission_oid, collecter les livres/auteurs matchés
            emissions_map: dict[str, list[dict[str, Any]]] = {}
            for avis in matching_avis:
                emission_oid = avis.get("emission_oid")
                if not emission_oid:
                    continue
                if emission_oid not in emissions_map:
                    emissions_map[emission_oid] = []
                emissions_map[emission_oid].append(avis)

            # Nombre total d'émissions uniques
            total_count = len(emissions_map)

            if total_count == 0:
                return {"emissions": [], "total_count": 0}

            # Récupérer les émissions (avec conversion String → ObjectId, CRITIQUE)
            emission_oids_as_objectid = [ObjectId(oid) for oid in emissions_map if oid]
            emissions_docs = list(
                self.emissions_collection.find(
                    {"_id": {"$in": emission_oids_as_objectid}}
                ).sort("date", -1)
            )

            # Paginer sur les émissions triées
            paginated_emissions = emissions_docs[offset : offset + limit]

            results = []
            for emission in paginated_emissions:
                emission_id_str = str(emission["_id"])
                emission_date = emission.get("date")

                # Format YYYYMMDD pour l'URL /emissions/YYYYMMDD
                emission_date_str = (
                    emission_date.strftime("%Y%m%d") if emission_date else None
                )

                # Construire le contexte depuis les avis matchés pour cette émission
                matched_avis = emissions_map.get(emission_id_str, [])
                context_parts = []
                seen_books: set[str] = set()
                query_lower = query_stripped.lower()
                for avis in matched_avis:
                    auteur = avis.get("auteur_nom_extrait", "")
                    titre = avis.get("livre_titre_extrait", "")
                    commentaire = avis.get("commentaire", "")
                    book_key = f"{auteur}-{titre}"
                    if book_key not in seen_books:
                        seen_books.add(book_key)
                        # Base : toujours commencer par auteur - titre
                        if auteur and titre:
                            book_label = f"{auteur} - {titre}"
                        elif titre:
                            book_label = titre
                        else:
                            book_label = ""
                        # Si le match vient du commentaire, ajouter l'extrait
                        commentaire_lower = commentaire.lower() if commentaire else ""
                        if commentaire and query_lower in commentaire_lower:
                            idx = commentaire_lower.find(query_lower)
                            start = max(0, idx - 30)
                            end = min(len(commentaire), idx + len(query_stripped) + 30)
                            snippet = commentaire[start:end].strip()
                            if start > 0:
                                snippet = "..." + snippet
                            if end < len(commentaire):
                                snippet = snippet + "..."
                            context_parts.append(
                                f"{book_label} : {snippet}" if book_label else snippet
                            )
                        elif book_label:
                            context_parts.append(book_label)

                search_context = " | ".join(context_parts[:3])  # Max 3 livres

                results.append(
                    {
                        "_id": emission_id_str,
                        "date": emission_date,
                        "emission_date": emission_date_str,
                        "search_context": search_context,
                    }
                )

            return {"emissions": results, "total_count": total_count}
        except Exception as e:
            print(f"Erreur lors de la recherche d'émissions: {e}")
            return {"emissions": [], "total_count": 0}

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
            # Issue #189: Résoudre editeur → editeur_id via get_or_create_editeur
            editeur_name = book_data.get("babelio_publisher") or book_data.get(
                "editeur", ""
            )
            editeur_oid = None
            if editeur_name and editeur_name.strip():
                editeur_oid, _ = self.get_or_create_editeur(editeur_name)

            # Vérifier si le livre existe déjà (même titre + même auteur)
            existing_book = self.livres_collection.find_one(
                {"titre": book_data["titre"], "auteur_id": book_data["auteur_id"]}
            )
            if existing_book:
                book_id = ObjectId(existing_book["_id"])

                # Préparer les mises à jour
                update_ops: dict[str, Any] = {}

                # Issue #189: Migrer editeur string → editeur_id
                if editeur_oid and not existing_book.get("editeur_id"):
                    update_ops["$set"] = {
                        "editeur_id": editeur_oid,
                        "updated_at": datetime.now(),
                    }
                    update_ops["$unset"] = {"editeur": ""}

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

            # Issue #189: Préparer book_data avec editeur_id pour l'insertion
            insert_data = dict(book_data)
            if editeur_oid:
                insert_data["editeur_id"] = editeur_oid
                # Retirer editeur string pour ne pas le stocker
                insert_data.pop("editeur", None)
                insert_data.pop("babelio_publisher", None)

            # Créer le nouveau livre
            from ..models.book import Book

            formatted_data = Book.for_mongodb_insert(insert_data)
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

    # ========== EMISSIONS METHODS (Issue #154) ==========

    def get_all_emissions(self) -> list[dict[str, Any]]:
        """Récupère toutes les émissions avec tri par date décroissante."""
        if self.emissions_collection is None:
            raise Exception("Connexion MongoDB non établie")

        emissions = list(self.emissions_collection.find().sort("date", -1))
        return emissions

    def get_emission_by_episode_id(self, episode_id: str) -> dict[str, Any] | None:
        """Récupère une émission par episode_id."""
        if self.emissions_collection is None:
            raise Exception("Connexion MongoDB non établie")

        episode_oid = ObjectId(episode_id)
        result = self.emissions_collection.find_one({"episode_id": episode_oid})
        return dict(result) if result else None

    def create_emission(self, emission_data: dict[str, Any]) -> str:
        """
        Crée une nouvelle émission dans la collection.

        Args:
            emission_data: Données préparées via Emission.for_mongodb_insert()

        Returns:
            ID de l'émission créée (string)
        """
        if self.emissions_collection is None:
            raise Exception("Connexion MongoDB non établie")

        result = self.emissions_collection.insert_one(emission_data)
        return str(result.inserted_id)

    def get_critiques_by_episode(self, episode_id: str) -> list[dict[str, Any]]:
        """
        Récupère les critiques d'un épisode via avis_critiques.summary.
        Utilise CritiquesExtractionService pour parser le summary.

        Returns:
            Liste de dictionnaires {id, nom, animateur}
        """
        from back_office_lmelp.services.critiques_extraction_service import (
            critiques_extraction_service,
        )

        # 1. Récupérer avis_critique pour cet épisode
        avis = self.get_critical_review_by_episode_oid(episode_id)
        if not avis:
            return []

        # 2. Extraire noms via CritiquesExtractionService
        detected_names = critiques_extraction_service.extract_critiques_from_summary(
            avis.get("summary", "")
        )

        # 3. Matcher avec collection critiques
        if self.critiques_collection is None:
            return []
        all_critiques = list(self.critiques_collection.find())
        matched_critiques = []

        for name in detected_names:
            match = critiques_extraction_service.find_matching_critique(
                name, all_critiques
            )
            if match:
                critique_doc = next(
                    c for c in all_critiques if c["nom"] == match["nom"]
                )
                matched_critiques.append(
                    {
                        "id": str(critique_doc["_id"]),
                        "nom": critique_doc["nom"],
                        "animateur": critique_doc.get("animateur", False),
                    }
                )

        return matched_critiques

    # ==========================================================================
    # Méthodes CRUD pour la collection 'avis'
    # ==========================================================================

    def get_avis_by_emission(self, emission_oid: str) -> list[dict[str, Any]]:
        """
        Récupère tous les avis d'une émission.

        Args:
            emission_oid: L'ID de l'émission (string)

        Returns:
            Liste des avis de l'émission
        """
        if self.avis_collection is None:
            return []
        return list(self.avis_collection.find({"emission_oid": emission_oid}))

    def get_avis_by_critique(self, critique_oid: str) -> list[dict[str, Any]]:
        """
        Récupère tous les avis d'un critique.

        Args:
            critique_oid: L'ID du critique (string)

        Returns:
            Liste des avis du critique
        """
        if self.avis_collection is None:
            return []
        return list(self.avis_collection.find({"critique_oid": critique_oid}))

    def get_critique_detail(self, critique_id: str) -> dict[str, Any] | None:
        """Récupère un critique avec avis enrichis, stats et distribution (Issue #191).

        Args:
            critique_id: ID du critique (MongoDB ObjectId en string)

        Returns:
            Dict avec critique_id, nom, animateur, variantes, nombre_avis,
            note_moyenne, note_distribution, coups_de_coeur, et oeuvres.
            None si le critique n'existe pas.
        """
        if self.critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # 1. Trouver le critique
            critique = self.critiques_collection.find_one(
                {"_id": ObjectId(critique_id)}
            )
            if not critique:
                return None

            # 2. Trouver tous les avis (critique_oid est un String)
            all_avis: list[dict[str, Any]] = []
            if self.avis_collection is not None:
                all_avis = list(
                    self.avis_collection.find({"critique_oid": critique_id})
                )

            # 3. Batch-lookup livres (livre_oid=String, livres._id=ObjectId)
            livre_oids = {a["livre_oid"] for a in all_avis if a.get("livre_oid")}
            livres_map: dict[str, dict[str, Any]] = {}
            if livre_oids and self.livres_collection is not None:
                livre_object_ids = []
                for oid in livre_oids:
                    with contextlib.suppress(Exception):
                        livre_object_ids.append(ObjectId(oid))
                if livre_object_ids:
                    livres_docs = list(
                        self.livres_collection.find({"_id": {"$in": livre_object_ids}})
                    )
                    for doc in livres_docs:
                        livres_map[str(doc["_id"])] = doc

            # 4. Batch-lookup auteurs pour les livres trouvés
            auteur_ids = {
                doc["auteur_id"] for doc in livres_map.values() if doc.get("auteur_id")
            }
            auteurs_map: dict[str, str] = {}
            if auteur_ids and self.auteurs_collection is not None:
                auteurs_docs = list(
                    self.auteurs_collection.find({"_id": {"$in": list(auteur_ids)}})
                )
                for doc in auteurs_docs:
                    auteurs_map[str(doc["_id"])] = doc.get("nom", "")

            # 5. Batch-lookup émissions (emission_oid=String, emissions._id=ObjectId)
            emission_oids = {
                a["emission_oid"] for a in all_avis if a.get("emission_oid")
            }
            emissions_map: dict[str, dict[str, Any]] = {}
            if emission_oids and self.emissions_collection is not None:
                emission_object_ids = []
                for oid in emission_oids:
                    with contextlib.suppress(Exception):
                        emission_object_ids.append(ObjectId(oid))
                if emission_object_ids:
                    emissions_docs = list(
                        self.emissions_collection.find(
                            {"_id": {"$in": emission_object_ids}}
                        )
                    )
                    for doc in emissions_docs:
                        emissions_map[str(doc["_id"])] = doc

            # 6. Distribution des notes et statistiques
            note_distribution = {str(i): 0 for i in range(2, 11)}
            all_notes: list[float] = []
            for avis in all_avis:
                note = avis.get("note")
                if note is not None:
                    all_notes.append(float(note))
                    key = str(int(note))
                    if key in note_distribution:
                        note_distribution[key] += 1

            note_moyenne = (
                round(sum(all_notes) / len(all_notes), 1) if all_notes else None
            )

            # 7. Construire la liste enrichie des oeuvres
            oeuvres = []
            coups_de_coeur = []
            for avis in all_avis:
                livre_oid = avis.get("livre_oid", "")
                livre_doc = livres_map.get(livre_oid)

                # Titre officiel depuis livres, fallback vers extrait
                livre_titre = (
                    livre_doc.get("titre", avis.get("livre_titre_extrait", ""))
                    if livre_doc
                    else avis.get("livre_titre_extrait", "")
                )

                # Info auteur
                auteur_oid_str = None
                auteur_nom = avis.get("auteur_nom_extrait", "")
                if livre_doc and livre_doc.get("auteur_id"):
                    auteur_oid_str = str(livre_doc["auteur_id"])
                    auteur_nom = auteurs_map.get(auteur_oid_str, auteur_nom)

                # Date d'émission
                emission_oid = avis.get("emission_oid", "")
                emission_doc = emissions_map.get(emission_oid)
                emission_date = None
                if emission_doc and emission_doc.get("date"):
                    em_date = emission_doc["date"]
                    if isinstance(em_date, datetime):
                        emission_date = em_date.strftime("%Y-%m-%d")
                    else:
                        emission_date = str(em_date)[:10]

                oeuvre: dict[str, Any] = {
                    "livre_oid": livre_oid,
                    "livre_titre": livre_titre,
                    "auteur_nom": auteur_nom,
                    "auteur_oid": auteur_oid_str,
                    "editeur": avis.get("editeur_extrait", ""),
                    "note": avis.get("note"),
                    "commentaire": avis.get("commentaire", ""),
                    "section": avis.get("section", ""),
                    "emission_date": emission_date,
                    "emission_oid": emission_oid,
                }
                oeuvres.append(oeuvre)

                # Coups de coeur: note >= 9
                if avis.get("note") is not None and avis["note"] >= 9:
                    coups_de_coeur.append(oeuvre)

            # Tri par date d'émission décroissante
            oeuvres.sort(
                key=lambda x: x.get("emission_date") or "",
                reverse=True,
            )
            coups_de_coeur.sort(
                key=lambda x: x.get("emission_date") or "",
                reverse=True,
            )

            return {
                "critique_id": str(critique["_id"]),
                "nom": critique.get("nom", ""),
                "animateur": critique.get("animateur", False),
                "variantes": critique.get("variantes", []),
                "nombre_avis": len(all_avis),
                "note_moyenne": note_moyenne,
                "note_distribution": note_distribution,
                "coups_de_coeur": coups_de_coeur,
                "oeuvres": oeuvres,
            }

        except Exception as e:
            print(f"Erreur lors de la récupération du critique {critique_id}: {e}")
            return None

    def get_avis_by_livre(self, livre_oid: str) -> list[dict[str, Any]]:
        """
        Récupère tous les avis d'un livre.

        Args:
            livre_oid: L'ID du livre (string)

        Returns:
            Liste des avis du livre
        """
        if self.avis_collection is None:
            return []
        return list(self.avis_collection.find({"livre_oid": livre_oid}))

    def get_avis_by_id(self, avis_id: str) -> dict[str, Any] | None:
        """
        Récupère un avis par son ID.

        Args:
            avis_id: L'ID de l'avis

        Returns:
            L'avis ou None si non trouvé
        """
        if self.avis_collection is None:
            return None
        try:
            result = self.avis_collection.find_one({"_id": ObjectId(avis_id)})
            return dict(result) if result else None
        except Exception:
            return None

    def save_avis_batch(self, avis_list: list[dict[str, Any]]) -> list[str]:
        """
        Sauvegarde un batch d'avis en base.

        Args:
            avis_list: Liste des avis à sauvegarder

        Returns:
            Liste des IDs des avis créés
        """
        if self.avis_collection is None or not avis_list:
            return []

        # Ajouter timestamps
        now = datetime.now()
        for avis in avis_list:
            avis["created_at"] = now
            avis["updated_at"] = now

        result = self.avis_collection.insert_many(avis_list)
        return [str(oid) for oid in result.inserted_ids]

    def delete_avis_by_emission(self, emission_oid: str) -> int:
        """
        Supprime tous les avis d'une émission.

        Utilisé pour ré-extraction : on supprime les anciens avant de recréer.

        Args:
            emission_oid: L'ID de l'émission

        Returns:
            Nombre d'avis supprimés
        """
        if self.avis_collection is None:
            return 0
        result = self.avis_collection.delete_many({"emission_oid": emission_oid})
        return int(result.deleted_count)

    def update_avis(self, avis_id: str, data: dict[str, Any]) -> bool:
        """
        Met à jour un avis (résolution manuelle d'entité).

        Args:
            avis_id: L'ID de l'avis
            data: Les champs à mettre à jour (livre_oid, critique_oid, note, etc.)

        Returns:
            True si la mise à jour a réussi
        """
        if self.avis_collection is None:
            return False

        # Ajouter timestamp de mise à jour
        data["updated_at"] = datetime.now()

        try:
            result = self.avis_collection.update_one(
                {"_id": ObjectId(avis_id)}, {"$set": data}
            )
            return bool(result.matched_count > 0)
        except Exception:
            return False

    def delete_avis(self, avis_id: str) -> bool:
        """
        Supprime un avis par son ID.

        Args:
            avis_id: L'ID de l'avis

        Returns:
            True si la suppression a réussi
        """
        if self.avis_collection is None:
            return False
        try:
            result = self.avis_collection.delete_one({"_id": ObjectId(avis_id)})
            return bool(result.deleted_count > 0)
        except Exception:
            return False

    def get_avis_stats(self) -> dict[str, Any]:
        """
        Récupère les statistiques sur les avis.

        Returns:
            Dictionnaire avec:
            - total: nombre total d'avis
            - unresolved_livre: avis sans livre_oid
            - unresolved_critique: avis sans critique_oid
            - missing_note: avis sans note
            - emissions_with_avis: nombre d'émissions ayant des avis extraits
        """
        if self.avis_collection is None:
            return {
                "total": 0,
                "unresolved_livre": 0,
                "unresolved_critique": 0,
                "missing_note": 0,
                "emissions_with_avis": 0,
            }

        total = self.avis_collection.count_documents({})
        unresolved_livre = self.avis_collection.count_documents({"livre_oid": None})
        unresolved_critique = self.avis_collection.count_documents(
            {"critique_oid": None}
        )
        missing_note = self.avis_collection.count_documents({"note": None})

        # Compter les émissions distinctes ayant des avis
        emissions_with_avis = len(self.avis_collection.distinct("emission_oid"))

        return {
            "total": total,
            "unresolved_livre": unresolved_livre,
            "unresolved_critique": unresolved_critique,
            "missing_note": missing_note,
            "emissions_with_avis": emissions_with_avis,
        }

    def count_avis_by_emission(self, emission_oid: str) -> int:
        """
        Compte le nombre d'avis pour une émission.

        Args:
            emission_oid: L'ID de l'émission

        Returns:
            Nombre d'avis
        """
        if self.avis_collection is None:
            return 0
        return int(self.avis_collection.count_documents({"emission_oid": emission_oid}))

    def get_palmares(self, page: int = 1, limit: int = 30) -> dict[str, Any]:
        """Get books ranked by average rating (descending).

        Only books with at least 2 reviews are included.
        Tied ratings are broken by number of reviews (descending),
        then by title (alphabetical).

        Args:
            page: Page number (1-indexed)
            limit: Number of items per page

        Returns:
            Dict with items, total, page, limit, total_pages
        """
        skip = (page - 1) * limit

        pipeline: list[dict[str, Any]] = [
            # Match avis with both livre_oid and note
            {"$match": {"livre_oid": {"$ne": None}, "note": {"$ne": None}}},
            # Group by book, compute average and count
            {
                "$group": {
                    "_id": "$livre_oid",
                    "note_moyenne": {"$avg": "$note"},
                    "nombre_avis": {"$sum": 1},
                }
            },
            # Filter: minimum 2 reviews
            {"$match": {"nombre_avis": {"$gte": 2}}},
            # Sort by note desc, then nombre_avis desc
            {"$sort": {"note_moyenne": -1, "nombre_avis": -1}},
            # Lookup book info
            {
                "$lookup": {
                    "from": "livres",
                    "let": {"livre_id": {"$toObjectId": "$_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", "$$livre_id"]}}}
                    ],
                    "as": "livre_info",
                }
            },
            {"$unwind": {"path": "$livre_info", "preserveNullAndEmptyArrays": True}},
            # Lookup author info
            {
                "$lookup": {
                    "from": "auteurs",
                    "localField": "livre_info.auteur_id",
                    "foreignField": "_id",
                    "as": "auteur_info",
                }
            },
            {"$unwind": {"path": "$auteur_info", "preserveNullAndEmptyArrays": True}},
            # Project final fields
            {
                "$project": {
                    "_id": 1,
                    "note_moyenne": {"$round": ["$note_moyenne", 1]},
                    "nombre_avis": 1,
                    "titre": "$livre_info.titre",
                    "auteur_id": {"$toString": "$livre_info.auteur_id"},
                    "auteur_nom": "$auteur_info.nom",
                    "url_babelio": "$livre_info.url_babelio",
                }
            },
            # Secondary sort by titre for stable ordering of equal notes
            {"$sort": {"note_moyenne": -1, "nombre_avis": -1, "titre": 1}},
            # Facet for pagination
            {
                "$facet": {
                    "metadata": [{"$count": "total"}],
                    "data": [{"$skip": skip}, {"$limit": limit}],
                }
            },
        ]

        if self.avis_collection is None:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "total_pages": 0,
            }

        result = list(self.avis_collection.aggregate(pipeline))

        if not result or not result[0]:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "total_pages": 0,
            }

        facet = result[0]
        metadata = facet.get("metadata", [])
        total = metadata[0]["total"] if metadata else 0
        data = facet.get("data", [])

        items = [
            {
                "livre_id": str(doc["_id"]),
                "titre": doc.get("titre", ""),
                "auteur_id": doc.get("auteur_id", ""),
                "auteur_nom": doc.get("auteur_nom", ""),
                "note_moyenne": doc.get("note_moyenne", 0),
                "nombre_avis": doc.get("nombre_avis", 0),
                "url_babelio": doc.get("url_babelio"),
            }
            for doc in data
        ]

        total_pages = (total + limit - 1) // limit if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }

    def get_notes_for_livres(self, livre_ids: list[str]) -> dict[str, float]:
        """Calcule les notes moyennes pour une liste de livres.

        Args:
            livre_ids: Liste des IDs de livres (strings)

        Returns:
            Dict {livre_id: note_moyenne} pour les livres ayant au moins un avis noté
        """
        if self.avis_collection is None or not livre_ids:
            return {}

        pipeline: list[dict[str, Any]] = [
            {"$match": {"livre_oid": {"$in": livre_ids}, "note": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$livre_oid",
                    "note_moyenne": {"$avg": "$note"},
                }
            },
        ]

        result = {}
        for doc in self.avis_collection.aggregate(pipeline):
            result[doc["_id"]] = round(doc["note_moyenne"], 1)

        return result

    # --- Editeur management (Issue #189) ---

    def search_editeur_by_name(self, name: str) -> dict[str, Any] | None:
        """Recherche un éditeur par nom (insensible casse/accents).

        Charge tous les éditeurs et compare via normalize_for_matching().

        Args:
            name: Nom de l'éditeur à rechercher

        Returns:
            Document éditeur si trouvé, None sinon
        """
        if self.editeurs_collection is None:
            raise Exception("Connexion MongoDB non établie")

        from ..utils.text_utils import normalize_for_matching

        normalized_name = normalize_for_matching(name)
        for editeur in self.editeurs_collection.find():
            if normalize_for_matching(editeur.get("nom", "")) == normalized_name:
                result: dict[str, Any] = editeur
                return result
        return None

    def create_editeur(self, name: str) -> ObjectId:
        """Crée un nouvel éditeur avec timestamps.

        Args:
            name: Nom de l'éditeur

        Returns:
            ObjectId du nouvel éditeur
        """
        if self.editeurs_collection is None:
            raise Exception("Connexion MongoDB non établie")

        now = datetime.now()
        result = self.editeurs_collection.insert_one(
            {"nom": name, "created_at": now, "updated_at": now}
        )
        return ObjectId(result.inserted_id)

    def get_or_create_editeur(self, name: str) -> tuple[ObjectId, bool]:
        """Trouve un éditeur existant ou en crée un nouveau.

        Args:
            name: Nom de l'éditeur

        Returns:
            Tuple (ObjectId, created: bool)
        """
        existing = self.search_editeur_by_name(name)
        if existing:
            return existing["_id"], False
        new_id = self.create_editeur(name)
        return new_id, True

    # --- Livre/Auteur refresh helpers (Issue #189) ---

    def update_livre_from_refresh(self, livre_id: str, updates: dict[str, Any]) -> bool:
        """Met à jour un livre avec les données rafraîchies.

        Quand editeur_id est fourni, le champ editeur (string) est supprimé
        du document ($unset) pour éviter la duplication.

        Args:
            livre_id: ID du livre
            updates: Champs à mettre à jour (titre, editeur_id)

        Returns:
            True si le livre a été trouvé et mis à jour
        """
        if self.livres_collection is None:
            raise Exception("Connexion MongoDB non établie")

        updates["updated_at"] = datetime.now()
        update_doc: dict[str, Any] = {"$set": updates}

        # Issue #189: Si editeur_id est fourni, supprimer le champ editeur string
        if "editeur_id" in updates:
            update_doc["$unset"] = {"editeur": ""}

        result = self.livres_collection.update_one(
            {"_id": ObjectId(livre_id)}, update_doc
        )
        return bool(result.matched_count > 0)

    def update_auteur_name_and_url(
        self,
        auteur_id: str,
        nom: str | None = None,
        url_babelio: str | None = None,
    ) -> bool:
        """Met à jour le nom et/ou l'URL Babelio d'un auteur.

        Args:
            auteur_id: ID de l'auteur
            nom: Nouveau nom (si None, pas de mise à jour)
            url_babelio: Nouvelle URL Babelio (si None, pas de mise à jour)

        Returns:
            True si mis à jour, False si rien à mettre à jour
        """
        if self.auteurs_collection is None:
            raise Exception("Connexion MongoDB non établie")

        set_fields: dict[str, Any] = {}
        if nom is not None:
            set_fields["nom"] = nom
        if url_babelio is not None:
            set_fields["url_babelio"] = url_babelio

        if not set_fields:
            return False

        set_fields["updated_at"] = datetime.now()
        result = self.auteurs_collection.update_one(
            {"_id": ObjectId(auteur_id)}, {"$set": set_fields}
        )
        return bool(result.matched_count > 0)


# Instance globale du service
mongodb_service = MongoDBService()
