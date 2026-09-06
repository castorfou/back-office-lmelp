"""Tests TDD pour l'endpoint de statistiques REST."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from back_office_lmelp.app import app


client = TestClient(app)


class TestStatsEndpoint:
    """Tests TDD pour l'endpoint REST de statistiques."""

    def test_stats_endpoint_should_exist_and_return_json(self):
        """Test TDD: L'endpoint /api/stats doit exister et retourner du JSON."""
        mock_stats = {
            "couples_en_base": 0,
            "couples_pending": 0,
            "couples_rejected": 0,
            "couples_verified_pas_en_base": 0,
            "couples_suggested_pas_en_base": 0,
            "couples_not_found_pas_en_base": 0,
            "episodes_non_traites": 0,
        }

        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_cache_statistics.return_value = mock_stats

            # Act
            response = client.get("/api/stats")

            # Assert
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

    def test_stats_endpoint_should_return_cache_statistics(self):
        """Test TDD: L'endpoint doit retourner les statistiques du cache."""
        mock_stats = {
            "couples_en_base": 5,
            "couples_pending": 10,
            "couples_rejected": 2,
            "couples_verified_pas_en_base": 3,
            "couples_suggested_pas_en_base": 4,
            "couples_not_found_pas_en_base": 3,
            "episodes_non_traites": 15,
        }

        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_cache_statistics.return_value = mock_stats

            # Act
            response = client.get("/api/stats")

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data == mock_stats
            mock_stats_service.get_cache_statistics.assert_called_once()

    def test_stats_detailed_endpoint_should_return_breakdown(self):
        """Test TDD: L'endpoint /api/stats/detailed doit retourner la répartition détaillée."""
        mock_breakdown = [
            {
                "_id": "verified",
                "count": 3,
                "books": [
                    {"auteur": "Albert Camus", "titre": "L'Étranger"},
                    {"auteur": "Victor Hugo", "titre": "Les Misérables"},
                ],
            },
            {
                "_id": "suggested",
                "count": 4,
                "books": [{"auteur": "Marguerite Duras", "titre": "L'Amant"}],
            },
        ]

        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_detailed_breakdown.return_value = mock_breakdown

            # Act
            response = client.get("/api/stats/detailed")

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data == mock_breakdown
            mock_stats_service.get_detailed_breakdown.assert_called_once()

    def test_stats_recent_endpoint_should_return_recent_books(self):
        """Test TDD: L'endpoint /api/stats/recent doit retourner les livres récents."""
        mock_recent = [
            {
                "_id": "68d440010000000000000001",
                "auteur": "Recent Author",
                "titre": "Recent Book",
                "validation_status": "mongo",
                "processed_at": "2025-09-24T21:07:06.994Z",
            }
        ]

        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_recent_processed_books.return_value = mock_recent

            # Act
            response = client.get("/api/stats/recent")

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data == mock_recent
            mock_stats_service.get_recent_processed_books.assert_called_once_with(
                10
            )  # Default limit

    def test_stats_recent_endpoint_should_accept_limit_parameter(self):
        """Test TDD: L'endpoint /api/stats/recent doit accepter un paramètre limit."""
        mock_recent = []

        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_recent_processed_books.return_value = mock_recent

            # Act
            response = client.get("/api/stats/recent?limit=5")

            # Assert
            assert response.status_code == 200
            mock_stats_service.get_recent_processed_books.assert_called_once_with(5)

    def test_stats_summary_endpoint_should_return_human_readable_text(self):
        """Test TDD: L'endpoint /api/stats/summary doit retourner du texte lisible."""
        mock_summary = """📊 STATISTIQUES CACHE LIVRES/AUTEURS

🚀 Auto-traités (en base) : 5
⏳ En attente validation  : 10
   ├─ ✅ Vérifiés         : 3
   ├─ 💡 Suggestions      : 4
   ├─ ❌ Non trouvés      : 3
   └─ ⏸️  Pending         : 0
🗑️  Rejetés             : 2
📝 Épisodes non traités : 15

Total livres traités : 17"""

        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_human_readable_summary.return_value = mock_summary

            # Act
            response = client.get("/api/stats/summary")

            # Assert
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
            assert response.text == mock_summary

    def test_stats_endpoints_should_handle_errors_gracefully(self):
        """Test TDD: Les endpoints doivent gérer les erreurs gracieusement."""
        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_cache_statistics.side_effect = Exception(
                "Database error"
            )

            # Act
            response = client.get("/api/stats")

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "error" in data
            assert "Database error" in data["error"]

    def test_stats_validation_endpoint_should_return_validation_breakdown(self):
        """Test TDD: L'endpoint /api/stats/validation doit retourner la répartition par validation_status."""
        mock_validation_stats = [
            {"_id": "mongo", "count": 5},
            {"_id": "pending", "count": 12},
            {"_id": "rejected", "count": 2},
        ]

        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_validation_status_breakdown.return_value = (
                mock_validation_stats
            )

            # Act
            response = client.get("/api/stats/validation")

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data == mock_validation_stats
            mock_stats_service.get_validation_status_breakdown.assert_called_once()

    def test_stats_endpoint_should_return_last_episode_date(self):
        """Test TDD Issue #128: L'endpoint /api/stats doit retourner la date du dernier épisode."""
        mock_stats = {
            "couples_en_base": 5,
            "last_episode_date": "2024-12-10T20:00:00",
        }

        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_cache_statistics.return_value = mock_stats

            # Act
            response = client.get("/api/stats")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "last_episode_date" in data
            assert data["last_episode_date"] == "2024-12-10T20:00:00"

    def test_stats_endpoint_should_return_episodes_without_avis_critiques(self):
        """Test TDD Issue #128: L'endpoint /api/stats doit retourner le nombre d'épisodes sans avis critiques."""
        mock_stats = {
            "couples_en_base": 5,
            "episodes_without_avis_critiques": 117,
        }

        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_cache_statistics.return_value = mock_stats

            # Act
            response = client.get("/api/stats")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "episodes_without_avis_critiques" in data
            assert data["episodes_without_avis_critiques"] == 117

    def test_stats_endpoint_should_return_avis_critiques_without_analysis(self):
        """Test TDD Issue #128: L'endpoint /api/stats doit retourner le nombre d'avis critiques sans analyse."""
        mock_stats = {
            "couples_en_base": 5,
            "avis_critiques_without_analysis": 0,
        }

        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service.get_cache_statistics.return_value = mock_stats

            # Act
            response = client.get("/api/stats")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "avis_critiques_without_analysis" in data
            assert data["avis_critiques_without_analysis"] == 0


class TestEpisodesWithoutTranscriptionCountEndpoint:
    """Tests TDD Issue #298: endpoint dédié, non mis en cache (dashboard stats)."""

    def test_endpoint_should_return_count_from_stats_service(self):
        """L'endpoint doit retourner le compte calculé par StatsService, sans passer par le cache dashboard."""
        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service._count_episodes_without_transcription.return_value = 3

            response = client.get("/api/episodes/without-transcription/count")

            assert response.status_code == 200
            assert response.json() == {"count": 3}
            mock_stats_service._count_episodes_without_transcription.assert_called_once()

    def test_endpoint_should_return_500_on_error(self):
        """L'endpoint doit retourner 500 si le calcul échoue."""
        with patch("back_office_lmelp.app.stats_service") as mock_stats_service:
            mock_stats_service._count_episodes_without_transcription.side_effect = (
                Exception("boom")
            )

            response = client.get("/api/episodes/without-transcription/count")

            assert response.status_code == 500
