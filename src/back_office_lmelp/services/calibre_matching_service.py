"""Service de matching entre les livres MongoDB et la bibliothèque Calibre.

Ce service implémente un algorithme de matching à 3 niveaux :
1. Exact : titre normalisé identique (accents, ligatures, tirets, apostrophes)
2. Containment : un titre contient l'autre (gère sous-titres, tomes, prix)
3. Validation auteur : pour les cas ambigus, comparaison tolérante des noms

Fonctionnalités :
- Matching complet MongoDB ↔ Calibre
- Enrichissement du palmarès avec données Calibre
- Détection des corrections à appliquer dans Calibre

Issue #199
"""

import logging
import re
import time
from typing import Any

from ..utils.text_utils import normalize_for_matching


logger = logging.getLogger(__name__)

# Longueur minimale de titre normalisé pour le matching par containment
MIN_CONTAINMENT_LENGTH = 4

# Tags Calibre à préserver dans la copie s'ils sont déjà présents
NOTABLE_TAGS = ("babelio", "lu", "onkindle")


class CalibreMatchingService:
    """Service de matching entre les livres MongoDB et Calibre."""

    def __init__(
        self,
        calibre_service: Any,
        mongodb_service: Any,
        virtual_library_tag: str | None = None,
    ):
        self._calibre_service = calibre_service
        self._mongodb_service = mongodb_service
        self._virtual_library_tag = virtual_library_tag
        self._cache: dict[str, Any] | None = None
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 300  # 5 minutes

    def invalidate_cache(self) -> None:
        """Invalide le cache des données de matching."""
        self._cache = None
        self._cache_timestamp = 0

    def _normalize_author_parts(self, name: str) -> set[str]:
        """Extrait et normalise les parties d'un nom d'auteur.

        Gère les formats :
        - Naturel : "Mohamed Mbougar Sarr"
        - Calibre pipe : "Appanah| Nathacha"
        - Calibre virgule : "Sarr, Mohamed Mbougar"
        - Avec ligatures : "Kœnig| Gaspard"
        - Avec tirets : "Mbougar-Sarr"

        Returns:
            Ensemble de tokens normalisés (minuscules, sans accents).
        """
        # Normaliser accents et ligatures
        normalized = normalize_for_matching(name)

        # Séparer sur pipe, virgule, espace et tiret
        parts = re.split(r"[|,\s\-]+", normalized)

        # Filtrer les parties vides et les initiales seules (1-2 chars avec points)
        return {p.rstrip(".") for p in parts if p and len(p.rstrip(".")) > 1}

    def _authors_match(self, mongo_author: str, calibre_authors: list[str]) -> bool:
        """Compare un auteur MongoDB avec les auteurs Calibre de manière tolérante.

        Le matching est basé sur l'intersection des tokens de noms :
        au moins 1 token significatif en commun (nom de famille typiquement).

        Returns:
            True si au moins un auteur Calibre matche l'auteur MongoDB.
        """
        mongo_parts = self._normalize_author_parts(mongo_author)

        for calibre_author in calibre_authors:
            calibre_parts = self._normalize_author_parts(calibre_author)
            # Intersection des parties normalisées
            common = mongo_parts & calibre_parts
            # Au moins un token significatif en commun (nom de famille)
            if common:
                return True

        return False

    def _author_strings_differ(
        self, mongo_author: str, calibre_authors: list[str]
    ) -> bool:
        """Vérifie si les noms d'auteurs diffèrent au niveau chaîne.

        Compare le nom MongoDB normalisé avec chaque nom Calibre normalisé.
        Retourne True si aucun nom Calibre ne correspond exactement
        (après normalisation accents/ligatures/casse).
        """
        norm_mongo = normalize_for_matching(mongo_author)
        for cal_author in calibre_authors:
            norm_cal = normalize_for_matching(cal_author)
            if norm_mongo == norm_cal:
                return False
        return True

    def _get_data(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
        """Récupère les données des deux sources avec cache.

        Returns:
            Tuple (calibre_books, mongo_livres, authors_by_id)
        """
        now = time.time()
        if self._cache and (now - self._cache_timestamp) < self._cache_ttl:
            return (
                self._cache["calibre_books"],
                self._cache["mongo_livres"],
                self._cache["authors_by_id"],
            )

        calibre_books = self._calibre_service.get_all_books_with_tags()

        mongo_livres = self._mongodb_service.get_all_books()
        mongo_authors = self._mongodb_service.get_all_authors()

        # Index auteurs par id
        authors_by_id = {a["_id"]: a["nom"] for a in mongo_authors}

        self._cache = {
            "calibre_books": calibre_books,
            "mongo_livres": mongo_livres,
            "authors_by_id": authors_by_id,
        }
        self._cache_timestamp = now

        return calibre_books, mongo_livres, authors_by_id

    def match_all(self) -> list[dict[str, Any]]:
        """Exécute le matching complet entre MongoDB et Calibre.

        Algorithme à 3 niveaux :
        1. Exact : titre normalisé identique
        2. Containment : un titre contient l'autre (min 4 chars)
        3. Validation auteur : pour les ambiguïtés

        Returns:
            Liste de résultats de matching.
        """
        if not self._calibre_service._available:
            return []

        try:
            calibre_books, mongo_livres, authors_by_id = self._get_data()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données: {e}")
            return []

        # Index Calibre par titre normalisé
        calibre_by_norm_title: dict[str, dict[str, Any]] = {}
        for book in calibre_books:
            norm = normalize_for_matching(book["title"])
            calibre_by_norm_title[norm] = book

        matches: list[dict[str, Any]] = []
        matched_calibre_ids: set[int] = set()
        matched_mongo_ids: set[str] = set()

        # Tier 1: Exact title match
        for livre in mongo_livres:
            norm_mongo = normalize_for_matching(livre.get("titre", ""))
            if not norm_mongo:
                continue

            calibre_book = calibre_by_norm_title.get(norm_mongo)
            if calibre_book and calibre_book["id"] not in matched_calibre_ids:
                mongo_author = authors_by_id.get(livre.get("auteur_id", ""), "")
                matches.append(
                    self._build_match_result(livre, mongo_author, calibre_book, "exact")
                )
                matched_calibre_ids.add(calibre_book["id"])
                matched_mongo_ids.add(livre["_id"])

        # Tier 2+3: Containment match (with optional author validation)
        for livre in mongo_livres:
            if livre["_id"] in matched_mongo_ids:
                continue

            norm_mongo = normalize_for_matching(livre.get("titre", ""))
            if not norm_mongo:
                continue

            mongo_author = authors_by_id.get(livre.get("auteur_id", ""), "")
            candidates: list[dict[str, Any]] = []

            for calibre_book in calibre_books:
                if calibre_book["id"] in matched_calibre_ids:
                    continue

                norm_calibre = normalize_for_matching(calibre_book["title"])
                if not norm_calibre:
                    continue

                # Check containment (both directions)
                # Equal-length strings: containment is only possible if equal,
                # but equal titles are already matched in Tier 1
                if len(norm_mongo) == len(norm_calibre):
                    continue

                shorter = min(norm_mongo, norm_calibre, key=len)
                longer = max(norm_mongo, norm_calibre, key=len)

                if len(shorter) < MIN_CONTAINMENT_LENGTH:
                    continue

                if shorter in longer:
                    candidates.append(calibre_book)

            if len(candidates) == 1:
                # Single containment match: validate by author
                match_book = candidates[0]
                if self._authors_match(mongo_author, match_book.get("authors", [])):
                    matches.append(
                        self._build_match_result(
                            livre, mongo_author, match_book, "containment"
                        )
                    )
                    matched_calibre_ids.add(match_book["id"])
                    matched_mongo_ids.add(livre["_id"])
            elif len(candidates) > 1:
                # Multiple candidates: validate by author
                for candidate in candidates:
                    if self._authors_match(mongo_author, candidate.get("authors", [])):
                        matches.append(
                            self._build_match_result(
                                livre,
                                mongo_author,
                                candidate,
                                "author_validated",
                            )
                        )
                        matched_calibre_ids.add(candidate["id"])
                        matched_mongo_ids.add(livre["_id"])
                        break

        return matches

    def _build_match_result(
        self,
        livre: dict[str, Any],
        mongo_author: str,
        calibre_book: dict[str, Any],
        match_type: str,
    ) -> dict[str, Any]:
        """Construit un résultat de matching."""
        mongo_titre = livre.get("titre", "")
        calibre_title = calibre_book.get("title", "")
        calibre_authors = calibre_book.get("authors", [])

        return {
            "mongo_livre_id": livre["_id"],
            "mongo_titre": mongo_titre,
            "mongo_auteur": mongo_author,
            "calibre_id": calibre_book["id"],
            "calibre_title": calibre_title,
            "calibre_authors": calibre_authors,
            "calibre_tags": calibre_book.get("tags", []),
            "calibre_read": calibre_book.get("read"),
            "calibre_rating": calibre_book.get("rating"),
            "match_type": match_type,
            "title_differs": (
                normalize_for_matching(mongo_titre)
                != normalize_for_matching(calibre_title)
            ),
            "author_differs": self._author_strings_differ(
                mongo_author, calibre_authors
            ),
        }

    def get_calibre_index(self) -> dict[str, dict[str, Any]]:
        """Construit un index Calibre pour l'enrichissement du palmarès.

        Index basé sur le titre normalisé → données du livre Calibre.
        Utilisé pour un lookup O(1) lors de l'enrichissement.

        Returns:
            Dict {titre_normalisé: calibre_book_data}
        """
        if not self._calibre_service._available:
            return {}

        try:
            calibre_books = self._calibre_service.get_all_books_with_tags()
            return {normalize_for_matching(b["title"]): b for b in calibre_books}
        except Exception:
            return {}

    def enrich_palmares_item(
        self, item: dict[str, Any], calibre_index: dict[str, dict[str, Any]]
    ) -> None:
        """Enrichit un item du palmarès avec les données Calibre.

        Ajoute calibre_in_library, calibre_read, calibre_rating, calibre_current_tags.
        """
        norm_title = normalize_for_matching(item.get("titre", ""))
        calibre_book = calibre_index.get(norm_title)

        if calibre_book:
            item["calibre_in_library"] = True
            item["calibre_read"] = calibre_book.get("read")
            item["calibre_rating"] = (
                calibre_book.get("rating") if calibre_book.get("read") else None
            )
            item["calibre_current_tags"] = calibre_book.get("tags")
        else:
            item["calibre_in_library"] = False
            item["calibre_read"] = None
            item["calibre_rating"] = None
            item["calibre_current_tags"] = None

    def get_corrections(self) -> dict[str, Any]:
        """Calcule les corrections à appliquer dans Calibre.

        Returns:
            Dict avec les corrections groupées par type :
            - author_corrections: différences de noms d'auteurs
            - title_corrections: différences de titres
            - missing_lmelp_tags: livres avec tags lmelp_ manquants
            - statistics: compteurs
        """
        matches = self.match_all()

        author_corrections: list[dict[str, Any]] = []
        title_corrections: list[dict[str, Any]] = []

        for match in matches:
            # Correction d'auteur
            if match["author_differs"]:
                author_corrections.append(
                    {
                        "calibre_id": match["calibre_id"],
                        "calibre_title": match["calibre_title"],
                        "calibre_authors": match["calibre_authors"],
                        "mongodb_author": match["mongo_auteur"],
                        "mongo_livre_id": match["mongo_livre_id"],
                        "match_type": match["match_type"],
                    }
                )

            # Correction de titre
            if match["title_differs"]:
                title_corrections.append(
                    {
                        "calibre_id": match["calibre_id"],
                        "calibre_title": match["calibre_title"],
                        "mongodb_title": match["mongo_titre"],
                        "author": match["mongo_auteur"],
                        "mongo_livre_id": match["mongo_livre_id"],
                        "match_type": match["match_type"],
                    }
                )

        # Compute expected lmelp_ tags for all matched livres
        all_livre_ids = [m["mongo_livre_id"] for m in matches]
        expected_tags_map = self._mongodb_service.get_expected_calibre_tags(
            all_livre_ids
        )

        # Detect missing lmelp_ tags
        missing_lmelp_tags: list[dict[str, Any]] = []
        for match in matches:
            calibre_tags = match.get("calibre_tags", [])
            livre_id = match["mongo_livre_id"]
            expected_lmelp = expected_tags_map.get(livre_id, [])

            # Find which expected tags are missing from Calibre
            existing_lmelp = {t for t in calibre_tags if t.startswith("lmelp_")}
            missing_tags = [t for t in expected_lmelp if t not in existing_lmelp]

            if missing_tags:
                # Build all_tags_to_copy: [virtual_library_tag] + [notable] + [lmelp_]
                all_tags_to_copy = list(expected_lmelp)
                # Preserve notable tags (lu, onkindle) if already in Calibre
                notable = [t for t in NOTABLE_TAGS if t in calibre_tags]
                for i, tag in enumerate(notable):
                    all_tags_to_copy.insert(i, tag)
                if self._virtual_library_tag:
                    all_tags_to_copy.insert(0, self._virtual_library_tag)

                missing_lmelp_tags.append(
                    {
                        "calibre_id": match["calibre_id"],
                        "calibre_title": match["calibre_title"],
                        "current_tags": calibre_tags,
                        "mongo_livre_id": livre_id,
                        "author": match["mongo_auteur"],
                        "expected_lmelp_tags": missing_tags,
                        "all_tags_to_copy": all_tags_to_copy,
                    }
                )

        return {
            "author_corrections": author_corrections,
            "title_corrections": title_corrections,
            "missing_lmelp_tags": missing_lmelp_tags,
            "statistics": {
                "total_author_corrections": len(author_corrections),
                "total_title_corrections": len(title_corrections),
                "total_missing_lmelp_tags": len(missing_lmelp_tags),
                "total_matches": len(matches),
            },
        }

    def get_onkindle_books(self) -> list[dict[str, Any]]:
        """Retourne les livres Calibre tagués 'onkindle', enrichis avec les données MongoDB.

        Pour chaque livre Calibre avec le tag 'onkindle', cherche le livre correspondant
        dans MongoDB (matching par titre normalisé) et enrichit avec :
        - mongo_livre_id, auteur_id, url_babelio (depuis livres collection)
        - note_moyenne (calculée depuis avis_critiques)

        Returns:
            Liste de dicts triés par titre, avec données Calibre + enrichissement MongoDB.
        """
        if not self._calibre_service._available:
            return []

        try:
            calibre_books, mongo_livres, authors_by_id = self._get_data()
        except Exception as e:
            logger.error(f"Erreur récupération données onkindle: {e}")
            return []

        # Filter calibre books with onkindle tag
        onkindle_books = [b for b in calibre_books if "onkindle" in b.get("tags", [])]

        if not onkindle_books:
            return []

        # Build MongoDB lookup: norm_title → mongo livre
        mongo_by_norm: dict[str, dict[str, Any]] = {}
        for livre in mongo_livres:
            norm = normalize_for_matching(livre.get("titre", ""))
            if norm:
                mongo_by_norm[norm] = livre

        # Build result with MongoDB enrichment
        matched_livre_ids = []
        pre_result = []
        for book in sorted(onkindle_books, key=lambda b: b["title"]):
            norm = normalize_for_matching(book["title"])
            mongo_livre = mongo_by_norm.get(norm)

            mongo_livre_id = None
            auteur_id = None
            url_babelio = None

            if mongo_livre:
                mongo_livre_id = str(mongo_livre["_id"])
                auteur_id_raw = mongo_livre.get("auteur_id")
                auteur_id = str(auteur_id_raw) if auteur_id_raw else None
                url_babelio = mongo_livre.get("url_babelio")
                matched_livre_ids.append(mongo_livre_id)

            pre_result.append(
                {
                    "calibre_id": book["id"],
                    "titre": book["title"],
                    "auteurs": book["authors"],
                    "calibre_rating": book.get("rating"),
                    "calibre_read": book.get("read"),
                    "mongo_livre_id": mongo_livre_id,
                    "auteur_id": auteur_id,
                    "url_babelio": url_babelio,
                    "note_moyenne": None,  # Will be filled below
                }
            )

        # Enrich with notes from avis_critiques
        notes_by_id = self._mongodb_service.get_notes_for_livres(matched_livre_ids)
        for item in pre_result:
            if item["mongo_livre_id"]:
                item["note_moyenne"] = notes_by_id.get(item["mongo_livre_id"])

        return pre_result
