"""Tests TDD pour le service autonome de consultation des statistiques."""

from unittest.mock import patch

from bson import ObjectId

from back_office_lmelp.services.stats_service import StatsService


class TestStatsService:
    """Tests TDD pour le service de consultation des statistiques."""

    def test_stats_service_should_get_cache_statistics(self):
        """Test TDD: Le service doit récupérer les statistiques du cache."""
        # Arrange
        mock_cache_stats = {
            "couples_en_base": 3,
            "couples_pending": 5,
            "couples_rejected": 1,
            "couples_verified_pas_en_base": 2,
            "couples_suggested_pas_en_base": 4,
            "couples_not_found_pas_en_base": 1,
            "episodes_non_traites": 10,
        }

        with (
            patch(
                "back_office_lmelp.services.stats_service.livres_auteurs_cache_service"
            ) as mock_cache,
            patch(
                "back_office_lmelp.services.stats_service.mongodb_service"
            ) as mock_mongodb,
        ):
            mock_cache.get_statistics_from_cache.return_value = mock_cache_stats
            # Mock MongoDB count_documents pour Issue #124
            mock_mongodb.get_collection.return_value.count_documents.return_value = 0
            # Mock MongoDB find_one pour Issue #128 (last_episode_date)
            mock_mongodb.get_collection.return_value.find_one.return_value = None
            # Mock MongoDB distinct pour Issue #128 (episodes/avis_critiques)
            mock_mongodb.get_collection.return_value.distinct.return_value = []

            # Act
            stats_service = StatsService()
            result = stats_service.get_cache_statistics()

            # Assert
            expected_result = {
                **mock_cache_stats,
                "books_without_url_babelio": 0,
                "authors_without_url_babelio": 0,
                "last_episode_date": None,
                "episodes_without_avis_critiques": 0,
                "avis_critiques_without_analysis": 0,
            }
            assert result == expected_result
            mock_cache.get_statistics_from_cache.assert_called_once()

    def test_stats_service_should_get_detailed_breakdown(self):
        """Test TDD: Le service doit fournir une répartition détaillée."""
        mock_detailed_stats = [
            {
                "_id": "verified",
                "count": 3,
                "books": [
                    {"auteur": "Albert Camus", "titre": "L'Étranger"},
                    {"auteur": "Victor Hugo", "titre": "Les Misérables"},
                ],
            },
            {
                "_id": "suggested",
                "count": 4,
                "books": [{"auteur": "Marguerite Duras", "titre": "L'Amant"}],
            },
            {
                "_id": "not_found",
                "count": 2,
                "books": [{"auteur": "Auteur Inconnu", "titre": "Livre Mystère"}],
            },
            {"_id": "pending", "count": 5, "books": []},
        ]

        with patch(
            "back_office_lmelp.services.stats_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.aggregate.return_value = (
                mock_detailed_stats
            )

            # Act
            stats_service = StatsService()
            result = stats_service.get_detailed_breakdown()

            # Assert
            assert result == mock_detailed_stats
            mock_mongodb.get_collection.assert_called_once_with("livresauteurs_cache")

    def test_stats_service_should_format_human_readable_summary(self):
        """Test TDD: Le service doit formater un résumé lisible pour humains."""
        mock_stats = {
            "couples_en_base": 3,
            "couples_pending": 5,
            "couples_rejected": 1,
            "couples_suggested_pas_en_base": 4,
            "couples_not_found_pas_en_base": 1,
            "avis_critiques_analyses": 38,
            "episodes_non_traites": 10,
            "livres_uniques": 0,
        }

        expected_summary = """📊 STATISTIQUES CACHE LIVRES/AUTEURS

🚀 Auto-traités (en base) : 3 (couples)
📚 Livres uniques         : 0
⏳ En attente validation  : 10
   ├─ 💡 Suggestions      : 4
   ├─ ❌ Non trouvés      : 1
   └─ ⏸️  Pending         : 5
🗑️  Rejetés             : 1
📺 Avis critiques analysés : 38
📝 Épisodes non traités : 10

Total livres traités : 14"""

        with patch.object(
            StatsService, "get_cache_statistics", return_value=mock_stats
        ):
            # Act
            stats_service = StatsService()
            result = stats_service.get_human_readable_summary()

            # Assert
            assert result == expected_summary

    def test_stats_service_should_get_validation_status_breakdown(self):
        """Test TDD: Le service doit récupérer la répartition par validation_status."""
        mock_validation_stats = [
            {"_id": "mongo", "count": 3},
            {"_id": "pending", "count": 12},
            {"_id": "rejected", "count": 1},
        ]

        with patch(
            "back_office_lmelp.services.stats_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.aggregate.return_value = (
                mock_validation_stats
            )

            # Act
            stats_service = StatsService()
            result = stats_service.get_validation_status_breakdown()

            # Assert
            assert result == mock_validation_stats
            # Vérifier que la bonne agrégation est appelée
            expected_pipeline = [
                {"$group": {"_id": "$validation_status", "count": {"$sum": 1}}}
            ]
            mock_mongodb.get_collection.return_value.aggregate.assert_called_with(
                expected_pipeline
            )

    def test_stats_service_should_get_recent_processed_books(self):
        """Test TDD: Le service doit récupérer les livres récemment traités."""
        mock_recent_books = [
            {
                "_id": ObjectId("68d440010000000000000001"),
                "auteur": "Recent Author",
                "titre": "Recent Book",
                "validation_status": "mongo",
                "processed_at": "2025-09-24T21:07:06.994Z",
            }
        ]

        with patch(
            "back_office_lmelp.services.stats_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.find.return_value.sort.return_value.limit.return_value = mock_recent_books

            # Act
            stats_service = StatsService()
            result = stats_service.get_recent_processed_books(limit=5)

            # Assert
            assert result == mock_recent_books
            # Vérifier la chaîne d'appels
            collection_mock = mock_mongodb.get_collection.return_value
            collection_mock.find.assert_called_once_with({"validation_status": "mongo"})
            collection_mock.find.return_value.sort.assert_called_once_with(
                "processed_at", -1
            )
            collection_mock.find.return_value.sort.return_value.limit.assert_called_once_with(
                5
            )

    def test_stats_service_should_display_console_stats(self):
        """Test TDD: Le service doit afficher les statistiques dans la console."""
        mock_summary = "Test summary"
        mock_breakdown = [{"_id": "verified", "count": 3}]
        mock_recent = [{"auteur": "Test Author", "titre": "Test Book"}]

        with (
            patch.object(
                StatsService, "get_human_readable_summary", return_value=mock_summary
            ),
            patch.object(
                StatsService, "get_detailed_breakdown", return_value=mock_breakdown
            ),
            patch.object(
                StatsService, "get_recent_processed_books", return_value=mock_recent
            ),
            patch("builtins.print") as mock_print,
        ):
            # Act
            stats_service = StatsService()
            stats_service.display_console_stats()

            # Assert
            mock_print.assert_called()
            # Vérifier qu'au moins le résumé est affiché
            print_calls = [
                call.args[0] for call in mock_print.call_args_list if call.args
            ]
            assert any(mock_summary in str(call) for call in print_calls)

    def test_stats_service_should_handle_empty_cache_gracefully(self):
        """Test TDD: Le service doit gérer gracieusement un cache vide."""
        empty_stats = {
            "couples_en_base": 0,
            "couples_pending": 0,
            "couples_rejected": 0,
            "couples_verified_pas_en_base": 0,
            "couples_suggested_pas_en_base": 0,
            "couples_not_found_pas_en_base": 0,
            "episodes_non_traites": 0,
            "books_without_url_babelio": 0,
            "authors_without_url_babelio": 0,
            "last_episode_date": None,
            "episodes_without_avis_critiques": 0,
            "avis_critiques_without_analysis": 0,
        }

        with patch.object(
            StatsService, "get_cache_statistics", return_value=empty_stats
        ):
            # Act
            stats_service = StatsService()
            result = stats_service.get_human_readable_summary()

            # Assert
            assert "Total livres traités : 0" in result
            assert "🚀 Auto-traités (en base) : 0" in result

    def test_stats_service_should_be_importable_and_instantiable(self):
        """Test TDD: Le service doit être importable et instanciable facilement."""
        # Act & Assert
        stats_service = StatsService()
        assert stats_service is not None
        assert hasattr(stats_service, "get_cache_statistics")
        assert hasattr(stats_service, "get_human_readable_summary")
        assert hasattr(stats_service, "display_console_stats")

    def test_stats_service_should_NOT_include_couples_verified_pas_en_base(self):
        """Test TDD: Les stats NE DOIVENT PAS inclure 'couples_verified_pas_en_base' (toujours 0)."""
        # Arrange
        mock_cache_stats = {
            "couples_en_base": 128,
            "couples_suggested_pas_en_base": 86,
            "couples_not_found_pas_en_base": 52,
            "avis_critiques_analyses": 38,  # Nouvelle stat
            "episodes_non_traites": 11,
        }

        with (
            patch(
                "back_office_lmelp.services.stats_service.livres_auteurs_cache_service"
            ) as mock_cache,
            patch(
                "back_office_lmelp.services.stats_service.mongodb_service"
            ) as mock_mongodb,
        ):
            mock_cache.get_statistics_from_cache.return_value = mock_cache_stats
            # Mock MongoDB count_documents pour Issue #124
            mock_mongodb.get_collection.return_value.count_documents.return_value = 0

            # Act
            stats_service = StatsService()
            result = stats_service.get_cache_statistics()

            # Assert
            assert "couples_verified_pas_en_base" not in result
            assert "avis_critiques_analyses" in result
            assert result["avis_critiques_analyses"] == 38
            # Issue #124: vérifier les nouvelles métriques
            assert "books_without_url_babelio" in result
            assert "authors_without_url_babelio" in result

    def test_stats_service_should_include_avis_critiques_analyses(self):
        """Test TDD: Les stats DOIVENT inclure 'avis_critiques_analyses' (avis_critique_id distincts)."""
        # Arrange
        mock_cache_stats = {
            "couples_en_base": 128,
            "couples_suggested_pas_en_base": 86,
            "couples_not_found_pas_en_base": 52,
            "avis_critiques_analyses": 42,  # Nouvelle stat
            "episodes_non_traites": 11,
        }

        with (
            patch(
                "back_office_lmelp.services.stats_service.livres_auteurs_cache_service"
            ) as mock_cache,
            patch(
                "back_office_lmelp.services.stats_service.mongodb_service"
            ) as mock_mongodb,
        ):
            mock_cache.get_statistics_from_cache.return_value = mock_cache_stats
            # Mock MongoDB count_documents pour Issue #124
            mock_mongodb.get_collection.return_value.count_documents.return_value = 0

            # Act
            stats_service = StatsService()
            result = stats_service.get_cache_statistics()

            # Assert
            assert "avis_critiques_analyses" in result
            assert result["avis_critiques_analyses"] == 42
            assert isinstance(result["avis_critiques_analyses"], int)

    def test_human_readable_summary_should_NOT_mention_livres_verifies(self):
        """Test TDD: Le résumé NE DOIT PAS mentionner 'Vérifiés' (section supprimée)."""
        # Arrange
        mock_stats = {
            "couples_en_base": 128,
            "couples_suggested_pas_en_base": 86,
            "couples_not_found_pas_en_base": 52,
            "avis_critiques_analyses": 38,
            "episodes_non_traites": 11,
        }

        with patch.object(
            StatsService, "get_cache_statistics", return_value=mock_stats
        ):
            # Act
            stats_service = StatsService()
            result = stats_service.get_human_readable_summary()

            # Assert
            assert "✅ Vérifiés" not in result
            assert "couples_verified_pas_en_base" not in result
            # Mais les autres sections doivent être présentes
            assert "💡 Suggestions" in result
            assert "❌ Non trouvés" in result

    def test_human_readable_summary_should_include_avis_critiques_analyses(self):
        """Test TDD: Le résumé DOIT inclure 'Avis critiques analysés'."""
        # Arrange
        mock_stats = {
            "couples_en_base": 128,
            "couples_suggested_pas_en_base": 86,
            "couples_not_found_pas_en_base": 52,
            "avis_critiques_analyses": 38,
            "episodes_non_traites": 11,
        }

        with patch.object(
            StatsService, "get_cache_statistics", return_value=mock_stats
        ):
            # Act
            stats_service = StatsService()
            result = stats_service.get_human_readable_summary()

            # Assert
            assert "📺 Avis critiques analysés : 38" in result
