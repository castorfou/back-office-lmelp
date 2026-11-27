"""Repérage des Passages d'une émission (Issue #427).

Un Passage est la portion de l'audio d'une émission où les critiques parlent
d'un livre, débat compris. Le repérage le situe à partir des Segments
horodatés de la transcription whisper et des livres du résumé des avis
critiques. Fonction pure : ni lecture ni écriture MongoDB.

Règles, validées à l'écoute (#391) puis revues sur les émissions anciennes
(#421) :

- un Segment mentionne un livre si son titre (fenêtre glissante, comparaison
  floue) ou le nom de famille d'un auteur y figure, ponctuation et tirets
  ignorés ; les noms propres sont aussi comparés à la prononciation ;
- chaque livre est placé par sa grappe de mentions la plus dense ;
- livres débattus : découpage contigu aux phrases de transition, par
  programmation dynamique ; le premier commence à la transition qui précède
  son vrai débat (ni sommaire ni courrier des auditeurs) ;
- coups de cœur : contigus, chacun ouvert par l'appel de son critique
  (« Arnaud ? », « À toi, Nelly. »), sinon par sa première rafale de mentions ;
- pas de recouvrement : deux Passages voisins partagent une frontière.
"""

import re
import statistics
from dataclasses import dataclass, field
from typing import Any

from rapidfuzz import fuzz

from ..services.avis_extraction_service import AvisExtractionService
from .livres_ecartes import is_titre_ecarte
from .text_utils import normalize_for_matching as normaliser


@dataclass(frozen=True)
class Segment:
    """Un morceau horodaté de la transcription (ms dans l'audio de l'épisode)."""

    debut_ms: int
    fin_ms: int
    texte: str


@dataclass(frozen=True)
class LivreDuResume:
    """Un livre tel que le résumé le cite.

    section 1 : livre débattu au programme ; section 2 : coup de cœur,
    recommandé par `critique`.
    """

    section: int
    titre: str
    auteur: str
    editeur: str = ""
    critique: str = ""


@dataclass(frozen=True)
class PassageRepere:
    livre: LivreDuResume
    debut_ms: int
    fin_ms: int


@dataclass(frozen=True)
class Reperage:
    passages: list[PassageRepere] = field(default_factory=list)
    sans_passage: list[LivreDuResume] = field(default_factory=list)


# --------------------------------------------------------------- résumé
def livres_du_resume(
    resume: str, livres_ecartes: list[dict[str, Any]] | None = None
) -> list[LivreDuResume]:
    """Livres des sections 1 (débattus) et 2 (coups de cœur) du résumé.

    Les titres écartés (`avis_critiques.livres_ecartes`) ne sont pas des
    livres : ils n'ont pas de Passage.
    """
    livres = []
    section = 0
    for ligne in resume.splitlines():
        if ligne.startswith("## 1."):
            section = 1
        elif ligne.startswith("## 2."):
            section = 2
        elif ligne.startswith("## "):
            section = 0
        elif section and ligne.startswith("|") and not ligne.startswith("|-"):
            cellules = AvisExtractionService._split_table_row(ligne)
            if len(cellules) < 3 or cellules[0] in ("Auteur", ""):
                continue
            auteur, titre, editeur = cellules[0], cellules[1], cellules[2]
            if not titre or is_titre_ecarte(titre, livres_ecartes):
                continue
            critique = cellules[3] if section == 2 and len(cellules) > 3 else ""
            livres.append(LivreDuResume(section, titre, auteur, editeur, critique))
    return livres


# -------------------------------------------------------------- mentions
MOTS_VIDES = {"de", "du", "des", "la", "le", "les", "l", "d", "et", "un", "une"}
PONCTUATION = re.compile(r"[.,;:!?«»\"()…]")
SEUIL_TITRE = 85
SEUIL_TITRE_UN_MOT = 92
SEUIL_AUTEUR = 85
SEUIL_AUTEUR_LONG = 80  # noms de 6 lettres et plus
SEUIL_NOM_COMPOSE = 88
SEUIL_PHONETIQUE = 86


def _noms_auteur(auteur: str) -> list[str]:
    """Noms de famille (dernier mot de chaque personne), normalisés."""
    auteur = re.sub(r"\(.*?\)", "", auteur).replace("d'après", ",")
    noms = []
    for personne in auteur.split(","):
        mots = normaliser(personne).split()
        if mots:
            noms.append(mots[-1])
    return [n for n in noms if len(n) >= 4]


def phonetique(mot: str) -> str:
    """Clé de prononciation française grossière : Gény = Jenni (« jeni »).

    Accents, tirets, apostrophes et h supprimés ; w→v, y→i, ph→f, qu→k ;
    g→j et c→s devant e/i, c→k sinon ; lettres doublées réduites ; finale
    muette retirée.
    """
    m = normaliser(mot).replace("-", "").replace("'", "")
    for avant, apres in (("ph", "f"), ("qu", "k"), ("w", "v"), ("y", "i"), ("h", "")):
        m = m.replace(avant, apres)
    m = re.sub(r"g(?=[ei])", "j", m)
    m = re.sub(r"c(?=[ei])", "s", m)
    m = m.replace("c", "k")
    m = re.sub(r"(.)\1+", r"\1", m)
    return re.sub(r"(es|e|s|t|x|d)$", "", m)


def _mentionne_titre_ou_auteur(texte: str, livre: LivreDuResume) -> bool:
    mots = normaliser(texte).replace("'", " ").split()
    titre = normaliser(livre.titre).replace("'", " ").split()
    titre_plein = [m for m in titre if m not in MOTS_VIDES] or titre
    n = len(titre_plein)
    pleins = [m for m in mots if m not in MOTS_VIDES]
    seuil = SEUIL_TITRE if n >= 2 else SEUIL_TITRE_UN_MOT
    cible = " ".join(titre_plein)
    for i in range(max(1, len(pleins) - n + 1)):
        if fuzz.ratio(" ".join(pleins[i : i + n]), cible) >= seuil:
            return True
    # mots seuls et paires accolées après une élision (« L'Espade » → « lespade »)
    candidats = mots + [
        a + b for a, b in zip(mots, mots[1:], strict=False) if len(a) == 1
    ]
    for nom in _noms_auteur(livre.auteur):
        seuil = SEUIL_AUTEUR if len(nom) < 6 else SEUIL_AUTEUR_LONG
        if any(len(m) >= 4 and fuzz.ratio(m, nom) >= seuil for m in candidats):
            return True
    return False


def _noms_propres(livre: LivreDuResume) -> list[str]:
    """Noms d'auteur sans tiret et mots à majuscule au milieu du titre."""
    mots_titre = re.sub(r"[^\w\s'-]", " ", livre.titre).replace("'", " ").split()
    propres = [w for w in mots_titre[1:] if w[:1].isupper() and len(w) >= 6]
    return propres + [n.replace("-", "") for n in _noms_auteur(livre.auteur)]


def _mentionne_nom_propre(texte: str, livre: LivreDuResume) -> bool:
    mots = normaliser(texte).replace("'", " ").replace("-", " ").split()
    paires = [a + b for a, b in zip(mots, mots[1:], strict=False)]
    # nom composé écrit en un ou deux mots : « blangras », « blanc gras »
    for nom in (n.replace("-", "") for n in _noms_auteur(livre.auteur)):
        if len(nom) >= 8 and any(
            len(m) >= 6 and fuzz.ratio(m, nom) >= SEUIL_NOM_COMPOSE
            for m in mots + paires
        ):
            return True
    # prononciation : « Gény » pour Jenni, « Valènes-âmes » pour Walenhammes
    cles = [phonetique(w) for w in mots]
    cles += [a + b for a, b in zip(cles, cles[1:], strict=False)]
    for nom in _noms_propres(livre):
        cle = phonetique(nom)
        if len(cle) >= 4 and any(
            abs(len(m) - len(cle)) <= 3 and fuzz.ratio(m, cle) >= SEUIL_PHONETIQUE
            for m in cles
        ):
            return True
    return False


def mentionne(texte: str, livre: LivreDuResume) -> bool:
    """Le texte cite-t-il le livre (titre ou nom d'auteur) ?"""
    texte = PONCTUATION.sub(" ", texte)
    return _mentionne_titre_ou_auteur(texte, livre) or _mentionne_nom_propre(
        texte, livre
    )


# ----------------------------------------------------- transitions, appels
TRANSITION = re.compile(
    r"\bon (commence|enchaine|continue|termine|poursuit|passe|finit)\b"
    r"|\bon va (parler|maintenant|debattre|continuer|terminer|finir|passer)\b"
    r"|\bpassons\b|\bapres (ce|cette)\b"
    r"|\bqui ouvre\b|\bj'ouvre\b|\bouvre le programme\b"
    r"|\bpremier livre\b|\ble livre suivant\b"
    # présentation d'un livre : « c'est La nuit des Valènes-âmes, chez Gallimard »
    r"|\bc'est\b.{0,80}\bchez\b"
)
APPEL_MOTS_MAX = 6


def est_transition(texte: str) -> bool:
    return bool(TRANSITION.search(normaliser(texte)))


def _prenom(critique: str) -> str | None:
    mots = normaliser(re.sub(r"\(.*?\)", "", critique)).split()
    return mots[0] if mots else None


def est_appel(texte: str, critique: str) -> bool:
    """Le présentateur passe-t-il la parole au critique ?

    Son prénom dans une phrase courte (« Arnaud ? », « À toi, Nelly. »,
    « celui de Nelly d'abord ») ou suivi d'un point d'interrogation en fin de
    phrase (« … du sous-sol. Arnaud ? »). Une phrase longue qui cite le
    critique en plein débat n'est pas un appel.
    """
    prenom = _prenom(critique)
    if not prenom:
        return False
    t = normaliser(texte)
    if not re.search(rf"\b{re.escape(prenom)}\b", t):
        return False
    courte = len(PONCTUATION.sub(" ", t).split()) <= APPEL_MOTS_MAX
    return courte or bool(re.search(rf"\b{re.escape(prenom)} ?\?\s*$", t))


# ------------------------------------------------------------- repérage
GRAPPE_MS = 300_000  # fenêtre de la grappe la plus dense
RAFALE_MS = 90_000  # 2 mentions dans cet intervalle ouvrent un coup de cœur
CHAINE_MS = 90_000  # mentions qui s'enchaînent vers le début d'un débat
APPEL_AVANT_MS = 60_000  # l'appel du critique précède sa rafale de moins d'1 min
SEGMENT_LONG_MS = 4_000  # au-delà, le voisinage seul ne suffit pas
TRANSITIONS_AVANT = 40  # Segments examinés avant le premier débat


@dataclass
class _Livre:
    livre: LivreDuResume
    mentions: list[int]  # index des Segments qui le mentionnent
    centre_ms: float = 0.0
    grappe_debut: int = 0
    debut: int = 0  # index du Segment de début
    fin_ms: int = 0


def _utile(texte: str) -> bool:
    texte = texte.strip()
    return bool(texte) and not set(texte) <= {".", " "}


def _mentions(segments: list[Segment], livre: LivreDuResume) -> list[int]:
    trouvees = []
    for i, seg in enumerate(segments):
        voisinage = " ".join(s.texte for s in segments[max(0, i - 1) : i + 2])
        if not mentionne(voisinage, livre):
            continue
        # le voisinage seul ne vaut que pour un Segment court
        if seg.fin_ms - seg.debut_ms > SEGMENT_LONG_MS and not mentionne(
            seg.texte, livre
        ):
            continue
        trouvees.append(i)
    return trouvees


def _placer(item: _Livre, segments: list[Segment]) -> None:
    """Centre et début de la grappe de mentions la plus dense."""
    ts = [segments[i].debut_ms for i in item.mentions]
    grappes = [[t for t in ts if t0 <= t <= t0 + GRAPPE_MS] for t0 in ts]
    meilleure = max(grappes, key=len)
    item.centre_ms = statistics.median(meilleure)
    item.grappe_debut = min(meilleure)


def _coups_de_coeur(
    items: list[_Livre], segments: list[Segment], plancher_ms: float
) -> list[_Livre]:
    """Place les coups de cœur à la suite ; rend ceux qui ont un Passage.

    Un coup de cœur jamais cité après le coup de cœur précédent (ou après
    les débats) n'a pas été présenté, ou pas reconnu : pas de Passage.
    """
    places = []
    for item in items:
        ts = [segments[i].debut_ms for i in item.mentions]
        apres = [t for t in ts if t > plancher_ms]
        if not apres:
            continue
        rafales = [t for t in apres if any(t < u <= t + RAFALE_MS for u in apres)]
        premier = min(rafales or apres)
        appels = [
            i
            for i, seg in enumerate(segments)
            if plancher_ms < seg.debut_ms <= premier
            and premier - seg.debut_ms <= APPEL_AVANT_MS
            and est_appel(seg.texte, item.livre.critique)
        ]
        # l'appel le plus proche de la présentation du livre : une phrase
        # courte qui cite le critique plus tôt (plaisanterie, aparté) n'est
        # pas la passation de parole
        if appels:
            item.debut = max(appels)
        else:
            item.debut = next(
                i for i, seg in enumerate(segments) if seg.debut_ms == premier
            )
        plancher_ms = segments[item.debut].debut_ms
        places.append(item)
    for k, item in enumerate(places):
        if k + 1 < len(places):
            item.fin_ms = segments[places[k + 1].debut].debut_ms
        else:
            item.fin_ms = segments[max(item.mentions)].fin_ms
    return places


def _premier_debat(item: _Livre, segments: list[Segment]) -> int:
    """Index du début du premier débattu : la transition qui précède son débat."""
    ts = sorted(segments[i].debut_ms for i in item.mentions)
    debut = item.grappe_debut
    for t in reversed([t for t in ts if t < debut]):
        if debut - t > CHAINE_MS:
            break
        debut = t
    i1 = next(i for i, seg in enumerate(segments) if seg.debut_ms == debut)
    transitions = [
        j
        for j in range(max(0, i1 - TRANSITIONS_AVANT), i1 + 1)
        if est_transition(segments[j].texte)
    ]
    return transitions[-1] if transitions else i1


def _debattus(items: list[_Livre], segments: list[Segment], fin_index: int) -> None:
    """Découpage contigu aux transitions, chaque bloc gardant ses mentions."""
    a = _premier_debat(items[0], segments)
    n, taille = len(items), fin_index - a
    cumuls = []
    for item in items:
        marque = [0] * taille
        for i in item.mentions:
            if a <= i < fin_index:
                marque[i - a] = 1
        cumul = [0]
        for v in marque:
            cumul.append(cumul[-1] + v)
        cumuls.append(cumul)
    candidats = [j for j in range(1, taille) if est_transition(segments[a + j].texte)]
    if len(candidats) < n - 1:
        candidats = list(range(1, taille))
    candidats = [0, *candidats, taille]
    moins_infini = -(10**9)
    score = [[moins_infini] * len(candidats) for _ in range(n)]
    precedent = [[0] * len(candidats) for _ in range(n)]
    for c in range(len(candidats)):
        score[0][c] = cumuls[0][candidats[c]]
    for k in range(1, n):
        for c in range(len(candidats)):
            for c0 in range(c):
                v = (
                    score[k - 1][c0]
                    + cumuls[k][candidats[c]]
                    - cumuls[k][candidats[c0]]
                )
                if v > score[k][c]:
                    score[k][c], precedent[k][c] = v, c0
    c = len(candidats) - 1
    coupes = [taille]
    for k in range(n - 1, 0, -1):
        c = precedent[k][c]
        coupes.append(candidats[c])
    coupes = [0, *coupes[::-1]]
    for k, item in enumerate(items):
        item.debut = a + coupes[k]
        if k + 1 < n:
            item.fin_ms = segments[a + coupes[k + 1]].debut_ms
        elif fin_index < len(segments):
            item.fin_ms = segments[fin_index].debut_ms
        else:
            item.fin_ms = segments[max(item.mentions)].fin_ms


def reperer_passages(segments: list[Segment], livres: list[LivreDuResume]) -> Reperage:
    """Situe le Passage de chaque livre du résumé dans l'émission."""
    segments = [s for s in segments if _utile(s.texte)]
    if not segments:
        return Reperage(sans_passage=list(livres))

    items = [_Livre(livre, _mentions(segments, livre)) for livre in livres]
    trouves = [it for it in items if it.mentions]
    for item in trouves:
        _placer(item, segments)
    trouves.sort(key=lambda it: (it.livre.section, it.centre_ms))
    debattus = [it for it in trouves if it.livre.section == 1]
    coups = [it for it in trouves if it.livre.section == 2]

    plancher = max((it.centre_ms for it in debattus), default=0)
    coups = _coups_de_coeur(coups, segments, plancher)
    if debattus:
        _debattus(debattus, segments, coups[0].debut if coups else len(segments))

    places = debattus + coups
    return Reperage(
        passages=[
            PassageRepere(it.livre, segments[it.debut].debut_ms, it.fin_ms)
            for it in places
        ],
        sans_passage=[it.livre for it in items if it not in places],
    )
