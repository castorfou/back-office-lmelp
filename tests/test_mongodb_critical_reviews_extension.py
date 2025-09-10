"""Tests pour l'extension du service MongoDB pour les avis critiques."""

from unittest.mock import Mock

import pytest

from back_office_lmelp.services.mongodb_service import MongoDBService


@pytest.fixture
def mongodb_service():
    """Service MongoDB pour les tests."""
    service = MongoDBService()
    service.client = Mock()
    service.db = Mock()
    service.episodes_collection = Mock()
    service.avis_critiques_collection = Mock()
    return service


@pytest.fixture
def mock_avis_critiques_data():
    """Données mock d'avis critiques."""
    return [
        {
            "_id": "686c489c28b9e451c1cee318",  # pragma: allowlist secret
            "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
            "episode_title": 'Les critiques littéraires du Masque & la Plume depuis le festival "Quai du Polar" à Lyon',
            "episode_date": "29 juin 2025",
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME du 29 juin 2025
| Auteur | Titre | Éditeur | Avis détaillés des critiques |
|--------|-------|---------|------------------------------|
| Aslak Nord | Piège à loup | Le bruit du monde | **Patricia Martin**: "Largement au-dessus du lot" (10) |
""",
            "created_at": "2025-07-07T22:22:20.391Z",
            "updated_at": "2025-07-07T22:22:20.391Z",
        },
        {
            "_id": "686c48b728b9e451c1cee31f",  # pragma: allowlist secret
            "episode_oid": "686bf5e18380ee925ae5e318",  # pragma: allowlist secret
            "episode_title": "Faut-il lire Raphaël Quenard, Miranda July, Mario Vargas Llosa, Etgar Keret… cet été ?",
            "episode_date": "06 juil. 2025",
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME
| Auteur | Titre | Éditeur | Avis détaillés des critiques |
|--------|-------|---------|------------------------------|
| Edgar Keret | Correction automatique | Éditions de l'Olivier | **Blandine Rinkel**: "Fantaisiste et grave à la fois" - 7 |
""",
            "created_at": "2025-07-07T22:22:47.408Z",
            "updated_at": "2025-07-07T22:22:47.408Z",
        },
    ]


class TestMongoDBCriticalReviewsExtension:
    """Tests pour les méthodes d'avis critiques du service MongoDB."""

    def test_get_all_critical_reviews_success(
        self, mongodb_service, mock_avis_critiques_data
    ):
        """Test de récupération réussie de tous les avis critiques."""
        # Configuration du mock
        mongodb_service.avis_critiques_collection.find.return_value.sort.return_value = mock_avis_critiques_data

        result = mongodb_service.get_all_critical_reviews()

        # Vérifications
        assert len(result) == 2
        assert (
            result[0]["episode_oid"]
            == "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
        )
        assert (
            result[1]["episode_oid"]
            == "686bf5e18380ee925ae5e318"  # pragma: allowlist secret
        )

        # Vérifier que la méthode MongoDB est appelée correctement
        mongodb_service.avis_critiques_collection.find.assert_called_once_with({})
        mongodb_service.avis_critiques_collection.find.return_value.sort.assert_called_once_with(
            "created_at", -1
        )

    def test_get_all_critical_reviews_with_limit(
        self, mongodb_service, mock_avis_critiques_data
    ):
        """Test de récupération avec limite."""
        # Configuration du mock pour la limite
        limited_data = mock_avis_critiques_data[:1]
        mongodb_service.avis_critiques_collection.find.return_value.sort.return_value.limit.return_value = limited_data

        result = mongodb_service.get_all_critical_reviews(limit=1)

        assert len(result) == 1
        assert (
            result[0]["episode_oid"]
            == "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
        )

        # Vérifier que la limite est appliquée
        mongodb_service.avis_critiques_collection.find.return_value.sort.return_value.limit.assert_called_once_with(
            1
        )

    def test_get_all_critical_reviews_no_connection(self, mongodb_service):
        """Test quand la connexion MongoDB n'est pas établie."""
        mongodb_service.avis_critiques_collection = None

        with pytest.raises(Exception, match="Connexion MongoDB non établie"):
            mongodb_service.get_all_critical_reviews()

    def test_get_all_critical_reviews_mongodb_error(self, mongodb_service):
        """Test de gestion d'erreur MongoDB."""
        mongodb_service.avis_critiques_collection.find.side_effect = Exception(
            "MongoDB connection error"
        )

        result = mongodb_service.get_all_critical_reviews()

        # En cas d'erreur, retourner une liste vide
        assert result == []

    def test_get_all_critical_reviews_objectid_conversion(self, mongodb_service):
        """Test de la conversion des ObjectId en string."""
        from bson import ObjectId

        mock_data_with_objectid = [
            {
                "_id": ObjectId("686c489c28b9e451c1cee318"),
                "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
                "episode_title": "Test Episode",
                "summary": "Test summary",
            }
        ]

        mongodb_service.avis_critiques_collection.find.return_value.sort.return_value = mock_data_with_objectid

        result = mongodb_service.get_all_critical_reviews()

        assert len(result) == 1
        assert isinstance(result[0]["_id"], str)
        assert result[0]["_id"] == "686c489c28b9e451c1cee318"

    def test_get_critical_reviews_by_episode_oid(
        self, mongodb_service, mock_avis_critiques_data
    ):
        """Test de récupération d'avis critiques par episode_oid."""
        target_episode_oid = "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
        filtered_data = [
            item
            for item in mock_avis_critiques_data
            if item["episode_oid"] == target_episode_oid
        ]

        mongodb_service.avis_critiques_collection.find.return_value.sort.return_value = filtered_data

        result = mongodb_service.get_critical_reviews_by_episode_oid(target_episode_oid)

        assert len(result) == 1
        assert result[0]["episode_oid"] == target_episode_oid

        # Vérifier que le filtre est appliqué
        mongodb_service.avis_critiques_collection.find.assert_called_once_with(
            {"episode_oid": target_episode_oid}
        )

    def test_get_critical_reviews_by_episode_oid_not_found(self, mongodb_service):
        """Test quand aucun avis critique n'est trouvé pour l'episode_oid."""
        mongodb_service.avis_critiques_collection.find.return_value.sort.return_value = []

        result = mongodb_service.get_critical_reviews_by_episode_oid("nonexistent_oid")

        assert result == []

    def test_get_critical_reviews_by_episode_oid_no_connection(self, mongodb_service):
        """Test quand la connexion MongoDB n'est pas établie."""
        mongodb_service.avis_critiques_collection = None

        with pytest.raises(Exception, match="Connexion MongoDB non établie"):
            mongodb_service.get_critical_reviews_by_episode_oid(
                "test_oid"
            )  # pragma: allowlist secret

    def test_get_all_critical_reviews_default_sort_order(
        self, mongodb_service, mock_avis_critiques_data
    ):
        """Test que les avis critiques sont triés par date de création décroissante par défaut."""
        # Les données mock sont déjà dans l'ordre attendu (plus récent en premier)
        mongodb_service.avis_critiques_collection.find.return_value.sort.return_value = mock_avis_critiques_data

        _ = mongodb_service.get_all_critical_reviews()

        # Vérifier l'ordre: le plus récent (2025-07-07T22:22:47) devrait être en premier
        # mais nos données de test inversent cet ordre, donc vérifier que sort() est appelé correctement
        mongodb_service.avis_critiques_collection.find.return_value.sort.assert_called_once_with(
            "created_at", -1
        )

    def test_get_all_critical_reviews_fields_validation(self, mongodb_service):
        """Test que tous les champs nécessaires sont présents dans les résultats."""
        required_fields = [
            "_id",
            "episode_oid",
            "episode_title",
            "episode_date",
            "summary",
        ]

        mock_data_complete = [
            {
                "_id": "test_id",
                "episode_oid": "test_episode_oid",
                "episode_title": "Test Episode Title",
                "episode_date": "01 jan. 2025",
                "summary": "Test summary with book data",
                "created_at": "2025-01-07T10:00:00Z",
                "updated_at": "2025-01-07T10:00:00Z",
            }
        ]

        mongodb_service.avis_critiques_collection.find.return_value.sort.return_value = mock_data_complete

        result = mongodb_service.get_all_critical_reviews()

        assert len(result) == 1
        review = result[0]

        for field in required_fields:
            assert field in review, f"Champ manquant: {field}"

        # Vérifier les types des champs critiques
        assert isinstance(review["episode_oid"], str)
        assert isinstance(review["episode_title"], str)
        assert isinstance(review["episode_date"], str)
        assert isinstance(review["summary"], str)
