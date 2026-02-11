"""Utilitaire d'information de build pour l'affichage de version (Issue #205)."""

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

GITHUB_REPO_URL = "https://github.com/castorfou/back-office-lmelp"

# Chemins où Docker build écrit les fichiers d'info
_BUILD_INFO_FILE = Path("/app/build_info.json")
_CHANGELOG_FILE = Path("/app/changelog.json")


def get_build_info() -> dict[str, Any]:
    """Récupère les informations de build.

    Stratégie 3 niveaux :
    1. build_info.json (Docker production)
    2. git commands (dev local)
    3. Valeurs "unknown" (fallback)

    Returns:
        Dict avec : commit_hash, commit_short, commit_date,
        build_date, commit_url, environment
    """
    # Priorité 1 : build_info.json (Docker)
    info = _read_build_info_file()
    if info:
        return info

    # Priorité 2 : git commands (dev local)
    info = _read_build_info_from_git()
    if info:
        return info

    # Priorité 3 : fallback
    return _fallback_info()


def get_changelog() -> list[dict[str, str]]:
    """Récupère le changelog (commits avec refs issue/PR).

    Stratégie 3 niveaux :
    1. changelog.json (Docker production)
    2. git log (dev local)
    3. Liste vide (fallback)

    Returns:
        Liste de dicts avec : hash, date, message
    """
    # Priorité 1 : changelog.json (Docker)
    changelog = _read_changelog_file()
    if changelog is not None:
        return changelog

    # Priorité 2 : git log (dev local)
    changelog = _read_changelog_from_git()
    if changelog is not None:
        return changelog

    # Priorité 3 : fallback
    return []


def _read_build_info_file() -> dict[str, Any] | None:
    """Lit les infos de build depuis le fichier JSON Docker."""
    if not _BUILD_INFO_FILE.exists():
        return None
    try:
        data = json.loads(_BUILD_INFO_FILE.read_text(encoding="utf-8"))
        commit_hash = data.get("commit_hash", "unknown")
        return {
            "commit_hash": commit_hash,
            "commit_short": (commit_hash[:7] if len(commit_hash) >= 7 else commit_hash),
            "commit_date": data.get("commit_date", "unknown"),
            "build_date": data.get("build_date", "unknown"),
            "commit_url": (
                f"{GITHUB_REPO_URL}/commit/{commit_hash}"
                if commit_hash != "unknown"
                else None
            ),
            "environment": "docker",
        }
    except Exception as e:
        logger.warning(f"Impossible de lire build_info.json: {e}")
        return None


def _read_build_info_from_git() -> dict[str, Any] | None:
    """Lit les infos de build via git (mode dev)."""
    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, timeout=5
        ).strip()
        commit_date = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci"], text=True, timeout=5
        ).strip()
        return {
            "commit_hash": commit_hash,
            "commit_short": commit_hash[:7],
            "commit_date": commit_date,
            "build_date": None,
            "commit_url": f"{GITHUB_REPO_URL}/commit/{commit_hash}",
            "environment": "development",
        }
    except Exception:
        return None


def _fallback_info() -> dict[str, Any]:
    """Fallback quand ni fichier ni git ne sont disponibles."""
    return {
        "commit_hash": "unknown",
        "commit_short": "unknown",
        "commit_date": "unknown",
        "build_date": "unknown",
        "commit_url": None,
        "environment": "unknown",
    }


def _read_changelog_file() -> list[dict[str, str]] | None:
    """Lit le changelog depuis le fichier JSON Docker."""
    if not _CHANGELOG_FILE.exists():
        return None
    try:
        data = json.loads(_CHANGELOG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else None
    except Exception as e:
        logger.warning(f"Impossible de lire changelog.json: {e}")
        return None


def _read_changelog_from_git() -> list[dict[str, str]] | None:
    """Lit le changelog via git log (mode dev)."""
    try:
        output = subprocess.check_output(
            ["git", "log", "--first-parent", "--format=%h|%ci|%s"],
            text=True,
            timeout=10,
        )
        entries = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3 and re.search(r"#\d+", parts[2]):
                entries.append(
                    {
                        "hash": parts[0],
                        "date": parts[1],
                        "message": parts[2],
                    }
                )
        return entries
    except Exception:
        return None
