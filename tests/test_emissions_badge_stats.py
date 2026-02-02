"""Tests TDD pour les statistiques de badges d'émissions (Issue #185)."""

from unittest.mock import MagicMock, patch


class TestEmissionsBadgeStatistics:
    """Tests pour les statistiques de comptage des badges d'émissions."""

    def setup_method(self):
        """Setup pour chaque test."""
        # Importer stats_service
        from back_office_lmelp.services.stats_service import stats_service

        self.stats_service = stats_service

        # Patcher mongodb_service après l'import
        self.mock_mongodb = MagicMock()
        self.stats_service.mongodb_service = self.mock_mongodb

    def teardown_method(self):
        """Teardown après chaque test."""
        # Réinitialiser mongodb_service à None pour éviter les side effects
        self.stats_service.mongodb_service = None

    def test_get_cache_statistics_should_include_emissions_badge_stats(self):
        """
        Test TDD: Les statistiques du cache doivent inclure les nouvelles métriques.

        Nouvelles métriques:
        - emissions_sans_avis: Nombre de pastilles grises (⚪)
        - emissions_with_problems: Nombre de pastilles rouges (🔴) + jaunes (🟡)
        """
        # Mock des autres services nécessaires
        self.mock_mongodb.get_collection = MagicMock()

        # Mock cache_service pour retourner stats de base
        mock_cache_service = MagicMock()
        mock_cache_service.get_statistics_from_cache.return_value = {
            "couples_en_base": 100,
            "episodes_non_traites": 10,
        }
        self.stats_service.cache_service = mock_cache_service

        # Mock les méthodes de comptage privées
        with (
            patch.object(
                self.stats_service, "_count_books_without_url_babelio", return_value=15
            ),
            patch.object(
                self.stats_service, "_count_authors_without_url_babelio", return_value=8
            ),
            patch.object(
                self.stats_service, "_get_last_episode_date", return_value="2025-10-15"
            ),
            patch.object(
                self.stats_service,
                "_count_episodes_without_avis_critiques",
                return_value=5,
            ),
            patch.object(
                self.stats_service,
                "_count_avis_critiques_without_analysis",
                return_value=3,
            ),
            patch.object(
                self.stats_service, "_count_emissions_sans_avis", return_value=12
            ),
            patch.object(
                self.stats_service, "_count_emissions_with_problems", return_value=8
            ),
        ):
            # EXECUTE
            stats = self.stats_service.get_cache_statistics()

        # ASSERT: Les nouvelles métriques doivent être présentes
        assert "emissions_sans_avis" in stats
        assert "emissions_with_problems" in stats
        assert stats["emissions_sans_avis"] == 12  # 12 pastilles grises
        assert stats["emissions_with_problems"] == 8  # 8 pastilles rouge+jaune

    def test_count_emissions_sans_avis_should_return_zero_if_all_have_avis(self):
        """Test TDD: Retourner 0 si toutes les émissions ont des avis extraits."""
        # Mock emissions collection retourne une liste vide
        mock_emissions_col = MagicMock()
        mock_emissions_col.find.return_value = []
        self.mock_mongodb.get_collection.return_value = mock_emissions_col

        # EXECUTE
        count = self.stats_service._count_emissions_sans_avis()

        # ASSERT
        assert count == 0

    def test_count_emissions_with_problems_should_return_zero_if_all_perfect(self):
        """Test TDD: Retourner 0 si toutes les émissions sont parfaites (🟢)."""
        # Mock emissions collection retourne une liste vide
        mock_emissions_col = MagicMock()
        mock_emissions_col.find.return_value = []
        self.mock_mongodb.get_collection.return_value = mock_emissions_col

        # EXECUTE
        count = self.stats_service._count_emissions_with_problems()

        # ASSERT
        assert count == 0

    def test_count_emissions_sans_avis_should_calculate_badge_when_not_persisted(self):
        """
        Test TDD: Calculer le badge dynamiquement quand badge_status n'existe pas en base.

        PROBLÈME RÉEL: badge_status n'est PAS persisté dans MongoDB, il est calculé à la volée.
        Les requêtes count_documents({badge_status: X}) retournent toujours 0.

        SOLUTION (optimisée Issue #194): Utiliser pipeline d'aggregation MongoDB au lieu
        d'itérer avec N requêtes.

        Cette méthode utilise maintenant un pipeline d'aggregation avec $lookup et $count.
        """
        # Mock emissions collection - la méthode optimisée utilise aggregation
        mock_emissions_col = MagicMock()

        # Mock aggregation result: 1 émission sans avis
        # (emission1_id n'a pas d'avis, emission2_id et emission3_id en ont)
        mock_emissions_col.aggregate.return_value = [{"total": 1}]

        def get_collection_side_effect(name):
            """Route vers la bonne collection mockée."""
            if name == "emissions":
                return mock_emissions_col
            return MagicMock()

        self.mock_mongodb.get_collection.side_effect = get_collection_side_effect

        # EXECUTE
        count = self.stats_service._count_emissions_sans_avis()

        # ASSERT: Devrait retourner 1 (seulement la première émission)
        assert count == 1

        # Vérifier que la méthode utilise bien aggregation
        mock_emissions_col.aggregate.assert_called_once()

        # Vérifier la structure du pipeline (lookup + match + count)
        pipeline = mock_emissions_col.aggregate.call_args[0][0]
        assert any("$lookup" in stage for stage in pipeline), (
            "Pipeline should contain $lookup stage"
        )
        assert any("$match" in stage for stage in pipeline), (
            "Pipeline should contain $match stage for avis_count == 0"
        )
        assert any("$count" in stage for stage in pipeline), (
            "Pipeline should contain $count stage"
        )
