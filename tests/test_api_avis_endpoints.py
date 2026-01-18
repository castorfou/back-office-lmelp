"""Tests pour les endpoints API de la collection avis."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient


class TestGetAvisByEmission:
    """Tests pour GET /api/avis/by-emission/{emission_id}."""

    def setup_method(self):
        """Setup pour chaque test."""
        # Patcher mongodb_service avant d'importer app
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()

        # Importer l'app après le patch
        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        """Teardown après chaque test."""
        self.patcher.stop()

    def test_get_avis_returns_list(self):
        """Test que GET retourne la liste des avis."""
        emission_id = str(ObjectId())
        avis_id = ObjectId()

        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.get_avis_by_emission.return_value = [
            {
                "_id": avis_id,
                "emission_oid": emission_id,
                "livre_oid": None,
                "critique_oid": None,
                "commentaire": "Très bon livre",
                "note": 9,
                "section": "programme",
                "livre_titre_extrait": "Mon Livre",
                "auteur_nom_extrait": "Auteur Test",
                "editeur_extrait": "Editeur Test",
                "critique_nom_extrait": "Critique Test",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
        ]
        self.mock_mongodb.livres_collection = None
        self.mock_mongodb.critiques_collection = None

        response = self.client.get(f"/api/avis/by-emission/{emission_id}")

        assert response.status_code == 200
        data = response.json()
        assert "avis" in data
        assert len(data["avis"]) == 1
        assert data["avis"][0]["note"] == 9
        assert data["avis"][0]["livre_titre_extrait"] == "Mon Livre"

    def test_get_avis_empty_list(self):
        """Test que GET retourne liste vide si pas d'avis."""
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.get_avis_by_emission.return_value = []
        # Mock nécessaire pour les stats de matching
        self.mock_mongodb.emissions_collection = MagicMock()
        self.mock_mongodb.emissions_collection.find_one.return_value = None
        self.mock_mongodb.livres_collection = None

        response = self.client.get(f"/api/avis/by-emission/{str(ObjectId())}")

        assert response.status_code == 200
        assert response.json()["avis"] == []

    def test_get_avis_enriches_livre_name(self):
        """Test que GET enrichit avec le nom du livre si résolu."""
        emission_id = str(ObjectId())
        livre_id = ObjectId()

        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.get_avis_by_emission.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": emission_id,
                "livre_oid": str(livre_id),
                "critique_oid": None,
                "commentaire": "Super",
                "note": 8,
                "section": "programme",
                "livre_titre_extrait": "Titre extrait",
                "auteur_nom_extrait": "",
                "editeur_extrait": "",
                "critique_nom_extrait": "",
            }
        ]
        self.mock_mongodb.livres_collection = MagicMock()
        self.mock_mongodb.livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "Titre Enrichi depuis MongoDB",
            "auteur_id": ObjectId(),
        }
        self.mock_mongodb.livres_collection.count_documents.return_value = 1
        self.mock_mongodb.critiques_collection = None
        # Mock nécessaire pour les stats de matching
        self.mock_mongodb.emissions_collection = MagicMock()
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": ObjectId(emission_id),
            "episode_id": "episode-123",
        }

        response = self.client.get(f"/api/avis/by-emission/{emission_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["avis"][0]["livre_titre"] == "Titre Enrichi depuis MongoDB"


class TestExtractAvisFromEmission:
    """Tests pour POST /api/avis/extract/{emission_id}."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()

        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        """Teardown après chaque test."""
        self.patcher.stop()

    def test_extract_returns_count(self):
        """Test que POST extract retourne le nombre d'avis extraits."""
        emission_id = ObjectId()

        # Mock des collections
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.emissions_collection = MagicMock()
        self.mock_mongodb.avis_critiques_collection = MagicMock()
        self.mock_mongodb.livres_collection = MagicMock()
        self.mock_mongodb.critiques_collection = MagicMock()

        # Mock de l'émission
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "episode_id": ObjectId(),
            "avis_critique_id": ObjectId(),
        }

        # Mock de l'avis_critique avec summary
        # Note: Les noms ne doivent pas contenir les mots du header (Auteur, Titre, etc.)
        # car le code les ignore pour distinguer headers et données
        self.mock_mongodb.avis_critiques_collection.find_one.return_value = {
            "_id": ObjectId(),
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME du test

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Rita Bullwinkel | Combats de filles | La Croisée | **Elisabeth Philippe**: Très bon livre. Note: 8 | 8 | 1 | | |

## 2. COUPS DE CŒUR DES CRITIQUES du test

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
""",
        }

        # Mock des livres et critiques (pas de match)
        self.mock_mongodb.livres_collection.find.return_value = []
        self.mock_mongodb.critiques_collection.find.return_value = []

        # Mock delete et save
        self.mock_mongodb.delete_avis_by_emission.return_value = 0
        self.mock_mongodb.save_avis_batch.return_value = [str(ObjectId())]

        response = self.client.post(f"/api/avis/extract/{str(emission_id)}")

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_count"] == 1
        assert "message" in data

    def test_extract_emission_not_found(self):
        """Test que POST retourne 404 si émission non trouvée."""
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.emissions_collection = MagicMock()
        self.mock_mongodb.avis_critiques_collection = MagicMock()
        self.mock_mongodb.emissions_collection.find_one.return_value = None

        response = self.client.post(f"/api/avis/extract/{str(ObjectId())}")

        assert response.status_code == 404
        assert "non trouvée" in response.json()["detail"]

    def test_extract_no_summary(self):
        """Test que POST retourne 400 si pas de summary."""
        emission_id = ObjectId()

        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.emissions_collection = MagicMock()
        self.mock_mongodb.avis_critiques_collection = MagicMock()

        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "avis_critique_id": ObjectId(),
        }
        self.mock_mongodb.avis_critiques_collection.find_one.return_value = {
            "_id": ObjectId(),
            "summary": "",  # Pas de summary
        }

        response = self.client.post(f"/api/avis/extract/{str(emission_id)}")

        assert response.status_code == 400
        assert "summary" in response.json()["detail"].lower()


class TestUpdateAvis:
    """Tests pour PUT /api/avis/{avis_id}."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()

        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        """Teardown après chaque test."""
        self.patcher.stop()

    def test_update_avis_success(self):
        """Test que PUT met à jour l'avis."""
        avis_id = str(ObjectId())

        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.update_avis.return_value = True

        response = self.client.put(
            f"/api/avis/{avis_id}",
            json={"livre_oid": "new_livre_id", "note": 10},
        )

        assert response.status_code == 200
        assert "succès" in response.json()["message"]
        self.mock_mongodb.update_avis.assert_called_once()

    def test_update_avis_not_found(self):
        """Test que PUT retourne 404 si avis non trouvé."""
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.update_avis.return_value = False

        response = self.client.put(f"/api/avis/{str(ObjectId())}", json={"note": 10})

        assert response.status_code == 404

    def test_update_avis_no_valid_fields(self):
        """Test que PUT retourne 400 si aucun champ valide."""
        self.mock_mongodb.avis_collection = MagicMock()

        response = self.client.put(
            f"/api/avis/{str(ObjectId())}",
            json={"invalid_field": "value"},
        )

        assert response.status_code == 400

    def test_update_avis_filters_fields(self):
        """Test que seuls les champs autorisés sont mis à jour."""
        avis_id = str(ObjectId())

        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.update_avis.return_value = True

        response = self.client.put(
            f"/api/avis/{avis_id}",
            json={
                "note": 9,
                "livre_oid": "livre_123",
                "emission_oid": "should_not_update",  # Non autorisé
                "_id": "should_not_update",  # Non autorisé
            },
        )

        assert response.status_code == 200
        # Vérifier que seuls note et livre_oid sont passés
        call_args = self.mock_mongodb.update_avis.call_args[0][1]
        assert "note" in call_args
        assert "livre_oid" in call_args
        assert "emission_oid" not in call_args
        assert "_id" not in call_args


class TestDeleteAvis:
    """Tests pour DELETE /api/avis/{avis_id}."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()

        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        """Teardown après chaque test."""
        self.patcher.stop()

    def test_delete_avis_success(self):
        """Test que DELETE supprime l'avis."""
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.delete_avis.return_value = True

        response = self.client.delete(f"/api/avis/{str(ObjectId())}")

        assert response.status_code == 200
        assert "supprimé" in response.json()["message"]

    def test_delete_avis_not_found(self):
        """Test que DELETE retourne 404 si avis non trouvé."""
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.delete_avis.return_value = False

        response = self.client.delete(f"/api/avis/{str(ObjectId())}")

        assert response.status_code == 404


class TestGetAvisStats:
    """Tests pour GET /api/stats/avis."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()

        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        """Teardown après chaque test."""
        self.patcher.stop()

    def test_get_stats_returns_all_fields(self):
        """Test que GET stats retourne tous les champs."""
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.emissions_collection = MagicMock()
        self.mock_mongodb.get_avis_stats.return_value = {
            "total": 100,
            "unresolved_livre": 10,
            "unresolved_critique": 5,
            "missing_note": 2,
            "emissions_with_avis": 20,
        }
        self.mock_mongodb.emissions_collection.count_documents.return_value = 50

        response = self.client.get("/api/stats/avis")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 100
        assert data["unresolved_livre"] == 10
        assert data["unresolved_critique"] == 5
        assert data["missing_note"] == 2
        assert data["emissions_with_avis"] == 20
        assert data["emissions_total"] == 50
        assert data["emissions_without_avis"] == 30


class TestGetAvisByCritique:
    """Tests pour GET /api/avis/by-critique/{critique_id}."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()

        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        """Teardown après chaque test."""
        self.patcher.stop()

    def test_get_avis_by_critique_returns_list(self):
        """Test que GET retourne la liste des avis du critique."""
        critique_id = str(ObjectId())

        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.get_avis_by_critique.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": "em1",
                "livre_oid": "livre1",
                "livre_titre_extrait": "Livre Test",
                "commentaire": "Super",
                "note": 9,
                "section": "programme",
            }
        ]

        response = self.client.get(f"/api/avis/by-critique/{critique_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["avis"]) == 1
        assert data["avis"][0]["note"] == 9


class TestGetAvisByLivre:
    """Tests pour GET /api/avis/by-livre/{livre_id}."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.mock_mongodb = MagicMock()
        self.patcher = patch("back_office_lmelp.app.mongodb_service", self.mock_mongodb)
        self.patcher.start()

        from back_office_lmelp.app import app

        self.client = TestClient(app)

    def teardown_method(self):
        """Teardown après chaque test."""
        self.patcher.stop()

    def test_get_avis_by_livre_returns_list(self):
        """Test que GET retourne la liste des avis du livre."""
        livre_id = str(ObjectId())

        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.get_avis_by_livre.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": "em1",
                "critique_oid": "critique1",
                "critique_nom_extrait": "Critique Test",
                "commentaire": "Excellent",
                "note": 10,
                "section": "coup_de_coeur",
            }
        ]

        response = self.client.get(f"/api/avis/by-livre/{livre_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["avis"]) == 1
        assert data["avis"][0]["note"] == 10
        assert data["avis"][0]["section"] == "coup_de_coeur"
