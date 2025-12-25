"""Modèle pour les émissions."""

from datetime import datetime
from typing import Any

from bson import ObjectId


class Emission:
    """Modèle représentant une émission du Masque et la Plume."""

    def __init__(self, data: dict[str, Any]):
        """Initialise une émission à partir des données MongoDB."""
        self.id: str = str(data.get("_id", ""))
        self.episode_id: str = str(data.get("episode_id", ""))
        self.avis_critique_id: str = str(data.get("avis_critique_id", ""))
        self.date: datetime | None = data.get("date")
        self.duree: int | None = data.get("duree")
        self.animateur_id: str | None = (
            str(data["animateur_id"]) if data.get("animateur_id") else None
        )
        self.avis_ids: list[str] = [
            str(avis_id) for avis_id in data.get("avis_ids", [])
        ]
        self.created_at: datetime = data.get("created_at", datetime.now())
        self.updated_at: datetime = data.get("updated_at", datetime.now())

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'émission en dictionnaire pour l'API."""
        return {
            "id": self.id,
            "episode_id": self.episode_id,
            "avis_critique_id": self.avis_critique_id,
            "date": self.date.isoformat() if self.date else None,
            "duree": self.duree,
            "animateur_id": self.animateur_id,
            "avis_ids": self.avis_ids,
            "created_at": self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else self.created_at,
            "updated_at": self.updated_at.isoformat()
            if isinstance(self.updated_at, datetime)
            else self.updated_at,
        }

    @staticmethod
    def for_mongodb_insert(data: dict[str, Any]) -> dict[str, Any]:
        """
        Prépare les données d'une émission pour insertion MongoDB.

        Args:
            data: Données de l'émission (episode_id, avis_critique_id, date, duree,
                  animateur_id, avis_ids)

        Returns:
            Dictionnaire formaté pour MongoDB avec ObjectId pour les références
        """
        now = datetime.now()

        # Convertir les IDs en ObjectId si nécessaire
        episode_id = data["episode_id"]
        if isinstance(episode_id, str):
            episode_id = ObjectId(episode_id)

        avis_critique_id = data["avis_critique_id"]
        if isinstance(avis_critique_id, str):
            avis_critique_id = ObjectId(avis_critique_id)

        animateur_id = data.get("animateur_id")
        if animateur_id and isinstance(animateur_id, str):
            animateur_id = ObjectId(animateur_id)

        return {
            "episode_id": episode_id,
            "avis_critique_id": avis_critique_id,
            "date": data["date"],
            "duree": data["duree"],
            "animateur_id": animateur_id,
            "avis_ids": data.get("avis_ids", []),
            "created_at": now,
            "updated_at": now,
        }
