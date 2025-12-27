"""Tests pour les méthodes emissions du MongoDBService (TDD)."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from bson import ObjectId

from back_office_lmelp.services.mongodb_service import MongoDBService


class TestGetAllEmissions:
    """Tests pour get_all_emissions()."""

    def test_should_get_all_emissions_empty(self):
        """GREEN: Doit retourner liste vide quand collection vide."""
        # Arrange
        service = MongoDBService()
        service.emissions_collection = MagicMock()
        service.emissions_collection.find.return_value.sort.return_value = []

        # Act
        result = service.get_all_emissions()

        # Assert
        assert result == []
        service.emissions_collection.find.assert_called_once()

    def test_should_get_all_emissions_with_data(self):
        """RED: Doit retourner émissions triées par date desc."""
        # Arrange
        service = MongoDBService()
        service.emissions_collection = MagicMock()

        mock_emission_1 = {
            "_id": ObjectId("686bf5e18380ee925ae5e318"),  # pragma: allowlist secret
            "episode_id": ObjectId(
                "686bf5e18380ee925ae5e319"  # pragma: allowlist secret
            ),
            "date": datetime(2025, 7, 6),
            "duree": 1800,
        }
        mock_emission_2 = {
            "_id": ObjectId("686bf5e18380ee925ae5e31a"),  # pragma: allowlist secret
            "episode_id": ObjectId(
                "686bf5e18380ee925ae5e31b"  # pragma: allowlist secret
            ),
            "date": datetime(2025, 7, 13),
            "duree": 1900,
        }

        # Simuler le tri MongoDB (plus récent en premier)
        service.emissions_collection.find.return_value.sort.return_value = [
            mock_emission_2,  # Plus récent
            mock_emission_1,  # Plus ancien
        ]

        # Act
        result = service.get_all_emissions()

        # Assert
        assert len(result) == 2
        assert result[0]["_id"] == mock_emission_2["_id"]
        assert result[1]["_id"] == mock_emission_1["_id"]
        service.emissions_collection.find.assert_called_once()
        service.emissions_collection.find.return_value.sort.assert_called_once_with(
            "date", -1
        )


class TestGetEmissionByEpisodeId:
    """Tests pour get_emission_by_episode_id()."""

    def test_should_get_emission_by_episode_id(self):
        """Doit retourner émission correspondant à l'episode_id."""
        # Arrange
        service = MongoDBService()
        service.emissions_collection = MagicMock()

        episode_id = "686bf5e18380ee925ae5e319"  # pragma: allowlist secret
        mock_emission = {
            "_id": ObjectId("686bf5e18380ee925ae5e318"),  # pragma: allowlist secret
            "episode_id": ObjectId(episode_id),
            "date": datetime(2025, 7, 6),
        }

        service.emissions_collection.find_one.return_value = mock_emission

        # Act
        result = service.get_emission_by_episode_id(episode_id)

        # Assert
        assert result is not None
        assert result["_id"] == mock_emission["_id"]
        service.emissions_collection.find_one.assert_called_once_with(
            {"episode_id": ObjectId(episode_id)}
        )

    def test_should_return_none_if_not_found(self):
        """Doit retourner None si aucune émission trouvée."""
        # Arrange
        service = MongoDBService()
        service.emissions_collection = MagicMock()
        service.emissions_collection.find_one.return_value = None

        # Act
        result = service.get_emission_by_episode_id(
            "686bf5e18380ee925ae5e319"  # pragma: allowlist secret
        )

        # Assert
        assert result is None


class TestCreateEmission:
    """Tests pour create_emission()."""

    def test_should_create_emission(self):
        """Doit créer une émission et retourner son ID."""
        # Arrange
        service = MongoDBService()
        service.emissions_collection = MagicMock()

        emission_data = {
            "episode_id": ObjectId(
                "686bf5e18380ee925ae5e319"  # pragma: allowlist secret
            ),
            "avis_critique_id": ObjectId(
                "686c48b728b9e451c1cee31f"  # pragma: allowlist secret
            ),
            "date": datetime(2025, 7, 6),
            "duree": 1800,
            "animateur_id": None,
            "avis_ids": [],
        }

        inserted_id = ObjectId("686bf5e18380ee925ae5e318")  # pragma: allowlist secret
        mock_result = MagicMock()
        mock_result.inserted_id = inserted_id
        service.emissions_collection.insert_one.return_value = mock_result

        # Act
        result = service.create_emission(emission_data)

        # Assert
        assert result == str(inserted_id)
        service.emissions_collection.insert_one.assert_called_once_with(emission_data)


class TestGetCritiquesByEpisode:
    """Tests pour get_critiques_by_episode()."""

    @patch(
        "back_office_lmelp.services.critiques_extraction_service.critiques_extraction_service"
    )
    def test_should_get_critiques_by_episode(self, mock_extraction_service):
        """Doit extraire et matcher critiques depuis summary."""
        # Arrange
        service = MongoDBService()
        service.avis_critiques_collection = MagicMock()
        service.critiques_collection = MagicMock()

        episode_id = "686bf5e18380ee925ae5e319"  # pragma: allowlist secret
        mock_avis = {
            "_id": ObjectId(),
            "summary": "**Jérôme Garcin**: Excellent livre",
        }

        mock_critique = {
            "_id": ObjectId("686c48b728b9e451c1cee320"),  # pragma: allowlist secret
            "nom": "Jérôme Garcin",
            "animateur": True,
        }

        service.avis_critiques_collection.find_one.return_value = mock_avis
        service.critiques_collection.find.return_value = [mock_critique]

        mock_extraction_service.extract_critiques_from_summary.return_value = [
            "Jérôme Garcin"
        ]
        mock_extraction_service.find_matching_critique.return_value = {
            "nom": "Jérôme Garcin",
            "match_type": "exact",
        }

        # Act
        result = service.get_critiques_by_episode(episode_id)

        # Assert
        assert len(result) == 1
        assert result[0]["nom"] == "Jérôme Garcin"
        assert result[0]["animateur"] is True
        assert result[0]["id"] == str(mock_critique["_id"])

    def test_should_return_empty_if_no_avis(self):
        """Doit retourner liste vide si pas d'avis critique."""
        # Arrange
        service = MongoDBService()
        service.avis_critiques_collection = MagicMock()
        service.avis_critiques_collection.find_one.return_value = None

        # Act
        result = service.get_critiques_by_episode(
            "686bf5e18380ee925ae5e319"  # pragma: allowlist secret
        )

        # Assert
        assert result == []
