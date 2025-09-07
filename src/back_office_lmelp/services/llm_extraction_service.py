"""Service d'extraction LLM pour les livres/auteurs/éditeurs depuis les avis critiques."""

import json
import os
from typing import Any

import openai
from dotenv import load_dotenv


load_dotenv()


class LLMExtractionService:
    """Service pour extraire les informations bibliographiques via LLM."""

    def __init__(self):
        """Initialise le service LLM."""

        # Configuration Azure OpenAI (à adapter selon vos credentials)
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")

        # Configuration du client OpenAI pour Azure
        if self.azure_endpoint and self.api_key:
            self.client = openai.AzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint,
            )
        else:
            # Pour les tests et le développement sans credentials Azure
            self.client = None

    async def extract_books_from_reviews(
        self, avis_critiques: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Extrait les informations bibliographiques depuis les avis critiques.

        Args:
            avis_critiques: Liste des avis critiques avec leurs summaries

        Returns:
            Liste des livres extraits avec métadonnées
        """
        if not avis_critiques:
            return []

        all_extracted_books = []

        for avis in avis_critiques:
            try:
                books_from_review = await self._extract_books_from_single_review(avis)
                all_extracted_books.extend(books_from_review)
            except Exception as e:
                print(
                    f"Erreur lors de l'extraction pour l'avis {avis.get('_id', 'unknown')}: {e}"
                )
                # Continuer avec les autres avis même si un échoue
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
            raise ValueError(
                "Client Azure OpenAI non configuré - vérifiez les variables d'environnement"
            )

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
        try:
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


# Instance globale du service
llm_extraction_service = LLMExtractionService()
