"""Registre des titres écartés d'un résumé (`avis_critiques.livres_ecartes`).

Un titre écarté est une ligne du résumé qui ne désigne pas un livre (ex. une
collection entière). Les extractions (avis, livres du cache) n'en produisent
rien. La comparaison passe par `normalize_for_matching` : casse, accents,
apostrophes et tirets typographiques sont ignorés, sans matching approximatif.
"""

from typing import Any

from .text_utils import normalize_for_matching


def is_titre_ecarte(titre: str, livres_ecartes: list[dict[str, Any]] | None) -> bool:
    """Indique si `titre` figure dans le registre des titres écartés."""
    if not titre or not livres_ecartes:
        return False
    normalized = normalize_for_matching(titre)
    return any(
        normalize_for_matching(entry.get("titre", "")) == normalized
        for entry in livres_ecartes
    )
