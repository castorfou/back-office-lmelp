"""Modèle pour les critiques littéraires."""

from datetime import datetime
from typing import Any


class Critique:
    """Modèle représentant un critique littéraire."""

    def __init__(self, data: dict[str, Any]):
        """Initialise un critique à partir des données MongoDB."""
        self.id: str = str(data.get("_id", ""))
        self.nom: str = data.get("nom", "")
        self.variantes: list[str] = data.get("variantes", [])
        self.animateur: bool = data.get("animateur", False)
        self.created_at: datetime = data.get("created_at", datetime.now())
        self.updated_at: datetime = data.get("updated_at", datetime.now())

    def to_dict(self) -> dict[str, Any]:
        """Convertit le critique en dictionnaire pour l'API."""
        return {
            "id": self.id,
            "nom": self.nom,
            "variantes": self.variantes,
            "animateur": self.animateur,
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
        Prépare les données d'un critique pour insertion MongoDB.

        Args:
            data: Données du critique (nom, variantes, animateur)

        Returns:
            Dictionnaire formaté pour MongoDB
        """
        now = datetime.now()

        return {
            "nom": data["nom"],
            "variantes": data.get("variantes", []),
            "animateur": data.get("animateur", False),
            "created_at": now,
            "updated_at": now,
        }

    def add_variante(self, variante: str) -> None:
        """
        Ajoute une variante au critique.

        Args:
            variante: Variante du nom à ajouter
        """
        if variante not in self.variantes:
            self.variantes.append(variante)
            self.updated_at = datetime.now()
