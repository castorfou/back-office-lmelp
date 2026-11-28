"""Clé d'écoute de lmelp-mobile (ADR 0003).

Une clé unique, partagée par le cercle des auditeurs, dans le document
`parametres` `{_id: "cle_ecoute", cle, creee_le, changements}`. Elle est créée
au premier démarrage ; l'invalider la remplace aussitôt. Seules les dates des
changements sont gardées, jamais les anciennes clés.
"""

import secrets
from datetime import UTC, datetime
from typing import Any

from .mongodb_service import mongodb_service


DOCUMENT = "cle_ecoute"


def _en_utc(date: datetime) -> datetime:
    """MongoDB rend des dates sans fuseau, en UTC : le dire au navigateur."""
    return date if date.tzinfo else date.replace(tzinfo=UTC)


def _nouvelle_cle() -> str:
    return secrets.token_urlsafe(24)


class CleEcouteService:
    def __init__(self, mongodb: Any = mongodb_service) -> None:
        self.mongodb_service = mongodb

    def _parametres(self) -> Any:
        return self.mongodb_service.get_collection("parametres")

    def assurer(self) -> dict[str, Any]:
        """Crée la clé si elle n'existe pas encore, et la renvoie."""
        self._parametres().update_one(
            {"_id": DOCUMENT},
            {
                "$setOnInsert": {
                    "cle": _nouvelle_cle(),
                    "creee_le": datetime.now(UTC),
                    "changements": [],
                }
            },
            upsert=True,
        )
        document: dict[str, Any] = self._parametres().find_one({"_id": DOCUMENT})
        return document

    def lire(self) -> dict[str, Any]:
        document = self.assurer()
        return {
            "cle": document["cle"],
            "creee_le": _en_utc(document["creee_le"]),
            "changements": [_en_utc(d) for d in document["changements"]],
        }

    def invalider(self) -> dict[str, Any]:
        """Remplace la clé : l'ancienne est refusée aussitôt et n'est pas gardée."""
        maintenant = datetime.now(UTC)
        self._parametres().update_one(
            {"_id": DOCUMENT},
            {
                "$set": {"cle": _nouvelle_cle(), "creee_le": maintenant},
                "$push": {"changements": maintenant},
            },
            upsert=True,
        )
        return self.lire()

    def est_valide(self, cle: str | None) -> bool:
        if not cle:
            return False
        document = self._parametres().find_one({"_id": DOCUMENT}, {"cle": 1})
        return bool(document) and secrets.compare_digest(
            document["cle"].encode(), cle.encode()
        )


cle_ecoute_service = CleEcouteService()
