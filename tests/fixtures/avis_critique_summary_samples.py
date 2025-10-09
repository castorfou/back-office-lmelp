"""Fixtures réalistes pour tester la mise à jour du summary (Issue #67).

Ces fixtures sont basées sur de vraies données de la collection avis_critiques,
avec des cas edge complexes (emojis, tableaux markdown, spans HTML, etc.).
"""

# Cas 1: Summary simple avec un seul livre (erreur d'auteur)
SUMMARY_SINGLE_BOOK_AUTHOR_ERROR = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 01 jan. 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Alain Mabancou | Ramsès de Paris | Seuil | **Patricia Martin**: "Magnifique" (9) | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | 1 | Patricia Martin | |
"""

SUMMARY_SINGLE_BOOK_AUTHOR_CORRECTED = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 01 jan. 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Alain Mabanckou | Ramsès de Paris | Seuil | **Patricia Martin**: "Magnifique" (9) | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | 1 | Patricia Martin | |
"""

# Cas 2: Summary avec plusieurs livres (correction sélective)
SUMMARY_MULTIPLE_BOOKS_MIXED = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 15 fév. 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Alain Mabancou | Ramsès de Paris | Seuil | **Patricia Martin**: "Excellent" (9) | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | 1 | Patricia Martin | |
| Adrien Bosque | L'invention de Tristan | Verdier | **Bernard Poiret**: "Très bon" (8) | <span style="background-color: #8BC34A; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.0</span> | 1 | | |
| Amélie Nothomb | Tant mieux | Albin Michel | **Elisabeth Philippe**: "Formidable" (10) | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">10.0</span> | 1 | Elisabeth Philippe | Elisabeth Philippe |
"""

# Après correction du premier livre seulement
SUMMARY_MULTIPLE_BOOKS_FIRST_CORRECTED = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 15 fév. 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Alain Mabanckou | Ramsès de Paris | Seuil | **Patricia Martin**: "Excellent" (9) | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | 1 | Patricia Martin | |
| Adrien Bosque | L'invention de Tristan | Verdier | **Bernard Poiret**: "Très bon" (8) | <span style="background-color: #8BC34A; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.0</span> | 1 | | |
| Amélie Nothomb | Tant mieux | Albin Michel | **Elisabeth Philippe**: "Formidable" (10) | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">10.0</span> | 1 | Elisabeth Philippe | Elisabeth Philippe |
"""

# Cas 3: Titre avec caractères spéciaux et apostrophes
SUMMARY_SPECIAL_CHARS = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 20 mars 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Laurent Mauvignier | La Maison Vide | Minuit | **Arnaud Viviant**: "Magnifique" (9) | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | 1 | Arnaud Viviant | |
"""

SUMMARY_SPECIAL_CHARS_CORRECTED = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 20 mars 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Laurent Mauvignier | La Maison vide | Minuit | **Arnaud Viviant**: "Magnifique" (9) | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | 1 | Arnaud Viviant | |
"""

# Cas 4: Titre contenant un pipe (|) - cas edge
SUMMARY_TITLE_WITH_PIPE = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 10 avril 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| John Doe | Le livre \\| la suite | Gallimard | **Patricia Martin**: "Intéressant" (7) | <span style="background-color: #CDDC39; color: black; padding: 2px 6px; border-radius: 3px; font-weight: bold;">7.0</span> | 1 | | |
"""

# Cas 5: Summary avec section "Coups de cœur" (structure complète)
SUMMARY_WITH_COUPS_DE_COEUR = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 29 juin 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Aslak Nord | Piège à loup | Le bruit du monde | **Patricia Martin**: "Largement au-dessus du lot" (10) | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.8</span> | 4 | Patricia Martin | |

## 2. COUPS DE CŒUR DES CRITIQUES du 29 juin 2025

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Jérôme Leroy | La petite fasciste | La Manufacture de Livres | Bernard Poiret | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">10</span> | "Absolument formidable" |
"""

SUMMARY_WITH_COUPS_DE_COEUR_CORRECTED = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 29 juin 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Aslak Nordström | Piège à loup | Le bruit du monde | **Patricia Martin**: "Largement au-dessus du lot" (10) | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">8.8</span> | 4 | Patricia Martin | |

## 2. COUPS DE CŒUR DES CRITIQUES du 29 juin 2025

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Jérôme Leroy | La petite fasciste | La Manufacture de Livres | Bernard Poiret | <span style="background-color: #00C851; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">10</span> | "Absolument formidable" |
"""

# Cas 6: Auteur avec caractères accentués et espaces
SUMMARY_ACCENTS_AND_SPACES = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 05 mai 2025

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Jakuta Alikavazovic | Comme un Empire dans un Empire | Gallimard | **Elisabeth Philippe**: "Superbe" (9) | <span style="background-color: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">9.0</span> | 1 | Elisabeth Philippe | |
"""

# Dictionnaire de test cases
TEST_CASES = {
    "single_book_author_error": {
        "original": SUMMARY_SINGLE_BOOK_AUTHOR_ERROR,
        "corrected": SUMMARY_SINGLE_BOOK_AUTHOR_CORRECTED,
        "book": {
            "auteur": "Alain Mabancou",
            "titre": "Ramsès de Paris",
            "editeur": "Seuil",
        },
        "correction": {
            "auteur": "Alain Mabanckou",
            "titre": "Ramsès de Paris",
            "editeur": "Seuil",
        },
    },
    "multiple_books_first_corrected": {
        "original": SUMMARY_MULTIPLE_BOOKS_MIXED,
        "corrected": SUMMARY_MULTIPLE_BOOKS_FIRST_CORRECTED,
        "book": {
            "auteur": "Alain Mabancou",
            "titre": "Ramsès de Paris",
            "editeur": "Seuil",
        },
        "correction": {
            "auteur": "Alain Mabanckou",
            "titre": "Ramsès de Paris",
            "editeur": "Seuil",
        },
    },
    "title_case_correction": {
        "original": SUMMARY_SPECIAL_CHARS,
        "corrected": SUMMARY_SPECIAL_CHARS_CORRECTED,
        "book": {
            "auteur": "Laurent Mauvignier",
            "titre": "La Maison Vide",
            "editeur": "Minuit",
        },
        "correction": {
            "auteur": "Laurent Mauvignier",
            "titre": "La Maison vide",  # Casse corrigée
            "editeur": "Minuit",
        },
    },
    "with_coups_de_coeur": {
        "original": SUMMARY_WITH_COUPS_DE_COEUR,
        "corrected": SUMMARY_WITH_COUPS_DE_COEUR_CORRECTED,
        "book": {
            "auteur": "Aslak Nord",
            "titre": "Piège à loup",
            "editeur": "Le bruit du monde",
        },
        "correction": {
            "auteur": "Aslak Nordström",  # Nom complet
            "titre": "Piège à loup",
            "editeur": "Le bruit du monde",
        },
    },
}
