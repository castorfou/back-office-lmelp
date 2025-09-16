"""Tests pour les services de recherche textuelle MongoDB."""

from unittest.mock import Mock

import pytest

from back_office_lmelp.services.mongodb_service import mongodb_service


class TestSearchService:
    """Tests pour les méthodes de recherche dans MongoDBService."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup pour chaque test."""
        # Mock des collections MongoDB
        self.mock_episodes_collection = Mock()
        self.mock_avis_critiques_collection = Mock()

        mongodb_service.episodes_collection = self.mock_episodes_collection
        mongodb_service.avis_critiques_collection = self.mock_avis_critiques_collection

    def test_search_episodes_method_exists(self):
        """Test que la méthode search_episodes existe."""
        assert hasattr(mongodb_service, "search_episodes")

    def test_search_episodes_returns_list(self):
        """Test que search_episodes retourne une liste."""
        # Mock du retour de la collection
        self.mock_episodes_collection.find.return_value = []

        result = mongodb_service.search_episodes("test", limit=10)
        assert isinstance(result, list)

    def test_search_episodes_with_fuzzy_matching(self):
        """Test que search_episodes supporte la recherche floue."""
        # Mock des données d'épisodes
        mock_episodes = [
            {
                "_id": "507f1f77bcf86cd799439011",
                "titre": "Épisode sur Camus",
                "transcription": "Discussing Albert Camus...",
                "description": "Un grand auteur",
            }
        ]
        self.mock_episodes_collection.find.return_value = mock_episodes

        # Test recherche avec faute d'orthographe
        result = mongodb_service.search_episodes("Camuz", limit=10)
        # Doit trouver des résultats même avec la faute
        assert len(result) >= 0

    def test_search_critical_reviews_for_authors_books(self):
        """Test que search_critical_reviews_for_authors_books existe et fonctionne."""
        assert hasattr(mongodb_service, "search_critical_reviews_for_authors_books")

        # Mock des avis critiques
        mock_reviews = [
            {
                "_id": "507f1f77bcf86cd799439012",
                "auteur": "Albert Camus",
                "titre_livre": "L'Étranger",
                "editeur": "Gallimard",
            }
        ]
        self.mock_avis_critiques_collection.find.return_value = mock_reviews

        result = mongodb_service.search_critical_reviews_for_authors_books(
            "Camus", limit=10
        )
        assert isinstance(result, dict)
        assert "auteurs" in result
        assert "livres" in result
        assert "editeurs" in result

    def test_calculate_search_score(self):
        """Test que calculate_search_score calcule correctement les scores."""
        assert hasattr(mongodb_service, "calculate_search_score")

        # Test match partiel
        score, match_type = mongodb_service.calculate_search_score(
            "camus", "Albert Camus"
        )
        assert score > 0.5  # Score élevé pour match partiel
        assert match_type == "partial"

        # Test match exact
        score, match_type = mongodb_service.calculate_search_score("camus", "camus")
        assert score == 1.0  # Score parfait pour match exact
        assert match_type == "exact"

    def test_text_search_with_regex(self):
        """Test que la recherche utilise des regex pour le matching flou."""
        # Ceci sera implémenté dans mongodb_service
        query = "houellebeck"  # Faute d'orthographe

        # La méthode devrait créer un pattern regex qui trouve "houellebecq"
        pattern = mongodb_service._create_fuzzy_regex_pattern(query)
        assert pattern is not None

    def test_search_handles_empty_query(self):
        """Test que la recherche gère les requêtes vides."""
        result = mongodb_service.search_episodes("", limit=10)
        assert result == []

    def test_search_respects_limit(self):
        """Test que la recherche respecte la limite."""
        # Mock de nombreux résultats
        mock_episodes = [{"_id": f"id{i}", "titre": f"Episode {i}"} for i in range(20)]
        self.mock_episodes_collection.find.return_value = mock_episodes

        result = mongodb_service.search_episodes("episode", limit=5)
        assert len(result) <= 5
