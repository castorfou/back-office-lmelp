"""Service MongoDB pour la gestion des épisodes."""

import os
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

    def connect(self) -> bool:
        """Établit la connexion à MongoDB."""
        try:
            self.client = MongoClient(self.mongo_url)
            # Test de connexion
            self.client.admin.command("ping")
            self.db = self.client.get_default_database()
            self.episodes_collection = self.db.episodes
            self.avis_critiques_collection = self.db.avis_critiques
            return True
        except Exception as e:
            print(f"Erreur de connexion MongoDB: {e}")
            # Clean up on connection failure
            self.client = None
            self.db = None
            self.episodes_collection = None
            self.avis_critiques_collection = None
            return False

    def disconnect(self) -> None:
        """Ferme la connexion MongoDB."""
        if self.client:
            self.client.close()

    def get_all_episodes(self) -> list[dict[str, Any]]:
        """Récupère tous les épisodes avec tri par date décroissante."""
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            episodes = list(
                self.episodes_collection.find(
                    {}, {"titre": 1, "titre_corrige": 1, "date": 1, "type": 1, "_id": 1}
                ).sort("date", -1)
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

    def update_episode_title(self, episode_id: str, titre_corrige: str) -> bool:
        """Met à jour le titre corrigé d'un épisode."""
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            result = self.episodes_collection.update_one(
                {"_id": ObjectId(episode_id)},
                {"$set": {"titre_corrige": titre_corrige}},
            )
            return bool(result.modified_count > 0)
        except Exception as e:
            print(
                f"Erreur lors de la mise à jour du titre de l'épisode {episode_id}: {e}"
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

    def get_statistics(self) -> dict[str, Any]:
        """Récupère les statistiques de la base de données."""
        if self.episodes_collection is None or self.avis_critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")

        try:
            # Total des épisodes
            total_episodes = self.episodes_collection.count_documents({})

            # Épisodes avec titres corrigés
            episodes_with_corrected_titles = self.episodes_collection.count_documents(
                {"titre_corrige": {"$ne": None, "$exists": True}}
            )

            # Épisodes avec descriptions corrigées
            episodes_with_corrected_descriptions = (
                self.episodes_collection.count_documents(
                    {"description_corrigee": {"$ne": None, "$exists": True}}
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

    def search_episodes(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Recherche textuelle dans les épisodes."""
        if self.episodes_collection is None:
            raise Exception("Connexion MongoDB non établie")

        if not query or len(query.strip()) == 0:
            return []

        try:
            # Créer un pattern regex pour la recherche floue
            fuzzy_pattern = self._create_fuzzy_regex_pattern(query)

            # Recherche dans les champs titre, description et transcription
            search_query = {
                "$or": [
                    {"titre": {"$regex": fuzzy_pattern, "$options": "i"}},
                    {"titre_corrige": {"$regex": fuzzy_pattern, "$options": "i"}},
                    {"description": {"$regex": fuzzy_pattern, "$options": "i"}},
                    {
                        "description_corrigee": {
                            "$regex": fuzzy_pattern,
                            "$options": "i",
                        }
                    },
                    {"transcription": {"$regex": fuzzy_pattern, "$options": "i"}},
                ]
            }

            episodes = list(
                self.episodes_collection.find(search_query)
                .sort("date", -1)
                .limit(limit)
            )

            # Conversion ObjectId et calcul des scores
            results = []
            for episode in episodes:
                episode["_id"] = str(episode["_id"])

                # Calculer le score et le type de match
                score, match_type = self._calculate_episode_search_score(query, episode)
                episode["score"] = score
                episode["match_type"] = match_type

                # Extraire le contexte de recherche
                episode["search_context"] = self._extract_search_context(query, episode)

                results.append(episode)

            # Garder le tri par date décroissante (déjà appliqué dans la requête MongoDB)

            return results
        except Exception as e:
            print(f"Erreur lors de la recherche d'épisodes: {e}")
            return []

    def search_critical_reviews_for_authors_books(
        self, query: str, limit: int = 10
    ) -> dict[str, list[dict[str, Any]]]:
        """Recherche textuelle dans les avis critiques pour auteurs, livres et éditeurs."""
        if self.avis_critiques_collection is None:
            raise Exception("Connexion MongoDB non établie")

        if not query or len(query.strip()) == 0:
            return {"auteurs": [], "livres": [], "editeurs": []}

        try:
            fuzzy_pattern = self._create_fuzzy_regex_pattern(query)

            # Recherche dans les avis critiques
            search_query = {
                "$or": [
                    {"auteur": {"$regex": fuzzy_pattern, "$options": "i"}},
                    {"titre_livre": {"$regex": fuzzy_pattern, "$options": "i"}},
                    {"editeur": {"$regex": fuzzy_pattern, "$options": "i"}},
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
                    score, match_type = self.calculate_search_score(
                        query, review["auteur"]
                    )
                    if score > 0:
                        auteurs_set.add((review["auteur"], score, match_type))

                # Livres
                if review.get("titre_livre"):
                    score, match_type = self.calculate_search_score(
                        query, review["titre_livre"]
                    )
                    if score > 0:
                        livres_set.add((review["titre_livre"], score, match_type))

                # Éditeurs
                if review.get("editeur"):
                    score, match_type = self.calculate_search_score(
                        query, review["editeur"]
                    )
                    if score > 0:
                        editeurs_set.add((review["editeur"], score, match_type))

            # Convertir en listes triées par score
            auteurs = [
                {"nom": nom, "score": score, "match_type": match_type}
                for nom, score, match_type in sorted(
                    auteurs_set, key=lambda x: x[1], reverse=True
                )[:limit]
            ]

            livres = [
                {"titre": titre, "score": score, "match_type": match_type}
                for titre, score, match_type in sorted(
                    livres_set, key=lambda x: x[1], reverse=True
                )[:limit]
            ]

            editeurs = [
                {"nom": nom, "score": score, "match_type": match_type}
                for nom, score, match_type in sorted(
                    editeurs_set, key=lambda x: x[1], reverse=True
                )[:limit]
            ]

            return {
                "auteurs": auteurs,
                "livres": livres,
                "editeurs": editeurs,
            }

        except Exception as e:
            print(f"Erreur lors de la recherche dans les avis critiques: {e}")
            return {"auteurs": [], "livres": [], "editeurs": []}

    def calculate_search_score(self, query: str, text: str) -> tuple[float, str]:
        """Calcule le score de pertinence et le type de match."""
        query_lower = query.lower().strip()
        text_lower = text.lower().strip()

        # Match exact (insensible à la casse)
        if query_lower == text_lower:
            return 1.0, "exact"

        # Match exact partiel
        if query_lower in text_lower:
            # Score basé sur la position et la longueur relative
            position = text_lower.find(query_lower)
            length_ratio = len(query_lower) / len(text_lower)

            # Bonus si le match est au début
            position_bonus = 0.1 if position == 0 else 0
            score = 0.5 + length_ratio * 0.3 + position_bonus

            return min(score, 0.9), "partial"

        # Recherche floue simple (distance d'édition approximative)
        fuzzy_score = self._calculate_fuzzy_score(query_lower, text_lower)
        if fuzzy_score > 0.3:
            return fuzzy_score, "fuzzy"

        return 0.0, "none"

    def _create_fuzzy_regex_pattern(self, query: str) -> str:
        """Crée un pattern regex pour la recherche floue."""
        # Échapper les caractères spéciaux regex
        import re

        escaped_query = re.escape(query.strip())

        # Permettre des variations de caractères pour la recherche floue
        # Par exemple: remplacer 'e' par '[eé]', 'a' par '[aà]', etc.
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
        """Calcule un score de correspondance floue simple."""
        # Implémentation simple basée sur les caractères communs
        query_chars = set(query.lower())
        text_chars = set(text.lower())

        if len(query_chars) == 0:
            return 0.0

        common_chars = query_chars.intersection(text_chars)
        ratio = len(common_chars) / len(query_chars)

        # Bonus si la longueur est similaire
        length_diff = abs(len(query) - len(text))
        length_bonus = max(0, 1 - length_diff / max(len(query), len(text)))

        return ratio * 0.7 + length_bonus * 0.3

    def _extract_search_context(self, query: str, episode: dict[str, Any]) -> str:
        """Extrait le contexte de recherche avec 10 mots avant et après le terme trouvé."""
        import re

        query_lower = query.lower()
        fields_to_search = [
            "titre",
            "titre_corrige",
            "description",
            "description_corrigee",
            "transcription",
        ]

        for field in fields_to_search:
            text = episode.get(field, "")
            if not text or not isinstance(text, str):
                continue

            text_lower = text.lower()

            # D'abord essayer la correspondance exacte
            match = re.search(re.escape(query_lower), text_lower)
            word_index = -1

            if match:
                start_pos = match.start()
                # Trouver l'index du mot
                words = text.split()
                text_lower_words = text_lower.split()
                char_count = 0
                for i, word in enumerate(text_lower_words):
                    if char_count <= start_pos < char_count + len(word):
                        word_index = i
                        break
                    char_count += len(word) + 1
            else:
                # Recherche floue si pas de correspondance exacte
                words = text.split()
                text_lower_words = [w.lower() for w in words]

                for i, word_lower in enumerate(text_lower_words):
                    if (
                        len(word_lower) >= 3
                        and len(query_lower) >= 3
                        and (
                            word_lower.startswith(query_lower[:3])
                            or query_lower[:3] in word_lower
                            or self._fuzzy_match_simple(query_lower, word_lower)
                        )
                    ):
                        word_index = i
                        break

            # Si un mot a été trouvé, extraire le contexte
            if word_index >= 0:
                words = text.split()
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


# Instance globale du service
mongodb_service = MongoDBService()
