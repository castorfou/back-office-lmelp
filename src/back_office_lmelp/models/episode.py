"""Modèles pour les épisodes."""

from datetime import datetime
from typing import Any


class Episode:
    """Modèle représentant un épisode du Masque et la Plume."""

    def __init__(self, data: dict[str, Any]):
        """Initialise un épisode à partir des données MongoDB."""
        self.id: str = data.get("_id", "")
        self.titre: str = data.get("titre", "")
        self.date: datetime | None = data.get("date")
        self.type: str = data.get("type", "")
        self.description: str = data.get("description", "")
        self.description_corrigee: str | None = data.get("description_corrigee")
        self.transcription: str | None = data.get("transcription")

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'épisode en dictionnaire pour l'API."""
        return {
            "id": self.id,
            "titre": self.titre,
            "date": self.date.isoformat() if self.date else None,
            "type": self.type,
            "description": self.description,
            "description_corrigee": self.description_corrigee,
            "transcription": self.transcription,
        }

    def to_summary_dict(self) -> dict[str, Any]:
        """Convertit l'épisode en résumé pour la liste."""
        return {
            "id": self.id,
            "titre": self.titre,
            "date": self.date.isoformat() if self.date else None,
            "type": self.type,
        }
