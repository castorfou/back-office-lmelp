# ruff: noqa  -- PROTOTYPE JETABLE (#421), jamais fusionné
import sys

import reperer as r
import reperer2 as r2


REF = {  # référence à l'écoute (#391) : début, fin
    "6af98629a3c9beafb9dcb702": {  # pragma: allowlist secret
        "Le Fondateur": "07:32",
        "Paradisi Gloria": "13:24",
        "Dans les grandes lignes": "19:20",
        "Rouge Truite": "26:53",
        "Saint Lucky Luke": "33:45",
        "Le Livre des souterrains": "40:16",
        "Vivre après": "41:51",
        "Je demande à en finir avec la vie": "43:04",
        "Comment j'ai cessé d'être une petite fasciste": "44:43",
    },
}


def s(m):
    a, b = m.split(":")
    return int(a) * 60 + int(b)


for eid in sys.argv[1:]:
    e = r.charger_entrees(eid)
    segs = r.segments_whisper(eid)
    res = r2.reperer_passages(segs, r.livres_du_resume(e["summary"]))
    ref = REF.get(eid, {})
    print(
        f"\n=== {e['date']} sommaire ignoré {[(r.hms(a), r.hms(b)) for a, b in res['sommaire_ignore']][:1]}"
    )
    for p in res["passages"]:
        d = ref.get(p["titre"])
        delta = f"Δ début {int(p['debut']) - s(d):+d} s" if d else ""
        print(
            f"  S{p['section']} {r.hms(p['debut'])}–{r.hms(p['fin'])} ({r.hms(p['fin'] - p['debut'])}) {'📣' if p.get('appel') else '  '} {p['titre'][:42]:42} {delta}"
        )
    for p in res["non_trouves"]:
        print("  NON TROUVÉ", p["titre"])
