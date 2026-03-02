"""Tests pour le service de recommandations par collaborative filtering.

Approche TDD :
- Les mocks sont construits depuis les vraies structures MongoDB (Issue #150)
- Types réels vérifiés : critique_oid=String, livre_oid=String, note=Number
"""

from unittest.mock import MagicMock

import pytest

from back_office_lmelp.services.recommendation_service import RecommendationService


# ---------------------------------------------------------------------------
# Données réelles de référence (vérifiées par MCP MongoDB)
# avis: critique_oid=String, livre_oid=String, note=Number (int)
# critiques: _id=ObjectId, nom=String
# livres: _id=ObjectId, titre=String, auteur_id=ObjectId
# auteurs: _id=ObjectId, nom=String
# ---------------------------------------------------------------------------

MOCK_AVIS_DATA = [
    # Critique A (critique_1) a noté 3 livres
    {"critique_oid": "critique_1", "livre_oid": "livre_1", "note": 8},
    {"critique_oid": "critique_1", "livre_oid": "livre_2", "note": 9},
    {"critique_oid": "critique_1", "livre_oid": "livre_3", "note": 7},
    {"critique_oid": "critique_1", "livre_oid": "livre_4", "note": 6},
    {"critique_oid": "critique_1", "livre_oid": "livre_5", "note": 5},
    {"critique_oid": "critique_1", "livre_oid": "livre_6", "note": 8},
    {"critique_oid": "critique_1", "livre_oid": "livre_7", "note": 9},
    {"critique_oid": "critique_1", "livre_oid": "livre_8", "note": 7},
    {"critique_oid": "critique_1", "livre_oid": "livre_9", "note": 6},
    {"critique_oid": "critique_1", "livre_oid": "livre_10", "note": 5},
    {"critique_oid": "critique_1", "livre_oid": "livre_11", "note": 8},
    # Critique B (critique_2) a noté 11 livres
    {"critique_oid": "critique_2", "livre_oid": "livre_1", "note": 7},
    {"critique_oid": "critique_2", "livre_oid": "livre_2", "note": 8},
    {"critique_oid": "critique_2", "livre_oid": "livre_3", "note": 6},
    {"critique_oid": "critique_2", "livre_oid": "livre_4", "note": 9},
    {"critique_oid": "critique_2", "livre_oid": "livre_5", "note": 8},
    {"critique_oid": "critique_2", "livre_oid": "livre_6", "note": 7},
    {"critique_oid": "critique_2", "livre_oid": "livre_7", "note": 9},
    {"critique_oid": "critique_2", "livre_oid": "livre_8", "note": 6},
    {"critique_oid": "critique_2", "livre_oid": "livre_9", "note": 8},
    {"critique_oid": "critique_2", "livre_oid": "livre_10", "note": 7},
    {"critique_oid": "critique_2", "livre_oid": "livre_11", "note": 8},
    # Critique C (critique_3) a noté seulement 5 livres → doit être filtré (< 10 avis)
    {"critique_oid": "critique_3", "livre_oid": "livre_1", "note": 9},
    {"critique_oid": "critique_3", "livre_oid": "livre_2", "note": 7},
    {"critique_oid": "critique_3", "livre_oid": "livre_3", "note": 8},
    {"critique_oid": "critique_3", "livre_oid": "livre_4", "note": 6},
    {"critique_oid": "critique_3", "livre_oid": "livre_5", "note": 9},
    # "Moi" a noté livre_1 dans Calibre (rating Calibre = 80 → note 8 sur 10)
    # livre_1 sera donc exclu des recommandations
]

# Livres Calibre de l'utilisateur (rating Calibre : 2-10 par pas de 2, scale directe)
MOCK_CALIBRE_BOOKS = [
    {"id": 1, "title": "Livre Un", "authors": ["Auteur A"], "rating": 8, "tags": []},
    {
        "id": 2,
        "title": "Livre Deux",
        "authors": ["Auteur B"],
        "rating": None,
        "tags": [],
    },
]

# Structure MongoDB livres (simulée — _id comme string pour simplifier les mocks)
MOCK_LIVRES = [
    {"_id": "livre_1", "titre": "Livre Un", "auteur_id": "auteur_1"},
    {"_id": "livre_2", "titre": "Livre Deux", "auteur_id": "auteur_2"},
    {"_id": "livre_3", "titre": "Livre Trois", "auteur_id": "auteur_1"},
    {"_id": "livre_4", "titre": "Livre Quatre", "auteur_id": "auteur_2"},
    {"_id": "livre_5", "titre": "Livre Cinq", "auteur_id": "auteur_1"},
    {"_id": "livre_6", "titre": "Livre Six", "auteur_id": "auteur_2"},
    {"_id": "livre_7", "titre": "Livre Sept", "auteur_id": "auteur_1"},
    {"_id": "livre_8", "titre": "Livre Huit", "auteur_id": "auteur_2"},
    {"_id": "livre_9", "titre": "Livre Neuf", "auteur_id": "auteur_1"},
    {"_id": "livre_10", "titre": "Livre Dix", "auteur_id": "auteur_2"},
    {"_id": "livre_11", "titre": "Livre Onze", "auteur_id": "auteur_1"},
]

MOCK_AUTEURS = [
    {"_id": "auteur_1", "nom": "Auteur Alpha"},
    {"_id": "auteur_2", "nom": "Auteur Beta"},
]


@pytest.fixture
def mock_calibre_service():
    """Mock du service Calibre."""
    mock = MagicMock()
    mock._available = True
    mock.get_all_books_with_tags.return_value = MOCK_CALIBRE_BOOKS
    return mock


@pytest.fixture
def mock_mongodb_service():
    """Mock du service MongoDB avec collections."""
    mock = MagicMock()
    mock.avis_collection = MagicMock()
    mock.avis_collection.aggregate.return_value = iter(MOCK_AVIS_DATA)
    mock.critiques_collection = MagicMock()
    mock.livres_collection = MagicMock()
    mock.auteurs_collection = MagicMock()
    return mock


@pytest.fixture
def service(mock_calibre_service, mock_mongodb_service):
    """Instance du service de recommandation avec mocks."""
    return RecommendationService(mock_calibre_service, mock_mongodb_service)


class TestRecommendationServiceInit:
    """Tests d'initialisation du service."""

    def test_service_stores_calibre_service(
        self, mock_calibre_service, mock_mongodb_service
    ):
        """Le service conserve une référence au service Calibre."""
        svc = RecommendationService(mock_calibre_service, mock_mongodb_service)
        assert svc._calibre_service is mock_calibre_service

    def test_service_stores_mongodb_service(
        self, mock_calibre_service, mock_mongodb_service
    ):
        """Le service conserve une référence au service MongoDB."""
        svc = RecommendationService(mock_calibre_service, mock_mongodb_service)
        assert svc._mongodb_service is mock_mongodb_service


class TestFilterCritiques:
    """Tests du filtre sur les critiques avec peu d'avis."""

    def test_filter_critiques_with_less_than_10_avis(self, service):
        """Les critiques avec < 10 avis sont exclus du dataset SVD."""
        avis_data = [
            {"critique_oid": "c1", "livre_oid": f"l{i}", "note": 7} for i in range(10)
        ]
        avis_data += [
            {"critique_oid": "c2", "livre_oid": f"l{i}", "note": 8}
            for i in range(5)  # Seulement 5 avis → doit être filtré
        ]

        result = service._filter_active_critiques(avis_data, min_avis=10)

        assert "c1" in result
        assert "c2" not in result

    def test_critique_with_exactly_10_avis_is_kept(self, service):
        """Un critique avec exactement 10 avis est conservé."""
        avis_data = [
            {"critique_oid": "c1", "livre_oid": f"l{i}", "note": 7} for i in range(10)
        ]

        result = service._filter_active_critiques(avis_data, min_avis=10)

        assert "c1" in result


class TestCalibreNotesLoading:
    """Tests du chargement des notes Calibre."""

    def test_load_calibre_notes_returns_dict(self, service):
        """Les notes Calibre sont retournées sous forme de {titre_normalise: note}."""
        result = service._load_calibre_notes()

        assert isinstance(result, dict)

    def test_load_calibre_notes_uses_rating_directly(self, service):
        """Les notes Calibre (2-10 par pas de 2) sont utilisées directement en scale 1-10."""
        result = service._load_calibre_notes()

        # "Livre Un" a rating=8 → 8.0 sur 10 (pas de conversion)
        assert "livre un" in result
        assert result["livre un"] == pytest.approx(8.0)

    def test_load_calibre_notes_excludes_books_without_rating(self, service):
        """Les livres sans note (rating=None) sont exclus."""
        result = service._load_calibre_notes()

        # "Livre Deux" a rating=None → exclu
        assert "livre deux" not in result

    def test_load_calibre_notes_returns_empty_if_calibre_unavailable(
        self, mock_calibre_service, mock_mongodb_service
    ):
        """Si Calibre n'est pas disponible, retourne un dict vide."""
        mock_calibre_service._available = False
        mock_calibre_service.get_all_books_with_tags.return_value = []
        svc = RecommendationService(mock_calibre_service, mock_mongodb_service)

        result = svc._load_calibre_notes()

        assert result == {}


class TestHybridScoreFormula:
    """Tests de la formule de score hybride."""

    def test_hybrid_score_formula(self, service):
        """score = 0.7 * svd_predict + 0.3 * masque_mean."""
        svd_predict = 8.0
        masque_mean = 6.0

        score = service._compute_hybrid_score(svd_predict, masque_mean)

        expected = 0.7 * 8.0 + 0.3 * 6.0
        assert score == pytest.approx(expected)


class TestGetRecommendations:
    """Tests de bout en bout pour get_recommendations."""

    def _setup_mongodb_mocks(self, mock_mongodb_service):
        """Configure les mocks MongoDB pour les tests d'intégration."""
        from bson import ObjectId

        # Mock livres avec vrais ObjectId
        livres_docs = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "titre": "Livre Deux",
                "auteur_id": ObjectId("507f1f77bcf86cd799430001"),
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439013"),
                "titre": "Livre Trois",
                "auteur_id": ObjectId("507f1f77bcf86cd799430001"),
            },
        ]
        mock_mongodb_service.livres_collection.find.return_value = iter(livres_docs)

        # Mock auteurs
        auteurs_docs = [
            {
                "_id": ObjectId("507f1f77bcf86cd799430001"),
                "nom": "Auteur Alpha",
            },
        ]
        mock_mongodb_service.auteurs_collection.find.return_value = iter(auteurs_docs)

    def test_get_recommendations_returns_list(
        self, service, mock_mongodb_service, mock_calibre_service
    ):
        """get_recommendations retourne une liste."""
        self._setup_mongodb_mocks(mock_mongodb_service)
        mock_mongodb_service.critiques_collection.find.return_value = iter([])

        result = service.get_recommendations(top_n=5)

        assert isinstance(result, list)

    def test_get_recommendations_result_has_required_fields(
        self, service, mock_mongodb_service, mock_calibre_service
    ):
        """Chaque recommandation a les champs requis."""
        self._setup_mongodb_mocks(mock_mongodb_service)
        mock_mongodb_service.critiques_collection.find.return_value = iter([])

        result = service.get_recommendations(top_n=5)

        if result:  # Si des recommandations sont retournées
            first = result[0]
            assert "rank" in first
            assert "livre_id" in first
            assert "titre" in first
            assert "auteur_id" in first
            assert "auteur_nom" in first
            assert "score_hybride" in first
            assert "svd_predict" in first
            assert "masque_mean" in first
            assert "masque_count" in first

    def test_get_recommendations_sorted_by_score_descending(
        self, service, mock_mongodb_service, mock_calibre_service
    ):
        """Les recommandations sont triées par score décroissant."""
        self._setup_mongodb_mocks(mock_mongodb_service)
        mock_mongodb_service.critiques_collection.find.return_value = iter([])

        result = service.get_recommendations(top_n=20)

        if len(result) > 1:
            scores = [item["score_hybride"] for item in result]
            assert scores == sorted(scores, reverse=True)

    def test_get_recommendations_rank_starts_at_1(
        self, service, mock_mongodb_service, mock_calibre_service
    ):
        """Le classement commence à 1."""
        self._setup_mongodb_mocks(mock_mongodb_service)
        mock_mongodb_service.critiques_collection.find.return_value = iter([])

        result = service.get_recommendations(top_n=5)

        if result:
            assert result[0]["rank"] == 1

    def test_get_recommendations_respects_top_n(
        self, service, mock_mongodb_service, mock_calibre_service
    ):
        """Le nombre de recommandations ne dépasse pas top_n."""
        self._setup_mongodb_mocks(mock_mongodb_service)
        mock_mongodb_service.critiques_collection.find.return_value = iter([])

        result = service.get_recommendations(top_n=3)

        assert len(result) <= 3

    def test_get_recommendations_returns_empty_when_no_calibre_notes(
        self, mock_calibre_service, mock_mongodb_service
    ):
        """Retourne une liste vide si l'utilisateur n'a pas de notes Calibre."""
        mock_calibre_service._available = False
        mock_calibre_service.get_all_books_with_tags.return_value = []
        svc = RecommendationService(mock_calibre_service, mock_mongodb_service)
        mock_mongodb_service.critiques_collection.find.return_value = iter([])
        self._setup_mongodb_mocks(mock_mongodb_service)

        result = svc.get_recommendations()

        assert result == []

    def test_get_recommendations_returns_empty_when_no_avis(
        self, mock_calibre_service, mock_mongodb_service
    ):
        """Retourne une liste vide si la base d'avis est vide."""
        mock_mongodb_service.avis_collection.aggregate.return_value = iter([])
        mock_mongodb_service.critiques_collection.find.return_value = iter([])
        svc = RecommendationService(mock_calibre_service, mock_mongodb_service)

        result = svc.get_recommendations()

        assert result == []
