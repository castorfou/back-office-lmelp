"""Tests TDD pour les statistiques de badges d'émissions (Issue #185)."""

from unittest.mock import MagicMock, patch

from bson import ObjectId


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

        SOLUTION: Itérer sur toutes les émissions et calculer le badge pour chacune.
        """
        # Créer des IDs stables pour les émissions et épisodes
        emission1_id = ObjectId("111111111111111111111111")
        episode1_id = ObjectId("aaaaaaaaaaaaaaaaaaaaaaaa")

        emission2_id = ObjectId("222222222222222222222222")
        episode2_id = ObjectId("bbbbbbbbbbbbbbbbbbbbbbbb")

        emission3_id = ObjectId("333333333333333333333333")
        episode3_id = ObjectId("cccccccccccccccccccccccc")

        # Mock emissions collection - retourne 3 émissions SANS badge_status
        mock_emissions_col = MagicMock()
        mock_emissions_col.find.return_value = [
            {
                "_id": emission1_id,
                "episode_id": episode1_id,
                "avis_critique_id": ObjectId(),
            },
            {
                "_id": emission2_id,
                "episode_id": episode2_id,
                "avis_critique_id": ObjectId(),
            },
            {
                "_id": emission3_id,
                "episode_id": episode3_id,
                "avis_critique_id": ObjectId(),
            },
        ]

        # Mock avis collection pour simuler les résultats de _calculate_emission_badge_status
        mock_avis_col = MagicMock()

        def avis_count_side_effect(query):
            """Simule les résultats selon l'emission_oid."""
            emission_oid = query.get("emission_oid")
            if not emission_oid:
                return 0
            # Première émission: pas d'avis (no_avis)
            # Deuxième émission: 2 avis (count_mismatch car note manquante)
            # Troisième émission: 3 avis (perfect)
            if emission_oid == str(emission1_id):
                return 0  # no_avis
            elif emission_oid == str(emission2_id):
                return 2
            elif emission_oid == str(emission3_id):
                return 3
            return 0

        def avis_find_side_effect(query):
            """Simule le find pour les avis."""
            emission_oid = query.get("emission_oid")
            if not emission_oid:
                return []
            if emission_oid == str(emission2_id):
                # count_mismatch: note manquante
                return [
                    {
                        "livre_titre_extrait": "L1",
                        "livre_oid": str(ObjectId()),
                        "note": 8,
                    },
                    {
                        "livre_titre_extrait": "L2",
                        "livre_oid": str(ObjectId()),
                        "note": None,
                    },
                ]
            elif emission_oid == str(emission3_id):
                # perfect: tous matchés, notes présentes
                return [
                    {
                        "livre_titre_extrait": "L1",
                        "livre_oid": str(ObjectId()),
                        "note": 8,
                    },
                    {
                        "livre_titre_extrait": "L2",
                        "livre_oid": str(ObjectId()),
                        "note": 7,
                    },
                    {
                        "livre_titre_extrait": "L3",
                        "livre_oid": str(ObjectId()),
                        "note": 9,
                    },
                ]
            return []

        mock_avis_col.count_documents.side_effect = avis_count_side_effect
        mock_avis_col.find.side_effect = avis_find_side_effect

        # Mock livres collection (pour count de livres_mongo)
        mock_livres_col = MagicMock()

        def livres_count_side_effect(query):
            """Simule le count des livres par episode."""
            # La requête utilise {"episodes": str(episode_id)} pas {"episodes": {"$in": ...}}
            episode_id_str = query.get("episodes")
            if not episode_id_str:
                return 0
            if episode_id_str == str(episode2_id):
                return 2  # Même count que summary (pas de mismatch côté count)
            elif episode_id_str == str(episode3_id):
                return 3  # Même count
            return 0

        mock_livres_col.count_documents.side_effect = livres_count_side_effect

        def get_collection_side_effect(name):
            """Route vers la bonne collection mockée."""
            collections = {
                "emissions": mock_emissions_col,
                "avis": mock_avis_col,
                "livres": mock_livres_col,
            }
            return collections.get(name, MagicMock())

        self.mock_mongodb.get_collection.side_effect = get_collection_side_effect
        self.mock_mongodb.avis_collection = mock_avis_col
        self.mock_mongodb.livres_collection = mock_livres_col

        # EXECUTE
        count = self.stats_service._count_emissions_sans_avis()

        # ASSERT: Devrait retourner 1 (seulement la première émission)
        assert count == 1
