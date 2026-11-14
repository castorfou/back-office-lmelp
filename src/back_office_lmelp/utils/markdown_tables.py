"""Réparation des tableaux markdown produits par le LLM."""

import re


_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")


def _is_separator(line: str) -> bool:
    return bool(_SEPARATOR_RE.match(line))


def _is_table_line(line: str) -> bool:
    return line.strip().startswith("|") or _is_separator(line)


def ensure_table_separators(markdown: str) -> str:
    """Insère la ligne ``|---|`` manquante sous chaque en-tête de tableau.

    Sans cette ligne, un rendu markdown n'affiche pas le tableau : en-tête et
    lignes deviennent du texte continu. L'en-tête est la première ligne d'un
    bloc de lignes commençant par ``|`` ; la ligne insérée a autant de colonnes.
    """
    lines = markdown.split("\n")
    result: list[str] = []
    for i, line in enumerate(lines):
        result.append(line)
        is_header = line.strip().startswith("|") and (
            i == 0 or not _is_table_line(lines[i - 1])
        )
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
        if is_header and not _is_separator(next_line):
            column_count = len(line.strip().strip("|").split("|"))
            result.append("|" + "---|" * column_count)
    return "\n".join(result)
