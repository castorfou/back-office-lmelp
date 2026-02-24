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
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        avis_doc = {
            "_id": ObjectId(),
            "emission_oid": str(emission_id),
            "commentaire": "Albert Camus La Peste",
            "section": "programme",
        }

        # Pass 1 (commentaire search): returns avis
        # Pass 2 (livre_oid search): empty (no livres matched)
        def avis_find_side_effect(query, *args, **kwargs):
            if "commentaire" in query:
                return [avis_doc]
            return []

        mock_avis_collection.find.side_effect = avis_find_side_effect
        mock_livres_collection.find.return_value = []
        mock_auteurs_collection.find.return_value = []

        mock_emissions_collection.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection
        service.livres_collection = mock_livres_collection
        service.auteurs_collection = mock_auteurs_collection

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
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        avis_doc = {
            "_id": ObjectId(),
            "emission_oid": str(emission_id),
            "commentaire": "Albert Camus La Peste",
            "section": "programme",
        }

        def avis_find_side_effect(query, *args, **kwargs):
            if "commentaire" in query:
                return [avis_doc]
            return []

        mock_avis_collection.find.side_effect = avis_find_side_effect
        mock_livres_collection.find.return_value = []
        mock_auteurs_collection.find.return_value = []

        mock_emissions_collection.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection
        service.livres_collection = mock_livres_collection
        service.auteurs_collection = mock_auteurs_collection

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
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        # Deux avis pour la même émission matchant via commentaire
        avis_docs = [
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "commentaire": "Albert Camus La Peste",
                "section": "programme",
            },
            {
                "_id": ObjectId(),
                "emission_oid": str(emission_id),
                "commentaire": "Albert Camus L'Étranger",
                "section": "coup_de_coeur",
            },
        ]

        def avis_find_side_effect(query, *args, **kwargs):
            if "commentaire" in query:
                return avis_docs
            return []

        mock_avis_collection.find.side_effect = avis_find_side_effect
        mock_livres_collection.find.return_value = []
        mock_auteurs_collection.find.return_value = []

        mock_emissions_collection.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection
        service.livres_collection = mock_livres_collection
        service.auteurs_collection = mock_auteurs_collection

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
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        avis_doc = {
            "_id": ObjectId(),
            "emission_oid": str(emission_id),
            "livre_titre_extrait": "Départ",
            "auteur_nom_extrait": "Julian Barnes",
            "editeur_extrait": "Stock",
            "commentaire": "Roman qui donne envie d'aimer la vie, grande complicité avec le lecteur",
            "section": "programme",
        }

        # commentaire search: returns avis; livre_oid search: empty
        def avis_find_side_effect(query, *args, **kwargs):
            if "commentaire" in query:
                return [avis_doc]
            return []

        mock_avis_collection.find.side_effect = avis_find_side_effect
        mock_livres_collection.find.return_value = []
        mock_auteurs_collection.find.return_value = []

        mock_emissions_collection.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection
        service.livres_collection = mock_livres_collection
        service.auteurs_collection = mock_auteurs_collection

        result = service.search_emissions("Roman qui donne envie")

        assert len(result["emissions"]) == 1, (
            "La recherche dans le commentaire doit trouver l'émission"
        )

        # Vérifier que la 1ère query avis.find contient bien le champ commentaire
        first_call_args = mock_avis_collection.find.call_args_list[0]
        query = first_call_args[0][0]
        assert "commentaire" in query, (
            f"Le 1er appel à avis.find() doit chercher dans 'commentaire'. Query: {query}"
        )

    def test_search_emissions_context_shows_commentaire_when_match_in_commentaire(self):
        """Quand la recherche matche dans commentaire, search_context inclut l'extrait du commentaire."""
        service = MongoDBService.__new__(MongoDBService)

        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        livre_id = ObjectId("6994e74f95e08117826da195")
        emission_date = datetime(2026, 2, 13)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        avis_doc = {
            "_id": ObjectId(),
            "emission_oid": str(emission_id),
            "livre_oid": str(livre_id),
            "livre_titre_extrait": "Départ",
            "auteur_nom_extrait": "Julian Barnes",
            "editeur_extrait": "Stock",
            "commentaire": "Roman qui donne envie d'aimer la vie, grande complicité avec le lecteur",
            "section": "programme",
        }

        def avis_find_side_effect(query, *args, **kwargs):
            if "commentaire" in query:
                return [avis_doc]
            return []

        mock_avis_collection.find.side_effect = avis_find_side_effect
        mock_livres_collection.find.return_value = []
        mock_auteurs_collection.find.return_value = []

        mock_emissions_collection.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection
        service.livres_collection = mock_livres_collection
        service.auteurs_collection = mock_auteurs_collection

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

    def test_search_emissions_uses_real_title_from_livres_collection(self):
        """search_emissions() utilise le vrai titre depuis livres pour le search_context."""
        service = MongoDBService.__new__(MongoDBService)

        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        livre_id = ObjectId("6994e74f95e08117826da195")
        emission_date = datetime(2026, 2, 13)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        # avis.livre_titre_extrait est tronqué ("Départ") mais le vrai titre est "Départ(s)"
        avis_doc = {
            "_id": ObjectId(),
            "emission_oid": str(emission_id),
            "livre_oid": str(livre_id),
            "livre_titre_extrait": "Départ",  # tronqué !
            "auteur_nom_extrait": "Julian Barnes",
            "editeur_extrait": "Stock",
            "commentaire": "Roman qui donne envie d'aimer la vie",
            "section": "programme",
        }

        livre_doc = {"_id": livre_id, "titre": "Départ(s)", "editeur": "Stock"}

        # Pass 2: livres trouve "Départ(s)" matching "Départ"
        def livres_find_side_effect(query, *args, **kwargs):
            if "$or" in query:
                return [livre_doc]
            # lookup by _id for context enrichment
            return [livre_doc]

        def avis_find_side_effect(query, *args, **kwargs):
            if "livre_oid" in query:
                return [avis_doc]
            return []

        mock_livres_collection.find.side_effect = livres_find_side_effect
        mock_avis_collection.find.side_effect = avis_find_side_effect
        mock_auteurs_collection.find.return_value = []

        mock_emissions_collection.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection
        service.livres_collection = mock_livres_collection
        service.auteurs_collection = mock_auteurs_collection

        result = service.search_emissions("Départ")

        emission = result["emissions"][0]
        search_context = emission["search_context"]

        assert "Départ(s)" in search_context, (
            f"Le titre doit venir de livres.titre ('Départ(s)'), got: '{search_context}'"
        )

    def test_search_emissions_empty_result_when_no_match(self):
        """search_emissions() retourne liste vide si aucun résultat."""
        service = MongoDBService.__new__(MongoDBService)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        mock_avis_collection.find.return_value = []
        mock_livres_collection.find.return_value = []
        mock_auteurs_collection.find.return_value = []

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection
        service.livres_collection = mock_livres_collection
        service.auteurs_collection = mock_auteurs_collection

        result = service.search_emissions("terme_inexistant_xyz")

        assert result["emissions"] == []
        assert result["total_count"] == 0

    def test_search_emissions_uses_objectid_conversion(self):
        """La jointure émissions utilise ObjectId() pour convertir emission_oid (String → ObjectId)."""
        service = MongoDBService.__new__(MongoDBService)

        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        emission_date = datetime(2025, 7, 6)

        mock_avis_collection = MagicMock()
        mock_emissions_collection = MagicMock()
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        avis_doc = {
            "_id": ObjectId(),
            "emission_oid": str(emission_id),  # String!
            "commentaire": "Albert Camus La Peste",
            "section": "programme",
        }

        def avis_find_side_effect(query, *args, **kwargs):
            if "commentaire" in query:
                return [avis_doc]
            return []

        mock_avis_collection.find.side_effect = avis_find_side_effect
        mock_livres_collection.find.return_value = []
        mock_auteurs_collection.find.return_value = []

        mock_emissions_collection.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis_collection
        service.emissions_collection = mock_emissions_collection
        service.livres_collection = mock_livres_collection
        service.auteurs_collection = mock_auteurs_collection

        service.search_emissions("Camus")

        # Vérifier que emissions.find() a été appelé avec ObjectId (pas String)
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


# ===========================================================================
# Tests TDD pour la recherche via sources canoniques (Issue #224)
# ===========================================================================


class TestSearchEmissionsCanonicalSources:
    """Tests pour la recherche via sources canoniques (livres.titre, auteurs.nom).

    Issue #224 : Searching "Quatre jours" didn't find the emission because
    search_emissions() was querying avis.livre_titre_extrait (LLM-extracted,
    non-canonical) instead of livres.titre (Babelio, canonical).

    Fix: Use canonical sources for search:
    - livres.titre (not avis.livre_titre_extrait)
    - livres.editeur (not avis.editeur_extrait)
    - auteurs.nom (not avis.auteur_nom_extrait)
    - avis.commentaire (unchanged, already canonical)
    """

    def _make_service_with_mocks(
        self,
        avis_docs=None,
        livres_docs=None,
        auteurs_docs=None,
        emission_date=None,
        emission_id=None,
    ):
        """Helper to build a MongoDBService with all collections mocked."""
        service = MongoDBService.__new__(MongoDBService)

        if emission_id is None:
            emission_id = ObjectId("694fea90e46eedc769bcd96c")
        if emission_date is None:
            emission_date = datetime(2025, 12, 7)

        mock_avis = MagicMock()
        mock_emissions = MagicMock()
        mock_livres = MagicMock()
        mock_auteurs = MagicMock()

        # Default: empty results
        mock_avis.find.return_value = avis_docs if avis_docs is not None else []
        mock_livres.find.return_value = livres_docs if livres_docs is not None else []
        mock_auteurs.find.return_value = (
            auteurs_docs if auteurs_docs is not None else []
        )
        mock_emissions.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": emission_date}
        ]

        service.avis_collection = mock_avis
        service.emissions_collection = mock_emissions
        service.livres_collection = mock_livres
        service.auteurs_collection = mock_auteurs

        return (
            service,
            emission_id,
            mock_avis,
            mock_livres,
            mock_auteurs,
            mock_emissions,
        )

    def test_search_by_canonical_titre_finds_emission_when_titre_extrait_differs(self):
        """Issue #224: 'Quatre jours' doit trouver l'émission même si livre_titre_extrait='4 jours'.

        Le titre Babelio (livres.titre) est 'Quatre jours sans ma mère'.
        Le LLM a extrait '4 jours sans ma mère' dans avis.livre_titre_extrait.
        La recherche doit utiliser livres.titre (source canonique).
        """
        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        livre_id = ObjectId("6935d067705ddce2450b2588")

        service = MongoDBService.__new__(MongoDBService)
        mock_avis = MagicMock()
        mock_emissions = MagicMock()
        mock_livres = MagicMock()
        mock_auteurs = MagicMock()

        avis_doc = {
            "_id": ObjectId(),
            "emission_oid": str(emission_id),
            "livre_oid": str(livre_id),
            "livre_titre_extrait": "4 jours sans ma mère",  # LLM extracted (chiffre)
            "auteur_nom_extrait": "Ramsès Kefi",
            "editeur_extrait": "Philippe Rey",
            "commentaire": "Un beau roman",
            "section": "programme",
        }

        livre_doc = {
            "_id": livre_id,  # ObjectId
            "titre": "Quatre jours sans ma mère",  # Babelio canonical (lettres)
            "editeur": "Philippe Rey",
        }

        # livres.find() returns the book matching "Quatre jours"
        mock_livres.find.return_value = [livre_doc]
        mock_auteurs.find.return_value = []

        # avis.find() with livre_oid filter returns the linked avis
        # We use side_effect to handle multiple calls:
        # 1st call: commentaire search → empty (no match in commentaire)
        # 2nd call: livre_oid filter → returns the avis
        def avis_find_side_effect(query, *args, **kwargs):
            if "livre_oid" in query:
                return [avis_doc]
            if "commentaire" in str(query):
                return []
            return []

        mock_avis.find.side_effect = avis_find_side_effect

        mock_emissions.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": datetime(2025, 12, 7)}
        ]

        service.avis_collection = mock_avis
        service.emissions_collection = mock_emissions
        service.livres_collection = mock_livres
        service.auteurs_collection = mock_auteurs

        result = service.search_emissions("Quatre jours")

        assert len(result["emissions"]) == 1, (
            f"Searching 'Quatre jours' should find the emission via livres.titre "
            f"(canonical), even though livre_titre_extrait='4 jours'. "
            f"Got {len(result['emissions'])} results."
        )
        assert result["total_count"] == 1

    def test_search_by_canonical_auteur_nom_finds_emission(self):
        """La recherche par nom d'auteur utilise auteurs.nom (canonique), pas auteur_nom_extrait."""
        emission_id = ObjectId("694fea90e46eedc769bcd96c")
        livre_id = ObjectId("6935d067705ddce2450b2588")
        auteur_id = ObjectId("6935d067705ddce2450b2587")

        service = MongoDBService.__new__(MongoDBService)
        mock_avis = MagicMock()
        mock_emissions = MagicMock()
        mock_livres = MagicMock()
        mock_auteurs = MagicMock()

        avis_doc = {
            "_id": ObjectId(),
            "emission_oid": str(emission_id),
            "livre_oid": str(livre_id),
            "livre_titre_extrait": "4 jours sans ma mère",
            "auteur_nom_extrait": "R. Kefi",  # abbreviated, non-canonical
            "editeur_extrait": "Philippe Rey",
            "commentaire": "Un beau roman",
            "section": "programme",
        }

        auteur_doc = {
            "_id": auteur_id,  # ObjectId
            "nom": "Ramsès Kefi",  # Babelio canonical full name
        }

        livre_doc_for_auteur = {
            "_id": livre_id,  # ObjectId
            "titre": "Quatre jours sans ma mère",
            "auteur_id": auteur_id,
            "editeur": "Philippe Rey",
        }

        # auteurs.find() returns the author matching "Kefi"
        mock_auteurs.find.return_value = [auteur_doc]

        # livres.find() returns books for that author (when queried by auteur_id)
        # and empty list when queried for titre/editeur regex
        def livres_find_side_effect(query, *args, **kwargs):
            if "auteur_id" in query:
                return [livre_doc_for_auteur]
            # titre/editeur regex search: no match (searching "Kefi" in titre)
            return []

        mock_livres.find.side_effect = livres_find_side_effect

        def avis_find_side_effect(query, *args, **kwargs):
            if "livre_oid" in query:
                return [avis_doc]
            return []

        mock_avis.find.side_effect = avis_find_side_effect

        mock_emissions.find.return_value.sort.return_value = [
            {"_id": emission_id, "date": datetime(2025, 12, 7)}
        ]

        service.avis_collection = mock_avis
        service.emissions_collection = mock_emissions
        service.livres_collection = mock_livres
        service.auteurs_collection = mock_auteurs

        result = service.search_emissions("Kefi")

        assert len(result["emissions"]) == 1, (
            f"Searching 'Kefi' should find the emission via auteurs.nom (canonical). "
            f"Got {len(result['emissions'])} results."
        )

    def test_search_livres_titre_is_queried_not_livre_titre_extrait(self):
        """La nouvelle implémentation doit chercher dans livres.titre, pas avis.livre_titre_extrait."""
        service = MongoDBService.__new__(MongoDBService)
        mock_avis = MagicMock()
        mock_emissions = MagicMock()
        mock_livres = MagicMock()
        mock_auteurs = MagicMock()

        mock_livres.find.return_value = []
        mock_auteurs.find.return_value = []
        mock_avis.find.return_value = []
        mock_emissions.find.return_value.sort.return_value = []

        service.avis_collection = mock_avis
        service.emissions_collection = mock_emissions
        service.livres_collection = mock_livres
        service.auteurs_collection = mock_auteurs

        service.search_emissions("Quatre jours")

        # livres_collection.find() doit être appelé avec une query sur "titre"
        assert mock_livres.find.called, "livres_collection.find() doit être appelé"
        livres_call_args = mock_livres.find.call_args_list
        searched_fields = []
        for call in livres_call_args:
            q = call[0][0] if call[0] else {}
            for key in q:
                if key == "$or":
                    searched_fields.extend(list(c.keys())[0] for c in q[key])
                else:
                    searched_fields.append(key)
        assert "titre" in searched_fields, (
            f"livres_collection.find() doit chercher dans 'titre'. "
            f"Fields found: {searched_fields}"
        )

    def test_search_auteurs_nom_is_queried_not_auteur_nom_extrait(self):
        """La nouvelle implémentation doit chercher dans auteurs.nom, pas avis.auteur_nom_extrait."""
        service = MongoDBService.__new__(MongoDBService)
        mock_avis = MagicMock()
        mock_emissions = MagicMock()
        mock_livres = MagicMock()
        mock_auteurs = MagicMock()

        mock_livres.find.return_value = []
        mock_auteurs.find.return_value = []
        mock_avis.find.return_value = []
        mock_emissions.find.return_value.sort.return_value = []

        service.avis_collection = mock_avis
        service.emissions_collection = mock_emissions
        service.livres_collection = mock_livres
        service.auteurs_collection = mock_auteurs

        service.search_emissions("Kefi")

        # auteurs_collection.find() doit être appelé avec une query sur "nom"
        assert mock_auteurs.find.called, "auteurs_collection.find() doit être appelé"
        auteurs_call_args = mock_auteurs.find.call_args_list
        searched_fields = []
        for call in auteurs_call_args:
            q = call[0][0] if call[0] else {}
            searched_fields.extend(q.keys())
        assert "nom" in searched_fields, (
            f"auteurs_collection.find() doit chercher dans 'nom'. "
            f"Fields found: {searched_fields}"
        )
