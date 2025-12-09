"""Tests TDD pour complete_missing_authors() (Issue #124 - Phase 14).

Ce module teste la fonctionnalité de complétion des auteurs manquants.
Quand un livre a déjà une URL Babelio mais que son auteur n'en a pas,
on scrape la page du livre pour récupérer l'URL de l'auteur.
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestCompleteMissingAuthors:
    """Tests pour la complétion des auteurs manquants."""

    @pytest.mark.asyncio
    async def test_should_find_books_with_url_but_author_without_url(self):
        """Test TDD: Trouver les livres avec URL dont l'auteur n'a pas d'URL.

        Problème business réel:
        - On a 14 auteurs sans URL Babelio
        - 11 de ces auteurs ont des livres qui ONT déjà une URL Babelio
        - On doit récupérer l'URL auteur depuis la page Babelio du livre

        Scénario:
        1. MongoDB contient un livre avec url_babelio
        2. L'auteur de ce livre n'a PAS de url_babelio
        3. complete_missing_authors() doit trouver ce cas
        4. Scraper la page du livre pour récupérer l'URL auteur
        5. Mettre à jour l'auteur dans MongoDB
        """
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        # Résultat de l'aggregation pipeline - livre avec URL mais auteur sans URL
        livre_result = {
            "_id": livre_id,
            "titre": "1984",
            "auteur_id": auteur_id,
            "url_babelio": "https://www.babelio.com/livres/Orwell-1984/1234",
            "auteur_info": {
                "_id": auteur_id,
                "nom": "George Orwell",
                # Pas de url_babelio → auteur à compléter
            },
        }

        # Mock du curseur async retourné par aggregate()
        async def mock_aggregate_cursor():
            yield livre_result

        mock_livres_collection.aggregate.return_value = mock_aggregate_cursor()

        mock_auteurs_collection.update_one.return_value = MagicMock(matched_count=1)

        def get_collection_side_effect(name):
            if name == "livres":
                return mock_livres_collection
            elif name == "auteurs":
                return mock_auteurs_collection
            return MagicMock()

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_author_url_from_book_page"
            ) as mock_scrape_author,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock scrape_author_url_from_book_page pour retourner l'URL auteur
            async def mock_scrape_author_async(book_url):
                return "https://www.babelio.com/auteur/George-Orwell/5678"

            mock_scrape_author.side_effect = mock_scrape_author_async

            from scripts.migration_donnees.migrate_url_babelio import (
                complete_missing_authors,
            )

            # Act
            result = await complete_missing_authors(dry_run=False)

            # Assert
            assert result is not None, "Doit retourner un résultat"
            assert result["auteur_updated"] is True, "Auteur doit être mis à jour"
            assert result["titre"] == "1984"
            assert result["auteur"] == "George Orwell"

            # Vérifier que l'auteur a été mis à jour dans MongoDB
            mock_auteurs_collection.update_one.assert_called_once()
            update_call = mock_auteurs_collection.update_one.call_args
            assert update_call[0][0] == {"_id": auteur_id}
            assert "url_babelio" in update_call[0][1]["$set"]
            assert (
                update_call[0][1]["$set"]["url_babelio"]
                == "https://www.babelio.com/auteur/George-Orwell/5678"
            )

    @pytest.mark.asyncio
    async def test_should_return_none_when_no_missing_authors(self):
        """Test TDD: Retourner None quand tous les auteurs ont déjà une URL.

        Scénario:
        1. Aucun livre ne correspond (tous les auteurs ont déjà leur URL)
        2. complete_missing_authors() doit retourner None
        """
        # Arrange
        mock_livres_collection = MagicMock()

        # Mock du curseur async vide (aucun résultat)
        async def mock_empty_aggregate_cursor():
            return
            yield  # Never reached - empty iterator

        mock_livres_collection.aggregate.return_value = mock_empty_aggregate_cursor()

        def get_collection_side_effect(name):
            if name == "livres":
                return mock_livres_collection
            return MagicMock()

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.side_effect = get_collection_side_effect

            from scripts.migration_donnees.migrate_url_babelio import (
                complete_missing_authors,
            )

            # Act
            result = await complete_missing_authors(dry_run=False)

            # Assert
            assert result is None, (
                "Doit retourner None quand plus d'auteurs à compléter"
            )
