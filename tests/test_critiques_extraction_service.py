"""Tests pour le service d'extraction des critiques."""

import pytest

from back_office_lmelp.services.critiques_extraction_service import (
    CritiquesExtractionService,
)


# Exemples de summary réels depuis la collection avis_critiques
SUMMARY_SAMPLE_1 = """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Etgar Keret | Correction automatique | Éditions de l'Olivier | **Blandine Rinkel**: "Fantaisiste et grave à la fois" - 7 <br> **Arnaud Viviant**: "Échapper au réel" - 8 <br> **Elisabeth Philippe**: "Black Mirror réécrit par Kafka" - 9 <br> **Jean-Marc Proust**: "Diversité" - 8 | 8.0 | 4 | Elisabeth Philippe | |

## 2. COUPS DE CŒUR DES CRITIQUES

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Arnaud Le Gouëfflec | Underground 2 | Glénage | Jean-Marc Proust | 9.0 | "Rockeurs maudits" |
| Jean-Daniel Beauvallet | Rock City Guide | GM Éditions | Rebecca Manzoni | 9.0 | "Guide touristique" |
"""

SUMMARY_SAMPLE_2 = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 22 juin 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Adrien Bosc | L'invention de Tristan | Stock | **Laurent Chalumeau**: Très bien mené - 8 <br> **Patricia Martin**: Absolument flamboyant - 9 <br> **Hubert Artus**: Beaucoup aimé - 7 <br> **Raphaël Léris**: Intéressant - 7 | 7.8 | 4 | Patricia Martin | |
"""

SUMMARY_SAMPLE_3 = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 01 juin 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Johanne Rigoulot | La vie continuée de Nelly Arcan | Les Avril | **Patricia Martin**: "Un livre qui a du style" - 9 <br> **Arnaud Viviant**: "Dévoré d'une traite" - 9 <br> **Jean-Marc Proust**: "Important" - 8 <br> **Elisabeth Philippe**: "Ne m'a pas totalement convaincue" - 6 | 8.0 | 4 | Patricia Martin, Arnaud Viviant | |

## 2. COUPS DE CŒUR DES CRITIQUES du 01 juin 2025

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Franck Courtès | À pied d'oeuvre | Folio | Arnaud Viviant | 9.0 | "Raconte l'esclavage moderne" |
| Nathalie Quintane | Chemoule, un chat français | POL | Elisabeth Philippe | 9.0 | "Drôle, doux, poétique" |
| Hervé Bourhis | Paul : La résurrection | Casterman | Jérôme Garcin | 9.0 | "Appris des choses" |
| Hafid Aggoune | Le mari de la comtesse de Ségur | Reconnaissance | Jean-Marc Proust | 9.0 | "Histoire du mari" |
"""


@pytest.fixture
def service():
    """Fixture pour le service d'extraction."""
    return CritiquesExtractionService()


def test_extract_critiques_from_summary_sample1(service):
    """Test d'extraction des critiques du premier exemple.

    Doit extraire:
    - Les critiques avec pattern **Nom**: (dans la section "Avis détaillés")
    - Les critiques dans la colonne "Critique" des tableaux de coups de cœur
    """
    critiques = service.extract_critiques_from_summary(SUMMARY_SAMPLE_1)

    # Vérifier que TOUS les critiques ont été détectés
    # (pattern **Nom**: + colonne "Critique" des coups de cœur)
    expected_names = [
        "Blandine Rinkel",
        "Arnaud Viviant",
        "Elisabeth Philippe",
        "Jean-Marc Proust",
        "Rebecca Manzoni",  # Animatrice dans la colonne "Critique"
    ]

    assert len(critiques) == len(expected_names)
    for name in expected_names:
        assert name in critiques


def test_extract_critiques_from_summary_sample2(service):
    """Test d'extraction des critiques du second exemple."""
    critiques = service.extract_critiques_from_summary(SUMMARY_SAMPLE_2)

    expected_names = [
        "Laurent Chalumeau",
        "Patricia Martin",
        "Hubert Artus",
        "Raphaël Léris",
    ]

    assert len(critiques) == len(expected_names)
    for name in expected_names:
        assert name in critiques


def test_extract_critiques_from_summary_sample3_with_jerome_garcin(service):
    """Test d'extraction incluant Jérôme Garcin (animateur).

    Vérifie que les animateurs dans la colonne "Critique" des coups de cœur
    sont bien extraits.
    """
    critiques = service.extract_critiques_from_summary(SUMMARY_SAMPLE_3)

    # Vérifier que Jérôme Garcin (animateur) est extrait
    expected_names = [
        "Patricia Martin",
        "Arnaud Viviant",
        "Jean-Marc Proust",
        "Elisabeth Philippe",
        "Jérôme Garcin",  # Animateur dans la colonne "Critique"
    ]

    assert len(critiques) == len(expected_names)
    for name in expected_names:
        assert name in critiques


def test_extract_critiques_empty_summary(service):
    """Test avec un summary vide."""
    critiques = service.extract_critiques_from_summary("")
    assert critiques == []


def test_extract_critiques_no_bold_pattern(service):
    """Test avec un summary sans pattern **Nom**:."""
    summary = "Ceci est un texte sans critiques."
    critiques = service.extract_critiques_from_summary(summary)
    assert critiques == []


def test_extract_critiques_removes_duplicates(service):
    """Test que les doublons sont supprimés."""
    summary = """
    **Blandine Rinkel**: "Premier avis" - 8
    **Blandine Rinkel**: "Second avis" - 9
    **Arnaud Viviant**: "Avis" - 7
    """

    critiques = service.extract_critiques_from_summary(summary)

    assert len(critiques) == 2
    assert "Blandine Rinkel" in critiques
    assert "Arnaud Viviant" in critiques


def test_extract_critiques_handles_special_chars(service):
    """Test avec des caractères spéciaux dans les noms."""
    summary = """
    **Jean-Marc Proust**: "Avis" - 8
    **Raphaël Léris**: "Avis" - 7
    """

    critiques = service.extract_critiques_from_summary(summary)

    assert len(critiques) == 2
    assert "Jean-Marc Proust" in critiques
    assert "Raphaël Léris" in critiques


def test_normalize_critique_name(service):
    """Test de normalisation des noms pour matching."""
    # Test avec des variations de casse et espaces
    assert service.normalize_critique_name("Blandine Rinkel") == "blandine rinkel"
    assert service.normalize_critique_name("BLANDINE RINKEL") == "blandine rinkel"
    assert service.normalize_critique_name("  Blandine  Rinkel  ") == "blandine rinkel"


def test_find_matching_critique_exact_match(service):
    """Test de recherche avec correspondance exacte."""
    existing_critiques = [
        {"nom": "Blandine Rinkel", "variantes": []},
        {"nom": "Arnaud Viviant", "variantes": ["Arnaud V."]},
    ]

    result = service.find_matching_critique("Blandine Rinkel", existing_critiques)

    assert result is not None
    assert result["nom"] == "Blandine Rinkel"
    assert result["match_type"] == "exact"


def test_find_matching_critique_variante_match(service):
    """Test de recherche avec correspondance sur variante."""
    existing_critiques = [
        {"nom": "Blandine Rinkel", "variantes": ["Blandine R.", "B. Rinkel"]},
    ]

    result = service.find_matching_critique("Blandine R.", existing_critiques)

    assert result is not None
    assert result["nom"] == "Blandine Rinkel"
    assert result["match_type"] == "variante"


def test_find_matching_critique_no_match(service):
    """Test de recherche sans correspondance."""
    existing_critiques = [
        {"nom": "Blandine Rinkel", "variantes": []},
    ]

    result = service.find_matching_critique("Patricia Martin", existing_critiques)

    assert result is None


def test_extract_critiques_hyphenated_name_without_space(service):
    """Test que les noms composés avec tiret mais sans espace sont extraits.

    Bug réel: épisode 13/08/2017 - Jean-Louis Ezine.
    Le LLM a transcrit "Jean-Louis Ezine" comme "Jean-Louisine" (collé en un mot)
    et "Jean-Louis" (prénom seul). Ces noms contiennent un tiret mais pas d'espace,
    et étaient filtrés par la condition `" " in nom`.
    Résultat: l'utilisateur ne voyait pas ces noms dans la page Identification des
    Critiques et ne pouvait pas faire le mapping manuel.
    """
    summary = """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques |
|--------|-------|---------|------------------------------|
| Richard Ford | Entre eux | Editions de l'Olivier | **Jean-Louisine**: Beau livre. Note: 9 <br> **Olivia de Lamberterie**: Éblouissant. Note: 9 |
| Agnès Martin-Lugand | J'ai toujours cette musique | Michel Lafon | **Jean-Louis**: Décevant. Note: 4 <br> **Olivia de Lamberterie**: Rassurant. Note: 7 |

## 2. COUPS DE CŒUR DES CRITIQUES
"""
    critiques = service.extract_critiques_from_summary(summary)

    # "Jean-Louisine" et "Jean-Louis" doivent être extraits
    # même s'ils n'ont pas d'espace (seulement un tiret)
    assert "Jean-Louisine" in critiques, (
        f"'Jean-Louisine' devrait être extrait, got: {critiques}"
    )
    assert "Jean-Louis" in critiques, (
        f"'Jean-Louis' devrait être extrait, got: {critiques}"
    )
    assert "Olivia de Lamberterie" in critiques
