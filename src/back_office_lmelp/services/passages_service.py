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
TOLERANCE_CONTACT_MS = 10  # deux bornes à moins de 10 ms se touchent


class CorrectionRefuseeError(ValueError):
    """Une correction qui casserait l'ordre des Passages."""


class PassageInconnuError(LookupError):
    """Aucun Passage avec cet id."""


class EmissionInconnueError(LookupError):
    """Aucun épisode avec cet id."""


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

    def episodes_sans_segments(self) -> list[dict[str, Any]]:
        """Épisodes non masqués qui ont un audio mais pas encore de Segments,
        du plus récent au plus ancien : la file de la retranscription
        horodatée de l'archive."""
        avec_segments = {
            d["episode_oid"]
            for d in self.mongodb_service.get_collection("episode_segments").find(
                {"segments.0": {"$exists": True}}, {"episode_oid": 1}
            )
        }
        episodes = self.mongodb_service.get_collection("episodes").find(
            {
                "masked": {"$ne": True},
                "audio_rel_filename": {"$nin": [None, ""]},
            },
            {"titre": 1, "date": 1},
        )
        resultat = []
        for episode in sorted(
            episodes, key=lambda e: e.get("date") or datetime.min, reverse=True
        ):
            if str(episode["_id"]) in avec_segments:
                continue
            date = episode.get("date")
            resultat.append(
                {
                    "id": str(episode["_id"]),
                    "titre": episode.get("titre"),
                    "date": date.isoformat() if isinstance(date, datetime) else date,
                }
            )
        return resultat

    def segments_de(self, episode_oid: str) -> list[dict[str, Any]]:
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
        segments = self.segments_de(episode_oid)
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

    def _a_des_segments(self, episode_oid: str) -> bool:
        return (
            self.mongodb_service.get_collection("episode_segments").find_one(
                {"episode_oid": episode_oid, "segments.0": {"$exists": True}},
                {"_id": 1},
            )
            is not None
        )

    def _episode(self, episode_oid: str) -> dict[str, Any]:
        """Date de l'épisode (AAAA-MM-JJ) et validation de ses Passages."""
        episode = (
            self.mongodb_service.get_collection("episodes").find_one(
                {"_id": ObjectId(episode_oid)}, {"date": 1, "passages_valides_le": 1}
            )
            or {}
        )
        date = episode.get("date")
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        return {
            "date": str(date)[:10] if date else None,
            "valide": bool(episode.get("passages_valides_le")),
        }

    def statuts(self) -> dict[str, str]:
        """Pastille de chaque émission qui a des Segments : `valide` (🟢) ou
        `a_verifier` (🟠). Une émission absente n'a pas de Segments (🔴)."""
        avec_segments = [
            d["episode_oid"]
            for d in self.mongodb_service.get_collection("episode_segments").find(
                {"segments.0": {"$exists": True}}, {"episode_oid": 1}
            )
        ]
        valides = {
            str(e["_id"])
            for e in self.mongodb_service.get_collection("episodes").find(
                {
                    "_id": {"$in": [ObjectId(o) for o in avec_segments]},
                    "passages_valides_le": {"$exists": True},
                },
                {"_id": 1},
            )
        }
        return {o: "valide" if o in valides else "a_verifier" for o in avec_segments}

    def passages_de(
        self, episode_oid: str, avec_segments: bool = True
    ) -> dict[str, Any]:
        """Segments, Passages (dans l'ordre de l'émission) et livres sans Passage.

        Chaque Passage porte son épisode et sa date, de quoi lire son audio.
        Un livre sans Passage dit pourquoi : `pas_de_segments` (l'émission n'a
        pas de transcription horodatée), `supprime` (Passage retiré à la
        correction) ou `non_repere` ; il porte l'id de son livre s'il est en
        base, le titre du résumé pouvant différer du titre validé.

        Le livre de chaque Passage est retrouvé à la lecture. Un Passage dont le
        livre n'est plus dans le résumé (titre écarté) n'est pas rendu ; il
        revient, avec sa correction, si le titre est rétabli.
        """
        noms = self._noms_des_livres(episode_oid)
        resume = {
            self._cle(livre.titre, None, noms): livre
            for livre in self._livres_du_resume(episode_oid)
        }
        stockes = list(
            self.mongodb_service.get_collection("passages").find(
                {"episode_oid": episode_oid}
            )
        )
        visibles = sorted(
            (p for p in stockes if not p.get("supprime")), key=lambda p: p["debut_ms"]
        )
        supprimes = {
            self._cle(p["titre"], p.get("livre_oid"), noms)
            for p in stockes
            if p.get("supprime")
        }
        segments = self.segments_de(episode_oid) if avec_segments else []
        a_des_segments = bool(segments) or (
            not avec_segments and self._a_des_segments(episode_oid)
        )
        episode = self._episode(episode_oid)
        date = episode["date"]

        def raison(cle: str) -> str:
            if not a_des_segments:
                return "pas_de_segments"
            return "supprime" if cle in supprimes else "non_repere"

        def livre_id(cle: str) -> str | None:
            return None if cle.startswith("titre:") else cle

        passages = []
        avec_passage = set()
        for stocke in visibles:
            cle = self._cle(stocke["titre"], stocke.get("livre_oid"), noms)
            livre = resume.get(cle)
            if livre is None:
                continue
            avec_passage.add(cle)
            passages.append(
                {
                    "id": str(stocke["_id"]),
                    "titre": stocke["titre"],
                    "auteur": livre.auteur,
                    "section": int(livre.section),
                    "livre_id": livre_id(cle),
                    "episode_id": episode_oid,
                    "date": date,
                    "debut_ms": stocke["debut_ms"],
                    "fin_ms": stocke["fin_ms"],
                    "origine": stocke.get("origine", ORIGINE_AUTO),
                    "place_main": bool(stocke.get("place_main")),
                }
            )

        return {
            "segments": [[s["debut_ms"], s["fin_ms"], s["texte"]] for s in segments],
            "a_des_segments": a_des_segments,
            "valide": episode["valide"],
            "passages": passages,
            "supprimes": [
                {"id": str(p["_id"]), "titre": p["titre"]}
                for p in stockes
                if p.get("supprime")
                and self._cle(p["titre"], p.get("livre_oid"), noms) in resume
            ],
            "sans_passage": [
                {
                    "titre": livre.titre,
                    "auteur": livre.auteur,
                    "section": int(livre.section),
                    "livre_id": livre_id(cle),
                    "raison": raison(cle),
                }
                for cle, livre in resume.items()
                if cle not in avec_passage
            ],
        }

    def passages_du_livre(self, livre_oid: str) -> dict[str, Any]:
        """Les Passages d'un livre dans ses émissions, par date, et les émissions
        où il n'en a pas, avec la raison."""
        livre = self.mongodb_service.get_collection("livres").find_one(
            {"_id": ObjectId(livre_oid)}, {"episodes": 1}
        )
        passages: list[dict[str, Any]] = []
        sans_passage: list[dict[str, Any]] = []
        for episode_oid in (livre or {}).get("episodes") or []:
            emission = self.passages_de(str(episode_oid), avec_segments=False)
            trouves = [p for p in emission["passages"] if p["livre_id"] == livre_oid]
            passages += trouves
            if not trouves:
                absent = next(
                    (s for s in emission["sans_passage"] if s["livre_id"] == livre_oid),
                    None,
                )
                sans_passage.append(
                    {
                        "episode_id": str(episode_oid),
                        "raison": absent["raison"]
                        if absent
                        else (
                            "non_repere"
                            if emission["a_des_segments"]
                            else "pas_de_segments"
                        ),
                    }
                )
        return {
            "passages": sorted(passages, key=lambda p: p["date"] or ""),
            "sans_passage": sans_passage,
        }


class CorrectionPassages:
    """Corrections à la main des Passages d'une émission.

    Une borne se pose à l'heure exacte d'un Segment : un début au début d'une
    phrase, une fin au début ou à la fin d'une phrase. Deux Passages voisins
    partagent une frontière : déplacer le début d'un Passage déplace la fin du
    précédent s'ils se touchaient ou s'ils se chevaucheraient (un trou entre
    eux reste un trou), et symétriquement pour la fin. Toute correction passe
    les Passages touchés en `corrige` et retire la validation de l'émission.
    Elle ne relance pas le repérage : il refait seulement les Passages
    automatiques, en les arrêtant aux bornes des Passages corrigés, ce qui
    donne le même résultat.
    """

    def __init__(self, service: PassagesService) -> None:
        self.service = service

    def _collection(self, nom: str) -> Any:
        return self.service.mongodb_service.get_collection(nom)

    # ------------------------------------------------------------ lectures
    def _passage(self, passage_id: str) -> dict[str, Any]:
        document = (
            self._collection("passages").find_one({"_id": ObjectId(passage_id)})
            if ObjectId.is_valid(passage_id)
            else None
        )
        if not document:
            raise PassageInconnuError(passage_id)
        return dict(document)

    def _verifier_episode(self, episode_oid: str) -> None:
        if not ObjectId.is_valid(episode_oid) or not self._collection(
            "episodes"
        ).find_one({"_id": ObjectId(episode_oid)}, {"_id": 1}):
            raise EmissionInconnueError(episode_oid)

    def _visibles(self, episode_oid: str) -> list[dict[str, Any]]:
        return sorted(
            self._collection("passages").find(
                {"episode_oid": episode_oid, "supprime": {"$ne": True}}
            ),
            key=lambda p: p["debut_ms"],
        )

    def _phrases(self, episode_oid: str) -> tuple[set[int], set[int]]:
        """Débuts et fins des Segments de l'émission."""
        segments = self.service.segments_de(episode_oid)
        return {s["debut_ms"] for s in segments}, {s["fin_ms"] for s in segments}

    # ----------------------------------------------------------- écritures
    def _clore_signalements(self, passage: dict[str, Any]) -> None:
        """Une correction à la main du Passage clôt les signalements ouverts de
        son livre ; un recalcul ne passe jamais par ici."""
        from .signalements_service import signalements_service

        episode_oid = passage["episode_oid"]
        cle = passage.get("livre_oid") or self.service._cle(
            passage["titre"], None, self.service._noms_des_livres(episode_oid)
        )
        if not cle.startswith("titre:"):
            signalements_service.clore_pour_correction(episode_oid, cle)

    def _corriger(self, passage: dict[str, Any], **bornes: int) -> None:
        self._collection("passages").update_one(
            {"_id": passage["_id"]},
            {
                "$set": {
                    **bornes,
                    "origine": ORIGINE_CORRIGE,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        self._clore_signalements(passage)

    def _marquer(self, passage: dict[str, Any], **champs: Any) -> None:
        self._collection("passages").update_one(
            {"_id": passage["_id"]},
            {"$set": {**champs, "updated_at": datetime.now(UTC)}},
        )
        self._clore_signalements(passage)

    def _devalider_et_relire(self, episode_oid: str) -> dict[str, Any]:
        """Une correction après validation fait repasser l'émission en 🟠."""
        self._collection("episodes").update_one(
            {"_id": ObjectId(episode_oid)}, {"$unset": {"passages_valides_le": ""}}
        )
        return self.service.passages_de(episode_oid, avec_segments=False)

    # ---------------------------------------------------------------- bornes
    def _deplacer(self, passage_id: str, cote: str, ms: int) -> dict[str, Any]:
        """Déplace le début (`cote="debut"`) ou la fin d'un Passage ; la borne
        du voisin de ce côté suit s'ils se touchaient ou se chevaucheraient."""
        passage = self._passage(passage_id)
        if passage.get("supprime"):
            raise CorrectionRefuseeError("Un Passage supprimé se restaure d'abord")
        debuts, fins = self._phrases(passage["episode_oid"])
        if ms not in debuts and (cote == "debut" or ms not in fins):
            raise CorrectionRefuseeError(
                "Une borne se pose au début ou à la fin d'une phrase"
            )
        visibles = self._visibles(passage["episode_oid"])
        index = next(i for i, p in enumerate(visibles) if p["_id"] == passage["_id"])
        if cote == "debut":
            voisin = visibles[index - 1] if index > 0 else None
            if ms >= passage["fin_ms"]:
                raise CorrectionRefuseeError("Le début doit précéder la fin du Passage")
            if voisin and ms <= voisin["debut_ms"]:
                raise CorrectionRefuseeError(
                    f"Le début ne peut pas précéder celui de « {voisin['titre']} »"
                )
            borne_voisin, autre_borne = "fin_ms", "debut_ms"
            deborde = voisin is not None and voisin["fin_ms"] > ms
        else:
            voisin = visibles[index + 1] if index + 1 < len(visibles) else None
            if ms <= passage["debut_ms"]:
                raise CorrectionRefuseeError("La fin doit suivre le début du Passage")
            if voisin and ms >= voisin["fin_ms"]:
                raise CorrectionRefuseeError(
                    f"La fin ne peut pas dépasser celle de « {voisin['titre']} »"
                )
            borne_voisin, autre_borne = "debut_ms", "fin_ms"
            deborde = voisin is not None and voisin["debut_ms"] < ms
        se_touchaient = (
            voisin is not None
            and abs(voisin[borne_voisin] - passage[autre_borne]) < TOLERANCE_CONTACT_MS
        )
        self._corriger(passage, **{autre_borne: ms})
        if voisin and voisin[borne_voisin] != ms and (se_touchaient or deborde):
            self._corriger(voisin, **{borne_voisin: ms})
        return self._devalider_et_relire(passage["episode_oid"])

    def deplacer_debut(self, passage_id: str, debut_ms: int) -> dict[str, Any]:
        return self._deplacer(passage_id, "debut", debut_ms)

    def deplacer_fin(self, passage_id: str, fin_ms: int) -> dict[str, Any]:
        return self._deplacer(passage_id, "fin", fin_ms)

    # --------------------------------------------------- supprimer, restaurer
    def supprimer(self, passage_id: str) -> dict[str, Any]:
        """Retire un Passage qui n'en est pas un ; il est gardé pour qu'un
        recalcul ne le recrée pas, et peut être restauré."""
        passage = self._passage(passage_id)
        self._marquer(passage, supprime=True)
        return self._devalider_et_relire(passage["episode_oid"])

    def restaurer(self, passage_id: str) -> dict[str, Any]:
        """Rend un Passage supprimé ; un Passage qui le chevauche s'arrête à
        son début et passe en `corrige`."""
        passage = self._passage(passage_id)
        self._marquer(passage, supprime=False)
        visibles = self._visibles(passage["episode_oid"])
        for avant, apres in zip(visibles, visibles[1:], strict=False):
            if avant["fin_ms"] > apres["debut_ms"]:
                self._corriger(avant, fin_ms=apres["debut_ms"])
        return self._devalider_et_relire(passage["episode_oid"])

    # ------------------------------------------------------ livre sur un trou
    def deposer(
        self, episode_oid: str, titre: str, debut_ms: int, fin_ms: int
    ) -> dict[str, Any]:
        """Place un livre sans Passage sur un trou, entre deux Passages : il va
        jusqu'à la fin du trou et commence à son début ou au début d'une
        phrase du trou. Il devient un Passage corrigé, placé à la main."""
        self._verifier_episode(episode_oid)
        etat = self.service.passages_de(episode_oid, avec_segments=False)
        cible = normalize_for_matching(titre)
        if any(normalize_for_matching(s["titre"]) == cible for s in etat["supprimes"]):
            raise CorrectionRefuseeError(f"Le Passage de « {titre} » est à restaurer")
        livre = next(
            (
                s
                for s in etat["sans_passage"]
                if normalize_for_matching(s["titre"]) == cible
            ),
            None,
        )
        if livre is None:
            raise CorrectionRefuseeError(f"« {titre} » n'est pas un livre à placer")
        visibles = self._visibles(episode_oid)
        trou = next(
            (
                (avant["fin_ms"], apres["debut_ms"])
                for avant, apres in zip(visibles, visibles[1:], strict=False)
                if avant["fin_ms"] <= debut_ms < apres["debut_ms"]
            ),
            None,
        )
        debuts, _ = self._phrases(episode_oid)
        if trou is None or fin_ms != trou[1]:
            raise CorrectionRefuseeError(
                "Un livre se dépose sur un trou, jusqu'à sa fin"
            )
        if debut_ms != trou[0] and debut_ms not in debuts:
            raise CorrectionRefuseeError(
                "Un livre commence au début d'une phrase du trou"
            )
        self._collection("passages").insert_one(
            {
                "episode_oid": episode_oid,
                "titre": livre["titre"],
                "livre_oid": livre.get("livre_id"),
                "debut_ms": debut_ms,
                "fin_ms": fin_ms,
                "origine": ORIGINE_CORRIGE,
                "supprime": False,
                "place_main": True,
                "updated_at": datetime.now(UTC),
            }
        )
        return self._devalider_et_relire(episode_oid)

    def _place_main(self, passage_id: str) -> dict[str, Any]:
        passage = self._passage(passage_id)
        if not passage.get("place_main"):
            raise CorrectionRefuseeError("Seul un livre placé à la main se reprend")
        return passage

    def _milieu(self, episode_oid: str, debut_ms: int, fin_ms: int) -> int:
        """Milieu d'une zone, calé sur le début de la phrase la plus proche."""
        milieu = (debut_ms + fin_ms) / 2
        debuts = [d for d in self._phrases(episode_oid)[0] if debut_ms < d < fin_ms]
        return min(debuts, key=lambda d: abs(d - milieu)) if debuts else round(milieu)

    def occuper(self, passage_id: str, mode: str) -> dict[str, Any]:
        """Un livre placé prend tout l'espace libre autour de lui (`tout`), ou
        sa première (`tete`) ou sa dernière (`fin`) partie, coupée à une phrase."""
        passage = self._place_main(passage_id)
        autres = [
            p
            for p in self._visibles(passage["episode_oid"])
            if p["_id"] != passage["_id"]
        ]
        precedent = next(
            (p for p in reversed(autres) if p["debut_ms"] < passage["debut_ms"]), None
        )
        suivant = next(
            (p for p in autres if p["debut_ms"] >= passage["debut_ms"]), None
        )
        debut = min(
            precedent["fin_ms"] if precedent else passage["debut_ms"],
            passage["debut_ms"],
        )
        fin = max(
            suivant["debut_ms"] if suivant else passage["fin_ms"], passage["fin_ms"]
        )
        if mode == "tete":
            fin = self._milieu(passage["episode_oid"], debut, fin)
        elif mode == "fin":
            debut = self._milieu(passage["episode_oid"], debut, fin)
        self._corriger(passage, debut_ms=debut, fin_ms=fin)
        return self._devalider_et_relire(passage["episode_oid"])

    def remettre(self, passage_id: str) -> dict[str, Any]:
        """Reprend un livre placé à la main : il redevient à placer."""
        passage = self._place_main(passage_id)
        self._collection("passages").delete_one({"_id": passage["_id"]})
        self._clore_signalements(passage)
        return self._devalider_et_relire(passage["episode_oid"])

    # ------------------------------------------------------------ validation
    def valider(self, episode_oid: str) -> dict[str, Any]:
        """Les Passages de l'émission sont vérifiés (pastille 🟢)."""
        self._verifier_episode(episode_oid)
        self._collection("episodes").update_one(
            {"_id": ObjectId(episode_oid)},
            {"$set": {"passages_valides_le": datetime.now(UTC)}},
        )
        return self.service.passages_de(episode_oid, avec_segments=False)

    def retirer_validation(self, episode_oid: str) -> dict[str, Any]:
        """Les Passages de l'émission redeviennent à vérifier (pastille 🟠)."""
        self._verifier_episode(episode_oid)
        return self._devalider_et_relire(episode_oid)


passages_service = PassagesService()
correction_passages = CorrectionPassages(passages_service)
