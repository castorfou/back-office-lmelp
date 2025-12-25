"""Tests pour le modèle Critique."""

from datetime import datetime

from bson import ObjectId

from back_office_lmelp.models.critique import Critique


def test_critique_init_from_mongodb_data():
    """Test d'initialisation d'un critique depuis MongoDB."""
    now = datetime(2025, 1, 15, 10, 0, 0)
    data = {
        "_id": ObjectId(
            "65abc0000000000000000001"
        ),  # pragma: allowlist secret  # pragma: allowlist secret
        "nom": "Blandine Rinkel",
        "variantes": ["Blandine R.", "B. Rinkel"],
        "animateur": False,
        "created_at": now,
        "updated_at": now,
    }

    critique = Critique(data)

    assert (
        critique.id == "65abc0000000000000000001"
    )  # pragma: allowlist secret  # pragma: allowlist secret
    assert critique.nom == "Blandine Rinkel"
    assert critique.variantes == ["Blandine R.", "B. Rinkel"]
    assert critique.animateur is False
    assert critique.created_at == now
    assert critique.updated_at == now


def test_critique_init_minimal():
    """Test d'initialisation avec données minimales."""
    data = {"nom": "Jérôme Garcin"}

    critique = Critique(data)

    assert critique.id == ""
    assert critique.nom == "Jérôme Garcin"
    assert critique.variantes == []
    assert critique.animateur is False
    assert isinstance(critique.created_at, datetime)
    assert isinstance(critique.updated_at, datetime)


def test_critique_to_dict():
    """Test de conversion d'un critique en dictionnaire."""
    now = datetime(2025, 1, 15, 10, 0, 0)
    data = {
        "_id": ObjectId("65abc0000000000000000001"),  # pragma: allowlist secret
        "nom": "Elisabeth Philippe",
        "variantes": ["Elisabeth P."],
        "animateur": False,
        "created_at": now,
        "updated_at": now,
    }

    critique = Critique(data)
    result = critique.to_dict()

    assert result == {
        "id": "65abc0000000000000000001",  # pragma: allowlist secret
        "nom": "Elisabeth Philippe",
        "variantes": ["Elisabeth P."],
        "animateur": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


def test_critique_for_mongodb_insert():
    """Test de préparation des données pour insertion MongoDB."""
    data = {
        "nom": "Patricia Martin",
        "variantes": ["Patricia M."],
        "animateur": False,
    }

    result = Critique.for_mongodb_insert(data)

    assert result["nom"] == "Patricia Martin"
    assert result["variantes"] == ["Patricia M."]
    assert result["animateur"] is False
    assert isinstance(result["created_at"], datetime)
    assert isinstance(result["updated_at"], datetime)


def test_critique_for_mongodb_insert_with_animateur():
    """Test de préparation des données pour un animateur."""
    data = {
        "nom": "Rebecca Manzoni",
        "animateur": True,
    }

    result = Critique.for_mongodb_insert(data)

    assert result["nom"] == "Rebecca Manzoni"
    assert result["variantes"] == []
    assert result["animateur"] is True


def test_critique_add_variante():
    """Test d'ajout d'une variante."""
    data = {
        "_id": ObjectId("65abc0000000000000000001"),  # pragma: allowlist secret
        "nom": "Arnaud Viviant",
        "variantes": ["Arnaud V."],
        "animateur": False,
    }

    critique = Critique(data)
    critique.add_variante("A. Viviant")

    assert "A. Viviant" in critique.variantes
    assert len(critique.variantes) == 2


def test_critique_add_variante_no_duplicate():
    """Test que l'ajout d'une variante existante ne crée pas de doublon."""
    data = {
        "_id": ObjectId("65abc0000000000000000001"),  # pragma: allowlist secret
        "nom": "Jean-Marc Proust",
        "variantes": ["Jean-Marc P.", "J-M Proust"],
        "animateur": False,
    }

    critique = Critique(data)
    critique.add_variante("Jean-Marc P.")

    assert critique.variantes.count("Jean-Marc P.") == 1
    assert len(critique.variantes) == 2
