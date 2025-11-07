"""Tests TDD pour l'enrichissement automatique du cache avec babelio_url et babelio_publisher lors de l'extraction."""

from unittest.mock import AsyncMock, patch

import pytest

from back_office_lmelp.services.books_extraction_service import (
    BooksExtractionService,
)


class TestBabelioCacheEnrichment:
    """Tests TDD pour l'enrichissement automatique Babelio lors de l'extraction."""

    @pytest.mark.asyncio
    async def test_should_enrich_extracted_book_with_babelio_url_when_confidence_high(
        self,
    ):
        """
        Test TDD RED: Quand un livre est extrait et Babelio retourne confidence >= 0.90,
        le livre doit être enrichi avec babelio_url et babelio_publisher.
        """
        # ARRANGE
        service = BooksExtractionService()

        # Mock du summary avec un livre
        avis_critique = {
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Albert Camus | L'Étranger | Gallimard |
""",
            "episode_oid": "test_episode_123",
            "episode_title": "Test Episode",
            "episode_date": "2024-01-15",
        }

        # Mock du BabelioService.verify_book()
        # Structure basée sur VRAIE réponse API:
        # curl -X POST "http://0.0.0.0:54321/api/verify-babelio" \
        #   -d '{"type": "book", "title": "Paracuellos, Intégrale", "author": "Carlos Gimenez"}'
        # Capturé: 2025-01-18
        mock_babelio_response = {
            "status": "verified",
            "original_title": "L'Étranger",
            "babelio_suggestion_title": "L'Étranger",
            "original_author": "Albert Camus",
            "babelio_suggestion_author": "Albert Camus",
            "confidence_score": 0.95,  # ✅ Clé réelle de l'API (pas "confidence")
            "babelio_url": "https://www.babelio.com/livres/Camus-LEtranger/1234",
            "babelio_publisher": "Gallimard",
            "error_message": None,
        }

        with patch(
            "back_office_lmelp.services.books_extraction_service.babelio_service"
        ) as mock_babelio_service:
            mock_babelio_service.verify_book = AsyncMock(
                return_value=mock_babelio_response
            )

            # ACT
            books = await service.extract_books_from_reviews([avis_critique])

            # ASSERT
            assert len(books) == 1
            book = books[0]

            # Vérifier que verify_book a été appelé
            mock_babelio_service.verify_book.assert_called_once_with(
                "L'Étranger", "Albert Camus"
            )

            # Vérifier que babelio_url et babelio_publisher sont enrichis
            assert "babelio_url" in book
            assert (
                book["babelio_url"]
                == "https://www.babelio.com/livres/Camus-LEtranger/1234"
            )
            assert "babelio_publisher" in book
            assert book["babelio_publisher"] == "Gallimard"

    @pytest.mark.asyncio
    async def test_should_not_enrich_when_babelio_confidence_low(self):
        """
        Test TDD: Quand Babelio retourne confidence < 0.90,
        le livre NE doit PAS être enrichi avec babelio_url/babelio_publisher.
        """
        # ARRANGE
        service = BooksExtractionService()

        avis_critique = {
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Jean Dupont | Livre Rare | Petit Éditeur |
""",
            "episode_oid": "test_episode_456",
            "episode_title": "Test Episode 2",
            "episode_date": "2024-01-16",
        }

        # Mock du BabelioService retournant faible confiance
        # Structure basée sur VRAIE réponse API (cas not_found):
        # curl -X POST "http://0.0.0.0:54321/api/verify-babelio" \
        #   -d '{"type": "book", "title": "Livre totalement inexistant xyz", "author": "Auteur inconnu"}'
        # Capturé: 2025-01-18
        mock_babelio_response = {
            "status": "not_found",
            "original_title": "Livre Rare",
            "babelio_suggestion_title": None,
            "original_author": "Jean Dupont",
            "babelio_suggestion_author": None,
            "confidence_score": 0.30,  # ✅ Clé réelle de l'API (confiance trop faible)
            "babelio_data": None,
            "babelio_url": None,
            "babelio_publisher": None,
            "error_message": None,
        }

        with patch(
            "back_office_lmelp.services.books_extraction_service.babelio_service"
        ) as mock_babelio_service:
            mock_babelio_service.verify_book = AsyncMock(
                return_value=mock_babelio_response
            )

            # ACT
            books = await service.extract_books_from_reviews([avis_critique])

            # ASSERT
            assert len(books) == 1
            book = books[0]

            # Vérifier que verify_book a été appelé
            mock_babelio_service.verify_book.assert_called_once()

            # Vérifier que babelio_url et babelio_publisher NE SONT PAS enrichis
            assert "babelio_url" not in book or book.get("babelio_url") is None
            assert (
                "babelio_publisher" not in book or book.get("babelio_publisher") is None
            )

    @pytest.mark.asyncio
    async def test_should_enrich_multiple_books_independently(self):
        """
        Test TDD: Quand plusieurs livres sont extraits, chacun doit être enrichi
        indépendamment selon sa propre vérification Babelio.
        """
        # ARRANGE
        service = BooksExtractionService()

        avis_critique = {
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Albert Camus | L'Étranger | Gallimard |
| Victor Hugo | Les Misérables | Le Livre de Poche |
| Jean Martin | Titre Rare | Petit Éditeur |
""",
            "episode_oid": "test_episode_789",
            "episode_title": "Test Episode 3",
            "episode_date": "2024-01-17",
        }

        # Mock du BabelioService avec différentes réponses
        # Structure basée sur VRAIES réponses API capturées: 2025-01-18
        def mock_verify_book_side_effect(title, author):
            if author == "Albert Camus":
                return {
                    "status": "verified",
                    "original_title": "L'Étranger",
                    "babelio_suggestion_title": "L'Étranger",
                    "original_author": "Albert Camus",
                    "babelio_suggestion_author": "Albert Camus",
                    "confidence_score": 0.95,  # ✅ Clé réelle
                    "babelio_url": "https://www.babelio.com/livres/Camus-LEtranger/1234",
                    "babelio_publisher": "Gallimard",
                    "error_message": None,
                }
            elif author == "Victor Hugo":
                return {
                    "status": "verified",
                    "original_title": "Les Misérables",
                    "babelio_suggestion_title": "Les Misérables",
                    "original_author": "Victor Hugo",
                    "babelio_suggestion_author": "Victor Hugo",
                    "confidence_score": 0.92,  # ✅ Clé réelle
                    "babelio_url": "https://www.babelio.com/livres/Hugo-Les-Miserables/5678",
                    "babelio_publisher": "Gallimard",
                    "error_message": None,
                }
            else:  # Jean Martin
                return {
                    "status": "not_found",
                    "original_title": "Titre Rare",
                    "babelio_suggestion_title": None,
                    "original_author": "Jean Martin",
                    "babelio_suggestion_author": None,
                    "confidence_score": 0.40,  # ✅ Clé réelle (confiance trop faible)
                    "babelio_data": None,
                    "babelio_url": None,
                    "babelio_publisher": None,
                    "error_message": None,
                }

        with patch(
            "back_office_lmelp.services.books_extraction_service.babelio_service"
        ) as mock_babelio_service:
            mock_babelio_service.verify_book = AsyncMock(
                side_effect=mock_verify_book_side_effect
            )

            # ACT
            books = await service.extract_books_from_reviews([avis_critique])

            # ASSERT
            assert len(books) == 3

            # Livre 1: Albert Camus - doit être enrichi
            camus_book = next(b for b in books if b["auteur"] == "Albert Camus")
            assert (
                camus_book["babelio_url"]
                == "https://www.babelio.com/livres/Camus-LEtranger/1234"
            )
            assert camus_book["babelio_publisher"] == "Gallimard"

            # Livre 2: Victor Hugo - doit être enrichi
            hugo_book = next(b for b in books if b["auteur"] == "Victor Hugo")
            assert (
                hugo_book["babelio_url"]
                == "https://www.babelio.com/livres/Hugo-Les-Miserables/5678"
            )
            assert hugo_book["babelio_publisher"] == "Gallimard"

            # Livre 3: Jean Martin - NE doit PAS être enrichi
            unknown_book = next(b for b in books if b["auteur"] == "Jean Martin")
            assert unknown_book.get("babelio_url") is None
            assert unknown_book.get("babelio_publisher") is None

            # Vérifier que verify_book a été appelé 3 fois
            assert mock_babelio_service.verify_book.call_count == 3

    @pytest.mark.asyncio
    async def test_should_handle_babelio_service_errors_gracefully(self):
        """
        Test TDD: Quand BabelioService échoue (erreur réseau, timeout, etc.),
        l'extraction doit continuer sans enrichissement Babelio.
        """
        # ARRANGE
        service = BooksExtractionService()

        avis_critique = {
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Test Auteur | Test Livre | Test Éditeur |
""",
            "episode_oid": "test_episode_error",
            "episode_title": "Test Episode Error",
            "episode_date": "2024-01-18",
        }

        # Mock du BabelioService qui échoue
        with patch(
            "back_office_lmelp.services.books_extraction_service.babelio_service"
        ) as mock_babelio_service:
            mock_babelio_service.verify_book = AsyncMock(
                side_effect=Exception("Babelio timeout")
            )

            # ACT
            books = await service.extract_books_from_reviews([avis_critique])

            # ASSERT
            assert len(books) == 1
            book = books[0]

            # Vérifier que l'extraction a réussi malgré l'erreur Babelio
            assert book["auteur"] == "Test Auteur"
            assert book["titre"] == "Test Livre"

            # Vérifier que babelio_url et babelio_publisher ne sont pas enrichis
            assert "babelio_url" not in book or book.get("babelio_url") is None
            assert (
                "babelio_publisher" not in book or book.get("babelio_publisher") is None
            )

    @pytest.mark.asyncio
    async def test_should_enrich_coups_de_coeur_books_as_well(self):
        """
        Test TDD: Les livres extraits depuis "COUPS DE CŒUR" doivent aussi
        être enrichis avec Babelio.
        """
        # ARRANGE
        service = BooksExtractionService()

        avis_critique = {
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur |
|--------|-------|---------|

## 2. COUPS DE CŒUR DES CRITIQUES

| Auteur | Titre | Éditeur | Critique |
|--------|-------|---------|----------|
| Marguerite Duras | L'Amant | Minuit | Jérôme Garcin |
""",
            "episode_oid": "test_episode_cdc",
            "episode_title": "Test Episode CDC",
            "episode_date": "2024-01-19",
        }

        # Mock du BabelioService
        # Structure basée sur VRAIE réponse API capturée: 2025-01-18
        mock_babelio_response = {
            "status": "verified",
            "original_title": "L'Amant",
            "babelio_suggestion_title": "L'Amant",
            "original_author": "Marguerite Duras",
            "babelio_suggestion_author": "Marguerite Duras",
            "confidence_score": 0.98,  # ✅ Clé réelle de l'API
            "babelio_url": "https://www.babelio.com/livres/Duras-LAmant/9999",
            "babelio_publisher": "Éditions de Minuit",
            "error_message": None,
        }

        with patch(
            "back_office_lmelp.services.books_extraction_service.babelio_service"
        ) as mock_babelio_service:
            mock_babelio_service.verify_book = AsyncMock(
                return_value=mock_babelio_response
            )

            # ACT
            books = await service.extract_books_from_reviews([avis_critique])

            # ASSERT
            assert len(books) == 1
            book = books[0]

            # Vérifier que c'est bien un coup de cœur
            assert book["coup_de_coeur"] is True

            # Vérifier que Babelio a enrichi le livre
            assert (
                book["babelio_url"]
                == "https://www.babelio.com/livres/Duras-LAmant/9999"
            )
            assert book["babelio_publisher"] == "Éditions de Minuit"
