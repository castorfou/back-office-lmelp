"""PROTOTYPE JETABLE — lecteurs de Passage dans lmelp (wayfinder #418).

Jamais fusionné. Lecture seule, aucune écriture MongoDB :
- Passages : fixture du prototype #398 (passages_temoins.json), rendus contigus
  (fin = début du suivant, cf. « Interface de correction des Passages ») ;
- Segments : ~/passages-temoins/<episode_id>.json ;
- audio : AUDIO_STORAGE_PATH/<audio_rel_filename>, servi derrière une clé
  d'écoute factice en ?cle=, comme le ferait lmelp-streaming.
Simulations (marquées « simule ») : un Passage supprimé et un livre présent dans
deux émissions.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .services.mongodb_service import mongodb_service
from .settings import settings
from .utils.text_utils import normalize_for_matching


TEMOINS = Path.home() / "passages-temoins"
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "prototype_correction_passages"
    / "passages_temoins.json"
)
CLE = "prototype-cle-ecoute"
BASE_STREAMING = "/api/prototype-lecteurs"
BASE_PUBLIQUE = "https://lmelp-streaming.exemple.fr"

# Titres du résumé ≠ titres en base
ALIAS = {
    "rouge truite": "rouges-truites",
    "saint lucky luke": (
        "les aventures de lucky luke d'apres morris, tome 12 : saint lucky luke"
    ),
}
SUPPRIME_SIMULE = "Le Livre des souterrains"
# Le Fondateur reçoit aussi un Passage (factice) dans l'émission du 04/10
DOUBLE_SIMULE = ("Le Fondateur", "2026-10-04", "La Maison d'été")

router = APIRouter(prefix="/api/prototype-lecteurs")


def _segments(episode_id: str) -> list[list[Any]]:
    path = TEMOINS / f"{episode_id}.json"
    if not path.exists():
        return []
    brut = json.loads(path.read_text())["transcription"]
    return [
        [s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s["text"].strip()]
        for s in brut
        if s["text"].strip() and not set(s["text"].strip()) <= {".", " "}
    ]


def _livre_id(titre: str, livres: list[dict[str, Any]]) -> str | None:
    cle = normalize_for_matching(titre)
    cle = ALIAS.get(cle, cle)
    for livre in livres:
        if normalize_for_matching(livre["titre"]) == cle:
            return str(livre["_id"])
    return None


@router.get("/tout")
def tout() -> dict[str, Any]:
    fixture = json.loads(FIXTURE.read_text())
    episodes_col = mongodb_service.episodes_collection
    livres_col = mongodb_service.livres_collection
    assert episodes_col is not None and livres_col is not None
    emissions = []
    for date, fx in sorted(fixture.items(), reverse=True):
        annee, mois, jour = date.split("-")
        episode = episodes_col.find_one(
            {"audio_rel_filename": {"$regex": f"-{jour}\\.{mois}\\.{annee}-"}}
        )
        if not episode:
            continue
        episode_id = str(episode["_id"])
        livres = list(livres_col.find({"episodes": episode_id}, {"titre": 1}))
        passages = sorted(fx["passages"], key=lambda p: p["debut"])
        sortie = []
        sans_passage = []
        for i, p in enumerate(passages):
            fin = p["fin"]
            if i + 1 < len(passages):
                fin = min(fin, passages[i + 1]["debut"])
            item = {
                "id": p["id"],
                "livre_id": _livre_id(p["titre"], livres),
                "titre": p["titre"],
                "auteur": p["auteur"],
                "debut": p["debut"],
                "fin": fin,
                "origine": p["origine"],
            }
            if p["titre"] == SUPPRIME_SIMULE:
                sans_passage.append({**item, "raison": "supprime", "simule": True})
            else:
                sortie.append(item)
        sans_passage += [
            {
                "livre_id": _livre_id(livre["titre"], livres),
                "titre": livre["titre"],
                "auteur": livre["auteur"],
                "raison": "non_repere",
            }
            for livre in fx.get("livres_sans_passage", [])
        ]
        emissions.append(
            {
                "date": date,
                "episode_id": episode_id,
                "titre": episode.get("titre"),
                "duree": episode.get("duree"),
                "audio_rel_filename": episode.get("audio_rel_filename"),
                "passages": sortie,
                "sans_passage": sans_passage,
                "segments": _segments(episode_id),
            }
        )
    # Simulation : un livre avec un Passage dans deux émissions
    titre, date_cible, emprunt = DOUBLE_SIMULE
    source = next(
        (p for e in emissions for p in e["passages"] if p["titre"] == titre), None
    )
    cible = next((e for e in emissions if e["date"] == date_cible), None)
    if source and cible:
        for p in cible["passages"]:
            if p["titre"] == emprunt:
                p.update(
                    {
                        "titre": titre,
                        "auteur": source["auteur"],
                        "livre_id": source["livre_id"],
                        "simule": True,
                    }
                )
    return {
        "base": BASE_STREAMING,
        "base_publique": BASE_PUBLIQUE,
        "cle": CLE,
        "emissions": emissions,
    }


@router.get("/audios/{rel:path}")
def audio(rel: str, cle: str = "") -> FileResponse:
    if cle != CLE:
        raise HTTPException(403, "Clé d'écoute refusée")
    racine = Path(settings.audio_storage_path).resolve()
    chemin = (racine / rel).resolve()
    if racine not in chemin.parents or not chemin.exists():
        raise HTTPException(404, "Audio absent")
    media = "audio/mp4" if chemin.suffix == ".m4a" else "audio/mpeg"
    return FileResponse(chemin, media_type=media, headers={"Cache-Control": "no-store"})
