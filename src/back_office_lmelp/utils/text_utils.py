"""Utilitaires pour le traitement de texte.

Ce module contient des fonctions utilitaires pour manipuler et transformer du texte,
notamment pour la recherche insensible aux accents.
"""

import unicodedata


def create_accent_insensitive_regex(term: str) -> str:
    """Convertit un terme de recherche en regex insensible aux accents et caractères typographiques.

    Transforme chaque caractère alphabétique en un charset regex qui matche
    toutes les variantes accentuées de ce caractère. Par exemple, 'e' devient
    '[eèéêëēĕėęě]' pour matcher 'e', 'è', 'é', 'ê', etc.

    Le terme est d'abord normalisé (accents retirés, ligatures converties) avant
    la transformation, ce qui permet de traiter aussi bien "cafe" que "café",
    "oeuvre" que "œuvre", de la même manière.

    Args:
        term: Le terme de recherche à convertir (ex: "carrere", "café", "oeuvre", "l'ami")

    Returns:
        Un pattern regex qui matche les variantes accentuées et typographiques du terme.
        Exemple: "carrere" -> "[cç][aàâäáãåāăąæ]rr[eèéêëēĕėęě]r[eèéêëēĕėęě]"
        Exemple: "café" -> "[cç][aàâäáãåāăąæ]f[eèéêëēĕėęě]"
        Exemple: "oeuvre" -> "[oòóôöõøōŏőœ][eèéêëēĕėęě]"
        Exemple: "l'ami" -> "l[''][aàâäáãåāăąæ]m[iìíîïĩīĭįı]"

    Examples:
        >>> create_accent_insensitive_regex("carrere")
        '[cç][aàâäáãåāăąæ]rr[eèéêëēĕėęě]r[eèéêëēĕėęě]'

        >>> create_accent_insensitive_regex("oeuvre")  # Matche aussi "œuvre"
        '[oòóôöõøōŏőœ][eèéêëēĕėęě]'

        >>> create_accent_insensitive_regex("Marie-Claire")  # Matche aussi "Marie–Claire"
        'm[aàâäáãåāăąæ]r[iìíîïĩīĭįı][eèéêëēĕėęě][-–][cç]l[aàâäáãåāăąæ][iìíîïĩīĭįı]r[eèéêëēĕėęě]'

    Note:
        - Issue #92: Insensibilité aux accents
        - Issue #173: Ligatures (œ ↔ oe, æ ↔ ae), tirets (– ↔ -), apostrophes (' ↔ ')
        - Les caractères non alphabétiques (espaces, apostrophes, etc.) sont préservés
        - La recherche est case-insensitive quand utilisée avec re.IGNORECASE
        - Conçu pour fonctionner avec les requêtes MongoDB $regex
    """
    # Mapping des caractères vers leurs variantes accentuées + typographie
    # Inclut les caractères Unicode courants en français et autres langues européennes
    accent_map = {
        "a": "[aàâäáãåāăą]",
        "e": "[eèéêëēĕėęě]",
        "i": "[iìíîïĩīĭįı]",
        "o": "[oòóôöõøōŏő]",
        "u": "[uùúûüũūŭůűų]",
        "c": "[cç]",
        "n": "[nñń]",
        "y": "[yÿý]",
        "-": "[-–]",  # Tiret simple + tiret cadratin
        "'": "['']",  # Apostrophe simple + apostrophe typographique
    }

    # Étape 1: Normaliser le terme (retirer les accents via NFD)
    # NFD = Normalization Form Decomposed (sépare les caractères de leurs accents)
    nfd = unicodedata.normalize("NFD", term)
    # Retirer tous les caractères de type "Mark, Nonspacing" (les accents)
    normalized_term = "".join(
        char for char in nfd if unicodedata.category(char) != "Mn"
    )

    # Étape 2: Normaliser les ligatures latines (Issue #173)
    # IMPORTANT: Remplacer les ligatures PAR LEURS SÉQUENCES avant conversion regex
    normalized_term = normalized_term.replace("œ", "oe").replace("Œ", "oe")
    normalized_term = normalized_term.replace("æ", "ae").replace("Æ", "ae")

    # Étape 3: Normaliser tirets et apostrophes typographiques (Issue #173)
    normalized_term = normalized_term.replace("–", "-")  # Tiret cadratin → simple
    normalized_term = normalized_term.replace(
        "'", "'"
    )  # Apostrophe typographique → simple

    # Étape 4: Convertir chaque caractère en charset avec variantes
    result = []
    i = 0
    while i < len(normalized_term.lower()):
        char = normalized_term.lower()[i]
        next_char = (
            normalized_term.lower()[i + 1]
            if i + 1 < len(normalized_term.lower())
            else None
        )

        # Détecter les séquences "oe" et "ae" pour gérer les ligatures (Issue #173)
        if char == "o" and next_char == "e":
            # Séquence "oe" → peut matcher "oe" ou "œ"
            result.append("(?:[oòóôöõøōŏő][eèéêëēĕėęě]|œ)")
            i += 2  # Sauter les 2 caractères
        elif char == "a" and next_char == "e":
            # Séquence "ae" → peut matcher "ae" ou "æ"
            result.append("(?:[aàâäáãåāăą][eèéêëēĕėęě]|æ)")
            i += 2  # Sauter les 2 caractères
        # Détecter un espace qui suit une lettre (Issue #173 - apostrophe optionnelle)
        # Ex: "d Ormesson" doit matcher "d' Ormesson" ET "l ami" doit matcher "l'ami"
        elif char == " " and i > 0 and normalized_term.lower()[i - 1].isalpha():
            # Espace après lettre → peut avoir apostrophe optionnelle avant l'espace
            # Pattern: ['']? ?  (apostrophe optionnelle + espace optionnel)
            # Ceci matche: "d Ormesson" → "d' Ormesson" ET "l ami" → "l'ami"
            result.append("['']? ?")
            i += 1
        else:
            # Caractère normal : utiliser le mapping ou le caractère tel quel
            result.append(accent_map.get(char, char))
            i += 1

    return "".join(result)
