"""Utilitaires pour le traitement de texte.

Ce module contient des fonctions utilitaires pour manipuler et transformer du texte,
notamment pour la recherche insensible aux accents.
"""

import unicodedata


def create_accent_insensitive_regex(term: str) -> str:
    """Convertit un terme de recherche en regex insensible aux accents.

    Transforme chaque caractère alphabétique en un charset regex qui matche
    toutes les variantes accentuées de ce caractère. Par exemple, 'e' devient
    '[eèéêëēĕėęě]' pour matcher 'e', 'è', 'é', 'ê', etc.

    Le terme est d'abord normalisé (accents retirés) avant la transformation,
    ce qui permet de traiter aussi bien "cafe" que "café" de la même manière.

    Args:
        term: Le terme de recherche à convertir (ex: "carrere", "café", "etranger")

    Returns:
        Un pattern regex qui matche les variantes accentuées du terme.
        Exemple: "carrere" -> "[cç][aàâäáãåāăą]rr[eèéêëēĕėęě]r[eèéêëēĕėęě]"
        Exemple: "café" -> "[cç][aàâäáãåāăą]f[eèéêëēĕėęě]"

    Examples:
        >>> create_accent_insensitive_regex("carrere")
        '[cç][aàâäáãåāăą]rr[eèéêëēĕėęě]r[eèéêëēĕėęě]'

        >>> create_accent_insensitive_regex("café")
        '[cç][aàâäáãåāăą]f[eèéêëēĕėęě]'

        >>> create_accent_insensitive_regex("francois")
        'fr[aàâäáãåāăą][nñń][cç][oòóôöõøōŏő][iìíîïĩīĭįı]s'

    Note:
        - Les caractères non alphabétiques (espaces, apostrophes, etc.) sont préservés
        - La recherche est case-insensitive quand utilisée avec re.IGNORECASE
        - Conçu pour fonctionner avec les requêtes MongoDB $regex
    """
    # Mapping des caractères vers leurs variantes accentuées
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
    }

    # Étape 1: Normaliser le terme (retirer les accents)
    # NFD = Normalization Form Decomposed (sépare les caractères de leurs accents)
    nfd = unicodedata.normalize("NFD", term)
    # Retirer tous les caractères de type "Mark, Nonspacing" (les accents)
    normalized_term = "".join(
        char for char in nfd if unicodedata.category(char) != "Mn"
    )

    # Étape 2: Convertir chaque caractère en charset avec variantes
    result = []
    for char in normalized_term.lower():
        # Si le caractère a des variantes accentuées, utiliser le charset
        # Sinon, garder le caractère tel quel (pour espaces, apostrophes, chiffres, etc.)
        result.append(accent_map.get(char, char))

    return "".join(result)
