"""Service d'extraction des critiques depuis les avis critiques."""

import re
from typing import Any


class CritiquesExtractionService:
    """Service pour extraire les noms des critiques depuis les summaries."""

    def extract_critiques_from_summary(self, summary: str) -> list[str]:
        """
        Extrait les noms des critiques depuis un summary d'avis critique.

        Le summary contient deux types de patterns:
        1. **Prénom Nom**: dans les avis détaillés (section "LIVRES DISCUTÉS")
        2. Noms dans la colonne "Critique" des tableaux de coups de cœur

        Args:
            summary: Texte du summary (format Markdown/HTML)

        Returns:
            Liste des noms de critiques détectés (dédupliqués)
        """
        if not summary:
            return []

        critiques = []
        seen = set()

        # Pattern 1: **Prénom Nom**: dans les avis détaillés
        pattern_bold = r"\*\*([^*]+)\*\*:"
        matches_bold = re.findall(pattern_bold, summary)

        for match in matches_bold:
            nom = match.strip()
            if (" " in nom or "-" in nom) and nom not in seen:
                critiques.append(nom)
                seen.add(nom)

        # Pattern 2: Colonne "Critique" des tableaux de coups de cœur
        # Format: | Auteur | Titre | Éditeur | Critique | Note | Commentaire |
        # Chercher les lignes de tableaux et extraire la 4ème colonne (index 3)
        # On cherche spécifiquement après "## 2. COUPS DE CŒUR"
        coups_de_coeur_section = re.search(
            r"## 2\. COUPS DE C[ΕŒ]UR.*?(?=##|$)", summary, re.DOTALL
        )

        if coups_de_coeur_section:
            section_text = coups_de_coeur_section.group(0)

            # Pattern pour extraire TOUTES les colonnes d'une ligne de tableau
            # Format: | col1 | col2 | col3 | col4 | col5 | col6 |
            # On split par | et on garde les colonnes 1-6 (indices 0-5 après split)
            lines = section_text.split("\n")

            for line in lines:
                if line.strip().startswith("|"):
                    columns = [col.strip() for col in line.split("|")]

                    # Vérifier qu'on a au moins 5 colonnes (pour atteindre la colonne Critique)
                    # Structure: colonne 0 vide, puis Auteur, Titre, Éditeur, Critique, Note, Commentaire
                    if len(columns) >= 5:
                        critique_name = columns[4].strip()

                        # Filtrer les headers et les séparateurs
                        if (
                            critique_name
                            and " " in critique_name  # Au moins prénom + nom
                            and not critique_name.startswith("-")  # Pas un séparateur
                            and critique_name.lower() != "critique"  # Pas le header
                            and critique_name not in seen
                        ):
                            critiques.append(critique_name)
                            seen.add(critique_name)

        return critiques

    def normalize_critique_name(self, name: str) -> str:
        """
        Normalise un nom de critique pour le matching.

        Args:
            name: Nom à normaliser

        Returns:
            Nom normalisé (minuscules, espaces nettoyés)
        """
        # Remplacer les espaces multiples par un seul espace
        normalized = re.sub(r"\s+", " ", name.strip())
        return normalized.lower()

    def find_matching_critique(
        self, detected_name: str, existing_critiques: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """
        Cherche un critique correspondant dans la base existante.

        Args:
            detected_name: Nom détecté dans le summary
            existing_critiques: Liste des critiques existants en base

        Returns:
            Dictionnaire avec {nom, match_type} si trouvé, None sinon
            match_type peut être: "exact" ou "variante"
        """
        normalized_detected = self.normalize_critique_name(detected_name)

        for critique in existing_critiques:
            # Vérifier correspondance exacte
            if self.normalize_critique_name(critique["nom"]) == normalized_detected:
                return {"nom": critique["nom"], "match_type": "exact"}

            # Vérifier correspondance sur les variantes
            for variante in critique.get("variantes", []):
                if self.normalize_critique_name(variante) == normalized_detected:
                    return {"nom": critique["nom"], "match_type": "variante"}

        return None


# Instance singleton du service
critiques_extraction_service = CritiquesExtractionService()
