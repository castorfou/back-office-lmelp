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

    def connect(self) -> bool:
        """Établit la connexion à MongoDB."""
        try:
            self.client = MongoClient(self.mongo_url)
            # Test de connexion
            self.client.admin.command("ping")
            self.db = self.client.get_default_database()
            self.episodes_collection = self.db.episodes
            return True
        except Exception as e:
            print(f"Erreur de connexion MongoDB: {e}")
            # Clean up on connection failure
            self.client = None
            self.db = None
            self.episodes_collection = None
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
                    {}, {"titre": 1, "date": 1, "type": 1, "_id": 1}
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


# Instance globale du service
mongodb_service = MongoDBService()
