"""Tests TDD pour les statistiques des auteurs dans get_migration_status() (Issue #124).

Ce module teste que get_migration_status() retourne les statistiques
pour les auteurs en plus des statistiques pour les livres.
"""

from unittest.mock import MagicMock


class TestBabelioMigrationAuthorStats:
    """Tests pour les statistiques des auteurs dans la migration Babelio."""

    def test_should_return_author_statistics_in_migration_status(self):
        """Test TDD: get_migration_status() doit retourner les stats des auteurs.

        Problème business réel:
        - Le dashboard affiche les stats des livres
        - On veut aussi afficher combien d'auteurs ont une liaison Babelio
        - get_migration_status() doit retourner total_authors, authors_with_url, authors_without_url_babelio

        Scénario:
        1. MongoDB contient 445 auteurs dont 431 ont url_babelio
        2. get_migration_status() doit retourner ces chiffres
        """
        # Arrange
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_problematic_collection = MagicMock()

        # Mock livres
        mock_livres_collection.count_documents.side_effect = lambda q: {
            "{}": 100,  # total_books
            "{'url_babelio': {'$exists': True, '$ne': None}}": 80,  # migrated
            "{'babelio_not_found': True}": 10,  # not_found
        }.get(str(q), 0)

        mock_livres_collection.find_one.return_value = None

        # Mock auteurs - 445 total, 431 avec URL
        def auteurs_count_side_effect(query):
            if query == {}:
                return 445  # total_authors
            elif query == {"url_babelio": {"$exists": True, "$ne": None}}:
                return 431  # authors_with_url
            return 0

        mock_auteurs_collection.count_documents.side_effect = auteurs_count_side_effect

        # Mock problematic cases
        mock_problematic_collection.find.return_value = []

        # Mock db
        mock_db = {
            "livres": mock_livres_collection,
            "auteurs": mock_auteurs_collection,
            "babelio_problematic_cases": mock_problematic_collection,
        }

        mock_mongodb_service = MagicMock()
        mock_mongodb_service.db = mock_db

        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        service = BabelioMigrationService(
            mongodb_service=mock_mongodb_service, babelio_service=MagicMock()
        )

        # Act
        result = service.get_migration_status()

        # Assert - Doit contenir les stats des auteurs
        assert "total_authors" in result, "Doit contenir total_authors"
        assert "authors_with_url" in result, "Doit contenir authors_with_url"
        assert "authors_without_url_babelio" in result, (
            "Doit contenir authors_without_url_babelio"
        )

        # Vérifier les valeurs
        assert result["total_authors"] == 445
        assert result["authors_with_url"] == 431
        assert result["authors_without_url_babelio"] == 14  # 445 - 431
