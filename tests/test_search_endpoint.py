"""Tests pour l'endpoint de recherche textuelle multi-entités."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestSearchEndpoint:
    """Tests pour l'endpoint /api/search."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_search_endpoint_exists(self):
        """Test que l'endpoint /api/search existe."""
        response = self.client.get("/api/search?q=test")
        # Le endpoint doit exister (ne pas retourner 404)
        assert response.status_code != 404

    def test_search_requires_query_parameter(self):
        """Test que l'endpoint requiert le paramètre q."""
        response = self.client.get("/api/search")
        assert response.status_code == 422  # Validation error

    def test_search_minimum_query_length(self):
        """Test que la recherche nécessite au moins 3 caractères."""
        response = self.client.get("/api/search?q=ab")
        assert response.status_code == 400
        assert "3 caractères minimum" in response.json()["detail"]

    @patch(
        "back_office_lmelp.services.mongodb_service.mongodb_service.search_emissions"
    )
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_episodes")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_auteurs")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_livres")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_editeurs")
    def test_search_returns_structured_response(
        self,
        mock_search_editeurs,
        mock_search_livres,
        mock_search_auteurs,
        mock_search_episodes,
        mock_search_emissions,
    ):
        """Test que la recherche retourne une réponse structurée."""
        # Mock des retours
        mock_search_episodes.return_value = {"episodes": [], "total_count": 0}
        mock_search_auteurs.return_value = {"auteurs": [], "total_count": 0}
        mock_search_livres.return_value = {"livres": [], "total_count": 0}
        mock_search_editeurs.return_value = {"editeurs": [], "total_count": 0}
        mock_search_emissions.return_value = {"emissions": [], "total_count": 0}

        response = self.client.get("/api/search?q=test")
        assert response.status_code == 200

        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "auteurs" in data["results"]
        assert "auteurs_total_count" in data["results"]
        assert "livres" in data["results"]
        assert "livres_total_count" in data["results"]
        assert "editeurs" in data["results"]
        assert "episodes" in data["results"]

    @patch(
        "back_office_lmelp.services.mongodb_service.mongodb_service.search_emissions"
    )
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_episodes")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_auteurs")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_livres")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_editeurs")
    def test_search_with_limit_parameter(
        self,
        mock_search_editeurs,
        mock_search_livres,
        mock_search_auteurs,
        mock_search_episodes,
        mock_search_emissions,
    ):
        """Test que l'endpoint accepte le paramètre limit."""
        # Mock des retours avec des données limitées
        mock_search_episodes.return_value = {"episodes": [], "total_count": 0}
        mock_search_auteurs.return_value = {"auteurs": [], "total_count": 0}
        mock_search_livres.return_value = {"livres": [], "total_count": 0}
        mock_search_editeurs.return_value = {"editeurs": [], "total_count": 0}
        mock_search_emissions.return_value = {"emissions": [], "total_count": 0}

        response = self.client.get("/api/search?q=test&limit=5")
        assert response.status_code == 200

        data = response.json()
        # Vérifier que chaque catégorie respecte la limite (exclure *_total_count)
        for category_name, category in data["results"].items():
            if not category_name.endswith("_total_count"):
                assert len(category) <= 5

    @patch(
        "back_office_lmelp.services.mongodb_service.mongodb_service.search_emissions"
    )
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_episodes")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_auteurs")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_livres")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_editeurs")
    def test_search_returns_score_and_match_type(
        self,
        mock_search_editeurs,
        mock_search_livres,
        mock_search_auteurs,
        mock_search_episodes,
        mock_search_emissions,
    ):
        """Test que chaque résultat inclut score et match_type."""
        # Mock des retours avec des données contenant score et match_type
        mock_search_episodes.return_value = {
            "episodes": [
                {
                    "titre": "Test Episode",
                    "score": 0.8,
                    "match_type": "partial",
                    "_id": "123",
                    "date": "2024-01-01",
                }
            ],
            "total_count": 1,
        }
        mock_search_auteurs.return_value = {
            "auteurs": [{"_id": "1", "nom": "Test Author", "livres": []}],
            "total_count": 1,
        }
        mock_search_livres.return_value = {"livres": [], "total_count": 0}
        mock_search_editeurs.return_value = {"editeurs": [], "total_count": 0}
        mock_search_emissions.return_value = {"emissions": [], "total_count": 0}

        response = self.client.get("/api/search?q=test")
        assert response.status_code == 200

        data = response.json()
        # Les épisodes ont score et match_type, mais pas forcément auteurs/livres/editeurs
        for episode in data["results"]["episodes"]:
            assert "score" in episode
            assert "match_type" in episode
            assert isinstance(episode["score"], int | float)
            assert episode["match_type"] in [
                "exact",
                "partial",
                "fuzzy",
                "found",
                "none",
            ]

    @patch(
        "back_office_lmelp.services.mongodb_service.mongodb_service.search_emissions"
    )
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_episodes")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_auteurs")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_livres")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_editeurs")
    def test_search_handles_special_characters(
        self,
        mock_search_editeurs,
        mock_search_livres,
        mock_search_auteurs,
        mock_search_episodes,
        mock_search_emissions,
    ):
        """Test que la recherche gère les caractères spéciaux."""
        mock_search_episodes.return_value = {"episodes": [], "total_count": 0}
        mock_search_auteurs.return_value = {"auteurs": [], "total_count": 0}
        mock_search_livres.return_value = {"livres": [], "total_count": 0}
        mock_search_editeurs.return_value = {"editeurs": [], "total_count": 0}
        mock_search_emissions.return_value = {"emissions": [], "total_count": 0}

        response = self.client.get("/api/search?q=camus&")
        assert response.status_code == 200

    @patch(
        "back_office_lmelp.services.mongodb_service.mongodb_service.search_emissions"
    )
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_episodes")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_auteurs")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_livres")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_editeurs")
    def test_search_case_insensitive(
        self,
        mock_search_editeurs,
        mock_search_livres,
        mock_search_auteurs,
        mock_search_episodes,
        mock_search_emissions,
    ):
        """Test que la recherche est insensible à la casse."""
        mock_search_episodes.return_value = {"episodes": [], "total_count": 0}
        mock_search_auteurs.return_value = {"auteurs": [], "total_count": 0}
        mock_search_livres.return_value = {"livres": [], "total_count": 0}
        mock_search_editeurs.return_value = {"editeurs": [], "total_count": 0}
        mock_search_emissions.return_value = {"emissions": [], "total_count": 0}

        response = self.client.get("/api/search?q=CAMUS")
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "CAMUS"

    @patch(
        "back_office_lmelp.services.mongodb_service.mongodb_service.search_emissions"
    )
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_episodes")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_auteurs")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_livres")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_editeurs")
    def test_search_includes_episodes_total_count(
        self,
        mock_search_editeurs,
        mock_search_livres,
        mock_search_auteurs,
        mock_search_episodes,
        mock_search_emissions,
    ):
        """Test que la réponse inclut episodes_total_count."""
        mock_search_episodes.return_value = {
            "episodes": [
                {
                    "titre": "Episode 1",
                    "_id": "1",
                    "date": "2024-01-01",
                    "score": 1.0,
                    "match_type": "exact",
                },
                {
                    "titre": "Episode 2",
                    "_id": "2",
                    "date": "2024-01-02",
                    "score": 0.8,
                    "match_type": "partial",
                },
            ],
            "total_count": 25,  # Plus d'épisodes trouvés que ceux affichés
        }
        mock_search_auteurs.return_value = {"auteurs": [], "total_count": 0}
        mock_search_livres.return_value = {"livres": [], "total_count": 0}
        mock_search_editeurs.return_value = {"editeurs": [], "total_count": 0}
        mock_search_emissions.return_value = {"emissions": [], "total_count": 0}

        response = self.client.get("/api/search?q=test")
        assert response.status_code == 200

        data = response.json()
        assert "episodes_total_count" in data["results"]
        assert data["results"]["episodes_total_count"] == 25
        assert len(data["results"]["episodes"]) == 2  # Seulement 2 affichés
        # Vérifier la structure de chaque épisode
        for episode in data["results"]["episodes"]:
            assert "search_context" in episode

    @patch(
        "back_office_lmelp.services.mongodb_service.mongodb_service.search_emissions"
    )
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_episodes")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_auteurs")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_livres")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_editeurs")
    def test_search_queries_collections_auteurs_and_livres(
        self,
        mock_search_editeurs,
        mock_search_livres,
        mock_search_auteurs,
        mock_search_episodes,
        mock_search_emissions,
    ):
        """Test que la recherche interroge les collections dédiées auteurs et livres."""
        # Mock des retours avec des données des collections
        mock_search_episodes.return_value = {"episodes": [], "total_count": 0}
        mock_search_auteurs.return_value = {
            "auteurs": [{"_id": "1", "nom": "Albert Camus", "livres": []}],
            "total_count": 1,
        }
        mock_search_livres.return_value = {
            "livres": [
                {
                    "_id": "2",
                    "titre": "L'Étranger",
                    "editeur": "Gallimard",
                    "auteur_id": "1",
                }
            ],
            "total_count": 1,
        }
        mock_search_editeurs.return_value = {"editeurs": [], "total_count": 0}
        mock_search_emissions.return_value = {"emissions": [], "total_count": 0}

        response = self.client.get("/api/search?q=Camus")
        assert response.status_code == 200

        data = response.json()

        # Vérifier que les collections dédiées ont été appelées
        mock_search_auteurs.assert_called_once()
        mock_search_livres.assert_called_once()

        # Vérifier que les résultats proviennent des collections dédiées
        assert len(data["results"]["auteurs"]) == 1
        assert data["results"]["auteurs"][0]["nom"] == "Albert Camus"
        assert data["results"]["auteurs_total_count"] == 1

        assert len(data["results"]["livres"]) == 1
        assert data["results"]["livres"][0]["titre"] == "L'Étranger"
        assert data["results"]["livres_total_count"] == 1

    @patch(
        "back_office_lmelp.services.mongodb_service.mongodb_service.search_emissions"
    )
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_episodes")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_auteurs")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_livres")
    @patch("back_office_lmelp.services.mongodb_service.mongodb_service.search_editeurs")
    def test_search_uses_search_editeurs_for_publishers(
        self,
        mock_search_editeurs,
        mock_search_livres,
        mock_search_auteurs,
        mock_search_episodes,
        mock_search_emissions,
    ):
        """Test que /api/search utilise search_editeurs() pour les éditeurs."""
        # Mock des retours
        mock_search_episodes.return_value = {"episodes": [], "total_count": 0}
        mock_search_auteurs.return_value = {"auteurs": [], "total_count": 0}
        mock_search_livres.return_value = {"livres": [], "total_count": 0}
        mock_search_editeurs.return_value = {
            "editeurs": [{"nom": "Gallimard"}],
            "total_count": 1,
        }
        mock_search_emissions.return_value = {"emissions": [], "total_count": 0}

        response = self.client.get("/api/search?q=Gallimard")
        assert response.status_code == 200

        data = response.json()

        # Vérifier que search_editeurs a été appelé
        mock_search_editeurs.assert_called_once()

        # Vérifier que les résultats contiennent les éditeurs
        assert len(data["results"]["editeurs"]) == 1
        assert data["results"]["editeurs"][0]["nom"] == "Gallimard"
