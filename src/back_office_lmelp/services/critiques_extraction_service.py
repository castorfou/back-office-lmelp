"""Service d'extraction des critiques depuis les avis critiques."""

import re
from typing import Any


class CritiquesExtractionService:
    """Service pour extraire les noms des critiques depuis les summaries."""

    def extract_critiques_from_summary(self, summary: str) -> list[str]:
        """
        Extrait les noms des critiques depuis un summary d'avis critique.

        Le summary contient des patterns comme **Prénom Nom**: "Commentaire"
        dans les tableaux markdown.

        Args:
            summary: Texte du summary (format Markdown/HTML)

        Returns:
            Liste des noms de critiques détectés (dédupliqués)
        """
        if not summary:
            return []

        # Pattern pour détecter **Prénom Nom**: dans le texte
        # Capture le texte entre ** et **: en s'assurant qu'il contient au moins un espace
        # (pour avoir prénom + nom)
        pattern = r"\*\*([^*]+)\*\*:"

        matches = re.findall(pattern, summary)

        if not matches:
            return []

        # Nettoyer les noms et supprimer les doublons
        critiques = []
        seen = set()

        for match in matches:
            # Nettoyer le nom (trim espaces)
            nom = match.strip()

            # Vérifier que c'est un nom valide (au moins un prénom et un nom)
            if " " in nom and nom not in seen:
                critiques.append(nom)
                seen.add(nom)

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
