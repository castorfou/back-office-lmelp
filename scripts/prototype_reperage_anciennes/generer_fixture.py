# ruff: noqa  -- PROTOTYPE JETABLE (#421), jamais fusionné
"""PROTOTYPE JETABLE (#421) — écrit les Passages du repérage v2 dans la fixture
des prototypes « Correction des passages » / livres-auteurs, pour les juger à
l'écoute.

    source /tmp/venv/bin/activate
    MONGODB_URL=mongodb://localhost:27018 PYTHONPATH=src \\
        python scripts/prototype_reperage_anciennes/generer_fixture.py
"""

import json
from pathlib import Path

import reperer as r
import reperer2 as r2


TEMOINS = {
    "6af98629a3c9beafb9dcb702": "référence à l'écoute (#391)",  # pragma: allowlist secret
    "6ac22e35a0c52ca090834c71": "retranscrit --max-context 0 (#425)",  # pragma: allowlist secret
    "6af47e76a1c0d162e8518b73": "ancien format, retranscrit --max-context 0",  # pragma: allowlist secret
    "6b061fd73a756aaf913fe936": "ancien format (pap), retranscrit --max-context 0",  # pragma: allowlist secret
}
FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "prototype_correction_passages"
    / "passages_temoins.json"
)

fx = json.loads(FIXTURE.read_text())
for eid, note in TEMOINS.items():
    e = r.charger_entrees(eid)
    res = r2.reperer_passages(r.segments_whisper(eid), r.livres_du_resume(e["summary"]))
    d = e["date"]
    fx[d] = {
        "date": d,
        "titre": f"Repérage v2 (#421) · {note}",
        "passages": [
            {
                "id": f"{d}-v2-{i}",
                "titre": p["titre"],
                "auteur": p["auteur"],
                "debut": round(p["debut"], 2),
                "fin": round(p["fin"], 2),
                "origine": "auto",
                "supprime": False,
            }
            for i, p in enumerate(res["passages"])
        ],
        "livres_sans_passage": [
            {"titre": p["titre"], "auteur": p["auteur"]} for p in res["non_trouves"]
        ],
        "simulation": None,
    }
    print(d, len(res["passages"]), "Passages,", len(res["non_trouves"]), "sans Passage")
FIXTURE.write_text(json.dumps(fx, ensure_ascii=False, indent=1) + "\n")
