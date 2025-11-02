"""Test end-to-end pour l'enrichissement automatique Babelio (Issue #85).

Ce test laisse tourner le VRAI CODE et ne mocke que les dépendances externes :
- MongoDB (avis critiques, cache)
- API Babelio externe (babelio_service.verify_book)

Le flux testé :
1. get_critical_reviews_by_episode_oid() → retourne avis critiques (mocked)
2. get_books_by_episode_oid() → cache vide [] (mocked)
3. extract_books_from_reviews() → VRAI CODE s'exécute
4. _enrich_books_with_babelio() → VRAI CODE s'exécute
5. babelio_service.verify_book() → mocked pour retourner haute confidence
6. format_books_for_simplified_display() → VRAI CODE s'exécute (BUG ICI)
7. API retourne JSON

Ce test DOIT ÉCHOUER car format_books_for_simplified_display() perd les champs Babelio.
"""

from unittest.mock import patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestBabelioEnrichmentEndToEnd:
    """Tests end-to-end pour l'enrichissement automatique Babelio."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_api_should_return_babelio_fields_when_book_enriched_during_extraction(
        self,
    ):
        """
        Test TDD (Issue #85): GET /api/livres-auteurs doit retourner babelio_url
        et babelio_publisher quand un livre est enrichi lors de l'extraction.

        Ce test laisse tourner le VRAI CODE et ne mocke que MongoDB et l'API Babelio externe.

        Flux testé (END-TO-END - simule "Relancer validation Biblio") :
        1. get_critical_reviews_by_episode_oid() → retourne avis critiques (MOCKED)
        2. get_books_by_episode_oid() → retourne [] (MOCKED - pas de cache)
        3. extract_books_from_reviews() → VRAI CODE extrait du summary
        4. _enrich_books_with_babelio() → VRAI CODE appelle Babelio
        5. babelio_service.verify_book() → MOCKED - retourne confidence 0.95
        6. format_books_for_simplified_display() → VRAI CODE formate
        7. API retourne JSON

        Ce test ÉCHOUE actuellement car format_books_for_simplified_display()
        ne préserve PAS babelio_url et babelio_publisher.
        """
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )

        # Mock 1: Avis critiques avec un livre dans le summary markdown
        # Format attendu par _extract_books_from_summary_fallback()
        mock_avis_critiques = [
            {
                "_id": avis_critique_id,
                "episode_oid": episode_oid,
                "episode_title": "Test Episode",
                "episode_date": "01 jan. 2025",
                "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Carlos Gimenez | Paracuellos, Intégrale | Audie-Fluide glacial |

## 2. COUPS DE CŒUR DES CRITIQUES

(Aucun)
""",
            }
        ]

        # Mock 2: Réponse de l'API Babelio (basée sur un VRAI appel API)
        # Structure capturée avec:
        # curl -X POST "http://0.0.0.0:54321/api/verify-babelio" \
        #   -d '{"type": "book", "title": "Paracuellos, Intégrale", "author": "Carlos Gimenez"}'
        # Capturé: 2025-01-19
        mock_babelio_response = {
            "status": "verified",
            "original_title": "Paracuellos, Intégrale",
            "babelio_suggestion_title": "Paracuellos, Intégrale",
            "original_author": "Carlos Gimenez",
            "babelio_suggestion_author": "Carlos Gimenez",
            "confidence_score": 0.95,  # Haute confidence → enrichissement activé
            "babelio_url": "https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880",
            "babelio_publisher": "Audie-Fluide glacial",
            "error_message": None,
        }

        with (
            patch(
                "back_office_lmelp.app.mongodb_service.get_critical_reviews_by_episode_oid"
            ) as mock_get_reviews,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service.get_books_by_episode_oid"
            ) as mock_cache_get,
            patch(
                "back_office_lmelp.services.babelio_service.BabelioService.verify_book"
            ) as mock_babelio_verify,
            patch(
                "back_office_lmelp.app.collections_management_service.cleanup_uncorrected_summaries_for_episode"
            ) as mock_cleanup,
        ):
            # Setup mocks
            mock_get_reviews.return_value = mock_avis_critiques
            mock_cache_get.return_value = []  # Cache vide - simule "Relancer validation Biblio"
            mock_babelio_verify.return_value = (
                mock_babelio_response  # Mock API Babelio externe
            )
            mock_cleanup.return_value = {"corrected": 0, "skipped": 0}

            # Act: Appeler l'API - le VRAI CODE s'exécute
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert: Vérifier la réponse HTTP
            assert response.status_code == 200
            books = response.json()

            # Assert: Vérifier qu'il y a un livre retourné
            assert len(books) == 1, "Devrait retourner 1 livre extrait du summary"
            book = books[0]

            # ASSERTION CRITIQUE (Issue #85):
            # L'API DOIT retourner les champs Babelio au frontend
            assert "babelio_url" in book, (
                "babelio_url doit être dans la réponse API (actuellement perdu par format_books_for_simplified_display)"
            )

            assert (
                book["babelio_url"]
                == "https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880"
            ), (
                f"babelio_url doit avoir la bonne valeur (pas null). Got: {book.get('babelio_url')}"
            )

            assert "babelio_publisher" in book, (
                "babelio_publisher doit être dans la réponse API (actuellement perdu par format_books_for_simplified_display)"
            )

            assert book["babelio_publisher"] == "Audie-Fluide glacial", (
                f"babelio_publisher doit avoir la bonne valeur (pas null). Got: {book.get('babelio_publisher')}"
            )

            # Vérifier aussi les champs essentiels
            assert book["auteur"] == "Carlos Gimenez"
            assert book["titre"] == "Paracuellos, Intégrale"
            assert book["editeur"] == "Audie-Fluide glacial"

            # Vérifier que le flux a été correctement suivi
            mock_get_reviews.assert_called_once_with(episode_oid)
            mock_cache_get.assert_called_once_with(episode_oid)
            mock_babelio_verify.assert_called_once()  # Vérification Babelio appelée
