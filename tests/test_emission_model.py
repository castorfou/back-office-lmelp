"""Tests pour le modèle Emission."""

from datetime import datetime

from bson import ObjectId

from back_office_lmelp.models.emission import Emission


def test_emission_init_from_mongodb_data():
    """Test d'initialisation d'une émission depuis MongoDB."""
    now = datetime(2025, 1, 15, 10, 0, 0)
    episode_date = datetime(2025, 7, 6, 0, 0, 0)

    data = {
        "_id": ObjectId(
            "65abc0000000000000000001"
        ),  # pragma: allowlist secret  # pragma: allowlist secret
        "episode_id": "507f1f77bcf86cd799439012",
        "avis_critique_id": "507f1f77bcf86cd799439013",
        "date": episode_date,
        "duree": 3600,
        "animateur_id": "507f1f77bcf86cd799439014",
        "avis_ids": ["507f1f77bcf86cd799439015", "507f1f77bcf86cd799439016"],
        "created_at": now,
        "updated_at": now,
    }

    emission = Emission(data)

    assert (
        emission.id == "65abc0000000000000000001"
    )  # pragma: allowlist secret  # pragma: allowlist secret
    assert emission.episode_id == "507f1f77bcf86cd799439012"
    assert emission.avis_critique_id == "507f1f77bcf86cd799439013"
    assert emission.date == episode_date
    assert emission.duree == 3600
    assert emission.animateur_id == "507f1f77bcf86cd799439014"
    assert emission.avis_ids == ["507f1f77bcf86cd799439015", "507f1f77bcf86cd799439016"]
    assert emission.created_at == now
    assert emission.updated_at == now


def test_emission_init_minimal():
    """Test d'initialisation avec données minimales."""
    episode_date = datetime(2025, 7, 6, 0, 0, 0)

    data = {
        "episode_id": "507f1f77bcf86cd799439012",
        "avis_critique_id": "507f1f77bcf86cd799439013",
        "date": episode_date,
        "duree": 3600,
    }

    emission = Emission(data)

    assert emission.id == ""
    assert emission.episode_id == "507f1f77bcf86cd799439012"
    assert emission.avis_critique_id == "507f1f77bcf86cd799439013"
    assert emission.date == episode_date
    assert emission.duree == 3600
    assert emission.animateur_id is None
    assert emission.avis_ids == []
    assert isinstance(emission.created_at, datetime)
    assert isinstance(emission.updated_at, datetime)


def test_emission_to_dict():
    """Test de conversion d'une émission en dictionnaire."""
    now = datetime(2025, 1, 15, 10, 0, 0)
    episode_date = datetime(2025, 7, 6, 0, 0, 0)

    data = {
        "_id": ObjectId("65abc0000000000000000001"),  # pragma: allowlist secret
        "episode_id": "507f1f77bcf86cd799439012",
        "avis_critique_id": "507f1f77bcf86cd799439013",
        "date": episode_date,
        "duree": 3600,
        "animateur_id": "507f1f77bcf86cd799439014",
        "avis_ids": ["507f1f77bcf86cd799439015"],
        "created_at": now,
        "updated_at": now,
    }

    emission = Emission(data)
    result = emission.to_dict()

    assert result == {
        "id": "65abc0000000000000000001",  # pragma: allowlist secret
        "episode_id": "507f1f77bcf86cd799439012",
        "avis_critique_id": "507f1f77bcf86cd799439013",
        "date": episode_date.isoformat(),
        "duree": 3600,
        "animateur_id": "507f1f77bcf86cd799439014",
        "avis_ids": ["507f1f77bcf86cd799439015"],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


def test_emission_for_mongodb_insert():
    """Test de préparation des données pour insertion MongoDB."""
    episode_date = datetime(2025, 7, 6, 0, 0, 0)

    data = {
        "episode_id": ObjectId("507f1f77bcf86cd799439012"),
        "avis_critique_id": ObjectId("507f1f77bcf86cd799439013"),
        "date": episode_date,
        "duree": 3600,
        "animateur_id": ObjectId("507f1f77bcf86cd799439014"),
        "avis_ids": [],
    }

    result = Emission.for_mongodb_insert(data)

    assert result["episode_id"] == ObjectId("507f1f77bcf86cd799439012")
    assert result["avis_critique_id"] == ObjectId("507f1f77bcf86cd799439013")
    assert result["date"] == episode_date
    assert result["duree"] == 3600
    assert result["animateur_id"] == ObjectId("507f1f77bcf86cd799439014")
    assert result["avis_ids"] == []
    assert isinstance(result["created_at"], datetime)
    assert isinstance(result["updated_at"], datetime)


def test_emission_for_mongodb_insert_without_animateur():
    """Test de préparation des données sans animateur."""
    episode_date = datetime(2025, 7, 6, 0, 0, 0)

    data = {
        "episode_id": ObjectId("507f1f77bcf86cd799439012"),
        "avis_critique_id": ObjectId("507f1f77bcf86cd799439013"),
        "date": episode_date,
        "duree": 3600,
    }

    result = Emission.for_mongodb_insert(data)

    assert result["episode_id"] == ObjectId("507f1f77bcf86cd799439012")
    assert result["avis_critique_id"] == ObjectId("507f1f77bcf86cd799439013")
    assert result["date"] == episode_date
    assert result["duree"] == 3600
    assert result["animateur_id"] is None
    assert result["avis_ids"] == []
