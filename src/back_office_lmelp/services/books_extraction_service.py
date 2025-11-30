"""Service d'extraction de livres/auteurs/éditeurs depuis les tableaux markdown des avis critiques."""

import json
import os
from typing import Any

import openai
from dotenv import load_dotenv

from .babelio_service import babelio_service


load_dotenv()


class BooksExtractionService:
    """Service pour extraire les informations bibliographiques via parsing des tableaux markdown."""

    def __init__(self):
        """Initialise le service d'extraction de livres."""

        # Configuration Azure OpenAI (à adapter selon vos credentials)
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")

        # Configuration du client OpenAI pour Azure - TOUTES les variables doivent être présentes
        if (
            self.azure_endpoint
            and self.api_key
            and self.azure_endpoint.strip()
            and self.api_key.strip()
        ):
            try:
                self.client = openai.AzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.azure_endpoint,
                )
            except Exception:
                # Si la création du client échoue, utiliser le fallback
                self.client = None
        else:
            # Pour les tests et le développement sans credentials Azure complets
            self.client = None

    async def extract_books_from_reviews(
        self, avis_critiques: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Extrait les informations bibliographiques depuis les tableaux markdown des avis critiques.
        Parse les sections "LIVRES DISCUTÉS AU PROGRAMME" et "COUPS DE CŒUR DES CRITIQUES".
        Enrichit automatiquement chaque livre avec Babelio (babelio_url, babelio_publisher).

        Args:
            avis_critiques: Liste des avis critiques avec leurs summaries

        Returns:
            Liste des livres extraits avec métadonnées (auteur/titre/éditeur + enrichissement Babelio)
        """
        if not avis_critiques:
            return []

        all_extracted_books = []

        for avis in avis_critiques:
            try:
                books_from_review = await self._extract_books_from_single_review(avis)
                all_extracted_books.extend(books_from_review)
            except Exception as e:
                error_msg = str(e)

                # Si c'est une erreur de connexion Azure OpenAI, essayer le fallback silencieusement
                if (
                    "Connection error" in error_msg
                    or "Client Azure OpenAI non configuré" in error_msg
                ):
                    try:
                        fallback_books = self._extract_books_from_summary_fallback(
                            avis.get("summary", ""),
                            avis.get("episode_oid", ""),
                            avis.get("episode_title", ""),
                            avis.get("episode_date", ""),
                        )
                        all_extracted_books.extend(fallback_books)
                    except Exception:
                        # Fallback échoué, continuer silencieusement
                        continue
                else:
                    # Autres erreurs, continuer sans fallback
                    continue

        # Enrichir automatiquement chaque livre avec Babelio (Option 1: enrichissement en temps réel)
        enriched_books = await self._enrich_books_with_babelio(all_extracted_books)

        return enriched_books

    async def _extract_books_from_single_review(
        self, avis_critique: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extrait les livres depuis un seul avis critique."""
        summary = avis_critique.get("summary", "")
        episode_oid = avis_critique.get("episode_oid", "")
        episode_title = avis_critique.get("episode_title", "")
        episode_date = avis_critique.get("episode_date", "")

        # Prompt pour l'extraction
        system_prompt = """Tu es un expert en extraction d'informations bibliographiques depuis des critiques littéraires.
À partir du résumé d'émission fourni, extrait UNIQUEMENT les livres mentionnés dans les tableaux "LIVRES DISCUTÉS AU PROGRAMME".
Ignore les "COUPS DE CŒUR" qui sont des recommandations séparées.

Pour chaque livre trouvé, retourne un objet JSON avec exactement ces champs:
- "auteur": string (nom de l'auteur)
- "titre": string (titre du livre)
- "editeur": string (nom de l'éditeur)
- "note_moyenne": number (note moyenne calculée depuis les avis, ou 0 si non disponible)
- "nb_critiques": number (nombre de critiques pour ce livre)
- "coups_de_coeur": array of strings (noms des critiques ayant donné un coup de cœur)

Retourne une liste JSON valide, même si vide: []"""

        user_prompt = f"""Résumé d'émission à analyser:
{summary}

Extrait les livres du tableau "LIVRES DISCUTÉS AU PROGRAMME" uniquement."""

        # Appel à l'API Azure OpenAI
        if self.client is None:
            # Mode démo/développement : retourner des données d'exemple parsées du contenu
            return self._extract_books_from_summary_fallback(
                summary, episode_oid, episode_title, episode_date
            )

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Peu de créativité pour l'extraction factuelle
                max_tokens=2000,
            )

            # Parse de la réponse
            content = response.choices[0].message.content.strip()
            books_data = json.loads(content)

            # Ajouter les métadonnées d'épisode à chaque livre
            enriched_books = []
            for book in books_data:
                enriched_book = book.copy()
                enriched_book["episode_oid"] = episode_oid
                enriched_book["episode_title"] = episode_title
                enriched_book["episode_date"] = episode_date
                enriched_books.append(enriched_book)

            return enriched_books

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise Exception(f"Erreur lors du parsing de la réponse LLM: {e}") from e
        except Exception:
            # En cas d'erreur Azure OpenAI, utiliser le fallback
            return self._extract_books_from_summary_fallback(
                summary, episode_oid, episode_title, episode_date
            )

    def _extract_books_from_summary_fallback(
        self, summary: str, episode_oid: str, episode_title: str, episode_date: str
    ) -> list[dict[str, Any]]:
        """
        Mode fallback : extrait les livres directement du summary sans LLM.
        Parse les DEUX tableaux markdown pour extraire les informations de livres.
        """
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

    async def _enrich_books_with_babelio(
        self, books: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Enrichit automatiquement chaque livre avec Babelio (babelio_url, babelio_publisher).
        Appelle verify_book() pour chaque livre et enrichit si confidence >= 0.90.

        Args:
            books: Liste des livres extraits

        Returns:
            Liste des livres enrichis avec babelio_url et babelio_publisher
        """
        enriched_books = []

        for book in books:
            enriched_book = book.copy()
            titre = book.get("titre", "")
            auteur = book.get("auteur", "")

            try:
                # Appeler Babelio verify_book()
                verification = await babelio_service.verify_book(titre, auteur)

                # ✅ FIX Issue #85: Utiliser la vraie clé "confidence_score" de l'API (pas "confidence")
                confidence = (
                    verification.get("confidence_score", 0) if verification else 0
                )

                # Enrichir si confidence >= 0.90
                if verification and confidence >= 0.90:
                    # ✅ FIX Issue #85: L'API retourne "babelio_url" directement (pas "url")
                    if verification.get("babelio_url"):
                        enriched_book["babelio_url"] = verification["babelio_url"]
                    if verification.get("babelio_publisher"):
                        enriched_book["babelio_publisher"] = verification[
                            "babelio_publisher"
                        ]

                    # ✅ FIX Issue #88: Enrichir suggested_title et suggested_author
                    # Ces champs sont ESSENTIELS pour que le frontend affiche le titre complet
                    # dans le modal de validation (LivresAuteurs.vue:validateSuggestion)
                    if verification.get("babelio_suggestion_title"):
                        enriched_book["suggested_title"] = verification[
                            "babelio_suggestion_title"
                        ]
                    if verification.get("babelio_suggestion_author"):
                        enriched_book["suggested_author"] = verification[
                            "babelio_suggestion_author"
                        ]

            except Exception:
                # En cas d'erreur Babelio (timeout, réseau, etc.), continuer sans enrichissement
                # Le livre reste tel quel sans babelio_url/babelio_publisher
                pass

            enriched_books.append(enriched_book)

        return enriched_books

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
