"""Tests pour les endpoints API de génération d'avis critiques."""

from datetime import datetime
from unittest.mock import patch

from bson import ObjectId


class TestGetEpisodesSansAvisCritiques:
    """Tests pour GET /api/episodes-sans-avis-critiques."""

    def test_should_return_list_of_episodes_without_avis(self, client):
        """Doit retourner la liste des épisodes sans avis critiques."""
        mock_episodes = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),  # pragma: allowlist secret
                "titre": "Épisode Test 1",
                "date": datetime(2025, 1, 15),
                "transcription": "Transcription de l'épisode 1",
                "episode_page_url": "https://www.radiofrance.fr/episode1",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),  # pragma: allowlist secret
                "titre": "Épisode Test 2",
                "date": datetime(2025, 1, 10),
                "transcription": "Transcription de l'épisode 2",
                "episode_page_url": None,
            },
        ]

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            # Mock avis_critiques collection (aucun avis)
            mock_service.avis_critiques_collection.find.return_value = []

            # Mock episodes collection
            mock_find = mock_service.episodes_collection.find.return_value
            mock_find.sort.return_value.limit.return_value = mock_episodes

            response = client.get("/api/episodes-sans-avis-critiques")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert (
                data[0]["id"] == "507f1f77bcf86cd799439011"  # pragma: allowlist secret
            )
            assert data[0]["titre"] == "Épisode Test 1"
            assert data[0]["transcription_length"] == 28
            assert data[0]["has_episode_page_url"] is True
            assert data[1]["has_episode_page_url"] is False

    def test_should_exclude_episodes_with_avis_critiques(self, client):
        """Doit exclure les épisodes qui ont déjà des avis critiques."""
        mock_avis = [
            {"episode_oid": "507f1f77bcf86cd799439011"}  # pragma: allowlist secret
        ]

        mock_episodes = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),  # pragma: allowlist secret
                "titre": "Épisode sans avis",
                "date": datetime(2025, 1, 10),
                "transcription": "Transcription",
                "episode_page_url": None,
            }
        ]

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            # Mock avis_critiques collection
            mock_service.avis_critiques_collection.find.return_value = mock_avis

            # Mock episodes collection
            mock_find = mock_service.episodes_collection.find.return_value
            mock_find.sort.return_value.limit.return_value = mock_episodes

            response = client.get("/api/episodes-sans-avis-critiques")

            assert response.status_code == 200
            data = response.json()
            # Vérifier que seul l'épisode sans avis est retourné
            assert len(data) == 1
            assert (
                data[0]["id"] == "507f1f77bcf86cd799439012"  # pragma: allowlist secret
            )

    def test_should_only_return_episodes_with_transcription(self, client):
        """Doit retourner seulement les épisodes avec transcription."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.avis_critiques_collection.find.return_value = []

            mock_episodes = [
                {
                    "_id": ObjectId(
                        "507f1f77bcf86cd799439011"  # pragma: allowlist secret
                    ),
                    "titre": "Épisode avec transcription",
                    "date": datetime(2025, 1, 15),
                    "transcription": "Longue transcription",
                    "episode_page_url": None,
                }
            ]

            mock_find = mock_service.episodes_collection.find.return_value
            mock_find.sort.return_value.limit.return_value = mock_episodes

            response = client.get("/api/episodes-sans-avis-critiques")

            assert response.status_code == 200
            data = response.json()
            # Tous les épisodes retournés doivent avoir transcription_length > 0
            assert all(ep["transcription_length"] > 0 for ep in data)

    def test_should_sort_by_date_descending(self, client):
        """Doit trier par date décroissante."""
        mock_episodes = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),  # pragma: allowlist secret
                "titre": "Épisode récent",
                "date": datetime(2025, 1, 20),
                "transcription": "Transcription",
                "episode_page_url": None,
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),  # pragma: allowlist secret
                "titre": "Épisode ancien",
                "date": datetime(2025, 1, 10),
                "transcription": "Transcription",
                "episode_page_url": None,
            },
        ]

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.avis_critiques_collection.find.return_value = []

            mock_find = mock_service.episodes_collection.find.return_value
            mock_find.sort.return_value.limit.return_value = mock_episodes

            response = client.get("/api/episodes-sans-avis-critiques")

            assert response.status_code == 200
            _ = response.json()
            # Vérifier que le tri est appliqué dans la query MongoDB
            mock_find.sort.assert_called_once_with([("date", -1)])

    def test_should_return_episode_page_url_when_present(self, client):
        """Doit retourner episode_page_url dans la réponse pour éviter fetch inutile."""
        mock_episodes = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),  # pragma: allowlist secret
                "titre": "Épisode avec URL",
                "date": datetime(2025, 1, 15),
                "transcription": "Transcription de l'épisode",
                "episode_page_url": "https://www.radiofrance.fr/franceinter/podcasts/episode-test",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),  # pragma: allowlist secret
                "titre": "Épisode sans URL",
                "date": datetime(2025, 1, 10),
                "transcription": "Transcription",
                "episode_page_url": None,
            },
        ]

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.avis_critiques_collection.find.return_value = []

            mock_find = mock_service.episodes_collection.find.return_value
            mock_find.sort.return_value.limit.return_value = mock_episodes

            response = client.get("/api/episodes-sans-avis-critiques")

            assert response.status_code == 200
            data = response.json()

            # Vérifier que episode_page_url est inclus dans la réponse
            assert "episode_page_url" in data[0]
            assert (
                data[0]["episode_page_url"]
                == "https://www.radiofrance.fr/franceinter/podcasts/episode-test"
            )
            assert data[0]["has_episode_page_url"] is True

            assert "episode_page_url" in data[1]
            assert data[1]["episode_page_url"] is None
            assert data[1]["has_episode_page_url"] is False


class TestGetEpisodesWithSummaries:
    """Tests pour GET /api/episodes-with-summaries."""

    def test_should_return_episodes_with_summaries(self, client):
        """Doit retourner les épisodes qui ont des avis critiques."""
        mock_avis = [
            {"episode_oid": "507f1f77bcf86cd799439011"},  # pragma: allowlist secret
            {"episode_oid": "507f1f77bcf86cd799439012"},  # pragma: allowlist secret
        ]

        mock_episodes = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),  # pragma: allowlist secret
                "titre": "Épisode avec summary 1",
                "date": datetime(2025, 1, 15),
                "transcription": "Transcription de l'épisode 1",
                "episode_page_url": "https://www.radiofrance.fr/episode1",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),  # pragma: allowlist secret
                "titre": "Épisode avec summary 2",
                "date": datetime(2025, 1, 10),
                "transcription": "Transcription de l'épisode 2",
                "episode_page_url": None,
            },
        ]

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            # Mock avis_critiques collection
            mock_service.avis_critiques_collection.find.return_value = mock_avis

            # Mock episodes collection
            mock_find = mock_service.episodes_collection.find.return_value
            mock_find.sort.return_value.limit.return_value = mock_episodes

            response = client.get("/api/episodes-with-summaries")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert (
                data[0]["id"] == "507f1f77bcf86cd799439011"  # pragma: allowlist secret
            )
            assert data[0]["titre"] == "Épisode avec summary 1"
            assert data[0]["has_summary"] is True
            assert data[1]["has_summary"] is True

    def test_should_return_empty_list_if_no_avis(self, client):
        """Doit retourner liste vide si aucun avis critique."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            # Mock avis_critiques collection (vide)
            mock_service.avis_critiques_collection.find.return_value = []

            response = client.get("/api/episodes-with-summaries")

            assert response.status_code == 200
            data = response.json()
            assert data == []

    def test_should_exclude_masked_episodes(self, client):
        """Doit exclure les épisodes masqués."""
        mock_avis = [
            {"episode_oid": "507f1f77bcf86cd799439011"},  # pragma: allowlist secret
            {"episode_oid": "507f1f77bcf86cd799439012"},  # pragma: allowlist secret
        ]

        # Episode 1 non masqué, Episode 2 masqué
        mock_episodes = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),  # pragma: allowlist secret
                "titre": "Épisode non masqué",
                "date": datetime(2025, 1, 15),
                "transcription": "Transcription",
                "episode_page_url": None,
            }
        ]

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.avis_critiques_collection.find.return_value = mock_avis

            mock_find = mock_service.episodes_collection.find.return_value
            mock_find.sort.return_value.limit.return_value = mock_episodes

            response = client.get("/api/episodes-with-summaries")

            assert response.status_code == 200
            data = response.json()
            # Vérifier que seul l'épisode non masqué est retourné
            assert len(data) == 1
            assert (
                data[0]["id"] == "507f1f77bcf86cd799439011"  # pragma: allowlist secret
            )

    def test_should_sort_by_date_descending(self, client):
        """Doit trier par date décroissante."""
        mock_avis = [
            {"episode_oid": "507f1f77bcf86cd799439011"},  # pragma: allowlist secret
        ]

        mock_episodes = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),  # pragma: allowlist secret
                "titre": "Épisode",
                "date": datetime(2025, 1, 15),
                "transcription": "Transcription",
                "episode_page_url": None,
            }
        ]

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.avis_critiques_collection.find.return_value = mock_avis

            mock_find = mock_service.episodes_collection.find.return_value
            mock_find.sort.return_value.limit.return_value = mock_episodes

            response = client.get("/api/episodes-with-summaries")

            assert response.status_code == 200
            # Vérifier que le tri est appliqué dans la query MongoDB
            mock_find.sort.assert_called_once_with([("date", -1)])


class TestGetSummaryByEpisode:
    """Tests pour GET /api/avis-critiques/by-episode/{episode_id}."""

    def test_should_return_existing_summary(self, client):
        """Doit retourner le summary existant pour un épisode."""
        mock_avis = {
            "_id": ObjectId("507f1f77bcf86cd799439999"),  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "summary": "## 1. LIVRES DISCUTÉS\n\nTest summary",
            "summary_phase1": "## 1. LIVRES DISCUTÉS\n\nPhase 1 summary",
            "metadata_source": {
                "animateur": "Jérôme Garcin",
                "critiques": ["Patricia Martin", "Arnaud Viviant"],
            },
            "created_at": datetime(2025, 1, 15, 10, 0, 0),
            "updated_at": datetime(2025, 1, 15, 11, 0, 0),
        }

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.avis_critiques_collection.find_one.return_value = mock_avis

            response = client.get(
                "/api/avis-critiques/by-episode/507f1f77bcf86cd799439011"  # pragma: allowlist secret
            )

            assert response.status_code == 200
            data = response.json()

            assert data["summary"] == "## 1. LIVRES DISCUTÉS\n\nTest summary"
            assert data["summary_phase1"] == "## 1. LIVRES DISCUTÉS\n\nPhase 1 summary"
            assert data["metadata"]["animateur"] == "Jérôme Garcin"
            assert "Patricia Martin" in data["metadata"]["critiques"]
            assert data["created_at"] == "2025-01-15T10:00:00"
            assert data["updated_at"] == "2025-01-15T11:00:00"

    def test_should_return_404_if_not_found(self, client):
        """Doit retourner 404 si aucun avis trouvé."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.avis_critiques_collection.find_one.return_value = None

            response = client.get(
                "/api/avis-critiques/by-episode/507f1f77bcf86cd799439999"  # pragma: allowlist secret
            )

            assert response.status_code == 404
            assert "Aucun avis critique trouvé" in response.json()["detail"]

    def test_should_handle_missing_optional_fields(self, client):
        """Doit gérer les champs optionnels manquants gracefully."""
        mock_avis = {
            "_id": ObjectId("507f1f77bcf86cd799439999"),  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "summary": "Test summary",
            # Pas de summary_phase1, metadata, timestamps
        }

        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.avis_critiques_collection.find_one.return_value = mock_avis

            response = client.get(
                "/api/avis-critiques/by-episode/507f1f77bcf86cd799439011"  # pragma: allowlist secret
            )

            assert response.status_code == 200
            data = response.json()

            assert data["summary"] == "Test summary"
            assert data["summary_phase1"] == ""
            assert data["metadata"] == {}
            assert data["created_at"] is None
            assert data["updated_at"] is None
