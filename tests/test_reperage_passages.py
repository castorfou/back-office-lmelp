"""Repérage des Passages d'une émission (Issue #427).

Fonction pure : Segments horodatés + livres du résumé → Passages. Testée sur
de vrais témoins (whisper.cpp -oj --max-context 0 et résumé avis_critiques),
avec des bornes de référence indépendantes de l'algorithme : l'écoute du
15/11/2026 (#391) et, pour les autres témoins, la lecture de la transcription
(passation de parole). Objectif de la spec : ±10 s.
"""

import json
from functools import cache
from pathlib import Path

import pytest

from back_office_lmelp.utils.reperage_passages import (
    LivreDuResume,
    Segment,
    est_appel,
    livres_du_resume,
    mentionne,
    phonetique,
    reperer_passages,
)


FIXTURES = Path(__file__).parent / "fixtures" / "passages"
TOLERANCE_S = 10


def charger_temoin(date: str) -> tuple[list[Segment], list[LivreDuResume]]:
    data = json.loads((FIXTURES / f"temoin_{date}.json").read_text())
    segments = [Segment(debut, fin, texte) for debut, fin, texte in data["segments"]]
    livres = livres_du_resume(data["resume"], data["livres_ecartes"])
    return segments, livres


@cache
def debuts_par_titre(date: str) -> dict[str, int]:
    segments, livres = charger_temoin(date)
    reperage = reperer_passages(segments, livres)
    return {p.livre.titre: p.debut_ms // 1000 for p in reperage.passages}


def s(mmss: str) -> int:
    minutes, secondes = mmss.split(":")
    return int(minutes) * 60 + int(secondes)


# Référence à l'écoute (#391). « Je demande à en finir avec la vie » : le coup
# de cœur commence à l'appel du critique (« Anna. », 42:51), règle validée à
# l'écoute dans #391 ; l'écoute avait retenu le « enchaînons » qui suit (43:04).
REFERENCE_2026_11_15 = {
    "Le Fondateur": "07:32",
    "Paradisi Gloria": "13:24",
    "Dans les grandes lignes": "19:20",
    "Rouge Truite": "26:53",
    "Saint Lucky Luke": "33:45",
    "Le Livre des souterrains": "40:16",
    "Vivre après": "41:51",
    "Je demande à en finir avec la vie": "42:51",
    "Comment j'ai cessé d'être une petite fasciste": "44:43",
}


# Références lues dans la transcription : la passation de parole (transition
# du présentateur pour un débattu, appel du critique pour un coup de cœur).
REFERENCE_2026_10_04 = {
    "L'Éléphant": "03:56",  # « Et j'ouvre le programme du masque… »
    "Chronique d'un royaume perdu": "10:17",  # « après ce roman bref… »
    "Je change de nom": "17:59",  # « On continue avec… »
    "Décolorer sa fille": "25:37",  # « On va parler maintenant… »
    "Un diamant dans les gravats": "32:33",  # « On termine avec… »
    "Les Noms de Feliza": "39:13",  # « on commence avec toi, Ilana »
    "Abdallah superstar": "40:51",  # « Arnaud ? »
    "Sur la route du retour": "42:17",  # « Cécile ? »
    "La Maison d'été": "44:11",  # « on termine avec toi Philippe »
}

# Ancien format : sommaire et courrier des auditeurs avant le premier débat.
REFERENCE_2024_07_21 = {
    "L'Imposture": "04:49",  # « Le livre qui ouvre le masque du jour… »
    "Ni de lait ni de laine": "16:21",  # « Arrive maintenant une autrice… »
    "L'Oiseau des Français": "23:58",  # « On continue ce masque… »
    "Bungalow": "31:45",  # « Et on termine ce masque… »
    "Petit traité du geste: Pour la beauté du sport": "37:51",  # « Patricia, … »
    "Quiche ta": "38:52",  # « … Laurent ? »
    "Baise-moi": "39:50",  # « À toi, Nelly. »
    "Légende au pluriel : La mer à la campagne": "41:21",  # « je termine… »
    "Emmanuelle Arsan, biographie d'un pseudonyme": "42:56",  # « Arnaud »
}

# Ancien format (pap). Whisper écrit « Valènes-âmes » et « Gény » pour La nuit
# de Walenhammes d'Alexis Jenni. Les deux coups de cœur de Michel Crépu,
# présentés d'un seul tenant, ne sont pas référencés (laissés au ⚠️, #421).
REFERENCE_2015_06_28 = {
    "Vernon Subutex, tome 2": "04:23",  # « Six mois après l'incroyable succès… »
    "La nuit de Walenhammes": "15:34",  # « c'est La nuit des Valènes-âmes… »
    "Numéro zéro": "24:48",  # « alors numéro 0 »
    "Soudain, seuls": "32:14",  # « Allez, soudain… »
    "Perfidia": "41:30",  # « Rapidement… Père Fidia… »
    "Jours tranquilles, brèves rencontres": "49:15",  # « … celui de Nelly d'abord »
    "Ça aussi, ça passera": "51:11",  # « Le conseil d'Olivia ? »
    "Pour Roland Barthes": "52:16",  # « Arnaud ? »
}

CAS = [
    (date, titre, debut)
    for date, reference in (
        ("2026-11-15", REFERENCE_2026_11_15),
        ("2026-10-04", REFERENCE_2026_10_04),
        ("2024-07-21", REFERENCE_2024_07_21),
        ("2015-06-28", REFERENCE_2015_06_28),
    )
    for titre, debut in reference.items()
]


@pytest.mark.parametrize("date,titre,debut", CAS)
def test_le_passage_commence_a_la_passation_de_parole_a_10_s_pres(date, titre, debut):
    debuts = debuts_par_titre(date)

    assert titre in debuts, f"« {titre} » sans Passage"
    assert abs(debuts[titre] - s(debut)) <= TOLERANCE_S, (
        f"« {titre} » commence à {debuts[titre] // 60:02d}:{debuts[titre] % 60:02d},"
        f" attendu {debut}"
    )


# ------------------------------------------------------------ cas ciblés
JENNI = LivreDuResume(1, "La nuit de Walenhammes", "Alexis Jenni", "Gallimard")


def test_un_nom_propre_deforme_par_whisper_est_reconnu_a_la_prononciation():
    assert phonetique("Gény") == phonetique("Jenni")
    assert mentionne("Le nouveau roman d'Alexis Gény,", JENNI)
    assert mentionne("c'est La nuit des Valènes-âmes, chez Gallimard.", JENNI)


def test_un_mot_ordinaire_du_titre_n_est_pas_compare_a_la_prononciation():
    livre = LivreDuResume(2, "Jours tranquilles, brèves rencontres", "Eve Babitz")

    assert not mentionne("la rencontre a eu lieu hier soir", livre)


def test_la_ponctuation_collee_a_un_nom_ne_l_empeche_pas_d_etre_reconnu():
    livre = LivreDuResume(1, "Ni de lait ni de laine", "Emmanuelle Salasc")

    assert mentionne(
        "avec les nouveaux livres de Zadie Smith, Emmanuel Salasque,", livre
    )


@pytest.mark.parametrize(
    "texte",
    ["Arnaud ?", "Aux éditions du sous-sol. Arnaud ?", "À toi, Arnaud."],
)
def test_le_presentateur_passe_la_parole_au_critique(texte):
    assert est_appel(texte, "Arnaud Viviant")


def test_le_prenom_du_critique_cite_en_plein_debat_n_est_pas_un_appel():
    assert not est_appel(
        "Laurent, je ne sais pas si toi tu l'as relu récemment,", "Laurent Chalumeau"
    )


def test_un_titre_ecarte_du_resume_n_a_pas_de_passage():
    resume = (
        "## 1. LIVRES DISCUTÉS AU PROGRAMME\n\n"
        "| Auteur | Titre | Éditeur | Avis |\n|---|---|---|---|\n"
        "| Luz | Un diamant dans les gravats | Stock | … |\n"
        "| Collectif | La Pléiade | Gallimard | … |\n"
    )

    livres = livres_du_resume(resume, [{"titre": "La Pléiade", "auteur": "Collectif"}])

    assert [livre.titre for livre in livres] == ["Un diamant dans les gravats"]


def _segments(*textes: str) -> list[Segment]:
    return [Segment(i * 3000, i * 3000 + 3000, t) for i, t in enumerate(textes)]


def test_un_livre_jamais_nomme_n_a_pas_de_passage_et_ne_laisse_pas_de_trou():
    modiano = LivreDuResume(1, "L'Éléphant", "Patrick Modiano")
    luz = LivreDuResume(1, "Un diamant dans les gravats", "Luz")
    absent = LivreDuResume(1, "Je change de nom", "Christine Angot")
    segments = _segments(
        "On commence avec L'Éléphant de Patrick Modiano.",
        "Modiano écrit encore sur Paris.",
        "Ce débat sur le livre est vif.",
        "On termine avec Un diamant dans les gravats de Luz.",
        "Luz raconte la reconstruction.",
    )

    reperage = reperer_passages(segments, [modiano, luz, absent])

    premier, second = reperage.passages
    assert reperage.sans_passage == [absent]
    assert (premier.livre, second.livre) == (modiano, luz)
    assert premier.fin_ms == second.debut_ms == 9000


@pytest.mark.parametrize("date", ["2026-10-04", "2024-07-21"])
def test_les_coups_de_coeur_se_suivent_sans_trou_ni_recouvrement(date):
    segments, livres = charger_temoin(date)
    coups = [
        p for p in reperer_passages(segments, livres).passages if p.livre.section == 2
    ]

    assert len(coups) >= 4
    for avant, apres in zip(coups, coups[1:], strict=False):
        assert avant.fin_ms == apres.debut_ms


def test_un_coup_de_coeur_cite_seulement_avant_les_debats_n_a_pas_de_passage():
    luz = LivreDuResume(1, "Un diamant dans les gravats", "Luz")
    coup = LivreDuResume(2, "Les Noms de Feliza", "Juan Gabriel Vásquez", "", "Ilana")
    # deux annonces séparées par un long Segment : la médiane de la grappe
    # (1 500 ms) ne tombe sur le début d'aucun Segment
    segments = [
        Segment(0, 1000, "Au sommaire, Les Noms de Feliza de Vásquez,"),
        Segment(3000, 4000, "et Les Noms de Feliza encore, en annonce."),
        Segment(4000, 10000, "Le programme est copieux ce soir à la tribune."),
        Segment(10000, 13000, "On commence avec Un diamant dans les gravats de Luz."),
        Segment(13000, 16000, "Luz parle du deuil."),
        Segment(16000, 19000, "Luz encore, et la reconstruction."),
    ]

    reperage = reperer_passages(segments, [luz, coup])

    # annoncé au sommaire mais jamais présenté : à placer, comme un livre
    # non reconnu ; le débat de Luz garde son Passage
    assert reperage.sans_passage == [coup]
    assert [p.livre for p in reperage.passages] == [luz]
