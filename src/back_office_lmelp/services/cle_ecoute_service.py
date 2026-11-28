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


def _est_complet(document: dict[str, Any] | None) -> bool:
    if not document:
        return False
    return (
        isinstance(document.get("cle"), str)
        and bool(document["cle"])
        and isinstance(document.get("creee_le"), datetime)
        and isinstance(document.get("changements"), list)
    )


class CleEcouteService:
    def _parametres(self) -> Any:
        return mongodb_service.get_collection("parametres")

    def assurer(self) -> dict[str, Any]:
        """Crée la clé si elle n'existe pas encore (ou si son document est
        incomplet), et renvoie le document."""
        document: dict[str, Any] | None = self._parametres().find_one({"_id": DOCUMENT})
        if document is not None and _est_complet(document):
            return document
        neuf = {
            "_id": DOCUMENT,
            "cle": _nouvelle_cle(),
            "creee_le": datetime.now(UTC),
            "changements": [],
        }
        self._parametres().replace_one({"_id": DOCUMENT}, neuf, upsert=True)
        return neuf

    def lire(self) -> dict[str, Any]:
        document = self.assurer()
        return {
            "cle": document["cle"],
            "creee_le": _en_utc(document["creee_le"]),
            "changements": [_en_utc(d) for d in document["changements"]],
        }

    def invalider(self) -> dict[str, Any]:
        """Remplace la clé : l'ancienne est refusée aussitôt et n'est pas gardée."""
        self.assurer()
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
        attendue = (document or {}).get("cle")
        if not isinstance(attendue, str) or not attendue:
            return False
        return secrets.compare_digest(attendue.encode(), cle.encode())


cle_ecoute_service = CleEcouteService()
