"""Service pour extraire les avis structurés depuis les summaries markdown."""

import logging
import os
import re
from difflib import SequenceMatcher
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

        # Format 1: "Note: X" ou "Note: X.Y" (avec deux-points)
        match = re.search(r"Note:\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if match:
            return round(float(match.group(1)))

        # Format 1b: "note 9" ou "note 8.5" (sans deux-points, en fin de texte)
        match = re.search(r"\bnote\s+(\d+(?:\.\d+)?)\s*$", text, re.IGNORECASE)
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

        # Format 1: "Note: X" en fin (avec deux-points)
        note_match = re.search(r"\s*Note:\s*\d+", rest, re.IGNORECASE)
        if note_match:
            commentaire = rest[: note_match.start()].strip()
            # Enlever le point final si présent
            if commentaire.endswith("."):
                commentaire = commentaire[:-1].strip()
        else:
            # Format 1b: "note 9" en fin (sans deux-points)
            note_space_match = re.search(
                r",?\s*note\s+\d+(?:\.\d+)?\s*$", rest, re.IGNORECASE
            )
            if note_space_match:
                commentaire = rest[: note_space_match.start()].strip()
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

        Stratégie de matching en trois passes:
        1. Matches exacts (titre extrait == titre base)
        2. Matches partiels (titre extrait contenu dans titre base)
        3. Matches par similarité (auteur, titre, ou couple auteur-titre)

        Args:
            extracted_avis: Liste des avis avec données brutes
            livres: Liste des livres de l'épisode (depuis MongoDB)
            critiques: Liste des critiques connus (depuis MongoDB)

        Returns:
            Liste des avis avec livre_oid et critique_oid résolus (ou None)
        """
        resolved, _ = self.resolve_entities_with_stats(
            extracted_avis, livres, critiques
        )
        return resolved

    def resolve_entities_with_stats(
        self,
        extracted_avis: list[dict[str, Any]],
        livres: list[dict[str, Any]],
        critiques: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Résout les entités extraites vers leurs IDs MongoDB avec statistiques.

        Stratégie de matching en trois passes:
        1. Matches exacts (titre extrait == titre base)
        2. Matches partiels (titre extrait contenu dans titre base)
        3. Matches par similarité (auteur, titre, ou couple auteur-titre)

        Args:
            extracted_avis: Liste des avis avec données brutes
            livres: Liste des livres de l'épisode (depuis MongoDB)
            critiques: Liste des critiques connus (depuis MongoDB)

        Returns:
            Tuple (avis résolus, statistiques de matching)
        """
        resolved_avis: list[dict[str, Any]] = []

        # Statistiques de matching
        stats = {
            "livres_summary": 0,  # Nombre de livres uniques dans le summary
            "livres_mongo": len(livres),
            "match_phase1": 0,  # Matches exacts
            "match_phase2": 0,  # Matches partiels
            "match_phase3": 0,  # Matches par similarité
            "match_phase4": 0,  # Matches fuzzy (quand counts égaux)
            "unmatched": 0,  # Sans match
        }

        # Initialiser tous les avis avec livre_oid = None et match_phase = None
        for avis in extracted_avis:
            resolved = avis.copy()
            resolved["livre_oid"] = None
            resolved["critique_oid"] = None
            resolved["match_phase"] = None
            resolved_avis.append(resolved)

        # Compter les livres uniques dans le summary (par titre extrait)
        unique_titles = {a.get("livre_titre_extrait", "") for a in extracted_avis}
        stats["livres_summary"] = len(unique_titles)

        # === Passe 1: Matches exacts pour les livres ===
        matched_livre_ids: set[str] = set()

        for resolved in resolved_avis:
            titre_extrait = resolved.get("livre_titre_extrait", "")
            livre_oid = self._find_matching_livre_exact(titre_extrait, livres)
            if livre_oid:
                resolved["livre_oid"] = livre_oid
                resolved["match_phase"] = 1
                matched_livre_ids.add(livre_oid)

        # === Passe 2: Matches partiels sur les livres non encore matchés ===
        for resolved in resolved_avis:
            if resolved["livre_oid"] is not None:
                continue  # Déjà résolu en passe 1

            titre_extrait = resolved.get("livre_titre_extrait", "")
            livre_oid = self._find_matching_livre_partial(titre_extrait, livres)
            if livre_oid:
                resolved["livre_oid"] = livre_oid
                resolved["match_phase"] = 2
                matched_livre_ids.add(livre_oid)

        # === Passe 3: Matches par similarité pour les avis non résolus ===
        unmatched_livres = [
            livre
            for livre in livres
            if str(livre.get("_id", "")) not in matched_livre_ids
        ]

        for resolved in resolved_avis:
            if resolved["livre_oid"] is not None:
                continue  # Déjà résolu en passe 1 ou 2

            titre_extrait = resolved.get("livre_titre_extrait", "")
            auteur_extrait = resolved.get("auteur_nom_extrait", "")
            livre_oid = self._find_matching_livre_by_similarity(
                titre_extrait, auteur_extrait, unmatched_livres
            )
            if livre_oid:
                resolved["livre_oid"] = livre_oid
                resolved["match_phase"] = 3
                matched_livre_ids.add(livre_oid)
                unmatched_livres = [
                    livre
                    for livre in unmatched_livres
                    if str(livre.get("_id", "")) != livre_oid
                ]

        # === Passe finale: Propager livre_oid aux avis avec le même titre ===
        # Construire un mapping titre -> livre_oid pour les avis déjà résolus
        title_to_livre_oid: dict[str, tuple[str, int]] = {}
        for resolved in resolved_avis:
            livre_oid = resolved.get("livre_oid")
            if livre_oid:
                titre = resolved.get("livre_titre_extrait", "")
                if titre and titre not in title_to_livre_oid:
                    title_to_livre_oid[titre] = (
                        livre_oid,
                        resolved.get("match_phase", 3),
                    )

        # Propager aux avis non encore résolus ayant le même titre
        for resolved in resolved_avis:
            if resolved.get("livre_oid") is None:
                titre = resolved.get("livre_titre_extrait", "")
                if titre in title_to_livre_oid:
                    livre_oid, match_phase = title_to_livre_oid[titre]
                    resolved["livre_oid"] = livre_oid
                    resolved["match_phase"] = match_phase

        # === Phase 4: Fuzzy matching quand # livres MongoDB == # livres summary ===
        # Si les comptages sont égaux, on peut associer les livres restants
        unmatched_avis_titles = {
            a.get("livre_titre_extrait", "")
            for a in resolved_avis
            if a.get("livre_oid") is None
        }
        remaining_livres = [
            livre
            for livre in livres
            if str(livre.get("_id", "")) not in matched_livre_ids
        ]

        # Si même nombre de livres non matchés des deux côtés
        if len(unmatched_avis_titles) > 0 and len(remaining_livres) == len(
            unmatched_avis_titles
        ):
            # Associer les livres restants par fuzzy matching
            self._fuzzy_match_remaining_books(
                resolved_avis, remaining_livres, matched_livre_ids
            )

        # Compter les matches par phase (par livre unique, pas par avis)
        matched_titles_phase1: set[str] = set()
        matched_titles_phase2: set[str] = set()
        matched_titles_phase3: set[str] = set()
        matched_titles_phase4: set[str] = set()
        unmatched_titles: set[str] = set()

        for resolved in resolved_avis:
            titre = resolved.get("livre_titre_extrait", "")
            phase = resolved.get("match_phase")
            if phase == 1:
                matched_titles_phase1.add(titre)
            elif phase == 2:
                matched_titles_phase2.add(titre)
            elif phase == 3:
                matched_titles_phase3.add(titre)
            elif phase == 4:
                matched_titles_phase4.add(titre)
            else:
                unmatched_titles.add(titre)

        stats["match_phase1"] = len(matched_titles_phase1)
        stats["match_phase2"] = len(matched_titles_phase2)
        stats["match_phase3"] = len(matched_titles_phase3)
        stats["match_phase4"] = len(matched_titles_phase4)
        stats["unmatched"] = len(unmatched_titles)

        # === Résolution des critiques (inchangée) ===
        for resolved in resolved_avis:
            critique_oid = self._find_matching_critique(
                resolved.get("critique_nom_extrait", ""), critiques
            )
            resolved["critique_oid"] = critique_oid

        # === Enrichissement: ajouter auteur_oid pour le lien cliquable ===
        # Note: On ne remplace PAS livre_titre_extrait par le titre officiel.
        # L'API enrichit avec livre_titre (titre officiel) séparément.
        # Garder livre_titre_extrait intact permet au frontend de grouper par livre_oid.
        livres_by_id = {str(livre.get("_id", "")): livre for livre in livres}

        for resolved in resolved_avis:
            livre_oid = resolved.get("livre_oid")
            if livre_oid and livre_oid in livres_by_id:
                # Ajouter l'auteur_id pour le lien cliquable
                resolved["auteur_oid"] = str(
                    livres_by_id[livre_oid].get("auteur_id", "")
                )

        return resolved_avis, stats

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

    def _find_matching_livre_by_similarity(
        self,
        titre_extrait: str,
        auteur_extrait: str,
        livres: list[dict[str, Any]],
        min_threshold: float = 0.3,
    ) -> str | None:
        """
        Trouve le livre correspondant par similarité (pour les typos).

        Stratégie: Pour chaque livre restant, calculer un score de similarité
        basé sur le titre ET l'auteur, puis prendre le meilleur match.

        Le score est le maximum de:
        - Similarité sur le titre (avec titre court si sous-titre présent)
        - Similarité sur l'auteur
        - Similarité sur le couple auteur-titre

        On prend le meilleur match parmi tous les livres restants, tant que
        le score dépasse un seuil minimum pour éviter les faux positifs évidents.

        Args:
            titre_extrait: Le titre extrait du markdown
            auteur_extrait: Le nom de l'auteur extrait du markdown
            livres: Liste des livres disponibles (non encore matchés)
            min_threshold: Seuil minimum pour éviter les faux positifs évidents

        Returns:
            L'ID du livre avec le meilleur score (ou None si score < min_threshold)
        """
        if not titre_extrait and not auteur_extrait:
            return None

        if not livres:
            return None

        normalized_titre = self._normalize_for_matching(titre_extrait)
        normalized_auteur = self._normalize_for_matching(auteur_extrait)

        best_match: tuple[str | None, float] = (None, 0.0)

        for livre in livres:
            livre_id = str(livre.get("_id", ""))
            livre_titre_complet = self._normalize_for_matching(livre.get("titre", ""))

            # Extraire le titre court (avant ":" si sous-titre présent)
            if ":" in livre_titre_complet:
                livre_titre_court = livre_titre_complet.split(":")[0].strip()
            else:
                livre_titre_court = livre_titre_complet

            max_score_for_livre = 0.0

            # Stratégie 1: Similarité sur le titre complet
            if normalized_titre and livre_titre_complet:
                score = SequenceMatcher(
                    None, normalized_titre, livre_titre_complet
                ).ratio()
                max_score_for_livre = max(max_score_for_livre, score)

            # Stratégie 2: Similarité sur le titre court (sans sous-titre)
            if normalized_titre and livre_titre_court:
                score = SequenceMatcher(
                    None, normalized_titre, livre_titre_court
                ).ratio()
                max_score_for_livre = max(max_score_for_livre, score)

            # Stratégie 3: Similarité sur l'auteur vs titre complet
            # (utile quand l'auteur est dans le titre: "Auteur, titre...")
            if normalized_auteur and livre_titre_complet:
                score = SequenceMatcher(
                    None, normalized_auteur, livre_titre_complet
                ).ratio()
                max_score_for_livre = max(max_score_for_livre, score)

            # Stratégie 4: Similarité sur le couple auteur-titre
            if normalized_titre and normalized_auteur and livre_titre_complet:
                combined_extrait = f"{normalized_auteur} {normalized_titre}"
                score = SequenceMatcher(
                    None, combined_extrait, livre_titre_complet
                ).ratio()
                max_score_for_livre = max(max_score_for_livre, score)

            # Garder le meilleur match global
            if max_score_for_livre > best_match[1]:
                best_match = (livre_id, max_score_for_livre)

        # Retourner le meilleur match s'il dépasse le seuil minimum
        if best_match[0] and best_match[1] >= min_threshold:
            if self._debug_log_enabled:
                logger.info(
                    f"🔍 [SIMILARITY] Match trouvé avec score {best_match[1]:.2f}: "
                    f"'{auteur_extrait}' - '{titre_extrait}' -> livre_id={best_match[0]}"
                )
            return best_match[0]

        return None

    def _fuzzy_match_remaining_books(
        self,
        resolved_avis: list[dict[str, Any]],
        remaining_livres: list[dict[str, Any]],
        matched_livre_ids: set[str],
    ) -> None:
        """
        Phase 4: Associe les livres restants quand # MongoDB == # summary.

        Algorithme:
        1. Si 1 livre restant de chaque côté → association automatique
        2. Sinon, pour chaque livre MongoDB, calculer la similarité avec
           chaque titre summary non matché, puis associer par meilleur score

        Args:
            resolved_avis: Liste des avis (modifiée in-place)
            remaining_livres: Livres MongoDB non encore matchés
            matched_livre_ids: Set des IDs déjà matchés (modifié in-place)
        """
        if not remaining_livres:
            return

        # Collecter les titres summary non matchés (uniques)
        unmatched_titles = list(
            {
                a.get("livre_titre_extrait", "")
                for a in resolved_avis
                if a.get("livre_oid") is None and a.get("livre_titre_extrait")
            }
        )

        if not unmatched_titles:
            return

        # Cas simple: 1 livre restant de chaque côté → association automatique
        if len(remaining_livres) == 1 and len(unmatched_titles) == 1:
            livre = remaining_livres[0]
            livre_id = str(livre.get("_id", ""))
            titre_summary = unmatched_titles[0]

            for resolved in resolved_avis:
                if (
                    resolved.get("livre_oid") is None
                    and resolved.get("livre_titre_extrait") == titre_summary
                ):
                    resolved["livre_oid"] = livre_id
                    resolved["match_phase"] = 4
                    matched_livre_ids.add(livre_id)

            if self._debug_log_enabled:
                logger.info(
                    f"🔗 [PHASE4] Association automatique (1 restant): "
                    f"'{titre_summary}' -> '{livre.get('titre')}'"
                )
            return

        # Cas général: calculer les distances et associer par meilleur score
        # Construire matrice de similarité
        similarity_matrix: list[tuple[str, str, float]] = []

        for livre in remaining_livres:
            livre_id = str(livre.get("_id", ""))
            livre_titre = self._normalize_for_matching(livre.get("titre", ""))

            for titre_summary in unmatched_titles:
                normalized_summary = self._normalize_for_matching(titre_summary)
                score = SequenceMatcher(None, normalized_summary, livre_titre).ratio()
                similarity_matrix.append((titre_summary, livre_id, score))

        # Trier par score décroissant et associer (greedy)
        similarity_matrix.sort(key=lambda x: x[2], reverse=True)
        assigned_titles: set[str] = set()
        assigned_livre_ids: set[str] = set()

        for titre_summary, livre_id, score in similarity_matrix:
            if titre_summary in assigned_titles or livre_id in assigned_livre_ids:
                continue

            # Associer ce titre à ce livre
            for resolved in resolved_avis:
                if (
                    resolved.get("livre_oid") is None
                    and resolved.get("livre_titre_extrait") == titre_summary
                ):
                    resolved["livre_oid"] = livre_id
                    resolved["match_phase"] = 4
                    matched_livre_ids.add(livre_id)

            assigned_titles.add(titre_summary)
            assigned_livre_ids.add(livre_id)

            if self._debug_log_enabled:
                logger.info(
                    f"🔗 [PHASE4] Fuzzy match (score={score:.2f}): "
                    f"'{titre_summary}' -> livre_id={livre_id}"
                )

            # Arrêter si tous les livres sont assignés
            if len(assigned_livre_ids) == len(remaining_livres):
                break

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
