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
  son vrai débat (ni sommaire ni courrier des auditeurs) ; le débat d'un livre
  non reconnu reste dans le Passage du livre précédent ;
- coups de cœur : contigus, chacun ouvert par l'appel de son critique
  (« Arnaud ? », « À toi, Nelly. »), sinon par sa première rafale de mentions ;
  un coup de cœur jamais cité après le précédent n'a pas de Passage ;
- pas de recouvrement : deux Passages voisins partagent une frontière.
"""

import re
import statistics
from dataclasses import dataclass, field
from enum import IntEnum
from functools import lru_cache
from typing import Any

from rapidfuzz import fuzz

from ..services.avis_extraction_service import AvisExtractionService
from .livres_ecartes import is_titre_ecarte
from .text_utils import normalize_for_matching


class Section(IntEnum):
    """Section du résumé où le livre est cité."""

    DEBATTU = 1  # « 1. Livres discutés au programme »
    COUP_DE_COEUR = 2  # « 2. Coups de cœur des critiques »


@dataclass(frozen=True)
class Segment:
    """Un morceau horodaté de la transcription (ms dans l'audio de l'épisode)."""

    debut_ms: int
    fin_ms: int
    texte: str


@dataclass(frozen=True)
class LivreDuResume:
    """Un livre tel que le résumé le cite ; `critique` recommande un coup de cœur."""

    section: Section
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
    """Livres débattus (section 1) et coups de cœur (section 2) du résumé.

    Les titres écartés (`avis_critiques.livres_ecartes`) ne sont pas des
    livres. Une cellule Critique entre parenthèses (« (Déjà dans le programme
    principal…) ») est une remarque du LLM, pas un coup de cœur.
    """
    livres = []
    section: Section | None = None
    for ligne in resume.splitlines():
        if ligne.startswith("## 1."):
            section = Section.DEBATTU
        elif ligne.startswith("## 2."):
            section = Section.COUP_DE_COEUR
        elif ligne.startswith("## "):
            section = None
        elif section and ligne.startswith("|") and not ligne.startswith("|-"):
            cellules = AvisExtractionService._split_table_row(ligne)
            if len(cellules) < 3 or cellules[0] in ("Auteur", ""):
                continue
            auteur, titre, editeur = cellules[0], cellules[1], cellules[2]
            critique = ""
            if section == Section.COUP_DE_COEUR and len(cellules) > 3:
                critique = cellules[3]
                if critique.startswith("("):
                    continue
            if titre and not is_titre_ecarte(titre, livres_ecartes):
                livres.append(LivreDuResume(section, titre, auteur, editeur, critique))
    return livres


# -------------------------------------------------------------- mentions
MOTS_VIDES = {"de", "du", "des", "la", "le", "les", "l", "d", "et", "un", "une"}
PONCTUATION = re.compile(r"[.,;:!?«»\"()…]")
PARENTHESES = re.compile(r"\(.*?\)")
SEUIL_TITRE = 85
SEUIL_TITRE_UN_MOT = 92
SEUIL_AUTEUR = 85
SEUIL_AUTEUR_LONG = 80  # noms de 6 lettres et plus
SEUIL_NOM_COMPOSE = 88
SEUIL_PHONETIQUE = 86
NOM_COURT = 4  # en dessous, le nom doit être écrit tel quel (« Luz », « Jul »)


# Le repérage teste chaque Segment contre chaque livre : ce qui ne dépend que
# du texte (mots, clés phonétiques) est calculé une fois, puis mis en cache.
@lru_cache(maxsize=20_000)
def _mots(texte: str) -> tuple[str, ...]:
    return tuple(normalize_for_matching(texte).replace("'", " ").split())


def _paires(mots: tuple[str, ...]) -> list[str]:
    """Mots voisins accolés : « blanc gras » → « blancgras »."""
    return [a + b for a, b in zip(mots, mots[1:], strict=False)]


@lru_cache(maxsize=2_000)
def _noms_auteur(auteur: str) -> tuple[str, ...]:
    """Nom de famille (dernier mot) de chaque personne, normalisé.

    Personnes séparées par une virgule, « et » ou « & » ; « d'après » sépare
    l'adaptateur de l'auteur adapté.
    """
    auteur = PARENTHESES.sub("", auteur).replace("d'après", ",")
    noms = []
    for personne in re.split(r",| et | & ", auteur):
        mots = normalize_for_matching(personne).split()
        if mots and len(mots[-1]) >= 3:
            noms.append(mots[-1])
    return tuple(noms)


def _nom_sans_tiret(nom: str) -> str:
    return nom.replace("-", "")


@lru_cache(maxsize=50_000)
def phonetique(mot: str) -> str:
    """Clé de prononciation française grossière : Gény = Jenni (« jeni »).

    Accents, tirets, apostrophes et h supprimés ; w→v, y→i, ph→f, qu→k ;
    g→j et c→s devant e/i, c→k sinon ; lettres doublées réduites ; finale
    muette retirée.
    """
    cle = _nom_sans_tiret(normalize_for_matching(mot)).replace("'", "")
    for avant, apres in (("ph", "f"), ("qu", "k"), ("w", "v"), ("y", "i"), ("h", "")):
        cle = cle.replace(avant, apres)
    cle = re.sub(r"g(?=[ei])", "j", cle)
    cle = re.sub(r"c(?=[ei])", "s", cle)
    cle = cle.replace("c", "k")
    cle = re.sub(r"(.)\1+", r"\1", cle)
    return re.sub(r"(es|e|s|t|x|d)$", "", cle)


def _cite_le_titre(mots: tuple[str, ...], livre: LivreDuResume) -> bool:
    titre = _mots(livre.titre)
    titre_plein = [m for m in titre if m not in MOTS_VIDES] or titre
    taille = len(titre_plein)
    pleins = [m for m in mots if m not in MOTS_VIDES]
    seuil = SEUIL_TITRE if taille >= 2 else SEUIL_TITRE_UN_MOT
    cible = " ".join(titre_plein)
    return any(
        fuzz.ratio(" ".join(pleins[i : i + taille]), cible) >= seuil
        for i in range(max(1, len(pleins) - taille + 1))
    )


def _cite_un_auteur(mots: tuple[str, ...], livre: LivreDuResume) -> bool:
    # mots seuls et paires accolées après une élision (« L'Espade » → « lespade »)
    candidats = list(mots) + [
        a + b for a, b in zip(mots, mots[1:], strict=False) if len(a) == 1
    ]
    for nom in _noms_auteur(livre.auteur):
        if len(nom) < NOM_COURT:
            if nom in mots:
                return True
            continue
        seuil = SEUIL_AUTEUR if len(nom) < 6 else SEUIL_AUTEUR_LONG
        if any(len(m) >= NOM_COURT and fuzz.ratio(m, nom) >= seuil for m in candidats):
            return True
    return False


def _noms_propres(livre: LivreDuResume) -> list[str]:
    """Noms d'auteur sans tiret et mots à majuscule au milieu du titre."""
    mots_titre = re.sub(r"[^\w\s'-]", " ", livre.titre).replace("'", " ").split()
    propres = [w for w in mots_titre[1:] if w[:1].isupper() and len(w) >= 6]
    return propres + [_nom_sans_tiret(n) for n in _noms_auteur(livre.auteur)]


@lru_cache(maxsize=20_000)
def _mots_et_cles(texte: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Mots du texte (et paires accolées), et leurs clés phonétiques."""
    mots = _mots(texte.replace("-", " "))
    cles = [phonetique(m) for m in mots]
    paires_cles = _paires(tuple(cles))
    return (*mots, *_paires(mots)), (*cles, *paires_cles)


def _cite_un_nom_propre(texte: str, livre: LivreDuResume) -> bool:
    mots, cles = _mots_et_cles(texte)
    # nom composé écrit en un ou deux mots : « blangras », « blanc gras »
    for nom in map(_nom_sans_tiret, _noms_auteur(livre.auteur)):
        if len(nom) >= 8 and any(
            len(m) >= 6 and fuzz.ratio(m, nom) >= SEUIL_NOM_COMPOSE for m in mots
        ):
            return True
    # prononciation : « Gény » pour Jenni, « Valènes-âmes » pour Walenhammes
    for nom in _noms_propres(livre):
        cle = phonetique(nom)
        if len(cle) >= NOM_COURT and any(
            abs(len(m) - len(cle)) <= 3 and fuzz.ratio(m, cle) >= SEUIL_PHONETIQUE
            for m in cles
        ):
            return True
    return False


def mentionne(texte: str, livre: LivreDuResume) -> bool:
    """Le texte cite-t-il le livre (titre ou nom d'auteur) ?"""
    texte = PONCTUATION.sub(" ", texte)
    mots = _mots(texte)
    return (
        _cite_le_titre(mots, livre)
        or _cite_un_auteur(mots, livre)
        or _cite_un_nom_propre(texte, livre)
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
    return bool(TRANSITION.search(normalize_for_matching(texte)))


def est_appel(texte: str, critique: str) -> bool:
    """Le présentateur passe-t-il la parole au critique ?

    Son prénom dans une phrase courte (« Arnaud ? », « À toi, Nelly. »,
    « celui de Nelly d'abord »), ou en fin de phrase après une phrase finie
    (« … du sous-sol. Arnaud ? », « … formidable. Anna. »). Une phrase longue
    qui cite le critique en plein débat n'est pas un appel.
    """
    mots_critique = normalize_for_matching(PARENTHESES.sub("", critique)).split()
    if not mots_critique:
        return False
    prenom = re.escape(mots_critique[0])
    texte_normalise = normalize_for_matching(texte)
    if not re.search(rf"\b{prenom}\b", texte_normalise):
        return False
    if len(PONCTUATION.sub(" ", texte_normalise).split()) <= APPEL_MOTS_MAX:
        return True
    return bool(
        re.search(rf"\b{prenom} ?\?\s*$", texte_normalise)
        or re.search(rf"[.!?] {prenom} ?[.!]?\s*$", texte_normalise)
    )


# ------------------------------------------------------------- repérage
GRAPPE_MS = 300_000  # fenêtre de la grappe la plus dense
RAFALE_MS = 90_000  # 2 mentions dans cet intervalle ouvrent un coup de cœur
CHAINE_MS = 90_000  # mentions qui s'enchaînent vers le début d'un débat
APPEL_AVANT_MS = 60_000  # l'appel du critique précède sa rafale de moins d'1 min
SEGMENT_LONG_MS = 4_000  # au-delà, le voisinage seul ne suffit pas
TRANSITIONS_AVANT = 40  # Segments examinés avant le premier débat


@dataclass
class _Placement:
    """Où un livre se trouve dans l'émission, au fil du repérage."""

    livre: LivreDuResume
    mentions: list[int]  # index des Segments qui le citent
    centre_ms: float = 0.0  # médiane de sa grappe la plus dense
    grappe_debut_ms: int = 0
    debut: int = 0  # index du Segment où son Passage commence
    fin_ms: int = 0


def _utile(segment: Segment) -> bool:
    """Écarte les Segments vides ou réduits à « ... » (musique, silence)."""
    texte = segment.texte.strip()
    return bool(texte) and not set(texte) <= {".", " "}


def _index_a(segments: list[Segment], debut_ms: float) -> int:
    return next(i for i, seg in enumerate(segments) if seg.debut_ms == debut_ms)


def _fin_derniere_mention(placement: _Placement, segments: list[Segment]) -> int:
    return segments[max(placement.mentions)].fin_ms


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


def _situer_grappe(placement: _Placement, segments: list[Segment]) -> None:
    instants = [segments[i].debut_ms for i in placement.mentions]
    grappes = [[t for t in instants if t0 <= t <= t0 + GRAPPE_MS] for t0 in instants]
    meilleure = max(grappes, key=len)
    placement.centre_ms = statistics.median(meilleure)
    placement.grappe_debut_ms = min(meilleure)


def _placer_coups_de_coeur(
    placements: list[_Placement], segments: list[Segment], plancher_ms: float
) -> list[_Placement]:
    """Place les coups de cœur à la suite ; rend ceux qui ont un Passage.

    Un coup de cœur jamais cité après le coup de cœur précédent (ou après
    les débats) n'a pas été présenté, ou pas reconnu : pas de Passage.
    """
    places = []
    for placement in placements:
        instants = [segments[i].debut_ms for i in placement.mentions]
        apres = [t for t in instants if t > plancher_ms]
        if not apres:
            continue
        rafales = [t for t in apres if any(t < u <= t + RAFALE_MS for u in apres)]
        presentation_ms = min(rafales or apres)
        appels = [
            i
            for i, seg in enumerate(segments)
            if plancher_ms < seg.debut_ms <= presentation_ms
            and presentation_ms - seg.debut_ms <= APPEL_AVANT_MS
            and est_appel(seg.texte, placement.livre.critique)
        ]
        # l'appel le plus proche de la présentation du livre : une phrase
        # courte qui cite le critique plus tôt (plaisanterie, aparté) n'est
        # pas la passation de parole
        placement.debut = max(appels) if appels else _index_a(segments, presentation_ms)
        plancher_ms = segments[placement.debut].debut_ms
        places.append(placement)
    for placement, suivant in zip(places, places[1:], strict=False):
        placement.fin_ms = segments[suivant.debut].debut_ms
    if places:
        places[-1].fin_ms = _fin_derniere_mention(places[-1], segments)
    return places


def _debut_du_premier_debat(placement: _Placement, segments: list[Segment]) -> int:
    """Index du début du premier débattu : la transition qui précède son débat."""
    instants = sorted(segments[i].debut_ms for i in placement.mentions)
    debut_ms = placement.grappe_debut_ms
    for t in reversed([t for t in instants if t < debut_ms]):
        if debut_ms - t > CHAINE_MS:
            break
        debut_ms = t
    index = _index_a(segments, debut_ms)
    transitions = [
        j
        for j in range(max(0, index - TRANSITIONS_AVANT), index + 1)
        if est_transition(segments[j].texte)
    ]
    return transitions[-1] if transitions else index


def _placer_debattus(
    placements: list[_Placement], segments: list[Segment], fin_index: int
) -> None:
    """Découpage contigu aux transitions, chaque bloc gardant ses mentions.

    Programmation dynamique sur les coupes possibles ; à score égal, la coupe
    la plus tardive gagne, si bien que le débat d'un livre non reconnu reste
    dans le Passage du livre précédent.
    """
    origine = _debut_du_premier_debat(placements[0], segments)
    nb_livres, etendue = len(placements), fin_index - origine
    # mentions_avant[k][j] : mentions du livre k dans les j premiers Segments
    mentions_avant = []
    for placement in placements:
        cite = [0] * etendue
        for i in placement.mentions:
            if origine <= i < fin_index:
                cite[i - origine] = 1
        cumul = [0]
        for v in cite:
            cumul.append(cumul[-1] + v)
        mentions_avant.append(cumul)
    coupes = [
        j for j in range(1, etendue) if est_transition(segments[origine + j].texte)
    ]
    if len(coupes) < nb_livres - 1:
        coupes = list(range(1, etendue))
    coupes = [0, *coupes, etendue]
    jamais = -(10**9)
    # score[k][c] : meilleur total des livres 0..k, le bloc k finissant à coupes[c]
    score = [[jamais] * len(coupes) for _ in range(nb_livres)]
    coupe_avant = [[0] * len(coupes) for _ in range(nb_livres)]
    for c in range(len(coupes)):
        score[0][c] = mentions_avant[0][coupes[c]]
    for k in range(1, nb_livres):
        for c in range(len(coupes)):
            for c_avant in range(c):
                total = (
                    score[k - 1][c_avant]
                    + mentions_avant[k][coupes[c]]
                    - mentions_avant[k][coupes[c_avant]]
                )
                if total >= score[k][c]:
                    score[k][c], coupe_avant[k][c] = total, c_avant
    c = len(coupes) - 1
    retenues = [etendue]
    for k in range(nb_livres - 1, 0, -1):
        c = coupe_avant[k][c]
        retenues.append(coupes[c])
    retenues = [0, *retenues[::-1]]
    for k, placement in enumerate(placements):
        placement.debut = origine + retenues[k]
        if k + 1 < nb_livres:
            placement.fin_ms = segments[origine + retenues[k + 1]].debut_ms
        elif fin_index < len(segments):
            placement.fin_ms = segments[fin_index].debut_ms
        else:
            placement.fin_ms = _fin_derniere_mention(placement, segments)


def reperer_passages(segments: list[Segment], livres: list[LivreDuResume]) -> Reperage:
    """Situe le Passage de chaque livre du résumé dans l'émission."""
    segments = [s for s in segments if _utile(s)]
    if not segments:
        return Reperage(sans_passage=list(livres))

    placements = [_Placement(livre, _mentions(segments, livre)) for livre in livres]
    cites = [p for p in placements if p.mentions]
    for placement in cites:
        _situer_grappe(placement, segments)
    cites.sort(key=lambda p: (p.livre.section, p.centre_ms))
    debattus = [p for p in cites if p.livre.section == Section.DEBATTU]
    coups = [p for p in cites if p.livre.section == Section.COUP_DE_COEUR]

    plancher_ms = max((p.centre_ms for p in debattus), default=0)
    coups = _placer_coups_de_coeur(coups, segments, plancher_ms)
    if debattus:
        _placer_debattus(debattus, segments, coups[0].debut if coups else len(segments))

    places = debattus + coups
    return Reperage(
        passages=[
            PassageRepere(p.livre, segments[p.debut].debut_ms, p.fin_ms) for p in places
        ],
        sans_passage=[p.livre for p in placements if p not in places],
    )
