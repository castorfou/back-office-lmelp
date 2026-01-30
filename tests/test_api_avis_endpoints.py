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
        auteur_id = ObjectId()

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
            "auteur_id": auteur_id,
        }
        self.mock_mongodb.livres_collection.count_documents.return_value = 1
        # Mock auteurs_collection pour l'enrichissement auteur_nom
        self.mock_mongodb.auteurs_collection = MagicMock()
        self.mock_mongodb.auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Auteur Test",
        }
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


class TestExtractAvisUsesCache:
    """Tests pour vérifier que /api/avis/extract utilise livresauteurs_cache (Issue #185)."""

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

    def test_extract_uses_livresauteurs_cache_not_direct_livres_query(self):
        """
        TDD RED: Vérifie que l'extraction utilise get_livres_from_collections
        (via livresauteurs_cache) au lieu de livres_collection.find direct.

        Scénario réel (26 octobre 2025):
        - "Le Fou de Dieu au bout du monde" est dans livresauteurs_cache avec status="mongo"
        - Mais son champ episodes[] ne contient pas cet épisode
        - Donc livres_collection.find({"episodes": episode_id}) ne le trouve pas
        - Mais get_livres_from_collections le trouve via le cache

        Ce test vérifie que le livre est trouvé et matché.
        """
        emission_id = ObjectId()
        episode_id = ObjectId()
        livre_id = ObjectId()
        auteur_id = ObjectId()

        # Mock des collections de base
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.emissions_collection = MagicMock()
        self.mock_mongodb.avis_critiques_collection = MagicMock()
        self.mock_mongodb.livres_collection = MagicMock()
        self.mock_mongodb.auteurs_collection = MagicMock()
        self.mock_mongodb.critiques_collection = MagicMock()

        # Mock de l'émission
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "episode_id": str(episode_id),
            "avis_critique_id": ObjectId(),
        }

        # Mock de l'avis_critique avec le livre "Le Fou de Dieu"
        self.mock_mongodb.avis_critiques_collection.find_one.return_value = {
            "_id": ObjectId(),
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME du test

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Javier Cercas | Le Fou de Dieu au bout du monde | Actes Sud | **Patricia Martin**: Magnifique. Note: 9 | 9 | 1 | | |
""",
        }

        # IMPORTANT: Le livre n'est PAS dans episodes[] direct
        # livres_collection.find({"episodes": str(episode_id)}) retourne []
        self.mock_mongodb.livres_collection.find.return_value = []

        # Mais le livre existe dans livres_collection avec un autre episode
        livre_data = {
            "_id": livre_id,
            "titre": "Le Fou de Dieu au bout du monde",
            "auteur_id": auteur_id,
            "editeur": "Actes Sud",
            "episodes": ["autre_episode_id"],  # Ne contient PAS l'episode actuel
        }

        # Mock de get_collection pour livresauteurs_cache
        mock_cache_collection = MagicMock()
        mock_cache_collection.find.return_value = [
            {
                "episode_oid": str(episode_id),
                "status": "mongo",
                "book_id": str(livre_id),
                "author_id": str(auteur_id),
            }
        ]

        def get_collection_side_effect(name):
            if name == "livresauteurs_cache":
                return mock_cache_collection
            return MagicMock()

        self.mock_mongodb.get_collection.side_effect = get_collection_side_effect

        # Mock livres_collection.find pour les requêtes par _id
        def livres_find_side_effect(query):
            if "_id" in query and "$in" in query["_id"]:
                return iter([livre_data])
            if "episodes" in query:
                return iter([])  # Pas trouvé par episodes direct
            return iter([])

        self.mock_mongodb.livres_collection.find.side_effect = livres_find_side_effect

        # Mock auteurs_collection
        self.mock_mongodb.auteurs_collection.find.return_value = iter(
            [{"_id": auteur_id, "nom": "Javier Cercas"}]
        )

        # Mock critiques (pas de match)
        self.mock_mongodb.critiques_collection.find.return_value = []

        # Mock delete et save
        self.mock_mongodb.delete_avis_by_emission.return_value = 0
        self.mock_mongodb.save_avis_batch.return_value = [str(ObjectId())]

        # Mock update_one pour l'ajout de l'episode
        self.mock_mongodb.livres_collection.update_one = MagicMock()

        response = self.client.post(f"/api/avis/extract/{str(emission_id)}")

        assert response.status_code == 200
        data = response.json()

        # Vérifier qu'on a bien extrait un avis
        assert data["extracted_count"] == 1

        # Le livre devrait avoir été matché (unresolved_livres = 0)
        assert data["unresolved_livres"] == 0, (
            "Le livre 'Le Fou de Dieu' devrait être matché via livresauteurs_cache"
        )

    def test_extract_adds_missing_episode_to_livre(self):
        """
        TDD RED: Vérifie que si un livre trouvé via le cache n'a pas
        l'episode_oid dans son champ episodes[], celui-ci est ajouté.

        Cela corrige la navigation future.
        """
        emission_id = ObjectId()
        episode_id = ObjectId()
        livre_id = ObjectId()
        auteur_id = ObjectId()

        # Mock des collections
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.emissions_collection = MagicMock()
        self.mock_mongodb.avis_critiques_collection = MagicMock()
        self.mock_mongodb.livres_collection = MagicMock()
        self.mock_mongodb.auteurs_collection = MagicMock()
        self.mock_mongodb.critiques_collection = MagicMock()

        # Mock de l'émission
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "episode_id": str(episode_id),
            "avis_critique_id": ObjectId(),
        }

        # Mock du summary
        self.mock_mongodb.avis_critiques_collection.find_one.return_value = {
            "_id": ObjectId(),
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Javier Cercas | Le Fou de Dieu | Actes Sud | **Patricia Martin**: Super. Note: 8 | 8 | 1 | | |
""",
        }

        # Livre sans l'episode_id actuel dans episodes[]
        livre_data = {
            "_id": livre_id,
            "titre": "Le Fou de Dieu",
            "auteur_id": auteur_id,
            "editeur": "Actes Sud",
            "episodes": ["ancien_episode"],  # Episode actuel manquant
        }

        # Mock cache
        mock_cache_collection = MagicMock()
        mock_cache_collection.find.return_value = [
            {
                "episode_oid": str(episode_id),
                "status": "mongo",
                "book_id": str(livre_id),
                "author_id": str(auteur_id),
            }
        ]

        def get_collection_side_effect(name):
            if name == "livresauteurs_cache":
                return mock_cache_collection
            return MagicMock()

        self.mock_mongodb.get_collection.side_effect = get_collection_side_effect

        # Mock livres_collection
        def livres_find_side_effect(query):
            if "_id" in query and "$in" in query["_id"]:
                return iter([livre_data])
            return iter([])

        self.mock_mongodb.livres_collection.find.side_effect = livres_find_side_effect

        # Mock auteurs
        self.mock_mongodb.auteurs_collection.find.return_value = iter(
            [{"_id": auteur_id, "nom": "Javier Cercas"}]
        )

        self.mock_mongodb.critiques_collection.find.return_value = []
        self.mock_mongodb.delete_avis_by_emission.return_value = 0
        self.mock_mongodb.save_avis_batch.return_value = [str(ObjectId())]

        # Mock update_one pour capturer l'appel
        self.mock_mongodb.livres_collection.update_one = MagicMock()

        response = self.client.post(f"/api/avis/extract/{str(emission_id)}")

        assert response.status_code == 200

        # Vérifier que update_one a été appelé pour ajouter l'episode_id
        self.mock_mongodb.livres_collection.update_one.assert_called()

        # Vérifier les arguments de l'appel
        call_args = self.mock_mongodb.livres_collection.update_one.call_args
        filter_arg = call_args[0][0]  # Premier argument positionnel
        update_arg = call_args[0][1]  # Deuxième argument positionnel

        # Le filtre doit cibler le livre par _id
        assert "_id" in filter_arg

        # L'update doit utiliser $addToSet pour ajouter l'episode
        assert "$addToSet" in update_arg
        assert "episodes" in update_arg["$addToSet"]
        assert update_arg["$addToSet"]["episodes"] == str(episode_id)

    @patch("back_office_lmelp.app.get_livres_from_collections")
    def test_extract_returns_unmatched_avis_list(self, mock_get_livres):
        """
        Test que /api/avis/extract retourne la liste des avis non matchés.

        Cas de test (Issue #185 - 14 septembre 2025):
        - Summary contient 10 livres (5 programme + 5 coups de cœur)
        - MongoDB contient 9 livres
        - 1 livre n'est pas matché: "Ça finit quand toujours" d'Agnès Gruda

        Expected: L'endpoint doit retourner ce livre dans `unmatched_avis`.
        """
        emission_id = ObjectId()
        episode_id = ObjectId()
        avis_critique_id = ObjectId()

        # Mock émission
        self.mock_mongodb.emissions_collection = MagicMock()
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "episode_id": str(episode_id),
            "avis_critique_id": str(avis_critique_id),
        }

        # Mock avis_critique avec summary contenant 10 livres (dont "Ça finit quand toujours")
        summary_with_10_books = """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur | Chef d'œuvre |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|-------------|
| Laurent Mauvignier | La Maison vide | Éditions de Minuit | **Elisabeth Philippe**: Sublime. Note: 10 | 10.0 | 1 | | |

## 2. COUPS DE CŒUR DES CRITIQUES

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Agnès Gruda | Ça finit quand toujours | Les Équateurs | Patricia Martin | 8.0 | Analyse forte de l'exil |
"""
        self.mock_mongodb.avis_critiques_collection = MagicMock()
        self.mock_mongodb.avis_critiques_collection.find_one.return_value = {
            "_id": avis_critique_id,
            "summary": summary_with_10_books,
        }

        # Mock livres: Seulement "La Maison vide", PAS "Ça finit quand toujours"
        livre_maison_vide_id = ObjectId()
        auteur_mauvignier_id = ObjectId()

        # Mock get_livres_from_collections pour retourner seulement "La Maison vide"
        async def mock_get_livres_async(episode_oid):
            return [
                {
                    "_id": str(livre_maison_vide_id),
                    "livre_id": str(livre_maison_vide_id),
                    "titre": "La Maison vide",
                    "auteur": "Laurent Mauvignier",
                    "auteur_id": str(auteur_mauvignier_id),
                    "editeur": "Éditions de Minuit",
                    "url_babelio": "https://www.babelio.com/...",
                }
            ]

        mock_get_livres.side_effect = mock_get_livres_async

        # Mock livres_collection pour update
        self.mock_mongodb.livres_collection = MagicMock()
        self.mock_mongodb.livres_collection.find_one.return_value = {
            "_id": livre_maison_vide_id,
            "titre": "La Maison vide",
            "auteur_id": auteur_mauvignier_id,
            "editeur": "Éditions de Minuit",
            "episodes": [str(episode_id)],
        }
        self.mock_mongodb.livres_collection.update_one = MagicMock()

        self.mock_mongodb.critiques_collection = MagicMock()
        self.mock_mongodb.critiques_collection.find.return_value = []
        self.mock_mongodb.delete_avis_by_emission.return_value = 0
        self.mock_mongodb.save_avis_batch.return_value = [str(ObjectId())]

        response = self.client.post(f"/api/avis/extract/{str(emission_id)}")

        assert response.status_code == 200
        data = response.json()

        # Vérifier que la réponse contient unmatched_avis
        assert "unmatched_avis" in data, "unmatched_avis manquant dans la réponse"

        # Vérifier que "Ça finit quand toujours" est dans la liste
        unmatched = data["unmatched_avis"]
        assert len(unmatched) == 1, f"Expected 1 unmatched, got {len(unmatched)}"

        # Vérifier le contenu du livre non matché
        gruda_avis = unmatched[0]
        assert gruda_avis["livre_titre_extrait"] == "Ça finit quand toujours"
        assert gruda_avis["auteur_nom_extrait"] == "Agnès Gruda"
        assert gruda_avis["editeur_extrait"] == "Les Équateurs"
        assert gruda_avis["livre_oid"] is None, "livre_oid devrait être None"


class TestMatchingStatsLivresMongo:
    """Tests pour vérifier que matching_stats.livres_mongo compte depuis collection livres.

    Issue #185: Le frontend affichait books.length (depuis le cache) au lieu de
    livres_mongo (depuis la collection livres), causant un affichage incohérent
    quand un livre est dans `livres` mais pas dans le cache.
    """

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

    def test_matching_stats_livres_mongo_counts_from_livres_collection(self):
        """
        TDD: Vérifie que matching_stats.livres_mongo compte les livres
        depuis la collection livres (pas le cache).

        Scénario réel (11 déc 2022):
        - 11 livres dans collection `livres` avec cet episode
        - 2 livres dans le summary (avis extraits)
        - Écart détecté : badge doit être rouge

        matching_stats.livres_mongo doit retourner 11 (pas le nombre du cache).
        """
        emission_id = str(ObjectId())
        episode_id = "678cceb8a414f2298877812f"

        # Setup minimal comme test_get_avis_returns_list
        self.mock_mongodb.avis_collection = MagicMock()
        self.mock_mongodb.livres_collection = MagicMock()
        self.mock_mongodb.critiques_collection = None
        self.mock_mongodb.emissions_collection = MagicMock()

        # Mock de l'émission (requis pour calculer livres_mongo)
        self.mock_mongodb.emissions_collection.find_one.return_value = {
            "_id": ObjectId(emission_id),
            "episode_id": episode_id,
        }

        # 2 avis extraits pour 2 livres summary
        self.mock_mongodb.get_avis_by_emission.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": emission_id,
                "livre_oid": None,
                "critique_oid": None,
                "commentaire": "Excellent",
                "note": 9,
                "section": "programme",
                "livre_titre_extrait": "Langages de vérité",
                "auteur_nom_extrait": "Salman Rushdie",
                "editeur_extrait": "Actes Sud",
                "critique_nom_extrait": "Patricia Martin",
                "match_phase": 1,
            },
            {
                "_id": ObjectId(),
                "emission_oid": emission_id,
                "livre_oid": None,
                "critique_oid": None,
                "commentaire": "Très bien",
                "note": 8,
                "section": "programme",
                "livre_titre_extrait": "La petite menteuse",
                "auteur_nom_extrait": "Pascale Robert-Diard",
                "editeur_extrait": "L'Iconoclaste",
                "critique_nom_extrait": "Arnaud Viviant",
                "match_phase": 1,
            },
        ]

        # IMPORTANT: 11 livres dans la collection livres (inclut "En salle")
        self.mock_mongodb.livres_collection.count_documents.return_value = 11

        response = self.client.get(f"/api/avis/by-emission/{emission_id}")

        assert response.status_code == 200
        data = response.json()

        # Vérifier que matching_stats existe
        assert "matching_stats" in data

        # ASSERTION CRITIQUE: livres_mongo doit être 11 (depuis collection livres)
        assert data["matching_stats"]["livres_mongo"] == 11, (
            f"livres_mongo devrait être 11 (depuis collection livres), "
            f"obtenu {data['matching_stats']['livres_mongo']}"
        )

        # livres_summary doit être 2 (titres uniques des avis)
        assert data["matching_stats"]["livres_summary"] == 2

        # Vérifier que count_documents a été appelé avec le bon episode_id
        self.mock_mongodb.livres_collection.count_documents.assert_called_once()
        call_args = self.mock_mongodb.livres_collection.count_documents.call_args[0][0]
        assert "episodes" in call_args
        assert call_args["episodes"] == episode_id
