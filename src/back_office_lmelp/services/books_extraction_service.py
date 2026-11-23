"""Service d'extraction de livres/auteurs/éditeurs depuis les tableaux markdown des avis critiques."""

from typing import Any

from ..utils.livres_ecartes import is_titre_ecarte
from ..utils.text_utils import normalize_for_matching


class BooksExtractionService:
    """Extrait les livres d'un résumé en lisant ses tableaux markdown, sans LLM."""

    async def extract_books_from_reviews(
        self, avis_critiques: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Extrait les livres des tableaux markdown des avis critiques.

        Lit les sections "LIVRES DISCUTÉS AU PROGRAMME" et "COUPS DE CŒUR DES
        CRITIQUES" et retire les titres écartés. N'interroge ni Babelio ni un
        LLM : l'URL et l'éditeur Babelio viennent de la validation livre par
        livre (« Valider avec Babelio »).

        Args:
            avis_critiques: Liste des avis critiques avec leurs summaries

        Returns:
            Liste des livres extraits avec métadonnées (auteur/titre/éditeur)

        Raises:
            ValueError: « Format markdown invalide » si un résumé n'a pas les
                deux sections attendues
        """
        all_extracted_books: list[dict[str, Any]] = []
        for avis in avis_critiques:
            books = self._extract_books_from_single_review(avis)
            all_extracted_books.extend(self._without_ecartes(books, avis))
        return all_extracted_books

    @staticmethod
    def _without_ecartes(
        books: list[dict[str, Any]], avis_critique: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Retire les titres du registre `livres_ecartes` de l'avis critique."""
        livres_ecartes = avis_critique.get("livres_ecartes")
        if not livres_ecartes:
            return books
        return [
            book
            for book in books
            if not is_titre_ecarte(book.get("titre", ""), livres_ecartes)
        ]

    def extract_books_from_summaries_markdown(
        self, avis_critiques: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extrait les livres des résumés, en ignorant ceux au format invalide.

        Sert à compléter un cache partiel à chaque chargement : un résumé au
        format invalide est ignoré, les titres écartés sont retirés.
        """
        books: list[dict[str, Any]] = []
        for avis in avis_critiques:
            summary = avis.get("summary", "")
            if not self._validate_markdown_format(summary)["valid"]:
                continue
            extracted = self._parse_summary_tables(
                summary,
                avis.get("episode_oid", ""),
                avis.get("episode_title", ""),
                avis.get("episode_date", ""),
            )
            books.extend(self._without_ecartes(extracted, avis))
        return books

    @staticmethod
    def books_missing_from_cache(
        extracted: list[dict[str, Any]], cached: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Livres extraits dont le titre ne correspond à aucune entrée de cache.

        Une entrée couvre son titre du résumé (`titre`), le titre proposé par
        Babelio (`suggested_title`, que le ramasse-miettes réécrit dans le
        résumé) et le titre validé (`validated_title`). Comparaison exacte après
        `normalize_for_matching`.
        """
        known_titles = {
            normalize_for_matching(entry[field])
            for entry in cached
            for field in ("titre", "suggested_title", "validated_title")
            if entry.get(field)
        }
        return [
            book
            for book in extracted
            if normalize_for_matching(book.get("titre", "")) not in known_titles
        ]

    def _extract_books_from_single_review(
        self, avis_critique: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extrait les livres d'un avis critique, après validation du format."""
        summary = avis_critique.get("summary", "")
        episode_oid = avis_critique.get("episode_oid", "")

        validation = self._validate_markdown_format(summary)
        if not validation["valid"]:
            raise ValueError(
                f"Format markdown invalide pour l'épisode {episode_oid}. "
                f"Sections manquantes: {', '.join(validation['missing_sections'])}. "
                f"Régénérez le résumé via {validation['help_url']}"
            )

        return self._parse_summary_tables(
            summary,
            episode_oid,
            avis_critique.get("episode_title", ""),
            avis_critique.get("episode_date", ""),
        )

    def _validate_markdown_format(self, summary: str) -> dict[str, Any]:
        """
        Valide que le markdown contient les sections attendues.

        Args:
            summary: Contenu markdown à valider

        Returns:
            {
                "valid": bool,
                "missing_sections": list[str],
                "help_url": str
            }
        """
        import re

        missing_sections = []

        # Vérifier la section "LIVRES DISCUTÉS AU PROGRAMME"
        if not re.search(
            r"## 1\. LIVRES DISCUTÉS AU PROGRAMME",
            summary,
        ):
            missing_sections.append(
                "Section '## 1. LIVRES DISCUTÉS AU PROGRAMME' manquante"
            )

        # Vérifier la section "COUPS DE CŒUR DES CRITIQUES"
        if not re.search(
            r"## 2\. COUPS DE CŒUR DES CRITIQUES",
            summary,
        ):
            missing_sections.append(
                "Section '## 2. COUPS DE CŒUR DES CRITIQUES' manquante"
            )

        return {
            "valid": len(missing_sections) == 0,
            "missing_sections": missing_sections,
            "help_url": "/avis_critiques",
        }

    def _parse_summary_tables(
        self, summary: str, episode_oid: str, episode_title: str, episode_date: str
    ) -> list[dict[str, Any]]:
        """Lit les DEUX tableaux markdown du résumé (programme, coups de cœur)."""
        import re

        books: list[dict[str, Any]] = []

        # 1. Chercher le tableau "LIVRES DISCUTÉS AU PROGRAMME"
        program_section = re.search(
            r"## 1\. LIVRES DISCUTÉS AU PROGRAMME.*?\n\n(.*?)(?=## 2\.|$)",
            summary,
            re.DOTALL,
        )

        if program_section:
            table_content = program_section.group(1)
            books.extend(
                self._parse_program_table(
                    table_content, episode_oid, episode_title, episode_date
                )
            )

        # 2. Chercher le tableau "COUPS DE CŒUR DES CRITIQUES"
        coups_coeur_section = re.search(
            r"## 2\. COUPS DE CŒUR DES CRITIQUES.*?\n\n(.*?)(?=## 3\.|$)",
            summary,
            re.DOTALL,
        )

        if coups_coeur_section:
            table_content = coups_coeur_section.group(1)
            books.extend(
                self._parse_coups_de_coeur_table(
                    table_content, episode_oid, episode_title, episode_date
                )
            )

        return books

    def _parse_program_table(
        self,
        table_content: str,
        episode_oid: str,
        episode_title: str,
        episode_date: str,
    ) -> list[dict[str, Any]]:
        """Parse le tableau des livres discutés au programme."""
        books = []

        # Parser les lignes du tableau markdown
        lines = table_content.strip().split("\n")

        for line in lines:
            if line.startswith("|") and not line.startswith("|-----"):
                # Ignorer les en-têtes
                if "Auteur" in line and "Titre" in line:
                    continue

                # Parser chaque ligne de livre
                parts = [
                    part.strip() for part in line.split("|")[1:-1]
                ]  # Enlever premiers et derniers vides

                if len(parts) >= 3:  # Au moins: Auteur, Titre, Éditeur
                    auteur = parts[0].strip()
                    titre = parts[1].strip()
                    editeur = parts[2].strip()

                    if auteur and titre and not auteur.startswith("---"):
                        book = {
                            "auteur": auteur,
                            "titre": titre,
                            "editeur": editeur,
                            "episode_oid": episode_oid,
                            "episode_title": episode_title,
                            "episode_date": episode_date,
                            # Indicateur: extrait depuis la section "au programme"
                            "programme": True,
                            "coup_de_coeur": False,
                        }
                        books.append(book)

        return books

    def _parse_coups_de_coeur_table(
        self,
        table_content: str,
        episode_oid: str,
        episode_title: str,
        episode_date: str,
    ) -> list[dict[str, Any]]:
        """Parse le tableau des coups de cœur des critiques."""
        books = []

        # Parser les lignes du tableau markdown
        lines = table_content.strip().split("\n")

        for line in lines:
            if line.startswith("|") and not line.startswith("|-----"):
                # Ignorer les en-têtes
                if "Auteur" in line and "Titre" in line:
                    continue

                # Parser chaque ligne de livre
                parts = [
                    part.strip() for part in line.split("|")[1:-1]
                ]  # Enlever premiers et derniers vides

                if len(parts) >= 3:  # Au moins: Auteur, Titre, Éditeur
                    auteur = parts[0].strip()
                    titre = parts[1].strip()
                    editeur = parts[2].strip()

                    if auteur and titre and not auteur.startswith("---"):
                        book = {
                            "auteur": auteur,
                            "titre": titre,
                            "editeur": editeur,
                            "episode_oid": episode_oid,
                            "episode_title": episode_title,
                            "episode_date": episode_date,
                            # Indicateur: extrait depuis la section "coups de coeur"
                            "programme": False,
                            "coup_de_coeur": True,
                        }
                        books.append(book)

        return books

    def format_books_for_display(
        self, books_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Formate les données de livres pour l'affichage frontend.

        Args:
            books_data: Données brutes des livres extraits

        Returns:
            Données formatées pour l'affichage
        """
        if not books_data:
            return []

        # Pour le MVP, on retourne les données telles quelles
        # Les formatages peuvent être ajoutés ici plus tard
        formatted_books = []

        for book in books_data:
            formatted_book = {
                "episode_oid": book.get("episode_oid", ""),
                "episode_title": book.get("episode_title", ""),
                "episode_date": book.get("episode_date", ""),
                "auteur": book.get("auteur", ""),
                "titre": book.get("titre", ""),
                "editeur": book.get("editeur", ""),
                "note_moyenne": float(book.get("note_moyenne", 0)),
                "nb_critiques": int(book.get("nb_critiques", 0)),
                "coups_de_coeur": book.get("coups_de_coeur", []),
            }
            formatted_books.append(formatted_book)

        return formatted_books

    def format_books_for_simplified_display(
        self, books_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Formate les données de livres pour l'affichage simplifié.
        Retourne les champs essentiels + statut unifié (système simplifié).

        Args:
            books_data: Données brutes des livres extraits

        Returns:
            Données simplifiées pour l'affichage avec statut unifié
        """
        if not books_data:
            return []

        simplified_books = []

        for book in books_data:
            simplified_book = {
                "episode_oid": book.get("episode_oid", ""),
                "episode_title": book.get("episode_title", ""),
                "episode_date": book.get("episode_date", ""),
                "auteur": book.get("auteur", ""),
                "titre": book.get("titre", ""),
                "editeur": book.get("editeur", ""),
                "programme": bool(book.get("programme", False)),
                "coup_de_coeur": not bool(
                    book.get("programme", False)
                ),  # programme=false = coup de cœur
            }

            # Ajouter le cache_id (mapping depuis _id MongoDB)
            if "_id" in book:
                simplified_book["cache_id"] = str(book["_id"])

            # Ajouter le statut unifié (système simplifié)
            if "status" in book:
                simplified_book["status"] = book["status"]

            # Ajouter les suggestions si disponibles (NoSQL: seulement si fournies)
            if "suggested_author" in book and book["suggested_author"]:
                simplified_book["suggested_author"] = book["suggested_author"]
            if "suggested_title" in book and book["suggested_title"]:
                simplified_book["suggested_title"] = book["suggested_title"]

            # Issue #85: Ajouter les enrichissements Babelio si disponibles
            if "babelio_url" in book and book["babelio_url"]:
                simplified_book["babelio_url"] = book["babelio_url"]
            if "babelio_publisher" in book and book["babelio_publisher"]:
                simplified_book["babelio_publisher"] = book["babelio_publisher"]

            # Issue #96: Ajouter book_id et author_id pour les liens clickables
            if "book_id" in book and book["book_id"]:
                # Convertir ObjectId en string si nécessaire
                book_id_value = book["book_id"]
                simplified_book["book_id"] = (
                    str(book_id_value) if book_id_value else None
                )
            if "author_id" in book and book["author_id"]:
                # Convertir ObjectId en string si nécessaire
                author_id_value = book["author_id"]
                simplified_book["author_id"] = (
                    str(author_id_value) if author_id_value else None
                )

            simplified_books.append(simplified_book)

        return simplified_books


# Instance globale du service
books_extraction_service = BooksExtractionService()
