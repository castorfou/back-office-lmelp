"""Modèle pour les auteurs."""

from datetime import datetime
from typing import Any

from bson import ObjectId


class Author:
    """Modèle représentant un auteur."""

    def __init__(self, data: dict[str, Any]):
        """Initialise un auteur à partir des données MongoDB."""
        self.id: str = str(data.get("_id", ""))
        self.nom: str = data.get("nom", "")
        self.url_babelio: str | None = data.get("url_babelio")
        self.livres: list[str] = [str(livre_id) for livre_id in data.get("livres", [])]
        self.created_at: datetime = data.get("created_at", datetime.now())
        self.updated_at: datetime = data.get("updated_at", datetime.now())

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'auteur en dictionnaire pour l'API."""
        return {
            "id": self.id,
            "nom": self.nom,
            "url_babelio": self.url_babelio,
            "livres": self.livres,
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
        Prépare les données d'un auteur pour insertion MongoDB.

        Args:
            data: Données de l'auteur (peut inclure url_babelio)

        Returns:
            Dictionnaire formaté pour MongoDB
        """
        now = datetime.now()
        return {
            "nom": data["nom"],
            "url_babelio": data.get("url_babelio"),
            "livres": data.get("livres", []),
            "created_at": now,
            "updated_at": now,
        }

    def add_book_reference(self, book_id: ObjectId) -> None:
        """
        Ajoute une référence de livre à l'auteur.

        Args:
            book_id: ID du livre à ajouter
        """
        book_id_str = str(book_id)
        if book_id_str not in self.livres:
            self.livres.append(book_id_str)
            self.updated_at = datetime.now()

    def remove_book_reference(self, book_id: ObjectId) -> None:
        """
        Supprime une référence de livre de l'auteur.

        Args:
            book_id: ID du livre à supprimer
        """
        book_id_str = str(book_id)
        if book_id_str in self.livres:
            self.livres.remove(book_id_str)
            self.updated_at = datetime.now()

    def to_summary_dict(self) -> dict[str, Any]:
        """Convertit l'auteur en résumé pour les listes."""
        return {
            "id": self.id,
            "nom": self.nom,
            "books_count": len(self.livres),
        }
