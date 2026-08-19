"""Service pour extraire les avis structurés depuis les summaries markdown."""

import logging
import os
import re
from difflib import SequenceMatcher
from typing import Any

from ..utils.text_utils import normalize_for_matching


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
            if (
                not line.strip()
                or line.strip().startswith("|--")
                or re.match(r"^\s*\|\s*Auteur\s*\|", line)
            ):
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
            # CRITIQUE: Vérifier que c'est le header (contient "Auteur" ET "Titre" ET "Éditeur")
            # pour éviter de skip les lignes dont le commentaire contient "Auteur" (Issue #185)
            is_header = "Auteur" in line and "Titre" in line and "Éditeur" in line
            if not line.strip() or line.strip().startswith("|--") or is_header:
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

                    # Nettoyer les guillemets du commentaire (Issue #185)
                    commentaire = commentaire.strip('"')

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
        - ", 10" ou ", 7" en fin de texte (format 14 sept. 2025)

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

        # Format 4: ", X" en fin de texte (format 14 sept. 2025)
        # Note: ne matche que les notes valides (1-10)
        match = re.search(r",\s*(\d+(?:\.\d+)?)\s*$", text)
        if match:
            note_value = round(float(match.group(1)))
            # Vérifier que c'est une note valide (1-10)
            if 1 <= note_value <= 10:
                return note_value

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
                else:
                    # Format 3: ", X" en fin (format 14 sept. 2025)
                    # Seulement si note valide (1-10) a été extraite
                    if note is not None:
                        trailing_match = re.search(r",\s*\d+(?:\.\d+)?\s*$", rest)
                        if trailing_match:
                            commentaire = rest[: trailing_match.start()].strip()

        # Nettoyer les guillemets autour du commentaire
        if commentaire.startswith('"') and commentaire.endswith('"'):
            commentaire = commentaire[1:-1].strip()

        return {
            "critique_nom_extrait": critique_nom,
            "commentaire": commentaire,
            "note": note,
        }

    def _extract_unique_books_from_avis(
        self, avis_list: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Extrait les livres uniques depuis une liste d'avis.

        Utilise (titre, auteur) comme clé pour identifier les livres uniques.

        Args:
            avis_list: Liste des avis extraits

        Returns:
            Liste de livres summary: [{"titre": str, "auteur": str}, ...]
        """
        seen_books: dict[tuple[str, str], dict[str, str]] = {}

        for avis in avis_list:
            titre = avis.get("livre_titre_extrait", "")
            auteur = avis.get("auteur_nom_extrait", "")
            key = (titre, auteur)

            if key not in seen_books:
                seen_books[key] = {
                    "titre": titre,
                    "auteur": auteur,
                }

        return list(seen_books.values())

    def match_livres(
        self,
        livres_summary: list[dict[str, str]],
        livres_mongo: list[dict[str, Any]],
    ) -> dict[tuple[str, str], tuple[str, int]]:
        """
        Matche les livres summary avec les livres MongoDB.

        Fonction PUBLIQUE principale pour le matching livre par livre.
        CRITIQUE pour Issue #185 : Cette fonction garantit qu'un livre MongoDB
        ne peut être matché qu'une seule fois.

        Args:
            livres_summary: Liste [{"titre": str, "auteur": str}, ...]
            livres_mongo: Liste [{"_id": ObjectId, "titre": str, ...}, ...]

        Returns:
            Dict {(titre, auteur): (livre_oid, match_phase)}
        """
        livre_matches: dict[tuple[str, str], tuple[str, int]] = {}
        matched_livre_mongo_ids: set[str] = set()  # Livres MongoDB déjà matchés
        remaining_livres_summary = livres_summary.copy()  # Livres summary restants

        # Phase 1: Matching exact (titre normalisé)
        for livre_summary in remaining_livres_summary[:]:  # Copie pour itération
            titre = livre_summary["titre"]
            auteur = livre_summary["auteur"]
            key = (titre, auteur)

            livre_oid = self._find_matching_livre_exact(titre, livres_mongo)
            if livre_oid and livre_oid not in matched_livre_mongo_ids:
                livre_matches[key] = (livre_oid, 1)
                matched_livre_mongo_ids.add(livre_oid)
                remaining_livres_summary.remove(livre_summary)  # Retirer du summary

        # Phase 2: Matching partiel sur livres summary RESTANTS
        livres_mongo_restants = [
            livre
            for livre in livres_mongo
            if str(livre["_id"]) not in matched_livre_mongo_ids
        ]

        for livre_summary in remaining_livres_summary[:]:
            titre = livre_summary["titre"]
            auteur = livre_summary["auteur"]
            key = (titre, auteur)

            livre_oid = self._find_matching_livre_partial(titre, livres_mongo_restants)
            if livre_oid:
                livre_matches[key] = (livre_oid, 2)
                matched_livre_mongo_ids.add(livre_oid)
                remaining_livres_summary.remove(livre_summary)
                # Mettre à jour la liste des livres MongoDB restants
                livres_mongo_restants = [
                    livre
                    for livre in livres_mongo_restants
                    if str(livre["_id"]) != livre_oid
                ]

        # Phase 3: Matching par similarité sur livres summary RESTANTS
        for livre_summary in remaining_livres_summary[:]:
            titre = livre_summary["titre"]
            auteur = livre_summary["auteur"]
            key = (titre, auteur)

            livre_oid = self._find_matching_livre_by_similarity(
                titre, auteur, livres_mongo_restants
            )
            if livre_oid:
                livre_matches[key] = (livre_oid, 3)
                matched_livre_mongo_ids.add(livre_oid)
                remaining_livres_summary.remove(livre_summary)
                # Mettre à jour la liste des livres MongoDB restants
                livres_mongo_restants = [
                    livre
                    for livre in livres_mongo_restants
                    if str(livre["_id"]) != livre_oid
                ]

        # Phase 4: Fuzzy matching (si même nombre de livres restants)
        if len(remaining_livres_summary) > 0 and len(remaining_livres_summary) == len(
            livres_mongo_restants
        ):
            fuzzy_matches = self._fuzzy_match_remaining_books_v2(
                remaining_livres_summary, livres_mongo_restants
            )
            livre_matches.update(fuzzy_matches)

        return livre_matches

    def _fuzzy_match_remaining_books_v2(
        self,
        livres_summary: list[dict[str, str]],
        livres_mongo: list[dict[str, Any]],
    ) -> dict[tuple[str, str], tuple[str, int]]:
        """
        Phase 4: Associe les livres restants par fuzzy matching.

        Algorithme:
        1. Si 1 livre restant de chaque côté → association automatique
        2. Sinon, calculer matrice de similarité titre summary/titre MongoDB
           et associer par meilleur score (greedy)

        Args:
            livres_summary: Livres summary non encore matchés
            livres_mongo: Livres MongoDB non encore matchés

        Returns:
            Dict {(titre, auteur): (livre_oid, match_phase=4)}
        """
        fuzzy_matches: dict[tuple[str, str], tuple[str, int]] = {}

        if not livres_mongo or not livres_summary:
            return fuzzy_matches

        # Cas simple: 1 livre restant de chaque côté → association automatique
        if len(livres_mongo) == 1 and len(livres_summary) == 1:
            livre = livres_mongo[0]
            livre_id = str(livre.get("_id", ""))
            livre_summary = livres_summary[0]
            key = (livre_summary["titre"], livre_summary["auteur"])

            fuzzy_matches[key] = (livre_id, 4)

            if self._debug_log_enabled:
                logger.info(
                    f"🔗 [PHASE4] Association automatique (1 restant): "
                    f"'{livre_summary['titre']}' -> '{livre.get('titre')}'"
                )
            return fuzzy_matches

        # Cas général: calculer les distances et associer par meilleur score
        # Construire matrice de similarité
        similarity_matrix: list[tuple[dict[str, str], str, float]] = []

        for livre in livres_mongo:
            livre_id = str(livre.get("_id", ""))
            livre_titre = self._normalize_for_matching(livre.get("titre", ""))

            for livre_summary in livres_summary:
                titre_summary = livre_summary["titre"]
                normalized_summary = self._normalize_for_matching(titre_summary)
                score = SequenceMatcher(None, normalized_summary, livre_titre).ratio()
                similarity_matrix.append((livre_summary, livre_id, score))

        # Trier par score décroissant et associer (greedy)
        similarity_matrix.sort(key=lambda x: x[2], reverse=True)
        assigned_summary_keys: set[tuple[str, str]] = set()
        assigned_livre_ids: set[str] = set()

        for livre_summary, livre_id, score in similarity_matrix:
            key = (livre_summary["titre"], livre_summary["auteur"])

            if key in assigned_summary_keys or livre_id in assigned_livre_ids:
                continue

            # Associer ce livre summary à ce livre MongoDB
            fuzzy_matches[key] = (livre_id, 4)
            assigned_summary_keys.add(key)
            assigned_livre_ids.add(livre_id)

            if self._debug_log_enabled:
                logger.info(
                    f"🔗 [PHASE4] Fuzzy match (score={score:.2f}): "
                    f"'{livre_summary['titre']}' -> livre_id={livre_id}"
                )

            # Arrêter si tous les livres sont assignés
            if len(assigned_livre_ids) == len(livres_mongo):
                break

        return fuzzy_matches

    def resolve_avis(
        self,
        avis_list: list[dict[str, Any]],
        livre_matches: dict[tuple[str, str], tuple[str, int]],
        critiques: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Applique les matches de livres aux avis individuels.

        Fonction PUBLIQUE pour appliquer les résultats du matching livre par livre
        à chaque avis individuel.

        Args:
            avis_list: Liste des avis à résoudre
            livre_matches: Dict {(titre, auteur): (livre_oid, match_phase)}
            critiques: Liste des critiques

        Returns:
            Liste des avis résolus avec livre_oid, match_phase et critique_oid
        """
        resolved_avis = []

        for avis in avis_list:
            resolved = avis.copy()

            # Clé du livre
            titre = avis.get("livre_titre_extrait", "")
            auteur = avis.get("auteur_nom_extrait", "")
            key = (titre, auteur)

            # Appliquer le match du livre (lookup simple)
            if key in livre_matches:
                livre_oid, match_phase = livre_matches[key]
                resolved["livre_oid"] = livre_oid
                resolved["match_phase"] = match_phase
            else:
                resolved["livre_oid"] = None
                resolved["match_phase"] = None

            # Matcher la critique (indépendant du livre)
            critique_oid = self._find_matching_critique(
                avis.get("critique_nom_extrait", ""), critiques
            )
            resolved["critique_oid"] = critique_oid

            resolved_avis.append(resolved)

        return resolved_avis

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

        REFACTORED pour Issue #185: Utilise maintenant un matching livre par livre
        au lieu de avis par avis, garantissant qu'un livre MongoDB ne peut être
        matché qu'une seule fois.

        Stratégie:
        1. Extraire les livres uniques depuis les avis
        2. Matcher les livres (phases 1-4)
        3. Appliquer les matches aux avis individuels
        4. Calculer les statistiques

        Args:
            extracted_avis: Liste des avis avec données brutes
            livres: Liste des livres de l'épisode (depuis MongoDB)
            critiques: Liste des critiques connus (depuis MongoDB)

        Returns:
            Tuple (avis résolus, statistiques de matching)
        """
        # 1. Extraire les livres uniques depuis les avis
        livres_summary = self._extract_unique_books_from_avis(extracted_avis)

        # 2. Matcher les livres (livre par livre, pas avis par avis)
        livre_matches = self.match_livres(livres_summary, livres)

        # 3. Appliquer les matches aux avis individuels
        resolved_avis = self.resolve_avis(extracted_avis, livre_matches, critiques)

        # 4. Calculer les statistiques (par livre unique, pas par avis)
        stats = {
            "livres_summary": len(livres_summary),
            "livres_mongo": len(livres),
            "match_phase1": 0,
            "match_phase2": 0,
            "match_phase3": 0,
            "match_phase4": 0,
            "unmatched": 0,
        }

        # Compter les matches par phase (par livre unique)
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

        # === Enrichissement: ajouter auteur_oid et editeur depuis MongoDB ===
        livres_by_id = {str(livre.get("_id", "")): livre for livre in livres}

        for resolved in resolved_avis:
            livre_oid = resolved.get("livre_oid")
            if livre_oid and livre_oid in livres_by_id:
                livre = livres_by_id[livre_oid]
                resolved["auteur_oid"] = str(livre.get("auteur_id", ""))
                resolved["editeur"] = livre.get("editeur", "")

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

        # Utilise normalize_for_matching (retire accents/ligatures) plutôt que
        # self._normalize_for_matching (casse/espaces uniquement) car les noms
        # extraits par l'IA depuis la transcription peuvent perdre les accents
        # (Issue #263: "Philippe Tretiak" vs variante stockée "Philippe Trétiak").
        normalized_nom = normalize_for_matching(nom_extrait)

        for critique in critiques:
            # Match sur le nom principal
            critique_nom = critique.get("nom", "")
            if normalize_for_matching(critique_nom) == normalized_nom:
                return str(critique.get("_id", ""))

            # Match sur les variantes
            variantes = critique.get("variantes", [])
            for variante in variantes:
                if normalize_for_matching(variante) == normalized_nom:
                    return str(critique.get("_id", ""))

        return None
