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

    # Babelio (Issue #254)
    @property
    def babelio_fair_sec(self) -> float:
        """Délai minimum entre requêtes Babelio (BABELIO_FAIR_SEC, défaut 2.0s).

        Prend la priorité sur BABELIO_MIN_INTERVAL (legacy).
        Configurable pour respecter le fair-use de Babelio.
        """
        fair_sec = os.environ.get("BABELIO_FAIR_SEC")
        if fair_sec is not None:
            return float(fair_sec)
        return float(os.environ.get("BABELIO_MIN_INTERVAL", "2.0"))

    @property
    def babelio_cache_day(self) -> float:
        """Durée de validité du cache Babelio en jours (BABELIO_CACHE_DAY, défaut 1.0)."""
        return float(os.environ.get("BABELIO_CACHE_DAY", "1.0"))

    @property
    def babelio_cache_dir(self) -> str:
        """Répertoire du cache Babelio (BABELIO_CACHE_DIR).

        Par défaut: /cache/babelio (répertoire externe monté dans Docker).
        Fallback: data/processed/babelio_cache (dev local).
        """
        return os.environ.get(
            "BABELIO_CACHE_DIR",
            os.path.join(os.getcwd(), "data", "processed", "babelio_cache"),
        )

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

    # RSS Le Masque et la Plume (Issue #295)
    @property
    def rss_masque_et_la_plume_url(self) -> str:
        """URL du flux RSS France Inter (RSS_MASQUE_ET_LA_PLUME_URL)."""
        return os.environ.get(
            "RSS_MASQUE_ET_LA_PLUME_URL",
            "https://radiofrance-podcast.net/podcast09/rss_14007.xml",
        )

    @property
    def rss_duree_mini_minutes(self) -> int:
        """Durée minimale en minutes pour retenir un épisode (RSS_DUREE_MINI_MINUTES, défaut 15)."""
        return int(os.environ.get("RSS_DUREE_MINI_MINUTES", "15"))

    @property
    def audio_storage_path(self) -> str:
        """Répertoire de stockage des fichiers audio téléchargés (AUDIO_STORAGE_PATH).

        Par défaut: /app/audios en production (volume Docker externe monté sur
        le service backend). Fallback: data/audios (dev local).
        """
        return os.environ.get(
            "AUDIO_STORAGE_PATH",
            os.path.join(os.getcwd(), "data", "audios"),
        )

    @property
    def rss_debug_log(self) -> bool:
        """Active les logs debug du service de sync RSS (RSS_DEBUG_LOG)."""
        return os.environ.get("RSS_DEBUG_LOG", "0").lower() in ("1", "true")

    # Notifications ntfy.sh (Issue #295)
    @property
    def ntfy_server_url(self) -> str | None:
        """URL du serveur ntfy.sh (NTFY_SERVER_URL). None désactive les notifications."""
        return os.environ.get("NTFY_SERVER_URL") or None

    @property
    def ntfy_topic(self) -> str | None:
        """Topic ntfy.sh (NTFY_TOPIC). None désactive les notifications."""
        return os.environ.get("NTFY_TOPIC") or None

    # Transcription PGX (Issue #302)
    @property
    def pgx_host(self) -> str | None:
        """IP de la station PGX (PGX_HOST). Toujours une IP directe, jamais un nom .local."""
        return os.environ.get("PGX_HOST") or None

    @property
    def pgx_user(self) -> str | None:
        """Utilisateur SSH sur PGX (PGX_USER)."""
        return os.environ.get("PGX_USER") or None

    @property
    def pgx_ssh_key_path(self) -> str | None:
        """Chemin de la clé privée SSH dédiée à PGX (PGX_SSH_KEY_PATH)."""
        return os.environ.get("PGX_SSH_KEY_PATH") or None

    @property
    def pgx_remote_audio_root(self) -> str | None:
        """Répertoire distant racine des audios sur PGX (PGX_REMOTE_AUDIO_ROOT)."""
        return os.environ.get("PGX_REMOTE_AUDIO_ROOT") or None

    @property
    def pgx_remote_transcription_root(self) -> str | None:
        """Répertoire distant racine des transcriptions sur PGX (PGX_REMOTE_TRANSCRIPTION_ROOT)."""
        return os.environ.get("PGX_REMOTE_TRANSCRIPTION_ROOT") or None

    @property
    def pgx_transcription_timeout_s(self) -> float:
        """Délai max d'attente d'une transcription PGX (PGX_TRANSCRIPTION_TIMEOUT_S, défaut 1800s)."""
        return float(os.environ.get("PGX_TRANSCRIPTION_TIMEOUT_S", "1800"))

    @property
    def pgx_poll_interval_s(self) -> float:
        """Intervalle de poll SSH pendant l'attente d'une transcription (PGX_POLL_INTERVAL_S, défaut 10s)."""
        return float(os.environ.get("PGX_POLL_INTERVAL_S", "10"))

    @property
    def pgx_transcription_retry_interval_hours(self) -> float:
        """Intervalle entre deux tentatives de reprise si PGX est injoignable au
        déclenchement via l'API (PGX_TRANSCRIPTION_RETRY_INTERVAL_HOURS, défaut 1h,
        Issue #309)."""
        return float(os.environ.get("PGX_TRANSCRIPTION_RETRY_INTERVAL_HOURS", "1"))

    @property
    def pgx_transcription_retry_max_hours(self) -> float:
        """Durée max cumulée de retry avant abandon définitif du cycle
        (PGX_TRANSCRIPTION_RETRY_MAX_HOURS, défaut 24h, Issue #309)."""
        return float(os.environ.get("PGX_TRANSCRIPTION_RETRY_MAX_HOURS", "24"))


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
