"""Utilitaire pour mettre à jour le summary des avis critiques (Issue #67).

Ce module fournit les fonctions pour remplacer les données d'un livre
dans les tableaux markdown du summary.
"""

import re


def replace_book_in_summary(
    summary: str,
    original_author: str,
    original_title: str,
    corrected_author: str,
    corrected_title: str,
) -> str:
    """
    Remplace un livre dans le summary (tableaux markdown).

    Args:
        summary: Le summary original contenant les tableaux markdown
        original_author: Nom d'auteur à remplacer
        original_title: Titre à remplacer
        corrected_author: Nom d'auteur corrigé
        corrected_title: Titre corrigé

    Returns:
        Summary avec le livre corrigé

    Note:
        Cette fonction préserve l'intégrité des tableaux markdown (pipes, newlines, etc.)
    """
    if not summary:
        return summary

    # Échapper les caractères spéciaux pour regex
    escaped_author = re.escape(original_author)
    escaped_title = re.escape(original_title)

    # Pattern pour matcher une ligne de tableau contenant l'auteur ET le titre
    # Format: | Auteur | Titre | ... |
    # On capture tout ce qui est avant l'auteur, entre auteur et titre, et après le titre
    pattern = (
        rf"(\|[^\|]*){escaped_author}([^\|]*\|[^\|]*){escaped_title}([^\|]*\|[^\n]*)"
    )

    # Fonction de remplacement qui préserve tout sauf auteur et titre
    def replacer(match: re.Match[str]) -> str:
        before_author = match.group(1)
        between = match.group(2)
        after_title = match.group(3)

        return (
            f"{before_author}{corrected_author}{between}{corrected_title}{after_title}"
        )

    # Remplacer la première occurrence (une ligne de tableau)
    updated_summary = re.sub(pattern, replacer, summary, count=1)

    return updated_summary


def should_update_summary(
    original_author: str,
    original_title: str,
    corrected_author: str,
    corrected_title: str,
) -> bool:
    """
    Détermine si le summary doit être mis à jour.

    Args:
        original_author: Nom d'auteur original
        original_title: Titre original
        corrected_author: Nom d'auteur corrigé
        corrected_title: Titre corrigé

    Returns:
        True si au moins un champ a changé, False sinon
    """
    return original_author != corrected_author or original_title != corrected_title
