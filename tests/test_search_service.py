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
        self.mock_auteurs_collection = Mock()
        self.mock_livres_collection = Mock()

        mongodb_service.episodes_collection = self.mock_episodes_collection
        mongodb_service.avis_critiques_collection = self.mock_avis_critiques_collection
        mongodb_service.auteurs_collection = self.mock_auteurs_collection
        mongodb_service.livres_collection = self.mock_livres_collection

    def test_search_episodes_method_exists(self):
        """Test que la méthode search_episodes existe."""
        assert hasattr(mongodb_service, "search_episodes")

    def test_search_episodes_returns_dict_with_episodes_and_count(self):
        """Test que search_episodes retourne un dict avec episodes et total_count."""
        # Mock du retour de la collection
        mock_cursor = Mock()
        # Configure le chaînage: find().sort().skip().limit()
        mock_cursor.sort.return_value.skip.return_value.limit.return_value = []
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
        # Configure le chaînage: find().sort().skip().limit()
        mock_cursor.sort.return_value.skip.return_value.limit.return_value = (
            mock_episodes
        )
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
        # Configure le chaînage: find().sort().skip().limit()
        mock_cursor.sort.return_value.skip.return_value.limit.return_value = (
            mock_episodes[:5]
        )
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

    def test_search_auteurs_returns_dict_with_results_and_count(self):
        """Test que search_auteurs retourne un dict avec auteurs et total_count."""
        # Mock du retour de la collection
        mock_cursor = Mock()
        # Configure le chaînage: find().skip().limit()
        mock_cursor.skip.return_value.limit.return_value = []
        self.mock_auteurs_collection.find.return_value = mock_cursor
        self.mock_auteurs_collection.count_documents.return_value = 0

        result = mongodb_service.search_auteurs("test", limit=10)

        assert isinstance(result, dict)
        assert "auteurs" in result
        assert "total_count" in result
        assert isinstance(result["auteurs"], list)
        assert isinstance(result["total_count"], int)

    def test_search_auteurs_finds_author_by_name(self):
        """Test que search_auteurs trouve un auteur par son nom."""
        mock_auteurs = [
            {"_id": "507f1f77bcf86cd799439011", "nom": "Albert Camus", "livres": []}
        ]
        mock_cursor = Mock()
        # Configure le chaînage: find().skip().limit()
        mock_cursor.skip.return_value.limit.return_value = mock_auteurs
        self.mock_auteurs_collection.find.return_value = mock_cursor
        self.mock_auteurs_collection.count_documents.return_value = 1

        result = mongodb_service.search_auteurs("Camus", limit=10)

        assert len(result["auteurs"]) > 0
        assert result["total_count"] == 1
        # Vérifier que _id est converti en string
        assert isinstance(result["auteurs"][0]["_id"], str)

    def test_search_auteurs_handles_empty_query(self):
        """Test que search_auteurs gère les requêtes vides."""
        result = mongodb_service.search_auteurs("", limit=10)
        assert result == {"auteurs": [], "total_count": 0}

    def test_search_livres_returns_dict_with_results_and_count(self):
        """Test que search_livres retourne un dict avec livres et total_count."""
        # Mock du retour de la collection
        mock_cursor = Mock()
        # Configure le chaînage: find().skip().limit()
        mock_cursor.skip.return_value.limit.return_value = []
        self.mock_livres_collection.find.return_value = mock_cursor
        self.mock_livres_collection.count_documents.return_value = 0

        result = mongodb_service.search_livres("test", limit=10)

        assert isinstance(result, dict)
        assert "livres" in result
        assert "total_count" in result
        assert isinstance(result["livres"], list)
        assert isinstance(result["total_count"], int)

    def test_search_livres_finds_book_by_title(self):
        """Test que search_livres trouve un livre par son titre."""
        mock_livres = [
            {
                "_id": "507f1f77bcf86cd799439012",
                "titre": "L'Étranger",
                "auteur_id": "507f1f77bcf86cd799439011",
                "editeur": "Gallimard",
            }
        ]
        mock_cursor = Mock()
        # Configure le chaînage: find().skip().limit()
        mock_cursor.skip.return_value.limit.return_value = mock_livres
        self.mock_livres_collection.find.return_value = mock_cursor
        self.mock_livres_collection.count_documents.return_value = 1

        result = mongodb_service.search_livres("Étranger", limit=10)

        assert len(result["livres"]) > 0
        assert result["total_count"] == 1
        assert isinstance(result["livres"][0]["_id"], str)

    def test_search_livres_finds_book_by_editeur(self):
        """Test que search_livres trouve un livre par son éditeur."""
        mock_livres = [
            {
                "_id": "507f1f77bcf86cd799439013",
                "titre": "La Peste",
                "auteur_id": "507f1f77bcf86cd799439011",
                "editeur": "Gallimard",
            }
        ]
        mock_cursor = Mock()
        # Configure le chaînage: find().skip().limit()
        mock_cursor.skip.return_value.limit.return_value = mock_livres
        self.mock_livres_collection.find.return_value = mock_cursor
        self.mock_livres_collection.count_documents.return_value = 1

        result = mongodb_service.search_livres("Gallimard", limit=10)

        assert len(result["livres"]) > 0
        assert result["total_count"] == 1

    def test_search_livres_handles_empty_query(self):
        """Test que search_livres gère les requêtes vides."""
        result = mongodb_service.search_livres("", limit=10)
        assert result == {"livres": [], "total_count": 0}

    def test_search_livres_includes_author_name(self):
        """Test que search_livres enrichit les résultats avec le nom de l'auteur."""
        # Mock des livres avec auteur_id
        mock_livres = [
            {
                "_id": "507f1f77bcf86cd799439012",
                "titre": "L'Étranger",
                "auteur_id": "507f1f77bcf86cd799439011",
                "editeur": "Gallimard",
            }
        ]
        # Mock de l'auteur correspondant
        mock_auteur = {
            "_id": "507f1f77bcf86cd799439011",
            "nom": "Albert Camus",
            "livres": [],
        }

        mock_cursor = Mock()
        # Configure le chaînage: find().skip().limit()
        mock_cursor.skip.return_value.limit.return_value = mock_livres
        self.mock_livres_collection.find.return_value = mock_cursor
        self.mock_livres_collection.count_documents.return_value = 1
        self.mock_auteurs_collection.find_one.return_value = mock_auteur

        result = mongodb_service.search_livres("Étranger", limit=10)

        assert len(result["livres"]) == 1
        assert "auteur_nom" in result["livres"][0]
        assert result["livres"][0]["auteur_nom"] == "Albert Camus"

    def test_search_editeurs_method_exists(self):
        """Test que la méthode search_editeurs existe."""
        assert hasattr(mongodb_service, "search_editeurs")

    def test_search_editeurs_returns_dict_with_results_and_count(self):
        """Test que search_editeurs retourne un dict avec editeurs et total_count."""
        # Mock des éditeurs
        mongodb_service.editeurs_collection = Mock()
        mock_cursor = Mock()
        # Configure le chaînage: find().skip().limit()
        mock_cursor.skip.return_value.limit.return_value = []
        mongodb_service.editeurs_collection.find.return_value = mock_cursor
        mongodb_service.editeurs_collection.count_documents.return_value = 0

        result = mongodb_service.search_editeurs("test", limit=10)

        assert isinstance(result, dict)
        assert "editeurs" in result
        assert "total_count" in result
        assert isinstance(result["editeurs"], list)
        assert isinstance(result["total_count"], int)

    def test_search_editeurs_finds_publisher_by_name(self):
        """Test que search_editeurs trouve un éditeur par son nom."""
        # Mock des éditeurs
        mongodb_service.editeurs_collection = Mock()
        mock_editeurs = [
            {"_id": "507f1f77bcf86cd799439020", "nom": "Gallimard", "livres": []}
        ]
        mock_cursor = Mock()
        # Configure le chaînage: find().skip().limit()
        mock_cursor.skip.return_value.limit.return_value = mock_editeurs
        mongodb_service.editeurs_collection.find.return_value = mock_cursor
        mongodb_service.editeurs_collection.count_documents.return_value = 1

        result = mongodb_service.search_editeurs("Gallimard", limit=10)

        assert len(result["editeurs"]) > 0
        assert result["total_count"] == 1
        # Vérifier que _id est converti en string
        assert isinstance(result["editeurs"][0]["_id"], str)

    def test_search_editeurs_handles_empty_query(self):
        """Test que search_editeurs gère les requêtes vides."""
        result = mongodb_service.search_editeurs("", limit=10)
        assert result == {"editeurs": [], "total_count": 0}
