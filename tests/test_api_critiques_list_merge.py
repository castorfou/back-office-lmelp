"""Tests TDD pour les nouveaux endpoints : GET /api/critiques et POST /api/critiques/merge.

Données de référence extraites de MongoDB (réelles) :
- critiques._id : ObjectId
- critiques.nom : String
- avis.critique_oid : String (pas ObjectId !)
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


OID_VIVIANT = "694eb58bffd25d11ce052759"  # pragma: allowlist secret
OID_PHILIPPE = "694eb72b3696842476c793cd"  # pragma: allowlist secret
OID_NEUHOFF = "695679b0b49e0e1c6b6e3161"  # pragma: allowlist secret


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_mongodb():
    with patch("back_office_lmelp.app.mongodb_service") as mock:
        mock.critiques_collection = MagicMock()
        mock.avis_collection = MagicMock()
        yield mock


# ── GET /api/critiques ────────────────────────────────────────────────────────


class TestGetAllCritiques:
    """Tests pour l'endpoint GET /api/critiques."""

    def test_returns_200(self, client, mock_mongodb):
        """L'endpoint retourne 200 avec une liste."""
        mock_mongodb.get_all_critiques.return_value = []
        response = client.get("/api/critiques")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_returns_critiques_with_required_fields(self, client, mock_mongodb):
        """Chaque critique a les champs id, nom, nombre_avis, note_moyenne."""
        mock_mongodb.get_all_critiques.return_value = [
            {
                "_id": ObjectId(OID_VIVIANT),
                "nom": "Arnaud Viviant",
                "animateur": False,
                "variantes": [],
                "nombre_avis": 706,
                "note_moyenne": 7.5,
            }
        ]
        response = client.get("/api/critiques")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        critique = data[0]
        assert critique["id"] == OID_VIVIANT
        assert critique["nom"] == "Arnaud Viviant"
        assert critique["nombre_avis"] == 706
        assert critique["note_moyenne"] == pytest.approx(7.5, abs=0.01)

    def test_returns_animateur_flag(self, client, mock_mongodb):
        """Le champ animateur est retourné."""
        mock_mongodb.get_all_critiques.return_value = [
            {
                "_id": ObjectId(OID_VIVIANT),
                "nom": "Arnaud Viviant",
                "animateur": True,
                "variantes": [],
                "nombre_avis": 10,
                "note_moyenne": None,
            }
        ]
        response = client.get("/api/critiques")
        assert response.json()[0]["animateur"] is True

    def test_note_moyenne_none_when_no_avis(self, client, mock_mongodb):
        """note_moyenne est null si le critique n'a aucun avis."""
        mock_mongodb.get_all_critiques.return_value = [
            {
                "_id": ObjectId(OID_VIVIANT),
                "nom": "Nouveau Critique",
                "animateur": False,
                "variantes": [],
                "nombre_avis": 0,
                "note_moyenne": None,
            }
        ]
        response = client.get("/api/critiques")
        assert response.json()[0]["note_moyenne"] is None

    def test_empty_list_when_no_critiques(self, client, mock_mongodb):
        """Retourne une liste vide si aucun critique en base."""
        mock_mongodb.get_all_critiques.return_value = []
        response = client.get("/api/critiques")
        assert response.status_code == 200
        assert response.json() == []

    def test_route_does_not_conflict_with_critique_detail(self, client, mock_mongodb):
        """/api/critiques ne doit pas être intercepté par /api/critique/{id}."""
        mock_mongodb.get_all_critiques.return_value = []
        response = client.get("/api/critiques")
        # Si la route était mal ordonnée, "critiques" serait interprété comme un {id}
        # et retournerait 404 (ObjectId invalide) plutôt que 200
        assert response.status_code == 200


# ── POST /api/critiques/merge ────────────────────────────────────────────────


class TestMergeCritiques:
    """Tests pour l'endpoint POST /api/critiques/merge."""

    def _mock_critiques(
        self, mock_mongodb, source_nom="Eric Neuhoff", target_nom="Éric Neuhoff"
    ):
        """Configure les mocks pour deux critiques existants."""
        mock_mongodb.critiques_collection.find_one.side_effect = lambda q: {
            ObjectId(OID_NEUHOFF): {
                "_id": ObjectId(OID_NEUHOFF),
                "nom": source_nom,
                "variantes": ["E. Neuhoff"],
                "animateur": False,
            },
            ObjectId(OID_VIVIANT): {
                "_id": ObjectId(OID_VIVIANT),
                "nom": target_nom,
                "variantes": [],
                "animateur": False,
            },
        }.get(q.get("_id"))

    def test_merge_success_returns_200(self, client, mock_mongodb):
        """Merge réussi → 200 avec résumé."""
        mock_mongodb.merge_critiques.return_value = {
            "merged_avis": 18,
            "deleted_critique": OID_NEUHOFF,
            "target_id": OID_VIVIANT,
        }
        # Mock pour valider le nom de confirmation
        mock_mongodb.critiques_collection.find_one.return_value = {
            "_id": ObjectId(OID_VIVIANT),
            "nom": "Éric Neuhoff",
            "variantes": [],
        }

        response = client.post(
            "/api/critiques/merge",
            json={
                "source_id": OID_NEUHOFF,
                "target_id": OID_VIVIANT,
                "target_nom": "Éric Neuhoff",  # confirmation correcte
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["merged_avis"] == 18
        assert data["deleted_critique"] == OID_NEUHOFF

    def test_merge_wrong_confirmation_returns_400(self, client, mock_mongodb):
        """Merge avec mauvais nom de confirmation → 400."""
        mock_mongodb.critiques_collection.find_one.return_value = {
            "_id": ObjectId(OID_VIVIANT),
            "nom": "Éric Neuhoff",
            "variantes": [],
        }

        response = client.post(
            "/api/critiques/merge",
            json={
                "source_id": OID_NEUHOFF,
                "target_id": OID_VIVIANT,
                "target_nom": "Eric Neuhoff",  # mauvais nom : sans accent
            },
        )
        assert response.status_code == 400
        assert "confirmation" in response.json()["detail"].lower()

    def test_merge_source_not_found_returns_404(self, client, mock_mongodb):
        """Merge avec source inexistant → 404."""

        # find_one retourne None pour source, quelque chose pour target
        def find_one_side_effect(q):
            if q.get("_id") == ObjectId(OID_NEUHOFF):
                return None  # source inexistant
            return {
                "_id": ObjectId(OID_VIVIANT),
                "nom": "Éric Neuhoff",
                "variantes": [],
            }

        mock_mongodb.critiques_collection.find_one.side_effect = find_one_side_effect

        response = client.post(
            "/api/critiques/merge",
            json={
                "source_id": OID_NEUHOFF,
                "target_id": OID_VIVIANT,
                "target_nom": "Éric Neuhoff",
            },
        )
        assert response.status_code == 404

    def test_merge_target_not_found_returns_404(self, client, mock_mongodb):
        """Merge avec target inexistant → 404."""
        mock_mongodb.critiques_collection.find_one.return_value = None

        response = client.post(
            "/api/critiques/merge",
            json={
                "source_id": OID_NEUHOFF,
                "target_id": OID_VIVIANT,
                "target_nom": "Éric Neuhoff",
            },
        )
        assert response.status_code == 404

    def test_merge_same_ids_returns_400(self, client, mock_mongodb):
        """Merge d'un critique avec lui-même → 400."""
        response = client.post(
            "/api/critiques/merge",
            json={
                "source_id": OID_VIVIANT,
                "target_id": OID_VIVIANT,
                "target_nom": "Arnaud Viviant",
            },
        )
        assert response.status_code == 400

    def test_merge_calls_service_method(self, client, mock_mongodb):
        """L'endpoint appelle bien mongodb_service.merge_critiques."""
        mock_mongodb.critiques_collection.find_one.return_value = {
            "_id": ObjectId(OID_VIVIANT),
            "nom": "Éric Neuhoff",
            "variantes": [],
        }
        mock_mongodb.merge_critiques.return_value = {
            "merged_avis": 5,
            "deleted_critique": OID_NEUHOFF,
            "target_id": OID_VIVIANT,
        }

        client.post(
            "/api/critiques/merge",
            json={
                "source_id": OID_NEUHOFF,
                "target_id": OID_VIVIANT,
                "target_nom": "Éric Neuhoff",
            },
        )
        mock_mongodb.merge_critiques.assert_called_once_with(OID_NEUHOFF, OID_VIVIANT)


# ── mongodb_service.get_all_critiques (méthode unitaire) ─────────────────────


class TestMongoDBServiceGetAllCritiques:
    """Tests unitaires pour mongodb_service.get_all_critiques()."""

    def test_get_all_critiques_uses_aggregation(self):
        """get_all_critiques utilise un pipeline d'agrégation."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.critiques_collection = MagicMock()
        service.critiques_collection.aggregate.return_value = []

        result = service.get_all_critiques()

        assert result == []
        service.critiques_collection.aggregate.assert_called_once()

    def test_get_all_critiques_returns_nombre_avis_and_note_moyenne(self):
        """get_all_critiques inclut nombre_avis et note_moyenne depuis le pipeline."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.critiques_collection = MagicMock()
        service.critiques_collection.aggregate.return_value = [
            {
                "_id": ObjectId(OID_VIVIANT),
                "nom": "Arnaud Viviant",
                "animateur": False,
                "variantes": [],
                "nombre_avis": 706,
                "note_moyenne": 7.5,
            }
        ]

        result = service.get_all_critiques()
        assert len(result) == 1
        assert result[0]["nombre_avis"] == 706
        assert result[0]["note_moyenne"] == pytest.approx(7.5, abs=0.01)


# ── mongodb_service.merge_critiques (méthode unitaire) ───────────────────────


class TestMongoDBServiceMergeCritiques:
    """Tests unitaires pour mongodb_service.merge_critiques()."""

    def _make_service(self):
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService()
        service.critiques_collection = MagicMock()
        service.avis_collection = MagicMock()
        return service

    def test_merge_updates_avis_critique_oid(self):
        """merge_critiques repointe tous les avis.critique_oid de source vers target."""
        service = self._make_service()
        service.critiques_collection.find_one.side_effect = lambda q: {
            ObjectId(OID_NEUHOFF): {
                "_id": ObjectId(OID_NEUHOFF),
                "nom": "Eric Neuhoff",
                "variantes": ["E. Neuhoff"],
            },
            ObjectId(OID_VIVIANT): {
                "_id": ObjectId(OID_VIVIANT),
                "nom": "Éric Neuhoff",
                "variantes": [],
            },
        }.get(q.get("_id"))
        service.avis_collection.update_many.return_value = MagicMock(modified_count=18)
        service.critiques_collection.update_one.return_value = MagicMock()
        service.critiques_collection.delete_one.return_value = MagicMock()

        service.merge_critiques(OID_NEUHOFF, OID_VIVIANT)

        service.avis_collection.update_many.assert_called_once_with(
            {"critique_oid": OID_NEUHOFF},
            {"$set": {"critique_oid": OID_VIVIANT}},
        )

    def test_merge_deletes_source_critique(self):
        """merge_critiques supprime le critique source de la collection critiques."""
        service = self._make_service()
        service.critiques_collection.find_one.side_effect = lambda q: {
            ObjectId(OID_NEUHOFF): {
                "_id": ObjectId(OID_NEUHOFF),
                "nom": "Eric Neuhoff",
                "variantes": [],
            },
            ObjectId(OID_VIVIANT): {
                "_id": ObjectId(OID_VIVIANT),
                "nom": "Éric Neuhoff",
                "variantes": [],
            },
        }.get(q.get("_id"))
        service.avis_collection.update_many.return_value = MagicMock(modified_count=0)
        service.critiques_collection.update_one.return_value = MagicMock()
        service.critiques_collection.delete_one.return_value = MagicMock()

        service.merge_critiques(OID_NEUHOFF, OID_VIVIANT)

        service.critiques_collection.delete_one.assert_called_once_with(
            {"_id": ObjectId(OID_NEUHOFF)}
        )

    def test_merge_fusionne_variantes(self):
        """merge_critiques fusionne les variantes de source dans target (sans doublons)."""
        service = self._make_service()
        service.critiques_collection.find_one.side_effect = lambda q: {
            ObjectId(OID_NEUHOFF): {
                "_id": ObjectId(OID_NEUHOFF),
                "nom": "Eric Neuhoff",
                "variantes": ["E. Neuhoff", "Éric Neuhoff"],
            },
            ObjectId(OID_VIVIANT): {
                "_id": ObjectId(OID_VIVIANT),
                "nom": "Éric Neuhoff",
                "variantes": ["Eric Neuhoff"],
            },
        }.get(q.get("_id"))
        service.avis_collection.update_many.return_value = MagicMock(modified_count=0)
        service.critiques_collection.delete_one.return_value = MagicMock()

        service.merge_critiques(OID_NEUHOFF, OID_VIVIANT)

        # update_one appelé sur target pour fusionner les variantes
        service.critiques_collection.update_one.assert_called_once()
        call_args = service.critiques_collection.update_one.call_args
        # Vérifier que le filtre pointe sur target
        assert call_args[0][0] == {"_id": ObjectId(OID_VIVIANT)}
        # Vérifier que les variantes fusionnées incluent les deux sources sans doublons
        new_variantes = call_args[0][1]["$set"]["variantes"]
        assert "E. Neuhoff" in new_variantes
        assert "Eric Neuhoff" in new_variantes
        # "Éric Neuhoff" est le nom du target, on ne l'ajoute pas en variante
        assert len(new_variantes) == len(set(new_variantes))  # pas de doublons

    def test_merge_returns_summary(self):
        """merge_critiques retourne un dictionnaire résumé."""
        service = self._make_service()
        service.critiques_collection.find_one.side_effect = lambda q: {
            ObjectId(OID_NEUHOFF): {
                "_id": ObjectId(OID_NEUHOFF),
                "nom": "Eric Neuhoff",
                "variantes": [],
            },
            ObjectId(OID_VIVIANT): {
                "_id": ObjectId(OID_VIVIANT),
                "nom": "Éric Neuhoff",
                "variantes": [],
            },
        }.get(q.get("_id"))
        service.avis_collection.update_many.return_value = MagicMock(modified_count=18)
        service.critiques_collection.update_one.return_value = MagicMock()
        service.critiques_collection.delete_one.return_value = MagicMock()

        result = service.merge_critiques(OID_NEUHOFF, OID_VIVIANT)

        assert result["merged_avis"] == 18
        assert result["deleted_critique"] == OID_NEUHOFF
        assert result["target_id"] == OID_VIVIANT


# ── find_matching_critique retourne critique_id ───────────────────────────────


class TestCritiquesExtractionReturnsId:
    """find_matching_critique doit inclure l'id du critique matché."""

    def test_find_matching_returns_id_for_exact_match(self):
        """find_matching_critique retourne le champ 'id' pour un match exact."""
        from back_office_lmelp.services.critiques_extraction_service import (
            CritiquesExtractionService,
        )

        service = CritiquesExtractionService()
        critiques = [
            {
                "_id": ObjectId(OID_VIVIANT),
                "nom": "Arnaud Viviant",
                "variantes": [],
            }
        ]
        result = service.find_matching_critique("Arnaud Viviant", critiques)
        assert result is not None
        assert result["id"] == OID_VIVIANT

    def test_find_matching_returns_id_for_variante_match(self):
        """find_matching_critique retourne 'id' pour un match sur variante."""
        from back_office_lmelp.services.critiques_extraction_service import (
            CritiquesExtractionService,
        )

        service = CritiquesExtractionService()
        critiques = [
            {
                "_id": ObjectId(OID_NEUHOFF),
                "nom": "Éric Neuhoff",
                "variantes": ["Eric Neuhoff"],
            }
        ]
        result = service.find_matching_critique("Eric Neuhoff", critiques)
        assert result is not None
        assert result["id"] == OID_NEUHOFF
