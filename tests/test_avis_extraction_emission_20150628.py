"""Coups de cœur sans note ni commentaire (Issue #405).

Émission du 28 juin 2015 : la section 2 du résumé liste les coups de cœur
avec des cellules Note et Commentaire vides. Chaque ligne nomme pourtant un
livre et un critique : elle doit donner un avis (note ``None``), sinon la
page Émission ne trouve aucun avis à rapprocher de ces livres.
"""

from back_office_lmelp.services.avis_extraction_service import AvisExtractionService


# Section 2 telle qu'enregistrée en base pour cette émission
SUMMARY = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 28 juin 2015

|Auteur|Titre|Éditeur|Avis détaillés des critiques|Note moyenne|Nb critiques|Coup de cœur|Chef d'œuvre|
|---|---|---|---|---|---|---|---|
|Isabelle Autissier|Soudain, seuls|Stock|**Michel Crépu**: Livre sensationnel, souffle. Note: 8|8.0|1|||

## 2. COUPS DE CŒUR DES CRITIQUES du 28 juin 2015

|Auteur|Titre|Éditeur|Critique|Note|Commentaire|
|---|---|---|---|---|---|
|Eve Babitz|Jours tranquilles, brèves rencontres|Gallmeister|Nelly Kaprièlian|||
|Pierre Boncenne|Le parapluie de Simon Leys|Éditions Philippe Rey|Michel Crépu|||
|Simon Leys|Quand vous viendrez me voir aux antipodes|Éditions Philippe Rey|Michel Crépu|||
|Milena Busquets|Ça aussi, ça passera|Gallimard|Olivia de Lamberterie|||
|Chantal Thomas|Pour Roland Barthes|Le Seuil|Arnaud Viviant|||
"""


def _coups_de_coeur() -> list[dict]:
    avis = AvisExtractionService().extract_avis_from_summary(SUMMARY, "emission_id")
    return [a for a in avis if a["section"] == "coup_de_coeur"]


def test_coups_de_coeur_without_note_are_extracted():
    coups_de_coeur = _coups_de_coeur()

    assert [
        (a["livre_titre_extrait"], a["critique_nom_extrait"]) for a in coups_de_coeur
    ] == [
        ("Jours tranquilles, brèves rencontres", "Nelly Kaprièlian"),
        ("Le parapluie de Simon Leys", "Michel Crépu"),
        ("Quand vous viendrez me voir aux antipodes", "Michel Crépu"),
        ("Ça aussi, ça passera", "Olivia de Lamberterie"),
        ("Pour Roland Barthes", "Arnaud Viviant"),
    ]


def test_coup_de_coeur_without_note_keeps_columns_in_place():
    babitz = _coups_de_coeur()[0]

    assert babitz["auteur_nom_extrait"] == "Eve Babitz"
    assert babitz["editeur_extrait"] == "Gallmeister"
    assert babitz["note"] is None
    assert babitz["commentaire"] == ""


def test_programme_row_with_empty_editeur_keeps_columns_in_place():
    """Même découpage en section 1 : un éditeur vide ne décale pas l'avis."""
    summary = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 28 juin 2015

|Auteur|Titre|Éditeur|Avis détaillés des critiques|Note moyenne|Nb critiques|Coup de cœur|Chef d'œuvre|
|---|---|---|---|---|---|---|---|
|Isabelle Autissier|Soudain, seuls||**Michel Crépu**: Livre sensationnel, souffle. Note: 8|8.0|1|||
"""
    avis = AvisExtractionService().extract_avis_from_summary(summary, "emission_id")

    assert [
        (a["critique_nom_extrait"], a["note"], a["editeur_extrait"]) for a in avis
    ] == [("Michel Crépu", 8, "")]


def test_coup_de_coeur_row_without_critic_name_gives_no_avis():
    """Une remarque du LLM à la place du critique (émission du 29/11/2015)."""
    summary = """## 2. COUPS DE CŒUR DES CRITIQUES du 29 novembre 2015

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Françoise Frenkel | Rien où poser sa tête | Gallimard (L'Arbalète) | (Déjà dans le programme principal, ne pas dupliquer) |  |  |
| Sempé | Sincères amitiés | Denoël | Olivia de Lamberterie | 10 | Absolument génial. |
| Alfred Hayes | Une jolie fille comme ça | Gallimard |  |  |  |
"""
    avis = AvisExtractionService().extract_avis_from_summary(summary, "emission_id")

    assert [(a["livre_titre_extrait"], a["critique_nom_extrait"]) for a in avis] == [
        ("Sincères amitiés", "Olivia de Lamberterie")
    ]
