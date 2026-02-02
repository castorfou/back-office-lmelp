"""
Tests de performance pour les méthodes optimisées de StatsService.

Ces tests vérifient que les optimisations utilisent des stratégies efficaces :
- Aggregation pipelines pour _count_emissions_sans_avis
- Batch fetching pour _count_emissions_with_problems
"""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from back_office_lmelp.services.stats_service import StatsService


@pytest.fixture
def mock_mongodb_service():
    """Mock MongoDB service with collections."""
    service = MagicMock()
    service.get_collection = MagicMock()
    service.avis_collection = MagicMock()
    service.livres_collection = MagicMock()
    return service


class TestCountEmissionsSansAvisOptimization:
    """Tests pour _count_emissions_sans_avis optimisé."""

    def test_uses_aggregation_pipeline(self, mock_mongodb_service):
        """Vérifie que la méthode utilise un pipeline d'aggregation."""
        # Arrange
        mock_collection = MagicMock()
        mock_mongodb_service.get_collection.return_value = mock_collection
        mock_collection.aggregate.return_value = [{"total": 42}]

        stats_service = StatsService()
        stats_service.mongodb_service = mock_mongodb_service

        # Act
        result = stats_service._count_emissions_sans_avis()

        # Assert
        assert result == 42
        mock_collection.aggregate.assert_called_once()
        pipeline = mock_collection.aggregate.call_args[0][0]
        # Vérifier la structure du pipeline
        assert any("$lookup" in stage for stage in pipeline), (
            "Pipeline should contain $lookup stage"
        )
        assert any("$match" in stage for stage in pipeline), (
            "Pipeline should contain $match stage"
        )

    def test_returns_zero_when_no_results(self, mock_mongodb_service):
        """Edge case: aucune émission sans avis."""
        mock_collection = MagicMock()
        mock_mongodb_service.get_collection.return_value = mock_collection
        mock_collection.aggregate.return_value = []

        stats_service = StatsService()
        stats_service.mongodb_service = mock_mongodb_service

        result = stats_service._count_emissions_sans_avis()

        assert result == 0

    def test_aggregation_pipeline_structure(self, mock_mongodb_service):
        """Vérifie la structure exacte du pipeline d'aggregation."""
        mock_collection = MagicMock()
        mock_mongodb_service.get_collection.return_value = mock_collection
        mock_collection.aggregate.return_value = [{"total": 5}]

        stats_service = StatsService()
        stats_service.mongodb_service = mock_mongodb_service

        stats_service._count_emissions_sans_avis()

        pipeline = mock_collection.aggregate.call_args[0][0]

        # Vérifier les étapes clés
        lookup_stages = [stage for stage in pipeline if "$lookup" in stage]
        assert len(lookup_stages) > 0, "Should have at least 1 $lookup stage"

        # Vérifier le lookup des avis
        lookup_stage = lookup_stages[0]
        assert lookup_stage["$lookup"]["from"] == "avis"
        assert lookup_stage["$lookup"]["localField"] == "emission_id_str"
        assert lookup_stage["$lookup"]["foreignField"] == "emission_oid"

        # Vérifier le match pour avis_count == 0
        match_stages = [stage for stage in pipeline if "$match" in stage]
        assert len(match_stages) > 0, "Should have at least 1 $match stage"


class TestCountEmissionsWithProblemsOptimization:
    """Tests pour _count_emissions_with_problems optimisé."""

    def test_uses_batch_fetching_not_iteration(self, mock_mongodb_service):
        """Vérifie que la méthode utilise batch fetching au lieu d'itération."""
        # Arrange
        emissions_collection = MagicMock()
        avis_collection = MagicMock()
        livres_collection = MagicMock()

        mock_mongodb_service.get_collection.side_effect = lambda name: {
            "emissions": emissions_collection,
            "avis": avis_collection,
            "livres": livres_collection,
        }[name]

        # Mock emissions data (1 emission)
        emissions_collection.find.return_value = [
            {"_id": ObjectId(), "episode_id": "ep1"}
        ]

        # Mock avis data (pas d'avis pour cette émission)
        avis_collection.find.return_value = []

        stats_service = StatsService()
        stats_service.mongodb_service = mock_mongodb_service

        # Act
        stats_service._count_emissions_with_problems()

        # Assert
        # Vérifie batch fetching (2 requêtes au total, pas N requêtes)
        assert emissions_collection.find.call_count == 1, (
            "Should fetch all emissions in single query"
        )
        assert avis_collection.find.call_count == 1, (
            "Should fetch all avis in single query"
        )

    def test_counts_unmatched_emissions(self, mock_mongodb_service):
        """Vérifie le comptage des émissions avec livres non matchés (badge jaune)."""
        emissions_collection = MagicMock()
        avis_collection = MagicMock()
        livres_collection = MagicMock()

        mock_mongodb_service.get_collection.side_effect = lambda name: {
            "emissions": emissions_collection,
            "avis": avis_collection,
            "livres": livres_collection,
        }[name]

        emission_id = ObjectId()
        emissions_collection.find.return_value = [
            {"_id": emission_id, "episode_id": "ep1"}
        ]

        # Avis avec livre non matché (livre_oid = None)
        avis_collection.find.return_value = [
            {
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "Book 1",
                "livre_oid": None,  # Non matché
                "note": 4,
            }
        ]

        # 1 livre dans MongoDB pour cet épisode
        livres_collection.count_documents.return_value = 1

        stats_service = StatsService()
        stats_service.mongodb_service = mock_mongodb_service

        result = stats_service._count_emissions_with_problems()

        # Devrait compter 1 (livre non matché = badge jaune = problème)
        assert result == 1

    def test_counts_count_mismatch_emissions(self, mock_mongodb_service):
        """Vérifie le comptage des émissions avec écart de comptage (badge rouge)."""
        emissions_collection = MagicMock()
        avis_collection = MagicMock()
        livres_collection = MagicMock()

        mock_mongodb_service.get_collection.side_effect = lambda name: {
            "emissions": emissions_collection,
            "avis": avis_collection,
            "livres": livres_collection,
        }[name]

        emission_id = ObjectId()
        emissions_collection.find.return_value = [
            {"_id": emission_id, "episode_id": "ep1"}
        ]

        # 1 avis extrait du summary
        avis_collection.find.return_value = [
            {
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "Book 1",
                "livre_oid": ObjectId(),  # Matché
                "note": 4,
            }
        ]

        # Mais 2 livres dans MongoDB (écart de comptage)
        livres_collection.count_documents.return_value = 2

        stats_service = StatsService()
        stats_service.mongodb_service = mock_mongodb_service

        result = stats_service._count_emissions_with_problems()

        # Devrait compter 1 (écart de comptage = badge rouge = problème)
        assert result == 1

    def test_counts_missing_notes(self, mock_mongodb_service):
        """Vérifie le comptage des émissions avec notes manquantes (badge rouge)."""
        emissions_collection = MagicMock()
        avis_collection = MagicMock()
        livres_collection = MagicMock()

        mock_mongodb_service.get_collection.side_effect = lambda name: {
            "emissions": emissions_collection,
            "avis": avis_collection,
            "livres": livres_collection,
        }[name]

        emission_id = ObjectId()
        emissions_collection.find.return_value = [
            {"_id": emission_id, "episode_id": "ep1"}
        ]

        # 1 avis avec note manquante
        avis_collection.find.return_value = [
            {
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "Book 1",
                "livre_oid": ObjectId(),
                "note": None,  # Note manquante
            }
        ]

        # 1 livre dans MongoDB (comptes égaux)
        livres_collection.count_documents.return_value = 1

        stats_service = StatsService()
        stats_service.mongodb_service = mock_mongodb_service

        result = stats_service._count_emissions_with_problems()

        # Devrait compter 1 (note manquante = badge rouge = problème)
        assert result == 1

    def test_ignores_emissions_without_avis(self, mock_mongodb_service):
        """Vérifie que les émissions sans avis ne sont pas comptées."""
        emissions_collection = MagicMock()
        avis_collection = MagicMock()
        livres_collection = MagicMock()

        mock_mongodb_service.get_collection.side_effect = lambda name: {
            "emissions": emissions_collection,
            "avis": avis_collection,
            "livres": livres_collection,
        }[name]

        emissions_collection.find.return_value = [
            {"_id": ObjectId(), "episode_id": "ep1"}
        ]

        # Aucun avis
        avis_collection.find.return_value = []

        stats_service = StatsService()
        stats_service.mongodb_service = mock_mongodb_service

        result = stats_service._count_emissions_with_problems()

        # Devrait retourner 0 (pas d'avis = badge blanc ≠ problème)
        assert result == 0

    def test_ignores_perfect_emissions(self, mock_mongodb_service):
        """Vérifie que les émissions parfaites ne sont pas comptées."""
        emissions_collection = MagicMock()
        avis_collection = MagicMock()
        livres_collection = MagicMock()

        mock_mongodb_service.get_collection.side_effect = lambda name: {
            "emissions": emissions_collection,
            "avis": avis_collection,
            "livres": livres_collection,
        }[name]

        emission_id = ObjectId()
        emissions_collection.find.return_value = [
            {"_id": emission_id, "episode_id": "ep1"}
        ]

        # Avis parfait : matché + note présente
        avis_collection.find.return_value = [
            {
                "emission_oid": str(emission_id),
                "livre_titre_extrait": "Book 1",
                "livre_oid": ObjectId(),  # Matché
                "note": 4,  # Note présente
            }
        ]

        # Comptes égaux (1 avis = 1 livre)
        livres_collection.count_documents.return_value = 1

        stats_service = StatsService()
        stats_service.mongodb_service = mock_mongodb_service

        result = stats_service._count_emissions_with_problems()

        # Devrait retourner 0 (parfait = badge vert ≠ problème)
        assert result == 0
