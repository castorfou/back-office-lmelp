"""Tests TDD pour l'endpoint statistiques cache-optimisé (Issue #66 - Phase 5)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from back_office_lmelp.app import app


client = TestClient(app)


class TestLivresAuteursStatsEndpoint:
    """Tests pour l'endpoint statistiques cache-optimisé /api/livres-auteurs/statistics."""

    def test_stats_endpoint_returns_cache_statistics(self):
        """Test TDD: L'endpoint statistiques utilise le cache optimisé (Issue #124: via stats_service)."""

        # Mock des statistiques optimisées depuis le cache
        mock_stats = {
            "episodes_non_traites": 15,
            "couples_en_base": 42,
            "couples_verified_pas_en_base": 8,
            "couples_suggested_pas_en_base": 12,
            "couples_not_found_pas_en_base": 3,
            "couples_pending": 23,
            "couples_rejected": 1,
        }

        with patch("back_office_lmelp.app.stats_service") as mock_service:
            # Mock: le service retourne les statistiques optimisées
            mock_service.get_cache_statistics.return_value = mock_stats

            # Act
            response = client.get("/api/livres-auteurs/statistics")

            # Assert
            assert response.status_code == 200
            stats = response.json()

            # Vérifier la structure des statistiques
            assert "episodes_non_traites" in stats
            assert "couples_en_base" in stats
            assert "couples_verified_pas_en_base" in stats
            assert "couples_suggested_pas_en_base" in stats
            assert "couples_not_found_pas_en_base" in stats

            # Vérifier les valeurs attendues
            assert stats["episodes_non_traites"] == 15
            assert stats["couples_en_base"] == 42
            assert stats["couples_verified_pas_en_base"] == 8
            assert stats["couples_suggested_pas_en_base"] == 12
            assert stats["couples_not_found_pas_en_base"] == 3

            # Vérifier que le service a bien été appelé
            mock_service.get_cache_statistics.assert_called_once()

    def test_stats_endpoint_handles_service_error(self):
        """Test TDD: L'endpoint gère les erreurs du service gracieusement (Issue #124: via stats_service)."""

        with patch("back_office_lmelp.app.stats_service") as mock_service:
            # Mock: le service lève une exception
            mock_service.get_cache_statistics.side_effect = Exception(
                "Database connection failed"
            )

            # Act
            response = client.get("/api/livres-auteurs/statistics")

            # Assert
            assert response.status_code == 500
            error = response.json()
            assert "detail" in error
            assert "Database connection failed" in error["detail"]

    def test_stats_endpoint_returns_zero_values_for_empty_cache(self):
        """Test TDD: L'endpoint gère correctement un cache vide (Issue #124: via stats_service)."""

        # Mock des statistiques vides (première utilisation)
        empty_stats = {
            "episodes_non_traites": 0,
            "couples_en_base": 0,
            "couples_verified_pas_en_base": 0,
            "couples_suggested_pas_en_base": 0,
            "couples_not_found_pas_en_base": 0,
            "couples_pending": 0,
            "couples_rejected": 0,
        }

        with patch("back_office_lmelp.app.stats_service") as mock_service:
            mock_service.get_cache_statistics.return_value = empty_stats

            # Act
            response = client.get("/api/livres-auteurs/statistics")

            # Assert
            assert response.status_code == 200
            stats = response.json()

            # Tous les compteurs doivent être à 0
            for _key, value in stats.items():
                assert isinstance(value, int)
                assert value >= 0

    def test_stats_endpoint_performance_cache_first(self):
        """Test TDD: L'endpoint utilise la méthode cache-first optimisée (Issue #124: via stats_service)."""

        mock_stats = {
            "episodes_non_traites": 5,
            "couples_en_base": 120,
            "couples_verified_pas_en_base": 0,
            "couples_suggested_pas_en_base": 0,
            "couples_not_found_pas_en_base": 0,
        }

        with patch("back_office_lmelp.app.stats_service") as mock_service:
            mock_service.get_cache_statistics.return_value = mock_stats

            # Act
            response = client.get("/api/livres-auteurs/statistics")

            # Assert
            assert response.status_code == 200

            # Vérifier qu'on utilise bien get_cache_statistics (cache-first)
            # et pas une autre méthode moins optimisée
            mock_service.get_cache_statistics.assert_called_once_with()

            # S'assurer qu'on utilise bien la méthode optimisée get_cache_statistics
            # (pas les anciennes méthodes séparées qui ont été supprimées)
            mock_service.get_cache_statistics.assert_called_once_with()
