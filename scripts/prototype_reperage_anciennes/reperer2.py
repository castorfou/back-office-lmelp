# ruff: noqa  -- PROTOTYPE JETABLE (#421), jamais fusionné
"""PROTOTYPE JETABLE — repérage v2 sur émissions anciennes (wayfinder #421).

Reprend reperer.py (#391) et applique :
- les règles validées à l'écoute (#391, #398) : Passages contigus, coups de
  cœur compris, un coup de cœur commence à l'appel du critique (« Arnaud ? »),
  fin = début du suivant ;
- les corrections relevées sur 2015/2024 (#421) :
  1. sommaire : >= 3 livres de section 1 en 90 s, dans les 6 premières minutes ;
     tout ce qui précède le premier débattu reste hors Passage (trou) ;
  2. noms : tirets et espaces ignorés (« Blanc-Gras » = « blanc gras ») ;
     égalité de grappes : celle qui contient le titre gagne ;
  3. transitions : « qui ouvre », « premier livre », « on commence » ;
     le premier débattu commence à sa transition, pas au début de l'émission.
"""

from __future__ import annotations

import re
import statistics

import reperer as r
from rapidfuzz import fuzz

from back_office_lmelp.utils.text_utils import normalize_for_matching as N


TRANSITION = re.compile(
    r"\bon (commence|enchaine|continue|termine|poursuit|passe|finit)\b"
    r"|\bon va (parler|maintenant|debattre|continuer|terminer|finir|passer)\b"
    r"|\bpassons\b|\bapres (ce|cette)\b"
    r"|\bqui ouvre\b|\bj'ouvre\b|\bouvre le programme\b|\bpremier livre\b|\ble livre suivant\b"
    # présentation d'un livre : « c'est La nuit des Valènes-âmes, chez Gallimard »
    r"|\bc'est\b.{0,80}\bchez\b"
)
SOMMAIRE_FIN_S = 360  # le sommaire est dans les 6 premières minutes
SOMMAIRE_MIN_LIVRES = 3
# R1 (#421, à l'essai) : "comptage" = sommaire écarté s'il cite >= 3 livres ;
# "grappe" = pas de sommaire, le premier débattu commence à la transition qui
# précède sa grappe de mentions la plus dense (son vrai débat)
DEPART = "grappe"


def noms_auteur(auteur: str) -> list[str]:
    return [n.replace("-", "") for n in r.noms_auteur(auteur)]


PONCT = re.compile(r"[.,;:!?«»\"()…]")


def mentionne(texte: str, livre: dict) -> str | None:
    # la ponctuation (revenue avec --max-context 0) colle aux noms : « salasque, »
    texte = PONCT.sub(" ", texte)
    raison = r.mentionne(texte, livre)
    if raison:
        return raison
    # nom composé : tiret ignoré, écrit en un ou deux mots (« blangras », « blanc gras »)
    mots = N(texte).replace("'", " ").replace("-", " ").split()
    candidats = mots + [a + b for a, b in zip(mots, mots[1:])]
    for nom in noms_auteur(livre["auteur"]):
        if len(nom) >= 8:
            for m in candidats:
                if len(m) >= 6 and fuzz.ratio(m, nom) >= 88:
                    return f"auteur « {m} »"
    return mentionne_phonetique(texte, livre)


def phonetique(mot: str) -> str:
    """Clé de prononciation française grossière : Gény = Jenni, Walenham = Valènes-âmes."""
    m = N(mot).replace("-", "").replace("'", "")
    for a, b in (("ph", "f"), ("qu", "k"), ("w", "v"), ("y", "i"), ("h", "")):
        m = m.replace(a, b)
    m = re.sub(r"g(?=[ei])", "j", m)
    m = re.sub(r"c(?=[ei])", "s", m)
    m = m.replace("c", "k")
    m = re.sub(r"(.)\1+", r"\1", m)
    m = re.sub(r"(es|e|s|t|x|d)$", "", m)
    return m


def mentionne_phonetique(texte: str, livre: dict) -> str | None:
    """Repli : mots rares du titre et noms d'auteur comparés à la prononciation."""
    mots = [
        w for w in N(PONCT.sub(" ", texte)).replace("'", " ").replace("-", " ").split()
    ]
    cles = [phonetique(w) for w in mots]
    cles += [a + b for a, b in zip(cles, cles[1:])]  # « valènes âmes » → un mot
    # noms propres seulement : mots à majuscule hors début du titre, noms d'auteur
    mots_titre = re.sub(r"[^\w\s'-]", " ", livre["titre"]).replace("'", " ").split()
    cibles = [w for w in mots_titre[1:] if w[:1].isupper() and len(w) >= 6]
    cibles += noms_auteur(livre["auteur"])
    for c in cibles:
        k = phonetique(c)
        if len(k) < 4:
            continue
        for m in cles:
            if abs(len(m) - len(k)) <= 3 and fuzz.ratio(m, k) >= 86:
                return f"phonétique « {m} » ≈ {c}"
    return None


def prenom(critique: str | None) -> str | None:
    if not critique:
        return None
    mots = N(re.sub(r"\(.*?\)", "", critique)).split()
    return mots[0] if mots else None


def est_appel(texte: str, pn: str | None) -> bool:
    """« Arnaud ? », « Et vous, Arnaud ? », « Arnaud » seul."""
    if not pn:
        return False
    t = N(texte).strip(" .!")
    # « Arnaud ? », « Anna. », ou en fin de phrase : « … du sous-sol. Arnaud ? »
    return bool(
        re.fullmatch(rf"(et vous,? |alors,? )?{pn} ?\??", t)
        or re.search(rf"(^|[.!?] ){pn} \?$", t)
    )


def reperer_passages(segments: list[dict], livres: list[dict]) -> dict:
    textes = []
    for i in range(len(segments)):
        voisins = segments[max(0, i - 1) : i + 2]
        textes.append(" ".join(v["texte"] for v in voisins))
    idx = {s["debut"]: i for i, s in enumerate(segments)}

    for livre in livres:
        livre["mentions"] = []
        for i, s in enumerate(segments):
            raison = mentionne(textes[i], livre)
            if (
                raison
                and mentionne(s["texte"], livre) is None
                and s["fin"] - s["debut"] > 4
            ):
                continue
            if raison:
                livre["mentions"].append(
                    {
                        "i": i,
                        "t": s["debut"],
                        "raison": raison,
                        "titre": raison.startswith("titre"),
                    }
                )

    # 1. sommaire : fenêtre de 90 s du début avec >= 3 livres de section 1
    s1 = [lv for lv in livres if lv["section"] == 1]
    ignorees = []
    instants = sorted(
        {m["t"] for lv in s1 for m in lv["mentions"] if m["t"] < SOMMAIRE_FIN_S}
    )
    for t0 in instants:
        n = sum(any(t0 <= m["t"] <= t0 + 90 for m in lv["mentions"]) for lv in s1)
        if DEPART == "comptage" and n >= SOMMAIRE_MIN_LIVRES:
            ignorees.append((t0, t0 + 90))
    for livre in livres:
        livre["utiles"] = [
            m
            for m in livre["mentions"]
            if not any(a <= m["t"] <= b for a, b in ignorees)
        ]

    # 2. ordre par grappe la plus dense ; à égalité, celle qui contient le titre
    for livre in livres:
        u = livre["utiles"]
        if not u:
            livre["centre"] = None
            continue
        grappes = [[m for m in u if m0["t"] <= m["t"] <= m0["t"] + 300] for m0 in u]
        meilleure = max(grappes, key=lambda g: (len(g), any(m["titre"] for m in g)))
        livre["centre"] = statistics.median(m["t"] for m in meilleure)
        livre["grappe_debut"] = min(m["t"] for m in meilleure)

    trouves = sorted(
        (lv for lv in livres if lv["centre"] is not None),
        key=lambda lv: (lv["section"], lv["centre"]),
    )
    non_trouves = [lv for lv in livres if lv["centre"] is None]
    s1t = [lv for lv in trouves if lv["section"] == 1]
    s2t = [lv for lv in trouves if lv["section"] == 2]

    def fin_seg(t: float) -> float:
        return segments[idx[t]]["fin"]

    # 3. coups de cœur : début = appel du critique avant la 1re rafale de
    #    mentions (après le coup de cœur précédent), sinon la rafale
    plancher = max((lv["centre"] for lv in s1t), default=0)
    for livre in s2t:
        apres = [m["t"] for m in livre["utiles"] if m["t"] > plancher]
        rafales = [t for t in apres if any(t < u <= t + r.RAFALE_S for u in apres)]
        premier = min(rafales or apres or [livre["centre"]])
        pn = prenom(livre.get("critique"))
        appels = [
            s["debut"]
            for s in segments
            if plancher < s["debut"] <= premier
            and premier - s["debut"] <= 60
            and est_appel(s["texte"], pn)
        ]
        livre["debut"] = min(appels) if appels else premier
        livre["appel"] = bool(appels)
        plancher = livre["debut"]
    # contigus : fin = début du suivant ; le dernier finit à sa dernière mention
    for k, livre in enumerate(s2t):
        if k + 1 < len(s2t):
            livre["fin"] = s2t[k + 1]["debut"]
        else:
            livre["fin"] = fin_seg(max(m["t"] for m in livre["utiles"]))

    # 4. débattus : comme #391 (programmation dynamique sur les transitions),
    #    mais le premier commence à la transition qui précède sa 1re mention utile
    if s1t:
        if DEPART == "grappe":
            # remonter de la grappe par les mentions qui s'enchaînent à < 90 s
            ts = sorted(m["t"] for m in s1t[0]["utiles"])
            t1 = s1t[0]["grappe_debut"]
            for t in reversed([t for t in ts if t < t1]):
                if t1 - t > 90:
                    break
                t1 = t
        else:
            t1 = min(m["t"] for m in s1t[0]["utiles"])
        i1 = idx[t1]
        trans = [
            j
            for j in range(max(0, i1 - 40), i1 + 1)
            if TRANSITION.search(N(segments[j]["texte"]))
        ]
        a = trans[-1] if trans else i1
        b = idx[s2t[0]["debut"]] if s2t else len(segments)
        n, M = len(s1t), b - a
        P = []
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
        cand = [
            j for j in range(1, M) if TRANSITION.search(N(segments[a + j]["texte"]))
        ]
        if len(cand) < n - 1:
            cand = list(range(1, M))
        cand = [0] + cand + [M]
        dp = [[NEG] * len(cand) for _ in range(n)]
        arg = [[0] * len(cand) for _ in range(n)]
        for c in range(len(cand)):
            dp[0][c] = P[0][cand[c]]
        for k in range(1, n):
            for c in range(len(cand)):
                for c0 in range(c):
                    v = dp[k - 1][c0] + P[k][cand[c]] - P[k][cand[c0]]
                    if v > dp[k][c]:
                        dp[k][c], arg[k][c] = v, c0
        c = len(cand) - 1
        coupes = [M]
        for k in range(n - 1, 0, -1):
            c = arg[k][c]
            coupes.append(cand[c])
        coupes = [0] + coupes[::-1]
        bornes = [a + j for j in coupes[:-1]]
        for k, livre in enumerate(s1t):
            livre["debut"] = segments[bornes[k]]["debut"]
            livre["fin"] = (
                segments[bornes[k + 1]]["debut"]
                if k + 1 < n
                else (
                    s2t[0]["debut"]
                    if s2t
                    else fin_seg(max(m["t"] for m in livre["utiles"]))
                )
            )

    return {
        "passages": trouves,
        "non_trouves": non_trouves,
        "sommaire_ignore": ignorees,
    }
