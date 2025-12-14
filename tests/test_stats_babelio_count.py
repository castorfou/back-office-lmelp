"""Tests TDD pour le comptage des entités sans URL Babelio (Issue #128)."""

from unittest.mock import MagicMock, patch

import pytest

from back_office_lmelp.services.stats_service import StatsService


class TestBabelioCount:
    """Tests pour le comptage des livres/auteurs sans URL Babelio."""

    @pytest.fixture
    def stats_service(self):
        """Fixture pour créer une instance de StatsService avec mocks."""
        with (
            patch(
                "back_office_lmelp.services.stats_service.livres_auteurs_cache_service"
            ),
            patch("back_office_lmelp.services.stats_service.mongodb_service"),
        ):
            service = StatsService()
            service.mongodb_service = MagicMock()
            return service

    def test_count_books_without_url_babelio_excludes_babelio_not_found(
        self, stats_service
    ):
        """
        Test TDD Issue #128: Ne doit PAS compter les livres avec babelio_not_found=true.

        Les livres avec babelio_not_found=true sont confirmés comme absents de Babelio,
        donc il n'y a rien à faire pour eux. On ne compte que ceux à traiter manuellement.
        """
        mock_collection = MagicMock()
        stats_service.mongodb_service.get_collection.return_value = mock_collection

        # Simuler 10 livres sans url_babelio dont 3 avec babelio_not_found=true
        # On s'attend à compter seulement 7 (10 - 3)
        mock_collection.count_documents.return_value = 7

        result = stats_service._count_books_without_url_babelio()

        # Vérifier que la requête exclut babelio_not_found=true
        mock_collection.count_documents.assert_called_once()
        query = mock_collection.count_documents.call_args[0][0]

        # La requête doit avoir un $and avec deux conditions:
        # 1. url_babelio est None ou n'existe pas
        # 2. babelio_not_found n'est pas True
        assert "$and" in query
        assert len(query["$and"]) == 2

        # Vérifier le résultat
        assert result == 7

    def test_count_authors_without_url_babelio_excludes_babelio_not_found(
        self, stats_service
    ):
        """
        Test TDD Issue #128: Ne doit PAS compter les auteurs avec babelio_not_found=true.

        Les auteurs avec babelio_not_found=true sont confirmés comme absents de Babelio,
        donc il n'y a rien à faire pour eux. On ne compte que ceux à traiter manuellement.
        """
        mock_collection = MagicMock()
        stats_service.mongodb_service.get_collection.return_value = mock_collection

        # Simuler 5 auteurs sans url_babelio dont 1 avec babelio_not_found=true
        # On s'attend à compter seulement 4 (5 - 1)
        mock_collection.count_documents.return_value = 4

        result = stats_service._count_authors_without_url_babelio()

        # Vérifier que la requête exclut babelio_not_found=true
        mock_collection.count_documents.assert_called_once()
        query = mock_collection.count_documents.call_args[0][0]

        # La requête doit avoir un $and avec deux conditions
        assert "$and" in query
        assert len(query["$and"]) == 2

        # Vérifier le résultat
        assert result == 4

    def test_count_books_includes_books_with_no_babelio_fields(self, stats_service):
        """
        Test TDD: Doit compter les livres qui n'ont ni url_babelio ni babelio_not_found.

        Ce sont les livres qui n'ont jamais été traités pour Babelio.
        """
        mock_collection = MagicMock()
        stats_service.mongodb_service.get_collection.return_value = mock_collection
        mock_collection.count_documents.return_value = 15

        result = stats_service._count_books_without_url_babelio()

        # Vérifier que le résultat est correct
        assert result == 15

    def test_count_authors_includes_authors_with_no_babelio_fields(self, stats_service):
        """
        Test TDD: Doit compter les auteurs qui n'ont ni url_babelio ni babelio_not_found.

        Ce sont les auteurs qui n'ont jamais été traités pour Babelio.
        """
        mock_collection = MagicMock()
        stats_service.mongodb_service.get_collection.return_value = mock_collection
        mock_collection.count_documents.return_value = 8

        result = stats_service._count_authors_without_url_babelio()

        # Vérifier que le résultat est correct
        assert result == 8
