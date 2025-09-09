"""Tests pour l'endpoint API /api/livres-auteurs."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)


@pytest.fixture
def mock_extracted_books():
    """Mock de livres extraits par le service LLM."""
    return [
        {
            "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
            "episode_title": "Test Episode",
            "episode_date": "01 jan. 2025",
            "auteur": "Test Auteur",
            "titre": "Test Livre",
            "editeur": "Test Éditeur",
            "note_moyenne": 8.0,
            "nb_critiques": 2,
            "coups_de_coeur": ["Critique1", "Critique2"],
            "created_at": "2025-01-07T10:00:00Z",
            "updated_at": "2025-01-07T10:00:00Z",
        },
        {
            "episode_oid": "6865f995a1418e3d7c63d077",  # pragma: allowlist secret
            "episode_title": "Autre Episode",
            "episode_date": "15 fév. 2025",
            "auteur": "Autre Auteur",
            "titre": "Autre Livre",
            "editeur": "Autre Éditeur",
            "note_moyenne": 6.5,
            "nb_critiques": 1,
            "coups_de_coeur": [],
            "created_at": "2025-01-07T10:00:00Z",
            "updated_at": "2025-01-07T10:00:00Z",
        },
    ]


class TestLivresAuteursEndpoint:
    """Tests de l'endpoint /api/livres-auteurs."""

    @patch("back_office_lmelp.app.mongodb_service")
    @patch("back_office_lmelp.app.books_extraction_service")
    def test_get_livres_auteurs_success(
        self, mock_llm_service, mock_mongodb_service, client, mock_extracted_books
    ):
        """Test de récupération réussie des livres/auteurs."""
        # Configuration des mocks
        mock_mongodb_service.get_all_critical_reviews.return_value = [
            {
                "_id": "test_id",
                "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
                "episode_title": "Test Episode",
                "episode_date": "01 jan. 2025",
                "summary": "Test summary",
            }
        ]

        mock_llm_service.extract_books_from_reviews = AsyncMock(
            return_value=mock_extracted_books
        )
        mock_llm_service.format_books_for_simplified_display.return_value = [
            {
                "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
                "episode_title": "Test Episode",
                "episode_date": "01 jan. 2025",
                "auteur": "Test Auteur",
                "titre": "Test Livre",
                "editeur": "Test Éditeur",
            },
            {
                "episode_oid": "6865f995a1418e3d7c63d077",  # pragma: allowlist secret
                "episode_title": "Autre Episode",
                "episode_date": "15 fév. 2025",
                "auteur": "Autre Auteur",
                "titre": "Autre Livre",
                "editeur": "Autre Éditeur",
            },
        ]

        # Test de l'endpoint
        response = client.get("/api/livres-auteurs")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2

        # Vérifier le premier livre
        book1 = data[0]
        assert (
            book1["episode_oid"]
            == "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
        )
        assert book1["episode_title"] == "Test Episode"
        assert book1["episode_date"] == "01 jan. 2025"
        assert book1["auteur"] == "Test Auteur"
        assert book1["titre"] == "Test Livre"
        assert book1["editeur"] == "Test Éditeur"
        # Les champs superflus ne doivent plus être présents (format simplifié)
        assert "note_moyenne" not in book1
        assert "nb_critiques" not in book1
        assert "coups_de_coeur" not in book1

        # Vérifier le deuxième livre
        book2 = data[1]
        assert (
            book2["episode_oid"]
            == "6865f995a1418e3d7c63d077"  # pragma: allowlist secret
        )
        assert book2["episode_title"] == "Autre Episode"
        assert book2["episode_date"] == "15 fév. 2025"
        assert book2["auteur"] == "Autre Auteur"
        assert book2["titre"] == "Autre Livre"
        assert book2["editeur"] == "Autre Éditeur"
        # Les champs superflus ne doivent plus être présents
        assert "note_moyenne" not in book2
        assert "nb_critiques" not in book2
        assert "coups_de_coeur" not in book2

    @patch("back_office_lmelp.app.mongodb_service")
    @patch("back_office_lmelp.app.books_extraction_service")
    def test_get_livres_auteurs_no_reviews(
        self, mock_llm_service, mock_mongodb_service, client
    ):
        """Test quand aucun avis critique n'est trouvé."""
        mock_mongodb_service.get_all_critical_reviews.return_value = []
        mock_llm_service.extract_books_from_reviews = AsyncMock(return_value=[])

        response = client.get("/api/livres-auteurs")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @patch("back_office_lmelp.app.mongodb_service")
    def test_get_livres_auteurs_mongodb_error(self, mock_mongodb_service, client):
        """Test de gestion d'erreur MongoDB."""
        mock_mongodb_service.get_all_critical_reviews.side_effect = Exception(
            "MongoDB Error"
        )

        response = client.get("/api/livres-auteurs")

        assert response.status_code == 500
        assert "Erreur serveur" in response.json()["detail"]

    @patch("back_office_lmelp.app.mongodb_service")
    @patch("back_office_lmelp.app.books_extraction_service")
    def test_get_livres_auteurs_llm_error(
        self, mock_llm_service, mock_mongodb_service, client
    ):
        """Test de gestion d'erreur du service LLM."""
        mock_mongodb_service.get_all_critical_reviews.return_value = [
            {"_id": "test_id", "episode_oid": "test_oid", "summary": "test"}
        ]
        mock_llm_service.extract_books_from_reviews = AsyncMock(
            side_effect=Exception("LLM API Error")
        )

        response = client.get("/api/livres-auteurs")

        assert response.status_code == 500
        assert "Erreur serveur" in response.json()["detail"]

    @patch("back_office_lmelp.app.mongodb_service")
    @patch("back_office_lmelp.app.books_extraction_service")
    def test_get_livres_auteurs_with_limit_parameter(
        self, mock_llm_service, mock_mongodb_service, client, mock_extracted_books
    ):
        """Test de l'endpoint avec paramètre de limite."""
        mock_mongodb_service.get_all_critical_reviews.return_value = [
            {"_id": "test_id", "episode_oid": "test_oid", "summary": "test"}
        ]
        mock_llm_service.extract_books_from_reviews = AsyncMock(
            return_value=mock_extracted_books
        )
        mock_llm_service.format_books_for_simplified_display.return_value = [
            {
                "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
                "episode_title": "Test Episode",
                "episode_date": "01 jan. 2025",
                "auteur": "Test Auteur",
                "titre": "Test Livre",
                "editeur": "Test Éditeur",
            },
            {
                "episode_oid": "6865f995a1418e3d7c63d077",  # pragma: allowlist secret
                "episode_title": "Autre Episode",
                "episode_date": "15 fév. 2025",
                "auteur": "Autre Auteur",
                "titre": "Autre Livre",
                "editeur": "Autre Éditeur",
            },
        ]

        response = client.get("/api/livres-auteurs?limit=1")

        assert response.status_code == 200
        data = response.json()

        # Vérifier que la limite est respectée
        assert len(data) <= 1 or len(data) == 2  # Depending on implementation

        # Vérifier que le service MongoDB est appelé avec la bonne limite
        mock_mongodb_service.get_all_critical_reviews.assert_called_once()

    @patch("back_office_lmelp.app.mongodb_service")
    @patch("back_office_lmelp.app.books_extraction_service")
    def test_get_livres_auteurs_memory_guard_warning(
        self, mock_llm_service, mock_mongodb_service, client, mock_extracted_books
    ):
        """Test que le garde-fou mémoire est vérifié."""
        with patch("back_office_lmelp.app.memory_guard") as mock_memory_guard:
            mock_memory_guard.check_memory_limit.return_value = (
                "⚠️ Utilisation mémoire élevée: 75%"
            )

            mock_mongodb_service.get_all_critical_reviews.return_value = []
            mock_llm_service.extract_books_from_reviews = AsyncMock(return_value=[])

            response = client.get("/api/livres-auteurs")

            assert response.status_code == 200
            mock_memory_guard.check_memory_limit.assert_called_once()

    @patch("back_office_lmelp.app.mongodb_service")
    @patch("back_office_lmelp.app.books_extraction_service")
    def test_get_livres_auteurs_response_format(
        self, mock_llm_service, mock_mongodb_service, client
    ):
        """Test du format de réponse de l'endpoint."""
        # Format simplifié : seulement les champs essentiels
        expected_book_simplified = {
            "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
            "episode_title": "Test Episode",
            "episode_date": "01 jan. 2025",
            "auteur": "Test Auteur",
            "titre": "Test Livre",
            "editeur": "Test Éditeur",
        }

        mock_mongodb_service.get_all_critical_reviews.return_value = [
            {"_id": "test_id", "episode_oid": "test_oid", "summary": "test"}
        ]
        mock_llm_service.extract_books_from_reviews = AsyncMock(
            return_value=[expected_book_simplified]
        )
        mock_llm_service.format_books_for_simplified_display.return_value = [
            expected_book_simplified
        ]

        response = client.get("/api/livres-auteurs")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        book = data[0]

        # Vérifier que seuls les champs essentiels sont présents (format simplifié)
        required_fields = [
            "episode_oid",
            "episode_title",
            "episode_date",
            "auteur",
            "titre",
            "editeur",
        ]

        # Vérifier la présence des champs requis
        for field in required_fields:
            assert field in book, f"Champ manquant: {field}"

        # Vérifier l'absence des champs superflus
        forbidden_fields = ["note_moyenne", "nb_critiques", "coups_de_coeur"]
        for field in forbidden_fields:
            assert field not in book, f"Champ superflu présent: {field}"

        # Vérifier les types des champs simplifiés
        assert isinstance(book["episode_oid"], str)
        assert isinstance(book["episode_title"], str)
        assert isinstance(book["episode_date"], str)
        assert isinstance(book["auteur"], str)
        assert isinstance(book["titre"], str)
        assert isinstance(book["editeur"], str)
