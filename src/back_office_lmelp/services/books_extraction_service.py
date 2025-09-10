"""Service d'extraction de livres/auteurs/éditeurs depuis les tableaux markdown des avis critiques."""

import json
import os
from typing import Any

import openai
from dotenv import load_dotenv


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

        Args:
            avis_critiques: Liste des avis critiques avec leurs summaries

        Returns:
            Liste des livres extraits avec métadonnées (auteur/titre/éditeur)
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

        return all_extracted_books

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
        Ne retourne que les champs essentiels: auteur, titre, éditeur + métadonnées épisode.

        Args:
            books_data: Données brutes des livres extraits

        Returns:
            Données simplifiées pour l'affichage (sans statistiques)
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
            }
            simplified_books.append(simplified_book)

        return simplified_books


# Instance globale du service
books_extraction_service = BooksExtractionService()
