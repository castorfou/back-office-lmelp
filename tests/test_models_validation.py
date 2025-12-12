"""Tests for Episode model validation and serialization."""

from datetime import datetime

from back_office_lmelp.models.episode import Episode


class TestEpisodeModel:
    """Test class for Episode model validation and methods."""

    def test_episode_initialization_full_data(self):
        """Test episode initialization with full data."""
        test_date = datetime(2024, 1, 15, 10, 30)
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Test Episode",
            "date": test_date,
            "type": "podcast",
            "description": "Test description",
            "description_corrigee": "Corrected description",
            "titre_corrige": "Corrected title",
            "transcription": "Test transcription",
        }

        episode = Episode(data)

        assert episode.id == "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        assert episode.titre == "Test Episode"
        assert episode.date == test_date
        assert episode.type == "podcast"
        assert episode.description == "Test description"
        assert episode.description_corrigee == "Corrected description"
        assert episode.titre_corrige == "Corrected title"
        assert episode.transcription == "Test transcription"

    def test_episode_initialization_minimal_data(self):
        """Test episode initialization with minimal data."""
        data = {}

        episode = Episode(data)

        assert episode.id == ""
        assert episode.titre == ""
        assert episode.date is None
        assert episode.type == ""
        assert episode.description == ""
        assert episode.description_corrigee is None
        assert episode.titre_corrige is None
        assert episode.transcription is None

    def test_episode_initialization_partial_data(self):
        """Test episode initialization with partial data."""
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Partial Episode",
            "type": "interview",
        }

        episode = Episode(data)

        assert episode.id == "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        assert episode.titre == "Partial Episode"
        assert episode.date is None
        assert episode.type == "interview"
        assert episode.description == ""
        assert episode.description_corrigee is None
        assert episode.titre_corrige is None
        assert episode.transcription is None

    def test_episode_to_dict_full_data(self):
        """Test episode to_dict method with full data."""
        test_date = datetime(2024, 3, 20, 14, 45)
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Full Episode",
            "date": test_date,
            "type": "discussion",
            "description": "Full description",
            "description_corrigee": "Corrected desc",
            "titre_corrige": "Corrected title",
            "transcription": "Full transcription",
        }

        episode = Episode(data)
        result = episode.to_dict()

        expected = {
            "id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Full Episode",
            "date": "2024-03-20T14:45:00",
            "type": "discussion",
            "description": "Full description",
            "description_corrigee": "Corrected desc",
            "titre_corrige": "Corrected title",
            "transcription": "Full transcription",
            "titre_origin": None,
            "description_origin": None,
            "masked": False,  # Issue #107: Champ masked ajouté
            "episode_page_url": None,  # Issue #129: URL de la page RadioFrance
        }

        assert result == expected

    def test_episode_to_dict_null_date(self):
        """Test episode to_dict method with null date."""
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "No Date Episode",
            "type": "test",
        }

        episode = Episode(data)
        result = episode.to_dict()

        assert result["date"] is None
        assert result["id"] == "507f1f77bcf86cd799439011"  # pragma: allowlist secret
        assert result["titre"] == "No Date Episode"

    def test_episode_to_dict_minimal_data(self):
        """Test episode to_dict method with minimal data."""
        data = {"_id": "507f1f77bcf86cd799439011"}

        episode = Episode(data)
        result = episode.to_dict()

        expected = {
            "id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "",
            "date": None,
            "type": "",
            "description": "",
            "description_corrigee": None,
            "titre_corrige": None,
            "transcription": None,
            "titre_origin": None,
            "description_origin": None,
            "masked": False,  # Issue #107: Champ masked ajouté
            "episode_page_url": None,  # Issue #129: URL de la page RadioFrance
        }

        assert result == expected

    def test_episode_to_summary_dict_full_data(self):
        """Test episode to_summary_dict method with full data."""
        test_date = datetime(2024, 2, 10, 9, 15)
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Summary Episode",
            "date": test_date,
            "type": "news",
            "description": "This should not appear in summary",
            "transcription": "This should not appear in summary",
        }

        episode = Episode(data)
        result = episode.to_summary_dict()

        expected = {
            "id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Summary Episode",
            "date": "2024-02-10T09:15:00",
            "type": "news",
            "duree": None,
            "masked": False,  # Issue #107: Champ masked ajouté
        }

        assert result == expected
        # Ensure summary doesn't include full content
        assert "description" not in result
        assert "transcription" not in result
        assert "description_corrigee" not in result
        # titre_corrige should no longer be included in summary (new logic)
        assert "titre_corrige" not in result

    def test_episode_to_summary_dict_null_date(self):
        """Test episode to_summary_dict method with null date."""
        data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "No Date Summary",
            "type": "test",
        }

        episode = Episode(data)
        result = episode.to_summary_dict()

        expected = {
            "id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "No Date Summary",
            "date": None,
            "type": "test",
            "duree": None,
            "masked": False,  # Issue #107: Champ masked ajouté
        }

        assert result == expected

    def test_episode_to_summary_dict_minimal_data(self):
        """Test episode to_summary_dict method with minimal data."""
        data = {}

        episode = Episode(data)
        result = episode.to_summary_dict()

        expected = {
            "id": "",
            "titre": "",
            "date": None,
            "type": "",
            "duree": None,
            "masked": False,  # Issue #107: Champ masked ajouté
        }

        assert result == expected

    def test_episode_to_summary_dict_with_titre_corrected(self):
        """Test episode to_summary_dict method with corrected title (new logic)."""
        test_date = datetime(2024, 8, 24, 9, 0)
        data = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "titre": "Justine Lévy, Antoine Wauters, Alice Ferney",  # Version corrigée dans titre
            "titre_origin": "Titre original",  # Version originale dans titre_origin
            "date": test_date,
            "type": "livres",
        }

        episode = Episode(data)
        result = episode.to_summary_dict()

        expected = {
            "id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "titre": "Justine Lévy, Antoine Wauters, Alice Ferney",  # Version corrigée affichée
            "date": "2024-08-24T09:00:00",
            "type": "livres",
            "duree": None,
            "masked": False,  # Issue #107: Champ masked ajouté
        }

        assert result == expected
        # Verify the corrected title is in titre field (new logic)
        assert result["titre"] == "Justine Lévy, Antoine Wauters, Alice Ferney"
        # titre_corrige should no longer be in summary
        assert "titre_corrige" not in result

    def test_episode_handles_none_values_gracefully(self):
        """Test episode handles None values in data gracefully."""
        data = {
            "_id": None,
            "titre": None,
            "date": None,
            "type": None,
            "description": None,
            "description_corrigee": None,
            "titre_corrige": None,
            "transcription": None,
        }

        episode = Episode(data)

        # Should handle None values by converting to empty strings where appropriate
        assert episode.id == ""  # None becomes ""
        assert episode.titre == ""  # None becomes ""
        assert episode.date is None  # None stays None for datetime
        assert episode.type == ""  # None becomes ""
        assert episode.description == ""  # None becomes ""
        assert episode.description_corrigee is None
        assert episode.titre_corrige is None
        assert episode.transcription is None

    def test_episode_datetime_serialization_edge_cases(self):
        """Test episode datetime serialization with edge cases."""
        # Test with microseconds
        test_date = datetime(2024, 12, 31, 23, 59, 59, 999999)
        data = {"date": test_date}

        episode = Episode(data)
        result = episode.to_dict()

        assert result["date"] == "2024-12-31T23:59:59.999999"

    def test_episode_string_representation_consistency(self):
        """Test that episode data remains consistent through operations."""
        original_data = {
            "_id": "507f1f77bcf86cd799439011",
            "titre": "Consistency Test",
            "date": datetime(2024, 6, 15),
            "type": "test",
        }

        episode = Episode(original_data)
        dict_result = episode.to_dict()
        summary_result = episode.to_summary_dict()

        # ID should be consistent across all representations
        assert episode.id == dict_result["id"] == summary_result["id"]
        assert episode.titre == dict_result["titre"] == summary_result["titre"]
        assert episode.type == dict_result["type"] == summary_result["type"]

    def test_episode_data_immutability(self):
        """Test that episode doesn't modify original data dict."""
        original_data = {"_id": "507f1f77bcf86cd799439011", "titre": "Original Title"}
        original_data_copy = original_data.copy()

        episode = Episode(original_data)
        episode.titre = "Modified Title"

        # Original data should remain unchanged
        assert original_data == original_data_copy
        assert episode.titre == "Modified Title"
