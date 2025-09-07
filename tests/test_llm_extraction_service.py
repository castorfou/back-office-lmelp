"""Tests pour le service d'extraction LLM des livres/auteurs/éditeurs."""

from unittest.mock import AsyncMock, Mock

import pytest

from back_office_lmelp.services.llm_extraction_service import LLMExtractionService


@pytest.fixture
def llm_service():
    """Service LLM pour les tests."""
    return LLMExtractionService()


@pytest.fixture
def mock_avis_critique():
    """Mock d'un avis critique avec données bibliographiques."""
    return {
        "_id": "test_id",
        "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
        "episode_title": "Test Episode",
        "episode_date": "01 jan. 2025",
        "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques |
|--------|-------|---------|------------------------------|
| Test Auteur | Test Livre | Test Éditeur | **Critique**: "Très bon livre" - 8 |
| Autre Auteur | Autre Livre | Autre Éditeur | **Autre Critique**: "Passable" - 6 |
""",
    }


class TestLLMExtractionService:
    """Tests du service d'extraction LLM."""

    def test_init(self, llm_service):
        """Test l'initialisation du service."""
        assert llm_service is not None
        assert hasattr(llm_service, "extract_books_from_reviews")

    @pytest.mark.asyncio
    async def test_extract_books_from_reviews_basic(
        self, llm_service, mock_avis_critique
    ):
        """Test l'extraction basique de livres depuis un avis critique."""
        # Mock de la réponse OpenAI
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = """[
{
    "auteur": "Test Auteur",
    "titre": "Test Livre",
    "editeur": "Test Éditeur",
    "note_moyenne": 8.0,
    "nb_critiques": 1,
    "coups_de_coeur": ["Critique"]
}
]"""

        # Mock le client Azure directement sur l'instance du service
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        llm_service.client = mock_client

        result = await llm_service.extract_books_from_reviews([mock_avis_critique])

        assert len(result) == 1
        book = result[0]
        assert (
            book["episode_oid"]
            == "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
        )
        assert book["episode_title"] == "Test Episode"
        assert book["episode_date"] == "01 jan. 2025"
        assert book["auteur"] == "Test Auteur"
        assert book["titre"] == "Test Livre"
        assert book["editeur"] == "Test Éditeur"
        assert book["note_moyenne"] == 8.0

    @pytest.mark.asyncio
    async def test_extract_books_from_reviews_multiple_books(
        self, llm_service, mock_avis_critique
    ):
        """Test l'extraction de plusieurs livres depuis un avis critique."""
        # Mock de la réponse OpenAI avec plusieurs livres
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = """[
{
    "auteur": "Test Auteur",
    "titre": "Test Livre",
    "editeur": "Test Éditeur",
    "note_moyenne": 8.0,
    "nb_critiques": 1,
    "coups_de_coeur": ["Critique"]
},
{
    "auteur": "Autre Auteur",
    "titre": "Autre Livre",
    "editeur": "Autre Éditeur",
    "note_moyenne": 6.0,
    "nb_critiques": 1,
    "coups_de_coeur": []
}
]"""

        # Mock le client Azure directement sur l'instance du service
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        llm_service.client = mock_client

        result = await llm_service.extract_books_from_reviews([mock_avis_critique])

        assert len(result) == 2
        # Vérifier que les métadonnées d'épisode sont propagées
        for book in result:
            assert (
                book["episode_oid"]
                == "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
            )
            assert book["episode_title"] == "Test Episode"
            assert book["episode_date"] == "01 jan. 2025"

        assert result[0]["auteur"] == "Test Auteur"
        assert result[1]["auteur"] == "Autre Auteur"

    @pytest.mark.asyncio
    async def test_extract_books_from_reviews_empty_input(self, llm_service):
        """Test l'extraction avec une liste vide d'avis critiques."""
        result = await llm_service.extract_books_from_reviews([])
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_books_from_reviews_api_error(
        self, llm_service, mock_avis_critique
    ):
        """Test la gestion d'erreur de l'API OpenAI."""
        # Mock le client Azure directement sur l'instance du service avec une erreur
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )
        llm_service.client = mock_client

        # Le service doit continuer et ne pas propager l'exception pour un seul avis
        result = await llm_service.extract_books_from_reviews([mock_avis_critique])
        assert result == []  # Liste vide car l'extraction a échoué

    @pytest.mark.asyncio
    async def test_extract_books_from_reviews_invalid_json_response(
        self, llm_service, mock_avis_critique
    ):
        """Test la gestion d'une réponse JSON invalide."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Invalid JSON response"

        # Mock le client Azure directement sur l'instance du service
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        llm_service.client = mock_client

        # Le service doit continuer et ne pas propager l'exception pour un seul avis
        result = await llm_service.extract_books_from_reviews([mock_avis_critique])
        assert result == []  # Liste vide car le parsing JSON a échoué

    def test_format_books_for_display(self, llm_service):
        """Test le formatage des livres pour l'affichage."""
        books_data = [
            {
                "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
                "episode_title": "Test Episode",
                "episode_date": "01 jan. 2025",
                "auteur": "Test Auteur",
                "titre": "Test Livre",
                "editeur": "Test Éditeur",
                "note_moyenne": "8.0",  # String dans les données brutes
                "nb_critiques": "2",  # String dans les données brutes
                "coups_de_coeur": ["Critique1", "Critique2"],
            }
        ]

        result = llm_service.format_books_for_display(books_data)

        assert len(result) == 1
        book = result[0]
        assert (
            book["episode_oid"]
            == "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
        )
        assert book["episode_title"] == "Test Episode"
        assert book["episode_date"] == "01 jan. 2025"
        assert book["auteur"] == "Test Auteur"
        assert book["titre"] == "Test Livre"
        assert book["editeur"] == "Test Éditeur"
        assert book["note_moyenne"] == 8.0  # Converti en float
        assert book["nb_critiques"] == 2  # Converti en int
        assert book["coups_de_coeur"] == ["Critique1", "Critique2"]

    def test_format_books_for_display_empty(self, llm_service):
        """Test le formatage avec une liste vide."""
        result = llm_service.format_books_for_display([])
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_books_preserves_episode_metadata(self, llm_service):
        """Test que les métadonnées de l'épisode sont préservées dans l'extraction."""
        mock_avis = {
            "_id": "test_id_2",
            "episode_oid": "other_episode_oid",
            "episode_title": "Autre Episode",
            "episode_date": "15 fév. 2025",
            "summary": """## 1. LIVRES DISCUTÉS
| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Auteur X | Livre Y | Editeur Z |
""",
        }

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = """[
{
    "auteur": "Auteur X",
    "titre": "Livre Y",
    "editeur": "Editeur Z",
    "note_moyenne": 7.5,
    "nb_critiques": 3,
    "coups_de_coeur": []
}
]"""

        # Mock le client Azure directement sur l'instance du service
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        llm_service.client = mock_client

        result = await llm_service.extract_books_from_reviews([mock_avis])

        assert len(result) == 1
        book = result[0]
        assert book["episode_oid"] == "other_episode_oid"
        assert book["episode_title"] == "Autre Episode"
        assert book["episode_date"] == "15 fév. 2025"
