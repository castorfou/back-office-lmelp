"""
Configuration centralisée de l'application.

Ce module centralise toutes les variables d'environnement et paramètres
de configuration de l'application.
"""

import os
from functools import lru_cache


class Settings:
    """Configuration de l'application."""

    # MongoDB
    @property
    def mongodb_uri(self) -> str:
        """URI de connexion MongoDB."""
        return os.environ.get(
            "MONGODB_URI", "mongodb://localhost:27017/masque_et_la_plume"
        )

    # Configuration Calibre (optionnel)
    @property
    def calibre_library_path(self) -> str | None:
        """
        Chemin vers la bibliothèque Calibre.

        Si non défini ou vide, l'intégration Calibre est désactivée.
        """
        return os.environ.get("CALIBRE_LIBRARY_PATH") or None

    @property
    def calibre_virtual_library_tag(self) -> str | None:
        """
        Tag pour filtrer une bibliothèque virtuelle Calibre.

        Si défini, seuls les livres avec ce tag seront affichés.
        Exemple: "guillaume" pour n'afficher que mes livres.
        """
        return os.environ.get("CALIBRE_VIRTUAL_LIBRARY_TAG") or None


@lru_cache
def get_settings() -> Settings:
    """
    Retourne l'instance Settings (singleton avec cache).

    Returns:
        Instance Settings
    """
    return Settings()


# Instance globale pour import direct
settings = get_settings()
