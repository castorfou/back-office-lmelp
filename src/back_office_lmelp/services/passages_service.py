"""Segments et Passages d'un épisode en base (Issue #427).

- `episode_segments` : un document par épisode, les Segments du .json
  whisper (`-oj`) en ms ;
- `passages` : un document par Passage. `titre` (du résumé) et `episode_oid`
  l'identifient tant que le livre n'est pas validé ; `livre_oid` est posé dès
  que le titre a un livre en base. Un Passage corrigé à la main
  (`origine: "corrige"`) ou supprimé (`supprime: True`) n'est jamais refait
  par le repérage.

`episode_oid` est une String, comme dans `avis_critiques` et
`livresauteurs_cache` ; `livre_oid` aussi (le `book_id` du cache converti).
"""

from datetime import UTC, datetime
from typing import Any

from ..utils.reperage_passages import (
    LivreDuResume,
    Segment,
    livres_du_resume,
    reperer_passages,
)
from ..utils.text_utils import normalize_for_matching
from .mongodb_service import mongodb_service


def segments_de_whisper(whisper: dict[str, Any]) -> list[dict[str, Any]]:
    """Segments d'une sortie whisper.cpp `-oj` (`transcription[].offsets` en ms)."""
    return [
        {
            "debut_ms": int(item["offsets"]["from"]),
            "fin_ms": int(item["offsets"]["to"]),
            "texte": item["text"].strip(),
        }
        for item in whisper.get("transcription", [])
    ]


class PassagesService:
    def __init__(self) -> None:
        self.mongodb_service = mongodb_service

    def _collection(self, nom: str) -> Any:
        return self.mongodb_service.get_collection(nom)

    def enregistrer_segments(self, episode_oid: str, whisper: dict[str, Any]) -> None:
        """Enregistre les Segments d'un épisode, puis recalcule ses Passages."""
        self._collection("episode_segments").update_one(
            {"episode_oid": episode_oid},
            {
                "$set": {
                    "segments": segments_de_whisper(whisper),
                    "updated_at": datetime.now(UTC),
                }
            },
            upsert=True,
        )
        self.recalculer(episode_oid)

    def _segments(self, episode_oid: str) -> list[dict[str, Any]]:
        document = self._collection("episode_segments").find_one(
            {"episode_oid": episode_oid}
        )
        return list(document["segments"]) if document else []

    def _livres(self, episode_oid: str) -> list[LivreDuResume]:
        avis = self._collection("avis_critiques").find_one({"episode_oid": episode_oid})
        if not avis or not avis.get("summary"):
            return []
        return livres_du_resume(avis["summary"], avis.get("livres_ecartes"))

    def _livres_en_base(self, episode_oid: str) -> dict[str, str]:
        """Titre du résumé normalisé → id du livre, pour les titres validés."""
        entrees = self._collection("livresauteurs_cache").find(
            {"episode_oid": episode_oid, "book_id": {"$ne": None}}
        )
        return {
            normalize_for_matching(e["titre"]): str(e["book_id"])
            for e in entrees
            if e.get("titre") and e.get("book_id")
        }

    def recalculer(self, episode_oid: str) -> None:
        """Repère de nouveau les Passages de l'épisode, corrections conservées."""
        segments = self._segments(episode_oid)
        if not segments:
            return
        livres = self._livres(episode_oid)
        reperage = reperer_passages(
            [Segment(s["debut_ms"], s["fin_ms"], s["texte"]) for s in segments], livres
        )
        en_base = self._livres_en_base(episode_oid)
        passages = self._collection("passages")
        gardes = {
            normalize_for_matching(p["titre"])
            for p in passages.find({"episode_oid": episode_oid})
            if p.get("origine") == "corrige" or p.get("supprime")
        }
        passages.delete_many(
            {"episode_oid": episode_oid, "origine": "auto", "supprime": {"$ne": True}}
        )
        maintenant = datetime.now(UTC)
        nouveaux = [
            {
                "episode_oid": episode_oid,
                "titre": p.livre.titre,
                "auteur": p.livre.auteur,
                "section": int(p.livre.section),
                "livre_oid": en_base.get(normalize_for_matching(p.livre.titre)),
                "debut_ms": p.debut_ms,
                "fin_ms": p.fin_ms,
                "origine": "auto",
                "supprime": False,
                "updated_at": maintenant,
            }
            for p in reperage.passages
            if normalize_for_matching(p.livre.titre) not in gardes
        ]
        if nouveaux:
            passages.insert_many(nouveaux)

    def passages_de(self, episode_oid: str) -> dict[str, Any]:
        """Segments, Passages (dans l'ordre de l'émission) et livres sans Passage."""
        documents = list(
            self._collection("passages").find(
                {"episode_oid": episode_oid, "supprime": {"$ne": True}}
            )
        )
        documents.sort(key=lambda p: p["debut_ms"])
        avec_passage = {normalize_for_matching(p["titre"]) for p in documents}
        return {
            "segments": [
                [s["debut_ms"], s["fin_ms"], s["texte"]]
                for s in self._segments(episode_oid)
            ],
            "passages": [
                {
                    "id": str(p["_id"]),
                    "titre": p["titre"],
                    "auteur": p.get("auteur", ""),
                    "section": p.get("section"),
                    "livre_id": p.get("livre_oid"),
                    "debut_ms": p["debut_ms"],
                    "fin_ms": p["fin_ms"],
                    "origine": p.get("origine", "auto"),
                }
                for p in documents
            ],
            "sans_passage": [
                {
                    "titre": livre.titre,
                    "auteur": livre.auteur,
                    "section": int(livre.section),
                }
                for livre in self._livres(episode_oid)
                if normalize_for_matching(livre.titre) not in avec_passage
            ],
        }


passages_service = PassagesService()
