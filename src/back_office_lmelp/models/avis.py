"""Modèle pour les avis individuels des critiques."""

from datetime import datetime
from typing import Any


class Avis:
    """Modèle représentant un avis individuel d'un critique sur un livre."""

    def __init__(self, data: dict[str, Any]):
        """Initialise un avis à partir des données MongoDB."""
        self.id: str = str(data.get("_id", ""))
        self.emission_oid: str = data.get("emission_oid", "")
        self.livre_oid: str | None = data.get("livre_oid")
        self.critique_oid: str | None = data.get("critique_oid")
        self.commentaire: str = data.get("commentaire", "")
        self.note: int | None = data.get("note")
        self.section: str = data.get("section", "programme")
        # Données brutes extraites (pour résolution manuelle)
        self.livre_titre_extrait: str = data.get("livre_titre_extrait", "")
        self.auteur_nom_extrait: str = data.get("auteur_nom_extrait", "")
        self.editeur_extrait: str = data.get("editeur_extrait", "")
        self.critique_nom_extrait: str = data.get("critique_nom_extrait", "")
        self.created_at: datetime = data.get("created_at", datetime.now())
        self.updated_at: datetime = data.get("updated_at", datetime.now())

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'avis en dictionnaire pour l'API."""
        return {
            "id": self.id,
            "emission_oid": self.emission_oid,
            "livre_oid": self.livre_oid,
            "critique_oid": self.critique_oid,
            "commentaire": self.commentaire,
            "note": self.note,
            "section": self.section,
            "livre_titre_extrait": self.livre_titre_extrait,
            "auteur_nom_extrait": self.auteur_nom_extrait,
            "editeur_extrait": self.editeur_extrait,
            "critique_nom_extrait": self.critique_nom_extrait,
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
        Prépare les données d'un avis pour insertion MongoDB.

        Args:
            data: Données de l'avis

        Returns:
            Dictionnaire formaté pour MongoDB
        """
        now = datetime.now()

        return {
            "emission_oid": data["emission_oid"],
            "livre_oid": data.get("livre_oid"),
            "critique_oid": data.get("critique_oid"),
            "commentaire": data.get("commentaire", ""),
            "note": data.get("note"),
            "section": data.get("section", "programme"),
            "livre_titre_extrait": data.get("livre_titre_extrait", ""),
            "auteur_nom_extrait": data.get("auteur_nom_extrait", ""),
            "editeur_extrait": data.get("editeur_extrait", ""),
            "critique_nom_extrait": data.get("critique_nom_extrait", ""),
            "created_at": now,
            "updated_at": now,
        }

    def has_unresolved_entities(self) -> bool:
        """
        Vérifie si l'avis a des entités non résolues.

        Returns:
            True si livre_oid ou critique_oid est None
        """
        return self.livre_oid is None or self.critique_oid is None

    def has_missing_note(self) -> bool:
        """
        Vérifie si l'avis a une note manquante.

        Returns:
            True si note est None
        """
        return self.note is None
