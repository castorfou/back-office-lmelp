"""Modèle pour les livres."""

from datetime import datetime
from typing import Any

from bson import ObjectId


class Book:
    """Modèle représentant un livre."""

    def __init__(self, data: dict[str, Any]):
        """Initialise un livre à partir des données MongoDB."""
        self.id: str = str(data.get("_id", ""))
        self.titre: str = data.get("titre", "")
        self.auteur_id: str = str(data.get("auteur_id", ""))
        self.editeur: str = data.get("editeur", "")
        self.url_babelio: str | None = data.get("url_babelio")
        self.episodes: list[str] = [
            str(episode_id) for episode_id in data.get("episodes", [])
        ]
        self.avis_critiques: list[str] = [
            str(avis_id) for avis_id in data.get("avis_critiques", [])
        ]
        self.created_at: datetime = data.get("created_at", datetime.now())
        self.updated_at: datetime = data.get("updated_at", datetime.now())

    def to_dict(self) -> dict[str, Any]:
        """Convertit le livre en dictionnaire pour l'API."""
        return {
            "id": self.id,
            "titre": self.titre,
            "auteur_id": self.auteur_id,
            "editeur": self.editeur,
            "url_babelio": self.url_babelio,
            "episodes": self.episodes,
            "avis_critiques": self.avis_critiques,
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
        Prépare les données d'un livre pour insertion MongoDB.

        Args:
            data: Données du livre (peut inclure babelio_publisher, url_babelio)

        Returns:
            Dictionnaire formaté pour MongoDB

        Note:
            Issue #85: babelio_publisher est prioritaire sur editeur
            (source plus fiable que la transcription)
            Issue #124: url_babelio est conservée si présente
        """
        now = datetime.now()

        # Issue #189: Si editeur_id est fourni, l'utiliser (pas de champ editeur string)
        # Sinon, fallback sur editeur string (compatibilité)
        result: dict[str, Any] = {
            "titre": data["titre"],
            "auteur_id": data["auteur_id"],
            "url_babelio": data.get("url_babelio"),
            "episodes": data.get("episodes", []),
            "avis_critiques": data.get("avis_critiques", []),
            "created_at": now,
            "updated_at": now,
        }

        if data.get("editeur_id"):
            result["editeur_id"] = data["editeur_id"]
        else:
            # Issue #85: Priorité à babelio_publisher si disponible
            editeur = data.get("babelio_publisher") or data.get("editeur", "")
            result["editeur"] = editeur

        return result

    def add_episode_reference(self, episode_id: ObjectId) -> None:
        """
        Ajoute une référence d'épisode au livre.

        Args:
            episode_id: ID de l'épisode à ajouter
        """
        episode_id_str = str(episode_id)
        if episode_id_str not in self.episodes:
            self.episodes.append(episode_id_str)
            self.updated_at = datetime.now()

    def remove_episode_reference(self, episode_id: ObjectId) -> None:
        """
        Supprime une référence d'épisode du livre.

        Args:
            episode_id: ID de l'épisode à supprimer
        """
        episode_id_str = str(episode_id)
        if episode_id_str in self.episodes:
            self.episodes.remove(episode_id_str)
            self.updated_at = datetime.now()

    def add_avis_critique_reference(self, avis_id: ObjectId) -> None:
        """
        Ajoute une référence d'avis critique au livre.

        Args:
            avis_id: ID de l'avis critique à ajouter
        """
        avis_id_str = str(avis_id)
        if avis_id_str not in self.avis_critiques:
            self.avis_critiques.append(avis_id_str)
            self.updated_at = datetime.now()

    def remove_avis_critique_reference(self, avis_id: ObjectId) -> None:
        """
        Supprime une référence d'avis critique du livre.

        Args:
            avis_id: ID de l'avis critique à supprimer
        """
        avis_id_str = str(avis_id)
        if avis_id_str in self.avis_critiques:
            self.avis_critiques.remove(avis_id_str)
            self.updated_at = datetime.now()

    def to_summary_dict(self) -> dict[str, Any]:
        """Convertit le livre en résumé pour les listes."""
        return {
            "id": self.id,
            "titre": self.titre,
            "auteur_id": self.auteur_id,
            "editeur": self.editeur,
            "episodes_count": len(self.episodes),
            "avis_count": len(self.avis_critiques),
        }
