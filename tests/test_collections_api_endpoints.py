"""Tests TDD pour les nouveaux endpoints API de gestion des collections (Issue #66)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestCollectionsAPIEndpoints:
    """Tests pour les nouveaux endpoints API de gestion des collections auteurs/livres."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_get_livres_auteurs_statistics_endpoint(self):
        """Test endpoint GET /api/livres-auteurs/statistics (Issue #124: via stats_service)."""
        with patch("back_office_lmelp.app.stats_service") as mock_service:
            mock_service.get_cache_statistics.return_value = {
                "episodes_non_traites": 5,
                "couples_en_base": 42,
                "couples_verified_pas_en_base": 18,
                "couples_suggested_pas_en_base": 12,
                "couples_not_found_pas_en_base": 8,
            }

            response = self.client.get("/api/livres-auteurs/statistics")

            assert response.status_code == 200
            data = response.json()
            assert "episodes_non_traites" in data
            assert "couples_en_base" in data
            assert "couples_verified_pas_en_base" in data
            assert "couples_suggested_pas_en_base" in data
            assert "couples_not_found_pas_en_base" in data
            assert data["episodes_non_traites"] == 5
            assert data["couples_verified_pas_en_base"] == 18

    def test_post_auto_process_verified_books_endpoint(self):
        """Test endpoint POST /api/livres-auteurs/auto-process-verified."""
        with patch(
            "back_office_lmelp.app.collections_management_service"
        ) as mock_service:
            mock_service.auto_process_verified_books.return_value = {
                "processed_count": 15,
                "created_authors": 8,
                "created_books": 15,
                "updated_references": 25,
            }

            response = self.client.post("/api/livres-auteurs/auto-process-verified")

            assert response.status_code == 200
            data = response.json()
            assert "processed_count" in data
            assert "created_authors" in data
            assert "created_books" in data
            assert data["processed_count"] == 15
            assert data["created_authors"] == 8

    def test_get_books_by_validation_status_endpoint(self):
        """Test endpoint GET /api/livres-auteurs/books/{status}."""
        with patch(
            "back_office_lmelp.app.collections_management_service"
        ) as mock_service:
            mock_books = [
                {
                    "_id": "64f1234567890abcdef12345",  # pragma: allowlist secret
                    "auteur": "Test Author",
                    "titre": "Test Book",
                    "status": "suggested",
                    "suggested_author": "Corrected Author",
                    "suggested_title": "Corrected Title",
                }
            ]
            mock_service.get_books_by_validation_status.return_value = mock_books

            response = self.client.get("/api/livres-auteurs/books/suggested")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["status"] == "suggested"
            assert "suggested_author" in data[0]

    def test_post_validate_suggestion_endpoint(self):
        """Test endpoint POST /api/livres-auteurs/validate-suggestion."""
        book_data = {
            "cache_id": "64f1234567890abcdef12345",  # pragma: allowlist secret
            "episode_oid": "68c707ad6e51b9428ab87e9e",  # pragma: allowlist secret
            "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
            "auteur": "Original Author",
            "titre": "Original Title",
            "user_validated_author": "Validated Author",
            "user_validated_title": "Validated Title",
            "editeur": "Test Publisher",
        }

        with patch(
            "back_office_lmelp.app.collections_management_service"
        ) as mock_service:
            mock_service.handle_book_validation.return_value = {
                "success": True,
                "author_id": "64f1234567890abcdef11111",  # pragma: allowlist secret
                "book_id": "64f1234567890abcdef22222",  # pragma: allowlist secret
            }

            response = self.client.post(
                "/api/livres-auteurs/validate-suggestion", json=book_data
            )

            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert data["success"] is True
            assert "author_id" in data
            assert "book_id" in data

    def test_get_all_authors_endpoint(self):
        """Test endpoint GET /api/authors pour récupérer tous les auteurs."""
        with patch(
            "back_office_lmelp.app.collections_management_service"
        ) as mock_service:
            mock_authors = [
                {
                    "id": "64f1234567890abcdef11111",  # pragma: allowlist secret
                    "nom": "Michel Houellebecq",
                    "livres": ["64f1234567890abcdef22222"],  # pragma: allowlist secret
                    "created_at": "2024-01-01T10:00:00",
                    "updated_at": "2024-01-01T10:00:00",
                },
                {
                    "id": "64f1234567890abcdef11112",  # pragma: allowlist secret
                    "nom": "Emmanuel Carrère",
                    "livres": ["64f1234567890abcdef22223"],  # pragma: allowlist secret
                    "created_at": "2024-01-01T11:00:00",
                    "updated_at": "2024-01-01T11:00:00",
                },
            ]
            mock_service.get_all_authors.return_value = mock_authors

            response = self.client.get("/api/authors")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert data[0]["nom"] == "Michel Houellebecq"
            assert data[1]["nom"] == "Emmanuel Carrère"

    def test_get_all_books_endpoint(self):
        """Test endpoint GET /api/books pour récupérer tous les livres."""
        with patch(
            "back_office_lmelp.app.collections_management_service"
        ) as mock_service:
            mock_books = [
                {
                    "id": "64f1234567890abcdef22222",  # pragma: allowlist secret
                    "titre": "Les Particules élémentaires",
                    "auteur_id": "64f1234567890abcdef11111",  # pragma: allowlist secret
                    "editeur": "Flammarion",
                    "episodes": [
                        "64f1234567890abcdef33333"  # pragma: allowlist secret
                    ],  # pragma: allowlist secret
                    "created_at": "2024-01-01T10:00:00",
                    "updated_at": "2024-01-01T10:00:00",
                }
            ]
            mock_service.get_all_books.return_value = mock_books

            response = self.client.get("/api/books")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["titre"] == "Les Particules élémentaires"
            assert data[0]["editeur"] == "Flammarion"

    def test_error_handling_for_statistics_endpoint(self):
        """Test gestion d'erreur pour l'endpoint statistics."""
        with patch(
            "back_office_lmelp.app.collections_management_service"
        ) as mock_service:
            mock_service.get_statistics.side_effect = Exception(
                "Database connection error"
            )

            response = self.client.get("/api/livres-auteurs/statistics")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    def test_validation_error_for_validate_suggestion_endpoint(self):
        """Test validation d'erreur pour l'endpoint validate-suggestion."""
        # Données invalides (champs manquants)
        invalid_data = {
            "id": "64f1234567890abcdef12345",  # pragma: allowlist secret
            # Champs requis manquants
        }

        response = self.client.post(
            "/api/livres-auteurs/validate-suggestion", json=invalid_data
        )

        # Devrait retourner une erreur de validation
        assert response.status_code in [400, 422]  # Bad Request ou Unprocessable Entity
