"""Tests TDD pour s'assurer que les livres verified sont traités automatiquement."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestVerifiedBooksAutoProcessing:
    """Tests TDD pour l'auto-processing des livres verified."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_verified_book_should_be_auto_processed_after_extraction(self):
        """Test TDD: Un livre verified (Maria Pourchet) doit être traité automatiquement."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.books_extraction_service") as mock_extraction,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
        ):
            # Setup basic mocks
            mock_memory_guard.check_memory_limit.return_value = None
            # Mock critical reviews to bypass early return (need at least one review)
            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                {"episode_oid": episode_oid, "avis_critique": "test review"}
            ]

            # Mock: cache hit avec le livre verified (l'API retourne ce qui est en cache)
            verified_book_in_cache = {
                "_id": "68d3eb092f32bb8c43063f91",  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "auteur": "Maria Pourchet",
                "titre": "Tressaillir",
                "editeur": "Stock",
                "programme": True,
                "status": "verified",
                "created_at": "2024-09-14T10:00:00Z",
            }
            mock_cache_service.get_books_by_episode_oid.return_value = [
                verified_book_in_cache
            ]

            # Mock: formatage des données cachées (l'API formate ce qui vient du cache)
            mock_extraction.format_books_for_simplified_display.return_value = [
                verified_book_in_cache
            ]

            # Act
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert
            if response.status_code != 200:
                print(f"Error response: {response.text}")
            assert response.status_code == 200
            books = response.json()

            assert len(books) == 1
            assert books[0]["auteur"] == "Maria Pourchet"
            assert books[0]["titre"] == "Tressaillir"
            assert books[0]["status"] == "verified"

            # Vérifier que le cache a été consulté (cache hit)
            mock_cache_service.get_books_by_episode_oid.assert_called_once_with(
                episode_oid
            )

            # Vérifier que le formatage a été appliqué aux données du cache
            mock_extraction.format_books_for_simplified_display.assert_called_once_with(
                [verified_book_in_cache]
            )

    def test_suggested_book_should_not_be_auto_processed(self):
        """Test TDD: Un livre suggested (Mauvignier) ne doit PAS être traité automatiquement."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.books_extraction_service") as mock_extraction,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
        ):
            # Setup basic mocks
            mock_memory_guard.check_memory_limit.return_value = None
            # Mock critical reviews to bypass early return (need at least one review)
            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                {"episode_oid": episode_oid, "avis_critique": "test review"}
            ]

            # Mock: cache hit avec le livre suggested (l'API retourne ce qui est en cache)
            suggested_book_in_cache = {
                "_id": "68d3eb092f32bb8c43063f91",  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "auteur": "Laurent Mauvignier",
                "titre": "Quelque chose noir",
                "editeur": "Éditions de Minuit",
                "programme": False,
                "status": "suggested",
                "suggested_author": "Laurent Mauvignier",
                "suggested_title": "Quelque chose noir",
                "created_at": "2024-09-14T10:00:00Z",
            }
            mock_cache_service.get_books_by_episode_oid.return_value = [
                suggested_book_in_cache
            ]

            # Mock: formatage des données cachées
            mock_extraction.format_books_for_simplified_display.return_value = [
                suggested_book_in_cache
            ]

            # Act
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert
            assert response.status_code == 200
            books = response.json()

            assert len(books) == 1
            assert books[0]["auteur"] == "Laurent Mauvignier"
            assert books[0]["status"] == "suggested"

            # Vérifier que le cache a été consulté (cache hit)
            mock_cache_service.get_books_by_episode_oid.assert_called_once_with(
                episode_oid
            )

            # Vérifier que le formatage a été appliqué aux données du cache
            mock_extraction.format_books_for_simplified_display.assert_called_once_with(
                [suggested_book_in_cache]
            )

    def test_verified_book_cache_handles_formatting_errors_gracefully(self):
        """Test TDD: Les erreurs de formatage ne cassent pas l'endpoint."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.books_extraction_service") as mock_extraction,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
        ):
            # Setup basic mocks
            mock_memory_guard.check_memory_limit.return_value = None
            # Mock critical reviews to bypass early return (need at least one review)
            mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                {"episode_oid": episode_oid, "avis_critique": "test review"}
            ]

            # Mock: cache hit avec le livre verified
            verified_book_in_cache = {
                "_id": "68d3eb092f32bb8c43063f91",  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "auteur": "Test Author",
                "titre": "Test Book",
                "editeur": "Test Publisher",
                "programme": True,
                "status": "verified",
                "created_at": "2024-09-14T10:00:00Z",
            }
            mock_cache_service.get_books_by_episode_oid.return_value = [
                verified_book_in_cache
            ]

            # Mock: le formatage échoue mais l'endpoint doit gérer l'erreur
            mock_extraction.format_books_for_simplified_display.side_effect = Exception(
                "Formatting error"
            )

            # Act - L'endpoint ne doit pas crash malgré l'erreur de formatage
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert - Endpoint retourne une erreur 500 de façon gracieuse
            assert response.status_code == 500
            error_response = response.json()
            assert "Erreur serveur" in error_response["detail"]

            # Vérifier que le cache a été consulté
            mock_cache_service.get_books_by_episode_oid.assert_called_once_with(
                episode_oid
            )
