"""Tests TDD pour la logique de cache par episode_oid."""

from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestCacheByEpisode:
    """Tests TDD pour la logique de cache globale par episode_oid."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_cache_hit_should_return_all_cached_books_for_episode(self):
        """Test TDD: Si cache hit pour episode_oid, retourner TOUS les livres cachés."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        # Livres déjà en cache pour cet épisode
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
                "status": "mongo",
            },
        ]

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
            patch("back_office_lmelp.app.books_extraction_service") as mock_extraction,
        ):
            # Setup mocks
            mock_memory_guard.check_memory_limit.return_value = None

            # CACHE HIT: Des livres existent pour cet episode_oid
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

            # CRITICAL: Cache hit - retourner toutes les données du cache
            assert len(books) == 2
            assert books[0]["auteur"] == "Laurent Mauvignier"
            assert books[0]["status"] == "suggested"
            assert books[1]["auteur"] == "Maria Pourchet"
            assert books[1]["status"] == "mongo"

            # CRITICAL: Vérifier qu'aucune extraction n'a été faite
            mock_extraction.extract_books_from_reviews.assert_not_called()

            # CRITICAL: Vérifier qu'on a bien cherché par episode_oid
            mock_cache_service.get_books_by_episode_oid.assert_called_once_with(
                episode_oid
            )

    def test_cache_miss_should_extract_and_wait_for_frontend_validation(self):
        """Test TDD: Si cache miss pour episode_oid, extraire et attendre validation frontend."""
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
        ):
            # Setup mocks
            mock_memory_guard.check_memory_limit.return_value = None

            # CACHE MISS: Aucun livre en cache pour cet episode_oid
            mock_cache_service.get_books_by_episode_oid.return_value = []

            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                {"_id": avis_critique_id, "episode_oid": episode_oid}
            ]

            # Extraction produit des livres bruts
            extracted_books = [
                {
                    "episode_oid": episode_oid,
                    "auteur": "Laurent Mauvignier",
                    "titre": "La Maison Vide",
                    "editeur": "Éditions de Minuit",
                    "programme": True,
                }
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

            # CRITICAL: Cache miss - faire l'extraction
            assert len(books) == 1
            assert books[0]["auteur"] == "Laurent Mauvignier"

            # CRITICAL: Vérifier que l'extraction a été faite
            mock_extraction.extract_books_from_reviews.assert_called_once()

            # CRITICAL: Vérifier qu'on a bien cherché par episode_oid
            mock_cache_service.get_books_by_episode_oid.assert_called_once_with(
                episode_oid
            )

    def test_cache_service_should_have_get_books_by_episode_oid_method(self):
        """Test TDD: Le service cache doit avoir une méthode get_books_by_episode_oid."""
        # Ce test valide que la méthode sera créée dans le service cache
        # À implémenter quand on créera la méthode
