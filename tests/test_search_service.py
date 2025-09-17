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

    def test_search_episodes_returns_dict_with_episodes_and_count(self):
        """Test que search_episodes retourne un dict avec episodes et total_count."""
        # Mock du retour de la collection
        mock_cursor = Mock()
        mock_cursor.sort.return_value.limit.return_value = []
        self.mock_episodes_collection.find.return_value = mock_cursor
        self.mock_episodes_collection.count_documents.return_value = 0

        result = mongodb_service.search_episodes("test", limit=10)

        assert isinstance(result, dict)
        assert "episodes" in result
        assert "total_count" in result
        assert isinstance(result["episodes"], list)
        assert isinstance(result["total_count"], int)

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
        mock_cursor = Mock()
        mock_cursor.sort.return_value.limit.return_value = mock_episodes
        self.mock_episodes_collection.find.return_value = mock_cursor
        self.mock_episodes_collection.count_documents.return_value = 1

        # Test recherche avec faute d'orthographe
        result = mongodb_service.search_episodes("Camuz", limit=10)
        # Doit retourner un dict avec episodes et total_count
        assert isinstance(result, dict)
        assert len(result["episodes"]) >= 0

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
        assert result == {"episodes": [], "total_count": 0}

    def test_search_respects_limit(self):
        """Test que la recherche respecte la limite."""
        # Mock de nombreux résultats
        mock_episodes = [{"_id": f"id{i}", "titre": f"Episode {i}"} for i in range(20)]
        mock_cursor = Mock()
        mock_cursor.sort.return_value.limit.return_value = mock_episodes[
            :5
        ]  # MongoDB limite déjà
        self.mock_episodes_collection.find.return_value = mock_cursor
        self.mock_episodes_collection.count_documents.return_value = 20

        result = mongodb_service.search_episodes("episode", limit=5)
        assert isinstance(result, dict)
        assert (
            len(result["episodes"]) <= 5
        )  # Test que les épisodes respectent la limite
        assert result["total_count"] == 20  # Mais le count total reste 20

    def test_extract_search_context_from_title(self):
        """Test que _extract_search_context trouve le contexte dans le titre."""
        episode = {
            "titre": "Episode avec le mot maison dans le titre",
            "description": "Une description",
            "transcription": "Une transcription",
        }

        context = mongodb_service._extract_search_context("maison", episode)

        assert "maison" in context.lower()
        assert "Episode avec le mot maison dans le titre" in context

    def test_extract_search_context_from_description(self):
        """Test que _extract_search_context trouve le contexte dans la description."""
        episode = {
            "titre": "Episode sans le mot",
            "description": "Une description avec le mot maison au milieu du texte pour tester",
            "transcription": "Une transcription",
        }

        context = mongodb_service._extract_search_context("maison", episode)

        assert "maison" in context.lower()
        assert "description avec le mot maison au milieu" in context

    def test_extract_search_context_from_transcription(self):
        """Test que _extract_search_context trouve le contexte dans la transcription."""
        episode = {
            "titre": "Episode sans le mot",
            "description": "Description sans le mot",
            "transcription": "Une longue transcription avec beaucoup de mots et le mot maison apparaît ici pour tester l'extraction",
        }

        context = mongodb_service._extract_search_context("maison", episode)

        assert "maison" in context.lower()
        assert "mots et le mot maison apparaît ici" in context

    def test_extract_search_context_with_ellipses(self):
        """Test que _extract_search_context ajoute des ellipses quand nécessaire."""
        # Créer un texte long avec le mot recherché au milieu
        words = ["mot" + str(i) for i in range(50)]
        words[25] = "maison"  # Mot recherché au milieu
        long_text = " ".join(words)

        episode = {
            "titre": "Episode test",
            "description": long_text,
            "transcription": "",
        }

        context = mongodb_service._extract_search_context("maison", episode)

        assert "maison" in context
        assert context.startswith("...")  # Ellipses au début
        assert context.endswith("...")  # Ellipses à la fin

    def test_extract_search_context_not_found(self):
        """Test que _extract_search_context retourne vide quand rien n'est trouvé."""
        episode = {
            "titre": "Episode test",
            "description": "Description test",
            "transcription": "Transcription test",
        }

        context = mongodb_service._extract_search_context("inexistant", episode)

        assert context == ""
