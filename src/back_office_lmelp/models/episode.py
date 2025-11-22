"""Modèles pour les épisodes."""

from datetime import datetime
from typing import Any


class Episode:
    """Modèle représentant un épisode du Masque et la Plume."""

    def __init__(self, data: dict[str, Any]):
        """Initialise un épisode à partir des données MongoDB."""
        self.id: str = data.get("_id") or ""
        self.titre: str = data.get("titre") or ""
        self.date: datetime | None = data.get("date")
        self.type: str = data.get("type") or ""
        self.description: str = data.get("description") or ""
        # Nouveaux champs pour stocker les versions originales
        self.titre_origin: str | None = data.get("titre_origin")
        self.description_origin: str | None = data.get("description_origin")
        # Anciens champs pour compatibilité (à supprimer plus tard)
        self.description_corrigee: str | None = data.get("description_corrigee")
        self.titre_corrige: str | None = data.get("titre_corrige")
        self.transcription: str | None = data.get("transcription")
        # Issue #107: Champ pour masquer les épisodes
        self.masked: bool = data.get("masked", False)

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'épisode en dictionnaire pour l'API."""
        return {
            "id": self.id,
            "titre": self.titre,
            "date": self.date.isoformat() if self.date else None,
            "type": self.type,
            "description": self.description,
            # Nouveaux champs
            "titre_origin": self.titre_origin,
            "description_origin": self.description_origin,
            # Anciens champs pour compatibilité (à supprimer plus tard)
            "description_corrigee": self.description_corrigee,
            "titre_corrige": self.titre_corrige,
            "transcription": self.transcription,
            # Issue #107: Champ masked
            "masked": self.masked,
        }

    def to_summary_dict(self) -> dict[str, Any]:
        """Convertit l'épisode en résumé pour la liste."""
        return {
            "id": self.id,
            "titre": self.titre,  # Maintenant contient directement la version corrigée
            "date": self.date.isoformat() if self.date else None,
            "type": self.type,
            # Issue #107: Champ masked
            "masked": self.masked,
        }
