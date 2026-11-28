"""Segments et Passages d'un épisode en base.

- `episode_segments` : un document par épisode, les Segments du .json
  whisper (`-oj`) en ms, sans les Segments vides ou réduits à « ... » ;
- `passages` : un document par Passage, `{episode_oid, titre, livre_oid,
  debut_ms, fin_ms, origine, supprime}`. `titre` (celui du résumé) et
  `episode_oid` l'identifient tant que le livre n'est pas validé ; `livre_oid`
  est posé dès que le titre a un livre en base. Section et auteur ne sont pas
  stockés : ils se lisent dans le résumé.

Un Passage corrigé à la main (`origine: "corrige"`) ou supprimé
(`supprime: True`) n'est jamais refait par le repérage, et les Passages
automatiques voisins s'arrêtent à ses bornes.

`episode_oid` et `livre_oid` sont des String, comme dans `avis_critiques`,
`livresauteurs_cache` et `avis`.
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


ORIGINE_AUTO = "auto"
ORIGINE_CORRIGE = "corrige"


def segments_de_whisper(whisper: dict[str, Any]) -> list[dict[str, Any]]:
    """Segments d'une sortie whisper.cpp `-oj` (`transcription[].offsets` en ms).

    Les Segments vides ou réduits à « ... » (musique, silence) sont écartés.
    """
    segments = []
    for item in whisper.get("transcription", []):
        texte = item["text"].strip()
        if not texte.strip(". "):
            continue
        segments.append(
            {
                "debut_ms": int(item["offsets"]["from"]),
                "fin_ms": int(item["offsets"]["to"]),
                "texte": texte,
            }
        )
    return segments


def _sans_chevauchement(
    passage: dict[str, Any], proteges: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Coupe un Passage automatique aux bornes des Passages corrigés voisins.

    Rend None s'il ne reste rien entre deux bornes corrigées.
    """
    debut, fin = passage["debut_ms"], passage["fin_ms"]
    for protege in proteges:
        if protege["fin_ms"] <= debut or fin <= protege["debut_ms"]:
            continue
        if debut < protege["debut_ms"]:
            fin = protege["debut_ms"]
        else:
            debut = protege["fin_ms"]
    if fin <= debut:
        return None
    return {**passage, "debut_ms": debut, "fin_ms": fin}


class PassagesService:
    def __init__(self) -> None:
        self.mongodb_service = mongodb_service

    def enregistrer_segments(self, episode_oid: str, whisper: dict[str, Any]) -> None:
        """Enregistre les Segments d'un épisode, puis recalcule ses Passages."""
        self.mongodb_service.get_collection("episode_segments").update_one(
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
        document = self.mongodb_service.get_collection("episode_segments").find_one(
            {"episode_oid": episode_oid}
        )
        return list(document["segments"]) if document else []

    def _livres_du_resume(self, episode_oid: str) -> list[LivreDuResume]:
        avis = self.mongodb_service.get_collection("avis_critiques").find_one(
            {"episode_oid": episode_oid}
        )
        if not avis or not avis.get("summary"):
            return []
        return livres_du_resume(avis["summary"], avis.get("livres_ecartes"))

    def _livres_en_base(self, episode_oid: str) -> dict[str, str]:
        """Titre du résumé normalisé → id du livre, pour les titres validés."""
        entrees = self.mongodb_service.get_collection("livresauteurs_cache").find(
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
        reperage = reperer_passages(
            [Segment(s["debut_ms"], s["fin_ms"], s["texte"]) for s in segments],
            self._livres_du_resume(episode_oid),
        )
        en_base = self._livres_en_base(episode_oid)
        collection = self.mongodb_service.get_collection("passages")
        proteges = [
            p
            for p in collection.find({"episode_oid": episode_oid})
            if p.get("origine") == ORIGINE_CORRIGE or p.get("supprime")
        ]
        titres_proteges = {normalize_for_matching(p["titre"]) for p in proteges}
        livres_proteges = {p["livre_oid"] for p in proteges if p.get("livre_oid")}
        bornes_corrigees = [p for p in proteges if not p.get("supprime")]

        maintenant = datetime.now(UTC)
        nouveaux = []
        for repere in reperage.passages:
            titre = normalize_for_matching(repere.livre.titre)
            livre_oid = en_base.get(titre)
            if titre in titres_proteges or (livre_oid and livre_oid in livres_proteges):
                continue
            passage = _sans_chevauchement(
                {
                    "episode_oid": episode_oid,
                    "titre": repere.livre.titre,
                    "livre_oid": livre_oid,
                    "debut_ms": repere.debut_ms,
                    "fin_ms": repere.fin_ms,
                    "origine": ORIGINE_AUTO,
                    "supprime": False,
                    "updated_at": maintenant,
                },
                bornes_corrigees,
            )
            if passage:
                nouveaux.append(passage)

        # les nouveaux Passages sont prêts avant de retirer les anciens
        collection.delete_many(
            {
                "episode_oid": episode_oid,
                "origine": ORIGINE_AUTO,
                "supprime": {"$ne": True},
            }
        )
        if nouveaux:
            collection.insert_many(nouveaux)

    def passages_de(self, episode_oid: str) -> dict[str, Any]:
        """Segments, Passages (dans l'ordre de l'émission) et livres sans Passage."""
        documents = sorted(
            self.mongodb_service.get_collection("passages").find(
                {"episode_oid": episode_oid, "supprime": {"$ne": True}}
            ),
            key=lambda p: p["debut_ms"],
        )
        livres = self._livres_du_resume(episode_oid)
        par_titre = {normalize_for_matching(livre.titre): livre for livre in livres}
        avec_passage = {normalize_for_matching(p["titre"]) for p in documents}

        def decrire(titre: str) -> dict[str, Any]:
            livre = par_titre.get(normalize_for_matching(titre))
            return {
                "auteur": livre.auteur if livre else "",
                "section": int(livre.section) if livre else None,
            }

        return {
            "segments": [
                [s["debut_ms"], s["fin_ms"], s["texte"]]
                for s in self._segments(episode_oid)
            ],
            "passages": [
                {
                    "id": str(p["_id"]),
                    "titre": p["titre"],
                    **decrire(p["titre"]),
                    "livre_id": p.get("livre_oid"),
                    "debut_ms": p["debut_ms"],
                    "fin_ms": p["fin_ms"],
                    "origine": p.get("origine", ORIGINE_AUTO),
                }
                for p in documents
            ],
            "sans_passage": [
                {"titre": livre.titre, **decrire(livre.titre)}
                for livre in livres
                if normalize_for_matching(livre.titre) not in avec_passage
            ],
        }


passages_service = PassagesService()
