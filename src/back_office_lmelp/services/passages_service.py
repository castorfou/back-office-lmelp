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

import logging
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from ..utils.reperage_passages import (
    LivreDuResume,
    Segment,
    livres_du_resume,
    reperer_passages,
)
from ..utils.text_utils import normalize_for_matching
from .mongodb_service import mongodb_service


logger = logging.getLogger(__name__)

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

    def _noms_des_livres(self, episode_oid: str) -> dict[str, str]:
        """Nom normalisé → id du livre, pour les livres de l'épisode en base.

        Un livre est connu sous plusieurs noms : le titre extrait du résumé, le
        titre suggéré par Babelio et le titre validé, que la validation écrit
        aussi dans le résumé (« Quiche ta » devient « Kichta ») ; et le titre du
        livre en base, qui reste lié à l'épisode quand un nouveau résumé vide le
        cache livres-auteurs.
        """
        noms: dict[str, str] = {}
        for livre in self.mongodb_service.get_collection("livres").find(
            {"episodes": episode_oid}, {"titre": 1}
        ):
            if livre.get("titre"):
                noms[normalize_for_matching(livre["titre"])] = str(livre["_id"])
        for entree in self.mongodb_service.get_collection("livresauteurs_cache").find(
            {"episode_oid": episode_oid, "book_id": {"$ne": None}}
        ):
            if not entree.get("book_id"):
                continue
            for champ in ("titre", "suggested_title", "validated_title"):
                if entree.get(champ):
                    noms[normalize_for_matching(entree[champ])] = str(entree["book_id"])
        return noms

    @staticmethod
    def _cle(titre: str, livre_oid: str | None, noms: dict[str, str]) -> str:
        """Ce qui identifie le livre d'un Passage : son id s'il est en base,
        sinon le titre du résumé."""
        titre_normalise = normalize_for_matching(titre)
        return livre_oid or noms.get(titre_normalise) or f"titre:{titre_normalise}"

    def recalculer_pour_avis(self, avis_critique_id: ObjectId | str) -> None:
        """Recalcule les Passages de l'épisode d'un avis critique.

        Un échec est journalisé : il ne doit pas empêcher l'action de
        l'utilisateur (écarter ou rétablir un titre) d'aboutir.
        """
        try:
            avis = self.mongodb_service.get_collection("avis_critiques").find_one(
                {"_id": ObjectId(avis_critique_id)}, {"episode_oid": 1}
            )
            if avis and avis.get("episode_oid"):
                self.recalculer(str(avis["episode_oid"]))
        except Exception as exc:
            logger.error(
                f"Repérage des Passages non recalculé ({avis_critique_id}): {exc}"
            )

    def recalculer(self, episode_oid: str) -> None:
        """Repère de nouveau les Passages de l'épisode, corrections conservées.

        Un livre a au plus un Passage : un Passage corrigé ou supprimé protège
        son livre, qu'il soit retrouvé par son id ou par son titre.
        """
        segments = self._segments(episode_oid)
        if not segments:
            return
        reperage = reperer_passages(
            [Segment(s["debut_ms"], s["fin_ms"], s["texte"]) for s in segments],
            self._livres_du_resume(episode_oid),
        )
        noms = self._noms_des_livres(episode_oid)
        collection = self.mongodb_service.get_collection("passages")
        proteges = [
            p
            for p in collection.find({"episode_oid": episode_oid})
            if p.get("origine") == ORIGINE_CORRIGE or p.get("supprime")
        ]
        cles_protegees = set()
        for protege in proteges:
            cle = self._cle(protege["titre"], protege.get("livre_oid"), noms)
            cles_protegees.add(cle)
            cles_protegees.add(self._cle(protege["titre"], None, {}))
            # le livre d'un Passage corrigé avant sa validation lui est donné
            if not protege.get("livre_oid") and not cle.startswith("titre:"):
                collection.update_one(
                    {"_id": protege["_id"]}, {"$set": {"livre_oid": cle}}
                )
        bornes_corrigees = [p for p in proteges if not p.get("supprime")]

        maintenant = datetime.now(UTC)
        nouveaux = []
        for repere in reperage.passages:
            cle = self._cle(repere.livre.titre, None, noms)
            if (
                cle in cles_protegees
                or self._cle(repere.livre.titre, None, {}) in cles_protegees
            ):
                continue
            passage = _sans_chevauchement(
                {
                    "episode_oid": episode_oid,
                    "titre": repere.livre.titre,
                    "livre_oid": None if cle.startswith("titre:") else cle,
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
        """Segments, Passages (dans l'ordre de l'émission) et livres sans Passage.

        Le livre de chaque Passage est retrouvé à la lecture. Un Passage dont le
        livre n'est plus dans le résumé (titre écarté) n'est pas rendu ; il
        revient, avec sa correction, si le titre est rétabli.
        """
        noms = self._noms_des_livres(episode_oid)
        resume = {
            self._cle(livre.titre, None, noms): livre
            for livre in self._livres_du_resume(episode_oid)
        }
        documents = sorted(
            self.mongodb_service.get_collection("passages").find(
                {"episode_oid": episode_oid, "supprime": {"$ne": True}}
            ),
            key=lambda p: p["debut_ms"],
        )
        passages = []
        for document in documents:
            cle = self._cle(document["titre"], document.get("livre_oid"), noms)
            livre = resume.get(cle)
            if livre is None:
                continue
            passages.append(
                {
                    "id": str(document["_id"]),
                    "titre": document["titre"],
                    "auteur": livre.auteur,
                    "section": int(livre.section),
                    "livre_id": None if cle.startswith("titre:") else cle,
                    "debut_ms": document["debut_ms"],
                    "fin_ms": document["fin_ms"],
                    "origine": document.get("origine", ORIGINE_AUTO),
                    "cle": cle,
                }
            )
        avec_passage = {p.pop("cle") for p in passages}

        return {
            "segments": [
                [s["debut_ms"], s["fin_ms"], s["texte"]]
                for s in self._segments(episode_oid)
            ],
            "passages": passages,
            "sans_passage": [
                {
                    "titre": livre.titre,
                    "auteur": livre.auteur,
                    "section": int(livre.section),
                }
                for cle, livre in resume.items()
                if cle not in avec_passage
            ],
        }


passages_service = PassagesService()
