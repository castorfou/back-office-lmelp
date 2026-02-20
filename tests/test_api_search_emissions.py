"""Tests TDD pour l'intégration des émissions dans la recherche (Issue #219).

Tests couvrant :
1. search_emissions() dans mongodb_service
2. /api/search retourne les émissions
3. /api/search retourne emission_date pour les épisodes
4. /api/advanced-search supporte le filtre 'emissions'
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.services.mongodb_service import MongoDBService


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_memory_guard():
    """Mock memory guard for testing."""
    with patch("back_office_lmelp.app.memory_guard") as mock:
        mock.check_memory_limit.return_value = None
        yield mock


# ===========================================================================
# Tests pour mongodb_service.search_emissions()
# ===========================================================================


class TestSearchEmissionsService:
    """Tests pour la méthode search_emissions() du MongoDBService."""

    def test_search_emissions_returns_correct_structure(self):
        """search_emissions() retourne {emissions: [...], total_count: int}."""
        service = MongoDBService.__new__(MongoDBService)

        # Mocks des collections
        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        emission_date = datetime(2025, 7, 6)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        # Un avis correspondant à la recherche "Camus"
        mock_avis_collection.find.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "La Peste",
                "auteur_nom_extrait": "Albert Camus",
                "editeur_extrait": "Gallimard",
                "section": "programme",
            }
        ]
        mock_avis_collection.count_documents.return_value = 1

        # L'émission correspondante (find().sort() chain)
        mock_emissions_collection.find.return_value.sort.return_value = [
            {
                "_id": emission_id,
                "date": emission_date,
            }
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection

        result = service.search_emissions("Camus")

        assert "emissions" in result
        assert "total_count" in result
        assert isinstance(result["emissions"], list)
        assert isinstance(result["total_count"], int)

    def test_search_emissions_result_has_required_fields(self):
        """Chaque résultat d'émission a _id, emission_date, search_context."""
        service = MongoDBService.__new__(MongoDBService)

        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        emission_date = datetime(2025, 7, 6)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        mock_avis_collection.find.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "La Peste",
                "auteur_nom_extrait": "Albert Camus",
                "editeur_extrait": "Gallimard",
                "section": "programme",
            }
        ]
        mock_avis_collection.count_documents.return_value = 1

        # find().sort() chain
        mock_emissions_collection.find.return_value.sort.return_value = [
            {
                "_id": emission_id,
                "date": emission_date,
            }
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection

        result = service.search_emissions("Camus")

        assert len(result["emissions"]) == 1
        emission = result["emissions"][0]
        assert "_id" in emission
        assert "emission_date" in emission
        assert "search_context" in emission

    def test_search_emissions_emission_date_format(self):
        """emission_date est au format YYYYMMDD (pour URL /emissions/YYYYMMDD)."""
        service = MongoDBService.__new__(MongoDBService)

        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        emission_date = datetime(2025, 7, 6)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        mock_avis_collection.find.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "La Peste",
                "auteur_nom_extrait": "Albert Camus",
                "editeur_extrait": "Gallimard",
                "section": "programme",
            }
        ]
        mock_avis_collection.count_documents.return_value = 1

        # find().sort() chain
        mock_emissions_collection.find.return_value.sort.return_value = [
            {
                "_id": emission_id,
                "date": emission_date,
            }
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection

        result = service.search_emissions("Camus")
        emission = result["emissions"][0]

        assert emission["emission_date"] == "20250706"

    def test_search_emissions_deduplicates_by_emission(self):
        """Plusieurs avis pour la même émission → un seul résultat d'émission."""
        service = MongoDBService.__new__(MongoDBService)

        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        emission_date = datetime(2025, 7, 6)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        # Deux avis pour la même émission (même emission_oid)
        mock_avis_collection.find.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "La Peste",
                "auteur_nom_extrait": "Albert Camus",
                "editeur_extrait": "Gallimard",
                "section": "programme",
            },
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "L'Étranger",
                "auteur_nom_extrait": "Albert Camus",
                "editeur_extrait": "Gallimard",
                "section": "coup_de_coeur",
            },
        ]
        mock_avis_collection.count_documents.return_value = 2

        # find().sort() chain
        mock_emissions_collection.find.return_value.sort.return_value = [
            {
                "_id": emission_id,
                "date": emission_date,
            }
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection

        result = service.search_emissions("Camus")

        # Deux avis mais UN seul résultat d'émission
        assert len(result["emissions"]) == 1

    def test_search_emissions_searches_in_commentaire(self):
        """search_emissions() trouve les émissions via le texte du commentaire critique."""
        service = MongoDBService.__new__(MongoDBService)

        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        emission_date = datetime(2026, 2, 13)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        # L'avis contient "Roman qui donne envie" dans commentaire,
        # pas dans livre_titre_extrait / auteur_nom_extrait / editeur_extrait
        mock_avis_collection.find.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "Départ",
                "auteur_nom_extrait": "Julian Barnes",
                "editeur_extrait": "Stock",
                "commentaire": "Roman qui donne envie d'aimer la vie, grande complicité avec le lecteur",
                "section": "programme",
            }
        ]
        mock_avis_collection.count_documents.return_value = 1

        mock_emissions_collection.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection

        result = service.search_emissions("Roman qui donne envie")

        assert len(result["emissions"]) == 1, (
            "La recherche dans le commentaire doit trouver l'émission"
        )

        # Vérifier que la query MongoDB contient bien le champ commentaire
        call_args = mock_avis_collection.find.call_args
        assert call_args is not None
        query = call_args[0][0]
        or_clauses = query.get("$or", [])
        searched_fields = [list(clause.keys())[0] for clause in or_clauses]
        assert "commentaire" in searched_fields, (
            f"Le champ 'commentaire' doit être dans la recherche $or, fields trouvés: {searched_fields}"
        )

    def test_search_emissions_context_shows_commentaire_when_match_in_commentaire(self):
        """Quand la recherche matche dans commentaire, search_context inclut l'extrait du commentaire."""
        service = MongoDBService.__new__(MongoDBService)

        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        emission_date = datetime(2026, 2, 13)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        # La query matche SEULEMENT dans le commentaire, pas dans titre/auteur/éditeur
        mock_avis_collection.find.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "Départ",
                "auteur_nom_extrait": "Julian Barnes",
                "editeur_extrait": "Stock",
                "commentaire": "Roman qui donne envie d'aimer la vie, grande complicité avec le lecteur",
                "section": "programme",
            }
        ]
        mock_avis_collection.count_documents.return_value = 1

        mock_emissions_collection.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection

        result = service.search_emissions("Roman qui donne envie")

        emission = result["emissions"][0]
        search_context = emission["search_context"]

        # Le contexte doit contenir livre/auteur ET l'extrait du commentaire
        assert "Julian Barnes" in search_context, (
            f"Le search_context doit contenir l'auteur pour le contexte, got: '{search_context}'"
        )
        assert "Départ" in search_context, (
            f"Le search_context doit contenir le titre pour le contexte, got: '{search_context}'"
        )
        assert "Roman qui donne envie" in search_context, (
            f"Le search_context doit contenir l'extrait du commentaire, got: '{search_context}'"
        )

    def test_search_emissions_empty_result_when_no_match(self):
        """search_emissions() retourne liste vide si aucun résultat."""
        service = MongoDBService.__new__(MongoDBService)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        mock_avis_collection.find.return_value = []
        mock_avis_collection.count_documents.return_value = 0

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection

        result = service.search_emissions("terme_inexistant_xyz")

        assert result["emissions"] == []
        assert result["total_count"] == 0

    def test_search_emissions_uses_objectid_conversion(self):
        """La jointure utilise ObjectId() pour convertir emission_oid (String → ObjectId)."""
        service = MongoDBService.__new__(MongoDBService)

        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        emission_date = datetime(2025, 7, 6)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        mock_avis_collection.find.return_value = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),  # String!
                "livre_titre_extrait": "La Peste",
                "auteur_nom_extrait": "Albert Camus",
                "editeur_extrait": "Gallimard",
                "section": "programme",
            }
        ]
        mock_avis_collection.count_documents.return_value = 1

        # find().sort() chain
        mock_emissions_collection.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection

        service.search_emissions("Camus")

        # Vérifier que find() a été appelé avec ObjectId (pas String)
        call_args = mock_emissions_collection.find.call_args
        assert call_args is not None
        query = call_args[0][0]
        ids_list = query["_id"]["$in"]
        assert all(isinstance(oid, ObjectId) for oid in ids_list), (
            "Les IDs doivent être des ObjectId, pas des strings"
        )


# ===========================================================================
# Tests pour search_episodes() enrichi avec emission_date
# ===========================================================================


class TestSearchEpisodesWithEmissionDate:
    """Tests pour l'enrichissement de search_episodes() avec emission_date."""

    def test_search_episodes_has_emission_date_field(self):
        """Chaque épisode dans les résultats a un champ emission_date."""
        service = MongoDBService.__new__(MongoDBService)

        episode_id = ObjectId("507f1f77bcf86cd799439011")
        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        emission_date = datetime(2025, 7, 6)

        mock_episodes_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        mock_episodes_collection.count_documents.return_value = 1
        mock_episodes_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = [
            {
                "_id": episode_id,
                "titre": "Émission du 6 juillet",
                "date": datetime(2025, 7, 6),
                "transcription": "Albert Camus La Peste",
            }
        ]

        # L'émission correspondante
        mock_emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "date": emission_date,
            "episode_id": episode_id,
        }

        service.episodes_collection = mock_episodes_collection
        service.emissions_collection = mock_emissions_collection

        result = service.search_episodes("Camus")

        assert len(result["episodes"]) == 1
        episode = result["episodes"][0]
        assert "emission_date" in episode

    def test_search_episodes_emission_date_format_yyyymmdd(self):
        """emission_date dans les épisodes est au format YYYYMMDD."""
        service = MongoDBService.__new__(MongoDBService)

        episode_id = ObjectId("507f1f77bcf86cd799439011")
        emission_id = ObjectId("694fea90e46eedc769bcd96c")

        mock_episodes_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        mock_episodes_collection.count_documents.return_value = 1
        mock_episodes_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = [
            {
                "_id": episode_id,
                "titre": "Émission du 31 décembre 2025",
                "date": datetime(2025, 12, 31),
                "transcription": "test",
            }
        ]

        mock_emissions_collection.find_one.return_value = {
            "_id": emission_id,
            "date": datetime(2025, 12, 31),
            "episode_id": episode_id,
        }

        service.episodes_collection = mock_episodes_collection
        service.emissions_collection = mock_emissions_collection

        result = service.search_episodes("test")

        episode = result["episodes"][0]
        assert episode["emission_date"] == "20251231"

    def test_search_episodes_emission_date_none_when_no_emission(self):
        """emission_date est None si aucune émission correspondante."""
        service = MongoDBService.__new__(MongoDBService)

        episode_id = ObjectId("507f1f77bcf86cd799439011")

        mock_episodes_collection = MagicMock()
        mock_emissions_collection = MagicMock()

        mock_episodes_collection.count_documents.return_value = 1
        mock_episodes_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = [
            {
                "_id": episode_id,
                "titre": "Episode sans émission",
                "date": datetime(2025, 1, 1),
                "transcription": "test",
            }
        ]

        # Pas d'émission correspondante
        mock_emissions_collection.find_one.return_value = None

        service.episodes_collection = mock_episodes_collection
        service.emissions_collection = mock_emissions_collection

        result = service.search_episodes("test")

        episode = result["episodes"][0]
        assert episode["emission_date"] is None


# ===========================================================================
# Tests pour /api/search avec émissions
# ===========================================================================


class TestSearchAPIWithEmissions:
    """Tests pour l'endpoint /api/search incluant les émissions."""

    def test_search_returns_emissions_key(self, client, mock_memory_guard):
        """GET /api/search?q=... retourne results.emissions."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.search_episodes.return_value = {
                "episodes": [],
                "total_count": 0,
            }
            mock_service.search_auteurs.return_value = {
                "auteurs": [],
                "total_count": 0,
            }
            mock_service.search_livres.return_value = {
                "livres": [],
                "total_count": 0,
            }
            mock_service.search_editeurs.return_value = {
                "editeurs": [],
                "total_count": 0,
            }
            mock_service.search_emissions.return_value = {
                "emissions": [],
                "total_count": 0,
            }

            response = client.get("/api/search?q=Camus")

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "emissions" in data["results"], (
                "La clé 'emissions' doit être présente dans results"
            )

    def test_search_returns_emission_results(self, client, mock_memory_guard):
        """GET /api/search?q=... retourne les résultats d'émissions avec emission_date."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.search_episodes.return_value = {
                "episodes": [],
                "total_count": 0,
            }
            mock_service.search_auteurs.return_value = {
                "auteurs": [],
                "total_count": 0,
            }
            mock_service.search_livres.return_value = {
                "livres": [],
                "total_count": 0,
            }
            mock_service.search_editeurs.return_value = {
                "editeurs": [],
                "total_count": 0,
            }
            mock_service.search_emissions.return_value = {
                "emissions": [
                    {
                        "_id": "694fea90e46eedc769bcd96c",
                        "emission_date": "20250706",
                        "search_context": "Albert Camus - La Peste",
                    }
                ],
                "total_count": 1,
            }

            response = client.get("/api/search?q=Camus")

            assert response.status_code == 200
            data = response.json()
            emissions = data["results"]["emissions"]
            assert len(emissions) == 1
            assert emissions[0]["emission_date"] == "20250706"
            assert "search_context" in emissions[0]

    def test_search_episodes_include_emission_date(self, client, mock_memory_guard):
        """GET /api/search?q=... : les épisodes ont emission_date."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.search_episodes.return_value = {
                "episodes": [
                    {
                        "_id": "507f1f77bcf86cd799439011",
                        "titre": "Émission du 31 déc",
                        "date": "2025-12-31T00:00:00",
                        "score": 1.0,
                        "match_type": "found",
                        "search_context": "Camus dans la transcription",
                        "emission_date": "20251231",
                    }
                ],
                "total_count": 1,
            }
            mock_service.search_auteurs.return_value = {
                "auteurs": [],
                "total_count": 0,
            }
            mock_service.search_livres.return_value = {
                "livres": [],
                "total_count": 0,
            }
            mock_service.search_editeurs.return_value = {
                "editeurs": [],
                "total_count": 0,
            }
            mock_service.search_emissions.return_value = {
                "emissions": [],
                "total_count": 0,
            }

            response = client.get("/api/search?q=Camus")

            assert response.status_code == 200
            data = response.json()
            episodes = data["results"]["episodes"]
            assert len(episodes) == 1
            assert "emission_date" in episodes[0]
            assert episodes[0]["emission_date"] == "20251231"


# ===========================================================================
# Tests pour /api/advanced-search avec filtre emissions
# ===========================================================================


class TestAdvancedSearchWithEmissions:
    """Tests pour l'endpoint /api/advanced-search avec le filtre emissions."""

    def test_advanced_search_accepts_emissions_entity(self, client, mock_memory_guard):
        """GET /api/advanced-search?q=...&entities=emissions ne retourne pas 400."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.search_emissions.return_value = {
                "emissions": [],
                "total_count": 0,
            }

            response = client.get("/api/advanced-search?q=Camus&entities=emissions")

            assert response.status_code == 200, (
                f"Le filtre 'emissions' doit être valide, got {response.status_code}: {response.text}"
            )

    def test_advanced_search_returns_emissions_in_results(
        self, client, mock_memory_guard
    ):
        """GET /api/advanced-search?q=...&entities=emissions retourne results.emissions."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.search_emissions.return_value = {
                "emissions": [
                    {
                        "_id": "694fea90e46eedc769bcd96c",
                        "emission_date": "20250706",
                        "search_context": "Albert Camus - La Peste",
                    }
                ],
                "total_count": 1,
            }

            response = client.get("/api/advanced-search?q=Camus&entities=emissions")

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "emissions" in data["results"]
            assert len(data["results"]["emissions"]) == 1

    def test_advanced_search_emissions_in_default_search(
        self, client, mock_memory_guard
    ):
        """GET /api/advanced-search?q=... (sans filtre) inclut les émissions par défaut."""
        with patch("back_office_lmelp.app.mongodb_service") as mock_service:
            mock_service.search_episodes.return_value = {
                "episodes": [],
                "total_count": 0,
            }
            mock_service.search_auteurs.return_value = {
                "auteurs": [],
                "total_count": 0,
            }
            mock_service.search_livres.return_value = {
                "livres": [],
                "total_count": 0,
            }
            mock_service.search_editeurs.return_value = {
                "editeurs": [],
                "total_count": 0,
            }
            mock_service.search_emissions.return_value = {
                "emissions": [],
                "total_count": 0,
            }

            response = client.get("/api/advanced-search?q=Camus")

            assert response.status_code == 200
            data = response.json()
            assert "emissions" in data["results"], (
                "Par défaut (sans filtre), 'emissions' doit être dans les résultats"
            )
