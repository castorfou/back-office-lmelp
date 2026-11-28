"""Lecture du .json horodaté de whisper.cpp (`-oj`)."""

import json
import os
from typing import Any


def lire_sortie_whisper(chemin: str) -> dict[str, Any] | None:
    """Contenu du .json, ou None s'il est absent ou ne se décode pas (encore en
    cours d'écriture, ou tronqué)."""
    if not os.path.exists(chemin):
        return None
    try:
        with open(chemin, encoding="utf-8") as f:
            return dict(json.load(f))
    except json.JSONDecodeError:
        return None
