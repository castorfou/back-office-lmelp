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

            # Dernière date de mise à jour (basée sur le plus récent titre ou description modifiée)
            # Utilisation de l'aggregation pour trouver la plus récente date de modification
            pipeline: list[dict[str, Any]] = [
                {
                    "$match": {
                        "$or": [
                            {"titre_corrige": {"$ne": None, "$exists": True}},
                            {"description_corrigee": {"$ne": None, "$exists": True}},
                        ]
                    }
                },
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


# Instance globale du service
mongodb_service = MongoDBService()
