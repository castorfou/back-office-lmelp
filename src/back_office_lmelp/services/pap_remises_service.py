"""Lecture des émissions livrées par lmelp-pap (collection `pap_remises`).

lmelp-pap copie le fichier audio dans le dossier audio du back-office, puis
écrit une fiche dans `pap_remises`. Le back-office ne fait que lire cette
collection : il n'y écrit jamais.
"""

import logging
import os
from typing import Any

from ..settings import settings
from .mongodb_service import mongodb_service


logger = logging.getLogger(__name__)

PAP_REMISES_COLLECTION = "pap_remises"


def count_livrees(collection: Any, audio_root: str) -> int:
    """Compte les émissions livrées par pap.

    Livrée = une fiche `pap_remises` dont le fichier
    `<audio_root>/<audio_rel_filename>` existe. Le comptage part des fiches,
    jamais du dossier audio, qui contient aussi les épisodes du flux RSS.

    Chaque fiche dont le fichier manque produit une ligne de log : c'est le
    signe d'un montage du dossier audio mal réglé entre les deux applis.
    """
    count = 0
    for fiche in collection.find({}, {"audio_rel_filename": 1}):
        rel = fiche.get("audio_rel_filename") or ""
        path = os.path.join(audio_root, rel)
        if rel and os.path.isfile(path):
            count += 1
        else:
            logger.warning(
                "fiche pap %s : fichier absent dans %s", fiche.get("_id"), path
            )
    return count


def count_pap_livrees() -> int:
    """Compte les émissions livrées dans la base et le dossier audio configurés."""
    collection = mongodb_service.get_collection(PAP_REMISES_COLLECTION)
    return count_livrees(collection, settings.audio_storage_path)
