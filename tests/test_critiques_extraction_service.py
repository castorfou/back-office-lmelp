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


@pytest.fixture
def service():
    """Fixture pour le service d'extraction."""
    return CritiquesExtractionService()


def test_extract_critiques_from_summary_sample1(service):
    """Test d'extraction des critiques du premier exemple."""
    critiques = service.extract_critiques_from_summary(SUMMARY_SAMPLE_1)

    # Vérifier que tous les critiques avec pattern **Nom**: ont été détectés
    # Note: Rebecca Manzoni apparaît dans la colonne "Critique" sans le pattern **:
    # et ne sera donc pas extrait (ce qui est OK pour l'issue #154)
    expected_names = [
        "Blandine Rinkel",
        "Arnaud Viviant",
        "Elisabeth Philippe",
        "Jean-Marc Proust",
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
