"""Tests TDD pour le retour de migrate_one_book_and_author() (Issue #124 - Phase 12.1).

Ce module teste que migrate_one_book_and_author() retourne None quand il n'y a plus de livres,
pour que MigrationRunner puisse arrêter la boucle correctement.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMigrateUrlBabelioReturnValue:
    """Tests pour la valeur de retour de migrate_one_book_and_author()."""

    @pytest.mark.asyncio
    async def test_should_return_none_when_no_books_to_migrate(self):
        """Test TDD: migrate_one_book_and_author() doit retourner None quand plus de livres.

        Problème business réel:
        - MigrationRunner boucle indéfiniment
        - Cause: migrate_one_book_and_author() retourne un dict même quand plus de livres
        - Solution: Retourner None quand find_one() ne trouve rien

        Scénario:
        1. MongoDB ne trouve aucun livre sans url_babelio
        2. migrate_one_book_and_author() doit retourner None (pas un dict)
        3. MigrationRunner détectera None et arrêtera la boucle
        """
        # Arrange - Mock MongoDB qui ne trouve aucun livre
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None  # Aucun livre trouvé

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.return_value = mock_collection

            # Mock BabelioService (ne sera pas utilisé)
            mock_babelio = AsyncMock()

            # Import après patch
            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act - Appeler la fonction
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert - DOIT retourner None (pas un dict)
            assert result is None, (
                "migrate_one_book_and_author() doit retourner None quand il n'y a "
                "plus de livres à traiter, sinon MigrationRunner boucle indéfiniment"
            )

    @pytest.mark.asyncio
    async def test_should_return_dict_when_book_found(self):
        """Test TDD: migrate_one_book_and_author() doit retourner un dict quand livre trouvé.

        Scénario:
        1. MongoDB trouve un livre sans url_babelio
        2. migrate_one_book_and_author() doit retourner un dict avec les résultats
        """
        from bson import ObjectId

        # Arrange - Mock MongoDB qui trouve un livre
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "Test Book",
            "auteur_id": auteur_id,
        }

        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Test Author",
        }

        def get_collection_side_effect(name):
            if name == "livres":
                return mock_livres_collection
            elif name == "auteurs":
                return mock_auteurs_collection
            elif name == "babelio_problematic_cases":
                mock_prob = MagicMock()
                mock_prob.find.return_value = []
                return mock_prob
            return MagicMock()

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock BabelioService.verify_book() - retourne not found
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {"status": "not_found"}

            # Import après patch
            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert - DOIT retourner un dict (pas None)
            assert result is not None, (
                "Doit retourner un dict quand un livre est trouvé"
            )
            assert isinstance(result, dict), "Doit retourner un dict"
            # Le dict peut contenir book_updated/author_updated OU titre/status
            assert (
                "book_updated" in result
                or "author_updated" in result
                or "titre" in result
                or "status" in result
            ), "Dict doit contenir des infos sur la migration"
