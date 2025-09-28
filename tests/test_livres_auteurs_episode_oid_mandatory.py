"""Tests TDD pour rendre episode_oid obligatoire dans l'endpoint livres-auteurs."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestLivresAuteursEpisodeOidMandatory:
    """Tests TDD pour s'assurer qu'episode_oid est obligatoire."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_get_livres_auteurs_should_reject_requests_without_episode_oid(self):
        """Test TDD: GET /api/livres-auteurs DOIT rejeter les requêtes sans episode_oid."""
        with patch("back_office_lmelp.app.memory_guard") as mock_memory_guard:
            mock_memory_guard.check_memory_limit.return_value = None

            # Act - Appeler l'endpoint sans episode_oid
            response = self.client.get("/api/livres-auteurs")

            # Assert - Doit retourner une erreur 422 (validation error)
            assert response.status_code == 422
            error_detail = response.json()
            assert "episode_oid" in str(error_detail).lower()
            assert "required" in str(error_detail).lower()

    def test_get_livres_auteurs_should_reject_requests_with_empty_episode_oid(self):
        """Test TDD: GET /api/livres-auteurs DOIT rejeter les requêtes avec episode_oid vide."""
        with patch("back_office_lmelp.app.memory_guard") as mock_memory_guard:
            mock_memory_guard.check_memory_limit.return_value = None

            # Act - Appeler l'endpoint avec episode_oid vide
            response = self.client.get("/api/livres-auteurs?episode_oid=")

            # Assert - Doit retourner une erreur 422 (validation error)
            assert response.status_code == 422
            error_detail = response.json()
            assert "episode_oid" in str(error_detail).lower()

    def test_get_livres_auteurs_should_accept_requests_with_valid_episode_oid(self):
        """Test TDD: GET /api/livres-auteurs DOIT accepter les requêtes avec episode_oid valide."""
        episode_oid = "678cce7aa414f229887780d3"  # pragma: allowlist secret

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb_service,
            patch("back_office_lmelp.app.books_extraction_service"),
            patch("back_office_lmelp.app.babelio_service"),
            patch("back_office_lmelp.app.livres_auteurs_cache_service"),
        ):
            # Setup mocks
            mock_memory_guard.check_memory_limit.return_value = None
            mock_mongodb_service.get_critical_reviews_by_episode_oid.return_value = []

            # Act - Appeler l'endpoint avec episode_oid valide
            response = self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert - Doit réussir
            assert response.status_code == 200
            assert isinstance(response.json(), list)

            # Vérifier que la fonction est appelée avec le bon episode_oid
            mock_mongodb_service.get_critical_reviews_by_episode_oid.assert_called_once_with(
                episode_oid
            )

    def test_get_livres_auteurs_should_never_call_get_all_critical_reviews(self):
        """Test TDD: GET /api/livres-auteurs NE DOIT JAMAIS appeler get_all_critical_reviews."""
        episode_oid = "678cce7aa414f229887780d3"  # pragma: allowlist secret

        with (
            patch("back_office_lmelp.app.memory_guard") as mock_memory_guard,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb_service,
            patch("back_office_lmelp.app.books_extraction_service"),
            patch("back_office_lmelp.app.babelio_service"),
            patch("back_office_lmelp.app.livres_auteurs_cache_service"),
        ):
            # Setup mocks
            mock_memory_guard.check_memory_limit.return_value = None
            mock_mongodb_service.get_critical_reviews_by_episode_oid.return_value = []

            # Act - Appeler l'endpoint avec episode_oid valide
            self.client.get(f"/api/livres-auteurs?episode_oid={episode_oid}")

            # Assert - get_all_critical_reviews ne doit jamais être appelée
            mock_mongodb_service.get_all_critical_reviews.assert_not_called()

            # Vérifier que seule la méthode spécifique à l'épisode est appelée
            mock_mongodb_service.get_critical_reviews_by_episode_oid.assert_called_once_with(
                episode_oid
            )

    def test_get_livres_auteurs_should_validate_episode_oid_format(self):
        """Test TDD: GET /api/livres-auteurs DOIT valider le format d'episode_oid."""
        invalid_episode_oid = "invalid-format"

        with patch("back_office_lmelp.app.memory_guard") as mock_memory_guard:
            mock_memory_guard.check_memory_limit.return_value = None

            # Act - Appeler l'endpoint avec episode_oid au format invalide
            response = self.client.get(
                f"/api/livres-auteurs?episode_oid={invalid_episode_oid}"
            )

            # Assert - Doit retourner une erreur 422 pour format invalide
            assert response.status_code == 422
            error_detail = response.json()
            assert "episode_oid" in str(error_detail).lower()
