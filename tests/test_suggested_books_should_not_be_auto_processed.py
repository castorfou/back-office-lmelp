"""Tests TDD pour s'assurer que les livres suggested ne sont PAS auto-traités."""

from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestSuggestedBooksNotAutoProcessed:
    """Tests TDD pour garantir que les livres suggested restent suggested."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_suggested_book_should_stay_suggested_not_become_mongo(self):
        """Test TDD: Dans le système simplifié actuel, GET n'auto-traite pas les livres."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        # Mock d'un livre extrait (système simplifié - pas de validation automatique)
        extracted_book = {
            "episode_oid": episode_oid,
            "auteur": "Laurent Mauvignier",
            "titre": "La Maison Vide",
            "editeur": "Éditions de Minuit",
            "programme": True,
        }

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch("back_office_lmelp.app.books_extraction_service") as mock_extraction,
            patch("back_office_lmelp.app.babelio_service") as mock_babelio,
        ):
            # Setup mocks pour système simplifié
            mock_memory_guard.check_memory_limit.return_value = None
            mock_cache_service.get_books_by_episode_oid.return_value = []  # Cache miss
            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                {"_id": avis_critique_id, "episode_oid": episode_oid, "summary": "test"}
            ]

            # Mock: extraction simple sans validation
            mock_extraction.extract_books_from_reviews = AsyncMock(
                return_value=[extracted_book]
            )
            mock_extraction.format_books_for_simplified_display.return_value = [
                extracted_book
            ]

            # Act
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert
            assert response.status_code == 200
            books = response.json()

            assert len(books) == 1
            assert books[0]["auteur"] == "Laurent Mauvignier"

            # CRITICAL: Système simplifié - AUCUNE validation/cache/auto-processing pendant GET
            mock_babelio.verify_author.assert_not_called()
            mock_babelio.verify_book.assert_not_called()
            mock_cache_service.create_cache_entry.assert_not_called()
            mock_mongodb.create_author_if_not_exists.assert_not_called()
            mock_mongodb.create_book_if_not_exists.assert_not_called()
            mock_cache_service.mark_as_processed.assert_not_called()

            print(
                "✅ Système simplifié: GET /api/livres-auteurs ne fait que l'extraction, pas de validation automatique"
            )

    def test_verified_book_should_not_be_auto_processed_during_get(self):
        """Test TDD: Dans le système actuel, GET n'auto-traite PAS les livres verified."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        extracted_book = {
            "episode_oid": episode_oid,
            "auteur": "Maria Pourchet",
            "titre": "Tressaillir",
            "editeur": "Stock",
            "programme": True,
        }

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch("back_office_lmelp.app.books_extraction_service") as mock_extraction,
            patch("back_office_lmelp.app.babelio_service") as mock_babelio,
        ):
            # Setup mocks pour système simplifié
            mock_memory_guard.check_memory_limit.return_value = None
            mock_cache_service.get_books_by_episode_oid.return_value = []  # Cache miss
            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                {"_id": avis_critique_id, "episode_oid": episode_oid}
            ]

            # Mock: extraction simple sans validation automatique
            mock_extraction.extract_books_from_reviews = AsyncMock(
                return_value=[extracted_book]
            )
            mock_extraction.format_books_for_simplified_display.return_value = [
                extracted_book
            ]

            # Act
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert
            assert response.status_code == 200
            books = response.json()

            assert len(books) == 1
            assert books[0]["auteur"] == "Maria Pourchet"

            # CRITICAL: Système simplifié - AUCUNE validation/cache/auto-processing pendant GET
            mock_babelio.verify_author.assert_not_called()
            mock_babelio.verify_book.assert_not_called()
            mock_cache_service.create_cache_entry.assert_not_called()
            mock_mongodb.create_author_if_not_exists.assert_not_called()
            mock_mongodb.create_book_if_not_exists.assert_not_called()
            mock_cache_service.mark_as_processed.assert_not_called()

            print(
                "✅ Système simplifié: Même les livres 'verified' ne sont PAS auto-traités pendant GET"
            )

    def test_current_laurent_mauvignier_problem_should_not_happen(self):
        """Test TDD: Dans le système simplifié, le problème Laurent Mauvignier ne peut plus arriver."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        # Simulation exacte du cas Laurent Mauvignier
        extracted_book = {
            "episode_oid": episode_oid,
            "auteur": "Laurent Mauvignier",
            "titre": "La Maison Vide",
            "editeur": "Éditions de Minuit",
            "programme": True,
        }

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch("back_office_lmelp.app.books_extraction_service") as mock_extraction,
            patch("back_office_lmelp.app.babelio_service") as mock_babelio,
        ):
            mock_memory_guard.check_memory_limit.return_value = None
            mock_cache_service.get_books_by_episode_oid.return_value = []  # Cache miss
            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                {"_id": avis_critique_id, "episode_oid": episode_oid}
            ]

            mock_extraction.extract_books_from_reviews = AsyncMock(
                return_value=[extracted_book]
            )
            mock_extraction.format_books_for_simplified_display.return_value = [
                extracted_book
            ]

            # Act
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert
            assert response.status_code == 200
            books = response.json()

            assert len(books) == 1
            assert books[0]["auteur"] == "Laurent Mauvignier"

            # CRITICAL: Dans le système simplifié, AUCUN traitement automatique
            # Le problème Laurent Mauvignier (suggested->mongo automatique) ne peut plus arriver
            mock_babelio.verify_author.assert_not_called()
            mock_babelio.verify_book.assert_not_called()
            mock_cache_service.create_cache_entry.assert_not_called()
            mock_mongodb.create_author_if_not_exists.assert_not_called()
            mock_mongodb.create_book_if_not_exists.assert_not_called()
            mock_cache_service.mark_as_processed.assert_not_called()

            print(
                "✅ Problème Laurent Mauvignier résolu: système simplifié ne fait plus d'auto-processing pendant GET"
            )
