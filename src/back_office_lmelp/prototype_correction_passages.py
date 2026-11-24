"""PROTOTYPE JETABLE — page « Correction des passages » (wayfinder #398).

Jamais fusionné. Lecture seule, aucune écriture MongoDB :
- Segments : ~/passages-temoins/<episode_id>.json (sortie whisper.cpp -oj) ;
- Passages repérés : scripts/prototype_correction_passages/passages_temoins.json
  (indexé par date : un ObjectId en clair déclenche detect-secrets) ;
- audio : AUDIO_STORAGE_PATH/<audio_rel_filename> (copié depuis PGX).
Les corrections et la validation restent dans la mémoire du navigateur.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .settings import settings


TEMOINS = Path.home() / "passages-temoins"
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "prototype_correction_passages"
    / "passages_temoins.json"
)

router = APIRouter(prefix="/api/prototype-passages")


def _fixture() -> dict:
    return dict(json.loads(FIXTURE.read_text()))


@router.get("/segments-disponibles")
def segments_disponibles() -> list[str]:
    """Épisodes dont les Segments horodatés existent (pastille orange)."""
    return sorted(p.stem for p in TEMOINS.glob("*.json"))


@router.get("/episodes/{episode_id}")
def episode(episode_id: str, date: str) -> dict:
    segs_path = TEMOINS / f"{episode_id}.json"
    if not segs_path.exists():
        raise HTTPException(404, "Pas de Segments pour cet épisode")
    brut = json.loads(segs_path.read_text())["transcription"]
    segments = [
        [s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s["text"].strip()]
        for s in brut
        if s["text"].strip() and not set(s["text"].strip()) <= {".", " "}
    ]
    fx = _fixture().get(date, {})
    return {
        "episode_id": episode_id,
        "segments": segments,
        "passages": fx.get("passages", []),
        "livres_sans_passage": fx.get("livres_sans_passage", []),
        "simulation": fx.get("simulation"),
    }


@router.get("/episodes/{episode_id}/audio")
def audio(episode_id: str, date: str) -> FileResponse:
    annee, mois, jour = date[:10].split("-")
    motif = f"*-{jour}.{mois}.{annee}-*.m4a"
    trouves = sorted((Path(settings.audio_storage_path) / annee).glob(motif))
    if not trouves:
        raise HTTPException(404, f"Audio absent : {motif}")
    return FileResponse(trouves[0], media_type="audio/mp4")
