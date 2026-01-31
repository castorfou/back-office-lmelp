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

        Vérifie si /calibre existe et contient metadata.db.
        Si c'est le cas, retourne "/calibre".
        Sinon, l'intégration Calibre est désactivée.
        """
        default_path = "/calibre"
        if os.path.isdir(default_path) and os.path.isfile(
            os.path.join(default_path, "metadata.db")
        ):
            return default_path

        return None

    @property
    def calibre_virtual_library_tag(self) -> str | None:
        """
        Tag pour filtrer une bibliothèque virtuelle Calibre.

        Si défini, seuls les livres avec ce tag seront affichés.
        Exemple: "guillaume" pour n'afficher que mes livres.
        """
        return os.environ.get("CALIBRE_VIRTUAL_LIBRARY_TAG") or None

    # Anna's Archive (Issue #188)
    @property
    def annas_archive_url(self) -> str | None:
        """
        URL de base pour Anna's Archive.

        Si non définie, le service utilisera le fallback Wikipedia.
        Exemple: "https://fr.annas-archive.se"

        Returns:
            URL de base ou None si non configurée
        """
        return os.environ.get("ANNAS_ARCHIVE_URL") or None


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
