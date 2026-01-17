"""Service pour extraire les avis structurés depuis les summaries markdown."""

import logging
import os
import re
from typing import Any


logger = logging.getLogger(__name__)


class AvisExtractionService:
    """Service pour extraire les avis structurés depuis les summaries."""

    def __init__(self):
        """Initialise le service."""
        self._debug_log_enabled = os.getenv(
            "AVIS_EXTRACTION_DEBUG_LOG", "0"
        ).lower() in ("1", "true")

    def extract_avis_from_summary(
        self, summary: str, emission_oid: str
    ) -> list[dict[str, Any]]:
        """
        Extrait tous les avis depuis un summary markdown.

        Args:
            summary: Le contenu markdown du summary
            emission_oid: L'ID de l'émission

        Returns:
            Liste des avis extraits (non résolus)
        """
        avis_list: list[dict[str, Any]] = []

        # Extraire de la Section 1 (livres au programme)
        avis_list.extend(self._extract_section1_avis(summary, emission_oid))

        # Extraire de la Section 2 (coups de cœur)
        avis_list.extend(self._extract_section2_avis(summary, emission_oid))

        return avis_list

    def _extract_section1_avis(
        self, summary: str, emission_oid: str
    ) -> list[dict[str, Any]]:
        """
        Extrait les avis de la section 'LIVRES DISCUTÉS AU PROGRAMME'.

        Args:
            summary: Le contenu markdown
            emission_oid: L'ID de l'émission

        Returns:
            Liste des avis extraits de la Section 1
        """
        if not summary:
            return []

        avis_list: list[dict[str, Any]] = []

        # Trouver la Section 1
        section1_match = re.search(
            r"##\s*1\.\s*LIVRES DISCUTÉS.*?\n(.*?)(?=##\s*2\.|$)",
            summary,
            re.DOTALL | re.IGNORECASE,
        )
        if not section1_match:
            return []

        section1_content = section1_match.group(1)

        # Parser les lignes du tableau (ignorer les headers et séparateurs)
        lines = section1_content.strip().split("\n")
        for line in lines:
            # Ignorer les lignes vides, headers et séparateurs
            if not line.strip() or line.strip().startswith("|--") or "Auteur" in line:
                continue

            # Parser la ligne du tableau
            if line.strip().startswith("|"):
                columns = [col.strip() for col in line.split("|")]
                # Enlever les colonnes vides au début et à la fin
                columns = [c for c in columns if c]

                if len(columns) >= 4:
                    auteur = columns[0]
                    titre = columns[1]
                    editeur = columns[2]
                    avis_cell = columns[3]

                    # Parser les avis individuels (séparés par <br>)
                    critic_entries = re.split(r"<br\s*/?>", avis_cell)
                    for entry in critic_entries:
                        entry = entry.strip()
                        if not entry:
                            continue

                        parsed = self._parse_section1_critic_entry(entry)
                        if parsed:
                            avis_list.append(
                                {
                                    "emission_oid": emission_oid,
                                    "section": "programme",
                                    "livre_titre_extrait": titre,
                                    "auteur_nom_extrait": auteur,
                                    "editeur_extrait": editeur,
                                    "critique_nom_extrait": parsed[
                                        "critique_nom_extrait"
                                    ],
                                    "commentaire": parsed["commentaire"],
                                    "note": parsed["note"],
                                }
                            )

        return avis_list

    def _extract_section2_avis(
        self, summary: str, emission_oid: str
    ) -> list[dict[str, Any]]:
        """
        Extrait les avis de la section 'COUPS DE CŒUR DES CRITIQUES'.

        Args:
            summary: Le contenu markdown
            emission_oid: L'ID de l'émission

        Returns:
            Liste des avis extraits de la Section 2
        """
        if not summary:
            return []

        avis_list: list[dict[str, Any]] = []

        # Trouver la Section 2
        section2_match = re.search(
            r"##\s*2\.\s*COUPS DE C[ŒOE]UR.*?\n(.*?)(?=##\s*3\.|$)",
            summary,
            re.DOTALL | re.IGNORECASE,
        )
        if not section2_match:
            return []

        section2_content = section2_match.group(1)

        # Parser les lignes du tableau
        lines = section2_content.strip().split("\n")
        for line in lines:
            # Ignorer les lignes vides, headers et séparateurs
            if not line.strip() or line.strip().startswith("|--") or "Auteur" in line:
                continue

            # Parser la ligne du tableau
            if line.strip().startswith("|"):
                columns = [col.strip() for col in line.split("|")]
                # Enlever les colonnes vides au début et à la fin
                columns = [c for c in columns if c]

                # Format Section 2: Auteur | Titre | Éditeur | Critique | Note | Commentaire
                if len(columns) >= 6:
                    auteur = columns[0]
                    titre = columns[1]
                    editeur = columns[2]
                    critique = columns[3]
                    note_cell = columns[4]
                    commentaire = columns[5]

                    # Parser la note depuis la cellule (peut contenir du HTML)
                    note = self._parse_note_from_text(note_cell)

                    avis_list.append(
                        {
                            "emission_oid": emission_oid,
                            "section": "coup_de_coeur",
                            "livre_titre_extrait": titre,
                            "auteur_nom_extrait": auteur,
                            "editeur_extrait": editeur,
                            "critique_nom_extrait": critique,
                            "commentaire": commentaire,
                            "note": note,
                        }
                    )

        return avis_list

    def _parse_note_from_text(self, text: str) -> int | None:
        """
        Extrait la note depuis du texte.

        Gère plusieurs formats:
        - "Note: 7" ou "Note: 9"
        - "<span style='...'>8.0</span>"
        - "(9)" ou "(10)" en fin de texte

        Args:
            text: Le texte contenant potentiellement une note

        Returns:
            La note (entier 1-10) ou None si non trouvée
        """
        if not text:
            return None

        # Format 1: "Note: X" ou "Note: X.Y"
        match = re.search(r"Note:\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if match:
            return round(float(match.group(1)))

        # Format 2: <span ...>X</span> ou <span ...>X.Y</span>
        match = re.search(r"<span[^>]*>(\d+(?:\.\d+)?)</span>", text, re.IGNORECASE)
        if match:
            return round(float(match.group(1)))

        # Format 3: (X) ou (X.Y) en fin de texte (format 26 oct. 2025)
        match = re.search(r"\((\d+(?:\.\d+)?)\)\s*$", text)
        if match:
            return round(float(match.group(1)))

        return None

    def _parse_section1_critic_entry(self, entry: str) -> dict[str, Any] | None:
        """
        Parse une entrée de critique dans Section 1.

        Formats supportés:
        - **Nom Critique**: Commentaire. Note: X
        - **Nom Critique**: "Commentaire" (X)

        Args:
            entry: L'entrée textuelle d'un critique

        Returns:
            Dictionnaire avec critique_nom_extrait, commentaire, note
            ou None si parsing impossible
        """
        if not entry:
            return None

        # Pattern: **Nom Critique**: Contenu
        match = re.match(r"\*\*([^*]+)\*\*:\s*(.+)", entry.strip())
        if not match:
            return None

        critique_nom = match.group(1).strip()
        rest = match.group(2).strip()

        # Extraire la note depuis le reste
        note = self._parse_note_from_text(rest)

        # Extraire le commentaire selon le format
        commentaire = rest

        # Format 1: "Note: X" en fin
        note_match = re.search(r"\s*Note:\s*\d+", rest, re.IGNORECASE)
        if note_match:
            commentaire = rest[: note_match.start()].strip()
            # Enlever le point final si présent
            if commentaire.endswith("."):
                commentaire = commentaire[:-1].strip()
        else:
            # Format 2: (X) en fin - enlever la note entre parenthèses
            paren_match = re.search(r"\s*\(\d+(?:\.\d+)?\)\s*$", rest)
            if paren_match:
                commentaire = rest[: paren_match.start()].strip()

        # Nettoyer les guillemets autour du commentaire
        if commentaire.startswith('"') and commentaire.endswith('"'):
            commentaire = commentaire[1:-1].strip()

        return {
            "critique_nom_extrait": critique_nom,
            "commentaire": commentaire,
            "note": note,
        }

    def resolve_entities(
        self,
        extracted_avis: list[dict[str, Any]],
        livres: list[dict[str, Any]],
        critiques: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Résout les entités extraites vers leurs IDs MongoDB.

        Stratégie de matching exclusive en deux passes:
        1. Matches exacts (titre extrait == titre base)
        2. Matches partiels (titre extrait contenu dans titre base) sur livres restants

        Args:
            extracted_avis: Liste des avis avec données brutes
            livres: Liste des livres de l'épisode (depuis MongoDB)
            critiques: Liste des critiques connus (depuis MongoDB)

        Returns:
            Liste des avis avec livre_oid et critique_oid résolus (ou None)
        """
        resolved_avis: list[dict[str, Any]] = []

        # Initialiser tous les avis avec livre_oid = None
        for avis in extracted_avis:
            resolved = avis.copy()
            resolved["livre_oid"] = None
            resolved["critique_oid"] = None
            resolved_avis.append(resolved)

        # === Passe 1: Matches exacts pour les livres ===
        matched_livre_ids: set[str] = set()

        for resolved in resolved_avis:
            titre_extrait = resolved.get("livre_titre_extrait", "")
            livre_oid = self._find_matching_livre_exact(titre_extrait, livres)
            if livre_oid:
                resolved["livre_oid"] = livre_oid
                matched_livre_ids.add(livre_oid)

        # === Passe 2: Matches partiels sur les livres non encore matchés ===
        # Note: On ne retire PAS les livres déjà matchés car plusieurs avis
        # peuvent référencer le même livre (même titre extrait)
        for resolved in resolved_avis:
            if resolved["livre_oid"] is not None:
                continue  # Déjà résolu en passe 1

            titre_extrait = resolved.get("livre_titre_extrait", "")
            livre_oid = self._find_matching_livre_partial(titre_extrait, livres)
            if livre_oid:
                resolved["livre_oid"] = livre_oid

        # === Résolution des critiques (inchangée) ===
        for resolved in resolved_avis:
            critique_oid = self._find_matching_critique(
                resolved.get("critique_nom_extrait", ""), critiques
            )
            resolved["critique_oid"] = critique_oid

        # === Enrichissement: remplacer livre_titre_extrait par le titre officiel ===
        # Créer un index des livres par ID pour lookup rapide
        livres_by_id = {str(livre.get("_id", "")): livre for livre in livres}

        for resolved in resolved_avis:
            livre_oid = resolved.get("livre_oid")
            if livre_oid and livre_oid in livres_by_id:
                # Remplacer le titre extrait par le titre officiel du livre
                resolved["livre_titre_extrait"] = livres_by_id[livre_oid].get(
                    "titre", resolved.get("livre_titre_extrait", "")
                )

        return resolved_avis

    def _normalize_for_matching(self, text: str) -> str:
        """
        Normalise un texte pour le matching.

        Convertit en minuscules et supprime les espaces superflus.

        Args:
            text: Le texte à normaliser

        Returns:
            Le texte normalisé
        """
        if not text:
            return ""
        return " ".join(text.lower().split())

    def _find_matching_livre_exact(
        self, titre_extrait: str, livres: list[dict[str, Any]]
    ) -> str | None:
        """
        Trouve le livre correspondant par titre exact normalisé.

        Args:
            titre_extrait: Le titre extrait du markdown
            livres: Liste des livres disponibles

        Returns:
            L'ID du livre trouvé ou None
        """
        if not titre_extrait:
            return None

        normalized_titre = self._normalize_for_matching(titre_extrait)

        for livre in livres:
            livre_titre = livre.get("titre", "")
            if self._normalize_for_matching(livre_titre) == normalized_titre:
                return str(livre.get("_id", ""))

        return None

    def _find_matching_livre_partial(
        self, titre_extrait: str, livres: list[dict[str, Any]]
    ) -> str | None:
        """
        Trouve le livre correspondant par inclusion partielle du titre.

        Le titre extrait doit être contenu dans le titre du livre.
        Exemple: "La sirène d'Hollywood" matche "Esther Williams, la sirène d'Hollywood. Mémoires"

        Args:
            titre_extrait: Le titre extrait du markdown
            livres: Liste des livres disponibles

        Returns:
            L'ID du livre trouvé ou None
        """
        if not titre_extrait:
            return None

        normalized_titre = self._normalize_for_matching(titre_extrait)
        if not normalized_titre:
            return None

        for livre in livres:
            livre_titre = livre.get("titre", "")
            normalized_livre_titre = self._normalize_for_matching(livre_titre)
            # Match partiel : le titre extrait est contenu dans le titre du livre
            if normalized_titre in normalized_livre_titre:
                return str(livre.get("_id", ""))

        return None

    def _find_matching_critique(
        self, nom_extrait: str, critiques: list[dict[str, Any]]
    ) -> str | None:
        """
        Trouve le critique correspondant par nom ou variante.

        Args:
            nom_extrait: Le nom extrait du markdown
            critiques: Liste des critiques connus

        Returns:
            L'ID du critique trouvé ou None
        """
        if not nom_extrait:
            return None

        normalized_nom = self._normalize_for_matching(nom_extrait)

        for critique in critiques:
            # Match sur le nom principal
            critique_nom = critique.get("nom", "")
            if self._normalize_for_matching(critique_nom) == normalized_nom:
                return str(critique.get("_id", ""))

            # Match sur les variantes
            variantes = critique.get("variantes", [])
            for variante in variantes:
                if self._normalize_for_matching(variante) == normalized_nom:
                    return str(critique.get("_id", ""))

        return None
