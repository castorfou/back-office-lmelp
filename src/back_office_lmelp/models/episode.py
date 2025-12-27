"""Modèles pour les épisodes."""

from datetime import datetime
from typing import Any


class Episode:
    """Modèle représentant un épisode du Masque et la Plume."""

    def __init__(self, data: dict[str, Any]):
        """Initialise un épisode à partir des données MongoDB."""
        _id = data.get("_id")
        self.id: str = str(_id) if _id is not None else ""
        self.titre: str = data.get("titre") or ""
        self.date: datetime | None = data.get("date")
        self.type: str = data.get("type") or ""
        self.description: str = data.get("description") or ""
        self.duree: int | None = data.get("duree")
        # Nouveaux champs pour stocker les versions originales
        self.titre_origin: str | None = data.get("titre_origin")
        self.description_origin: str | None = data.get("description_origin")
        # Anciens champs pour compatibilité (à supprimer plus tard)
        self.description_corrigee: str | None = data.get("description_corrigee")
        self.titre_corrige: str | None = data.get("titre_corrige")
        self.transcription: str | None = data.get("transcription")
        # Issue #107: Champ pour masquer les épisodes
        self.masked: bool = data.get("masked", False)
        # Issue #129: URL de la page RadioFrance de l'épisode
        self.episode_page_url: str | None = data.get("episode_page_url")

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
            # Issue #129: URL de la page RadioFrance
            "episode_page_url": self.episode_page_url,
        }

    def to_summary_dict(self) -> dict[str, Any]:
        """Convertit l'épisode en résumé pour la liste."""
        return {
            "id": self.id,
            "titre": self.titre,  # Maintenant contient directement la version corrigée
            "date": self.date.isoformat() if self.date else None,
            "type": self.type,
            "duree": self.duree,
            # Issue #107: Champ masked
            "masked": self.masked,
        }
