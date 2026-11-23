"""PROTOTYPE JETABLE — repérage des Passages d'un épisode témoin (wayfinder #391).

Pas du code de production : aucun test, aucune gestion d'erreur. Sert à juger
à l'écoute si l'on peut situer début et fin de chaque Passage à ±10 s.

Usage :
    source /tmp/venv/bin/activate
    PYTHONPATH=src python scripts/prototype_reperage_passages/reperer.py

Entrées : ~/passages-temoins/<episode_id>.json (segments whisper.cpp -oj)
          + avis_critiques.summary dans MongoDB (lu une fois, mis en cache
          dans inputs/ pour relancer sans MongoDB).
Sortie  : passages.html (lecteur : choisir le .m4a de l'épisode sur sa machine).

Méthode (toute la logique est dans reperer_passages()) :
1. Livres du résumé : section 1 (débattus) et section 2 (coups de cœur).
2. Mentions : un segment mentionne un livre si son titre (fenêtre glissante,
   floue) ou un nom d'auteur (mot à mot, flou) y apparaît. Le voisinage
   immédiat (segment précédent + suivant) est inclus pour les segments courts.
3. Annonce du programme : toute fenêtre de 90 s qui mentionne au moins 3
   livres de la section 1 est ignorée (le sommaire du début d'émission).
4. Ordre : livres triés par la médiane de leur grappe de mentions la plus
   dense (fenêtre de 5 min).
5. Bornes :
   - section 2 (coups de cœur) : début = 1re rafale de mentions (2 en
     RAFALE_S) après le coup de cœur précédent ; fin = dernière mention
     avant le suivant (entre deux, il peut y avoir autre chose) ;
   - section 1 (débattus) : découpage contigu, frontières choisies parmi
     les phrases de transition de l'animatrice (« On enchaîne avec… »), par
     programmation dynamique (chaque bloc contient le plus de mentions de
     son livre ; une mention en passant ne pèse presque rien). Le dernier
     débattu finit à sa dernière mention.
6. Élargissement : MARGE_S de chaque côté (arrondi vers plus large).
"""

from __future__ import annotations

import json
import os
import re
import statistics
from pathlib import Path

from rapidfuzz import fuzz

from back_office_lmelp.utils.text_utils import normalize_for_matching

ICI = Path(__file__).parent
TEMOINS = Path.home() / "passages-temoins"
EPISODES = ["6af98629a3c9beafb9dcb702", "6ac22e35a0c52ca090834c71"]

MARGE_S = 5  # élargissement de chaque borne
RAFALE_S = 90  # 2 mentions dans cet intervalle pour ouvrir un Passage
SEUIL_TITRE = 85
SEUIL_AUTEUR = 85
TRANSITION = re.compile(
    r"\bon (commence|enchaine|continue|termine|poursuit|passe|finit)\b"
    r"|\bon va (parler|maintenant|debattre|continuer|terminer|finir|passer)\b"
    r"|\bpassons\b|\bapres (ce|cette)\b"
)
MOTS_VIDES = {"de", "du", "des", "la", "le", "les", "l", "d", "et", "un", "une"}


# ---------------------------------------------------------------- entrées
def charger_entrees(episode_id: str) -> dict:
    cache = ICI / "inputs" / f"{episode_id}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    from bson import ObjectId
    from pymongo import MongoClient

    db = MongoClient(os.environ["MONGODB_URL"])["masque_et_la_plume"]
    ep = db.episodes.find_one({"_id": ObjectId(episode_id)})
    avis = db.avis_critiques.find_one({"episode_oid": episode_id})
    data = {
        "episode_id": episode_id,
        "titre": ep["titre"],
        "date": ep["date"].strftime("%Y-%m-%d"),
        "audio_rel_filename": ep["audio_rel_filename"],
        "summary": avis["summary"],
    }
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return data


def livres_du_resume(summary: str) -> list[dict]:
    livres, section = [], None
    for ligne in summary.splitlines():
        if ligne.startswith("## 1."):
            section = 1
        elif ligne.startswith("## 2."):
            section = 2
        elif ligne.startswith("|") and section and not ligne.startswith("|-"):
            cols = [c.strip() for c in ligne.strip("|").split("|")]
            if cols[0] == "Auteur":
                continue
            livre = {"section": section, "auteur": cols[0], "titre": cols[1]}
            if section == 2:
                livre["critique"] = cols[3]
            livres.append(livre)
    return livres


def noms_auteur(auteur: str) -> list[str]:
    """Noms de famille (dernier mot de chaque personne), normalisés."""
    auteur = re.sub(r"\(.*?\)", "", auteur).replace("d'après", ",")
    noms = []
    for personne in auteur.split(","):
        mots = normalize_for_matching(personne).split()
        if mots:
            noms.append(mots[-1])
    return [n for n in noms if len(n) >= 4]


# ---------------------------------------------------------------- repérage
def mentionne(texte: str, livre: dict) -> str | None:
    mots = normalize_for_matching(texte).replace("'", " ").split()
    titre = [
        m for m in normalize_for_matching(livre["titre"]).replace("'", " ").split()
    ]
    titre_plein = [m for m in titre if m not in MOTS_VIDES] or titre
    n = len(titre_plein)
    pleins = [m for m in mots if m not in MOTS_VIDES]
    seuil = SEUIL_TITRE if n >= 2 else 92
    for i in range(max(1, len(pleins) - n + 1)):
        fenetre = " ".join(pleins[i : i + n])
        if fuzz.ratio(fenetre, " ".join(titre_plein)) >= seuil:
            return f"titre « {fenetre} »"
    # mots seuls et paires accolées (« L'Espade » → « lespade »)
    # (pas « de vie » → « devie » → Devi : seulement après une élision)
    candidats = mots + [a + b for a, b in zip(mots, mots[1:]) if len(a) == 1]
    for nom in noms_auteur(livre["auteur"]):
        for m in candidats:
            seuil = SEUIL_AUTEUR if len(nom) < 6 else SEUIL_AUTEUR - 5
            if len(m) >= 4 and fuzz.ratio(m, nom) >= seuil:
                return f"auteur « {m} »"
    return None


def reperer_passages(segments: list[dict], livres: list[dict]) -> dict:
    # segments : [{"debut": s, "fin": s, "texte": str}]
    textes = []
    for i, s in enumerate(segments):
        voisins = segments[max(0, i - 1) : i + 2]
        textes.append(" ".join(v["texte"] for v in voisins))

    for livre in livres:
        livre["mentions"] = []
        for i, s in enumerate(segments):
            raison = mentionne(textes[i], livre)
            if raison and mentionne(s["texte"], livre) is None:
                # le voisinage seul : on ne garde que s'il est court
                if s["fin"] - s["debut"] > 4:
                    continue
            if raison:
                livre["mentions"].append({"i": i, "t": s["debut"], "raison": raison})

    # 3. sommaire du début : fenêtres de 90 s avec >= 4 livres de section 1
    #    (3 ne suffit pas : conclusion de A + présentation de B + 1 faux)
    s1 = [lv for lv in livres if lv["section"] == 1]
    ignorees: list[tuple[float, float]] = []
    instants = sorted({m["t"] for lv in s1 for m in lv["mentions"]})
    for t0 in instants:
        n = sum(any(t0 <= m["t"] <= t0 + 90 for m in lv["mentions"]) for lv in s1)
        if n >= 4:
            ignorees.append((t0, t0 + 90))
    for livre in livres:
        for m in livre["mentions"]:
            m["sommaire"] = any(a <= m["t"] <= b for a, b in ignorees)
        livre["utiles"] = [m for m in livre["mentions"] if not m["sommaire"]]

    # 4. ordre par grappe la plus dense
    for livre in livres:
        ts = [m["t"] for m in livre["utiles"]]
        if not ts:
            livre["centre"] = None
            continue
        meilleure = max(
            ([t for t in ts if t0 <= t <= t0 + 300] for t0 in ts), key=len
        )
        livre["centre"] = statistics.median(meilleure)

    trouves = sorted((lv for lv in livres if lv["centre"] is not None),
                     key=lambda lv: (lv["section"], lv["centre"]))
    non_trouves = [lv for lv in livres if lv["centre"] is None]

    # 5. bornes
    def fin_seg(t: float) -> float:
        return next(s["fin"] for s in segments if s["debut"] == t)

    idx = {s["debut"]: i for i, s in enumerate(segments)}
    s1t = [lv for lv in trouves if lv["section"] == 1]
    s2t = [lv for lv in trouves if lv["section"] == 2]

    # 5a. coups de cœur : à la suite, chacun ouvert par une rafale de mentions
    derniere = max(lv["centre"] for lv in s1t) if s1t else 0
    prec = None
    for livre in s2t:
        if prec is not None:
            derniere = max([m["t"] for m in prec["utiles"]
                            if m["t"] < livre["centre"]], default=prec["centre"])
        apres = [m["t"] for m in livre["utiles"] if m["t"] > derniere]
        rafales = [t for t in apres if any(t < u <= t + RAFALE_S for u in apres)]
        livre["debut"] = min(rafales or apres or [livre["centre"]])
        prec = livre
    for k, livre in enumerate(s2t):
        limite = s2t[k + 1]["debut"] if k + 1 < len(s2t) else segments[-1]["fin"]
        avant = [m["t"] for m in livre["utiles"] if m["t"] < limite]
        livre["fin"] = fin_seg(max(avant)) if avant else livre["debut"]

    # 5b. débattus : découpage contigu de la section 1, dans l'ordre des
    # centres, qui maximise le nombre de mentions de chaque livre dans son
    # propre bloc (programmation dynamique). Une mention en passant d'un
    # autre livre ne pèse presque rien face à celles de son vrai débat.
    if s1t:
        a = idx[min(m["t"] for m in s1t[0]["utiles"] if m["t"] <= s1t[0]["centre"])]
        b = idx[s2t[0]["debut"]] if s2t else len(segments)
        n, M = len(s1t), b - a
        P = []  # P[k][j] = mentions du livre k dans les segments [a, a+j)
        for lv in s1t:
            marque = [0] * M
            for m in lv["utiles"]:
                if a <= idx[m["t"]] < b:
                    marque[idx[m["t"]] - a] = 1
            pk = [0]
            for v in marque:
                pk.append(pk[-1] + v)
            P.append(pk)
        NEG = -(10**9)
        # candidats : phrases de transition de l'animatrice (« On enchaîne
        # avec… »), sinon tous les segments
        cand = [j for j in range(1, M)
                if TRANSITION.search(normalize_for_matching(segments[a + j]["texte"]))]
        if len(cand) < n - 1:
            cand = list(range(1, M))
        cand = [0] + cand + [M]
        # dp2[k][c] : meilleur score des livres 0..k, bloc k finissant au
        # candidat c (exclu)
        dp2 = [[NEG] * len(cand) for _ in range(n)]
        arg2 = [[0] * len(cand) for _ in range(n)]
        for c in range(len(cand)):
            dp2[0][c] = P[0][cand[c]]
        for k in range(1, n):
            for c in range(len(cand)):
                for c0 in range(c):
                    v = dp2[k - 1][c0] + P[k][cand[c]] - P[k][cand[c0]]
                    if v > dp2[k][c]:
                        dp2[k][c], arg2[k][c] = v, c0
        c = len(cand) - 1
        coupes_t = [M]
        for k in range(n - 1, 0, -1):
            c = arg2[k][c]
            coupes_t.append(cand[c])
        coupes_t = [0] + coupes_t[::-1]
        bornes = [a + j for j in coupes_t[:-1]]
        for k, livre in enumerate(s1t):
            livre["debut"] = segments[bornes[k]]["debut"]
            if k + 1 < n:
                livre["fin"] = segments[bornes[k + 1]]["debut"]
            else:
                avant = [m["t"] for m in livre["utiles"] if idx[m["t"]] < b]
                livre["fin"] = fin_seg(max(avant))

    for livre in trouves:
        livre["debut_large"] = max(0, livre["debut"] - MARGE_S)
        livre["fin_large"] = livre["fin"] + MARGE_S

    return {"passages": trouves, "non_trouves": non_trouves,
            "sommaire_ignore": ignorees}


# ---------------------------------------------------------------- sortie
def segments_whisper(episode_id: str) -> list[dict]:
    d = json.loads((TEMOINS / f"{episode_id}.json").read_text())
    segs = []
    for s in d["transcription"]:
        texte = s["text"].strip()
        if not texte or set(texte) <= {".", " "}:
            continue  # scorie « ... » de la musique de fin
        segs.append({"debut": s["offsets"]["from"] / 1000,
                     "fin": s["offsets"]["to"] / 1000, "texte": texte})
    return segs


def hms(t: float) -> str:
    t = int(t)
    return f"{t // 60:02d}:{t % 60:02d}"


def main() -> None:
    episodes = []
    for eid in EPISODES:
        entrees = charger_entrees(eid)
        segs = segments_whisper(eid)
        livres = livres_du_resume(entrees["summary"])
        res = reperer_passages(segs, livres)
        print(f"\n=== {entrees['date']} {entrees['titre'][:60]}")
        for p in res["passages"]:
            print(f"  S{p['section']} {hms(p['debut_large'])} → {hms(p['fin_large'])}"
                  f"  ({hms(p['fin_large'] - p['debut_large'])})  {p['titre']}"
                  f"  [{len(p['utiles'])} mentions]")
        for p in res["non_trouves"]:
            print(f"  NON TROUVÉ : {p['titre']}")
        episodes.append({
            "id": eid, "date": entrees["date"], "titre": entrees["titre"],
            "audio": entrees["audio_rel_filename"],
            "segments": segs,
            "passages": [
                {k: p[k] for k in ("section", "titre", "auteur", "debut", "fin",
                                   "debut_large", "fin_large")}
                | {"critique": p.get("critique"),
                   "mentions": [{"t": m["t"], "raison": m["raison"]}
                                for m in p["utiles"]]}
                for p in res["passages"]
            ],
            "non_trouves": [p["titre"] for p in res["non_trouves"]],
        })
    gabarit = (ICI / "gabarit.html").read_text()
    sortie = gabarit.replace(
        "/*DONNEES*/null", json.dumps(episodes, ensure_ascii=False)
    ).replace("/*MARGE*/0", str(MARGE_S))
    (ICI / "passages.html").write_text(sortie)
    print(f"\n→ {ICI / 'passages.html'}")


if __name__ == "__main__":
    main()
