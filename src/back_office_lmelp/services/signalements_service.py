"""Signalements de Passages mal découpés (Issue #427, US 12 à 21).

Un auditeur, sur lmelp ou lmelp-mobile, signale un Passage de façon anonyme.
Le Passage est désigné par `(episode_id, livre_id)`, jamais par son id, qui
change à chaque recalcul. Un signalement reste `ouvert` jusqu'à une correction
à la main du Passage (`corrige`) ou un rejet (`rejete`) ; un recalcul ne le
clôt jamais.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from bson import ObjectId
from pydantic import BaseModel, Field, model_validator

from .mongodb_service import mongodb_service


Motif = Literal["debut_trop_tot", "fin_trop_tot", "deborde", "mauvais_livre", "autre"]
OUVERT, CORRIGE, REJETE = "ouvert", "corrige", "rejete"


class NouveauSignalement(BaseModel):
    episode_id: str
    livre_id: str
    debut_ms: int = Field(ge=0, strict=True)
    fin_ms: int = Field(ge=0, strict=True)
    motif: Motif
    instant_ms: int = Field(ge=0, strict=True)
    commentaire: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def bornes_dans_l_ordre(self) -> "NouveauSignalement":
        if self.fin_ms <= self.debut_ms:
            raise ValueError("fin_ms doit suivre debut_ms")
        return self


class PassageIntrouvableError(LookupError):
    """Pas de Passage pour cet épisode et ce livre."""


class SignalementInconnuError(LookupError):
    """Pas de signalement sous cet id."""


class SignalementDejaClosError(ValueError):
    """Le signalement n'est plus ouvert."""


class SignalementsService:
    def _signalements(self) -> Any:
        return mongodb_service.get_collection("signalements")

    @staticmethod
    def _passages_de(episode_oid: str) -> dict[str, Any]:
        """Passages de l'émission, et sa date (AAAA-MM-JJ)."""
        from .passages_service import passages_service

        etat = passages_service.passages_de(episode_oid, avec_segments=False)
        return {**etat, "date": passages_service._episode(episode_oid)["date"]}

    def creer(self, demande: NouveauSignalement, source: str) -> None:
        if not ObjectId.is_valid(demande.episode_id):
            raise PassageIntrouvableError(demande.episode_id)
        etat = self._passages_de(demande.episode_id)
        if not any(p["livre_id"] == demande.livre_id for p in etat["passages"]):
            raise PassageIntrouvableError(demande.livre_id)
        self._signalements().insert_one(
            {
                "episode_oid": demande.episode_id,
                "livre_oid": demande.livre_id,
                "debut_ms": demande.debut_ms,
                "fin_ms": demande.fin_ms,
                "motif": demande.motif,
                "instant_ms": demande.instant_ms,
                "commentaire": demande.commentaire or None,
                "cree_le": datetime.now(UTC),
                "source": "mobile" if source == "mobile" else "web",
                "etat": OUVERT,
            }
        )

    def compte_ouverts(self) -> int:
        return int(self._signalements().count_documents({"etat": OUVERT}))

    def ouverts(self) -> list[dict[str, Any]]:
        """Signalements ouverts, du plus récent au plus ancien, avec le
        Passage tel qu'il est maintenant (bornes actuelles, id pour la page de
        correction)."""
        emissions: dict[str, dict[str, Any]] = {}
        resultat = []
        for s in self._signalements().find({"etat": OUVERT}).sort("cree_le", -1):
            episode = s["episode_oid"]
            if episode not in emissions:
                emissions[episode] = self._passages_de(episode)
            etat = emissions[episode]
            actuel = next(
                (p for p in etat["passages"] if p["livre_id"] == s["livre_oid"]), None
            )
            resultat.append(
                {
                    "id": str(s["_id"]),
                    "episode_id": episode,
                    "date": etat["date"],
                    "livre_id": s["livre_oid"],
                    "titre": actuel["titre"] if actuel else None,
                    "motif": s["motif"],
                    "instant_ms": s["instant_ms"],
                    "commentaire": s.get("commentaire"),
                    "cree_le": _en_utc(s["cree_le"]),
                    "source": s["source"],
                    "bornes_ecoutees": {
                        "debut_ms": s["debut_ms"],
                        "fin_ms": s["fin_ms"],
                    },
                    "bornes_actuelles": (
                        {"debut_ms": actuel["debut_ms"], "fin_ms": actuel["fin_ms"]}
                        if actuel
                        else None
                    ),
                    "passage_id": actuel["id"] if actuel else None,
                }
            )
        return resultat

    def rejeter(self, signalement_id: str) -> None:
        if not ObjectId.is_valid(signalement_id):
            raise SignalementInconnuError(signalement_id)
        document = self._signalements().find_one({"_id": ObjectId(signalement_id)})
        if document is None:
            raise SignalementInconnuError(signalement_id)
        if document["etat"] != OUVERT:
            raise SignalementDejaClosError(signalement_id)
        self._clore({"_id": document["_id"]}, REJETE)

    def clore_pour_correction(self, episode_oid: str, livre_oid: str) -> None:
        """Le Passage de ce livre a été corrigé à la main."""
        self._clore(
            {"episode_oid": episode_oid, "livre_oid": livre_oid, "etat": OUVERT},
            CORRIGE,
        )

    def _clore(self, filtre: dict[str, Any], etat: str) -> None:
        self._signalements().update_many(
            filtre, {"$set": {"etat": etat, "clos_le": datetime.now(UTC)}}
        )


def _en_utc(date: datetime) -> datetime:
    return date if date.tzinfo else date.replace(tzinfo=UTC)


signalements_service = SignalementsService()
