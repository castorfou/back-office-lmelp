"""Utilitaires pour le logging de démarrage de l'application."""

import os
import re
import sys


def mask_mongodb_url(url: str) -> str:
    """Masque le mot de passe dans une URL MongoDB.

    Args:
        url: URL MongoDB (format mongodb:// ou mongodb+srv://)

    Returns:
        URL avec mot de passe masqué par '***'

    Examples:
        >>> mask_mongodb_url("mongodb://user:password@host:27017/db")  # pragma: allowlist secret
        'mongodb://user:***@host:27017/db'
        >>> mask_mongodb_url("mongodb://localhost:27017/db")
        'mongodb://localhost:27017/db'
    """
    if not url:
        return url

    # Pattern pour capturer: mongodb[+srv]://[user]:[password]@[host]
    # Utiliser une recherche non-greedy (.+?) pour le password, puis chercher le DERNIER @
    # avant le host (qui ne contient pas @ dans les credentials)
    # Groupe 1: protocole + user + :
    # Groupe 2: password (à masquer) - tous caractères jusqu'au dernier @
    # Groupe 3: @ + reste de l'URL
    pattern = r"(mongodb(?:\+srv)?://[^:]+:)(.+)(@[^@]+)"

    match = re.match(pattern, url)
    if match:
        # Remplacer le groupe 2 (password) par ***
        return f"{match.group(1)}***{match.group(3)}"

    # Si pas de match (pas de password), retourner l'URL telle quelle
    return url


def is_running_in_docker() -> bool:
    """Détecte si l'application s'exécute dans un container Docker.

    Returns:
        True si dans Docker, False sinon

    Note:
        Détection basée sur la présence du fichier /.dockerenv
    """
    return os.path.exists("/.dockerenv")


def log_startup_info() -> None:
    """Affiche les informations de démarrage de l'application.

    Affiche:
    - Version Python
    - Environnement (Docker ou local)
    - Répertoire de travail
    - Variables d'environnement critiques
    - Chemins sys.path
    """
    print("=" * 50)
    print("🚀 DÉMARRAGE BACK-OFFICE LMELP")
    print("=" * 50)

    # Version (Issue #205)
    from .build_info import get_build_info

    build_info = get_build_info()
    print(f"🏷️  Version: {build_info['commit_short']} ({build_info['environment']})")
    if build_info.get("commit_url"):
        print(f"   Commit: {build_info['commit_url']}")

    # Version Python
    python_version = sys.version.split()[0]
    print(f"🐍 Python: {python_version}")

    # Détection environnement
    if is_running_in_docker():
        print("🐳 Environnement: Docker container")
    else:
        print("💻 Environnement: Local")

    # Répertoire de travail
    print(f"📂 Working directory: {os.getcwd()}")

    # Variables d'environnement critiques
    env_vars = {
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "not set"),
        "API_HOST": os.getenv("API_HOST", "not set"),
        "API_PORT": os.getenv("API_PORT", "not set"),
        "MONGODB_URL": mask_mongodb_url(os.getenv("MONGODB_URL", "not set")),
        "PYTHONPATH": os.getenv("PYTHONPATH", "not set"),
        "BABELIO_CACHE_ENABLED": os.getenv("BABELIO_CACHE_ENABLED", "not set"),
        "BABELIO_CACHE_DIR": os.getenv("BABELIO_CACHE_DIR", "not set"),
        "CALIBRE_VIRTUAL_LIBRARY_TAG": os.getenv(
            "CALIBRE_VIRTUAL_LIBRARY_TAG", "not set"
        ),
    }

    print("\n📋 Variables d'environnement:")
    for key, value in env_vars.items():
        print(f"   {key}: {value}")

    # Chemins sys.path (premiers 3 et derniers 2)
    print("\n🛤️  sys.path:")
    paths_to_show = sys.path[:3] + ["..."] + sys.path[-2:]
    for path in paths_to_show:
        if path == "...":
            print(f"   {path}")
        else:
            print(f"   - {path}")

    print("=" * 50)
    print()
