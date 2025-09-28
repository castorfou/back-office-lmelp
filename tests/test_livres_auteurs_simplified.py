"""Tests TDD pour /api/livres-auteurs simplifié (sans appels babelio_service)."""

from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestLivresAuteursSimplified:
    """Tests TDD pour l'endpoint /api/livres-auteurs sans vérifications Babelio."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_livres_auteurs_should_only_extract_without_babelio_calls(self):
        """Test TDD: L'endpoint doit extraire les livres SANS faire d'appels Babelio."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch("back_office_lmelp.app.books_extraction_service") as mock_extraction,
            patch("back_office_lmelp.app.babelio_service") as mock_babelio,
        ):
            # Setup mocks
            mock_memory_guard.check_memory_limit.return_value = None
            mock_cache_service.get_books_by_episode_oid.return_value = []
            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                {"_id": avis_critique_id, "episode_oid": episode_oid, "summary": "test"}
            ]

            # Mock: extraction retourne des livres bruts (sans statuts de validation)
            extracted_books = [
                {
                    "episode_oid": episode_oid,
                    "auteur": "Laurent Mauvignier",
                    "titre": "La Maison Vide",
                    "editeur": "Éditions de Minuit",
                    "programme": True,
                },
                {
                    "episode_oid": episode_oid,
                    "auteur": "Maria Pourchet",
                    "titre": "Tressaillir",
                    "editeur": "Stock",
                    "programme": True,
                },
            ]

            mock_extraction.extract_books_from_reviews = AsyncMock(
                return_value=extracted_books
            )
            # Les livres extraits n'ont PAS de statut de validation
            mock_extraction.format_books_for_simplified_display.return_value = (
                extracted_books
            )

            # Act
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert
            assert response.status_code == 200
            books = response.json()

            assert len(books) == 2
            assert books[0]["auteur"] == "Laurent Mauvignier"
            assert books[1]["auteur"] == "Maria Pourchet"

            # CRITICAL: Vérifier qu'AUCUN appel Babelio n'a été fait
            mock_babelio.verify_author.assert_not_called()
            mock_babelio.verify_book.assert_not_called()

            # CRITICAL: Vérifier qu'AUCUN cache n'a été créé (pas de validation)
            mock_cache_service.create_cache_entry.assert_not_called()

            # CRITICAL: Vérifier qu'AUCUN auto-processing n'a été fait
            mock_mongodb.create_author_if_not_exists.assert_not_called()
            mock_mongodb.create_book_if_not_exists.assert_not_called()

    def test_livres_auteurs_should_return_cached_books_when_available(self):
        """Test TDD: L'endpoint doit retourner les livres du cache quand disponibles."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        # Livres déjà validés en cache
        cached_books = [
            {
                "auteur": "Laurent Mauvignier",
                "titre": "La Maison Vide",
                "editeur": "Éditions de Minuit",
                "programme": True,
                "status": "suggested",
                "suggested_author": "Laurent Mauvignier",
                "suggested_title": "La Maison vide",
            },
            {
                "auteur": "Maria Pourchet",
                "titre": "Tressaillir",
                "editeur": "Stock",
                "programme": True,
                "status": "mongo",  # Auto-processé
            },
        ]

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch("back_office_lmelp.app.books_extraction_service") as mock_extraction,
            patch("back_office_lmelp.app.babelio_service") as mock_babelio,
        ):
            # Setup mocks
            mock_memory_guard.check_memory_limit.return_value = None
            mock_cache_service.get_books_by_episode_oid.return_value = cached_books
            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                {"_id": avis_critique_id, "episode_oid": episode_oid}
            ]

            mock_extraction.format_books_for_simplified_display.return_value = (
                cached_books
            )

            # Act
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert
            assert response.status_code == 200
            books = response.json()

            assert len(books) == 2
            assert books[0]["auteur"] == "Laurent Mauvignier"
            assert books[0]["status"] == "suggested"  # Status du cache
            assert books[1]["auteur"] == "Maria Pourchet"
            assert books[1]["status"] == "mongo"  # Status du cache

            # CRITICAL: Cache hit - aucune extraction ni validation
            mock_extraction.extract_books_from_reviews.assert_not_called()
            mock_babelio.verify_author.assert_not_called()
            mock_babelio.verify_book.assert_not_called()

    def test_livres_auteurs_should_handle_cache_miss_with_extraction(self):
        """Test TDD: L'endpoint doit gérer cache miss global avec extraction complète."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id1 = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret
        avis_critique_id2 = ObjectId(
            "68c718a16e51b9428ab88067"  # pragma: allowlist secret
        )  # pragma: allowlist secret

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

            # Cache miss global pour cet episode
            mock_cache_service.get_books_by_episode_oid.return_value = []

            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                {
                    "_id": avis_critique_id1,
                    "episode_oid": episode_oid,
                    "summary": "test1",
                },
                {
                    "_id": avis_critique_id2,
                    "episode_oid": episode_oid,
                    "summary": "test2",
                },
            ]

            # Cache miss global -> extraction complète de tous les avis critiques
            extracted_books = [
                {"auteur": "Author 1", "titre": "Title 1", "episode_oid": episode_oid},
                {"auteur": "Author 2", "titre": "Title 2", "episode_oid": episode_oid},
            ]
            mock_extraction.extract_books_from_reviews = AsyncMock(
                return_value=extracted_books
            )
            mock_extraction.format_books_for_simplified_display.return_value = (
                extracted_books
            )

            # Act
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert
            assert response.status_code == 200
            books = response.json()
            assert len(books) == 2

            # CRITICAL: Cache miss global -> extraction appelée une fois pour tous les avis
            mock_extraction.extract_books_from_reviews.assert_called_once()

            # CRITICAL: AUCUNE validation Babelio (comportement simplifié)
            mock_babelio.verify_author.assert_not_called()
            mock_babelio.verify_book.assert_not_called()
