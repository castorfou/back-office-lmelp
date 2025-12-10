"""Tests TDD pour process_one_book_author() - traitement batch d'un livre (Issue #124).

Cette fonction traite UN livre depuis les données batch (pas de requête MongoDB).
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestProcessOneBookAuthor:
    """Tests pour le traitement d'un livre en mode batch."""

    @pytest.mark.asyncio
    async def test_should_process_one_book_and_update_author(self):
        """Test TDD: Traiter un livre et mettre à jour son auteur.

        Scénario:
        1. Recevoir les données d'un livre (depuis batch)
        2. Scraper l'URL auteur depuis la page du livre
        3. Mettre à jour l'auteur dans MongoDB
        4. Retourner le résultat
        """
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        book_data = {
            "livre_id": livre_id,
            "titre": "1984",
            "auteur": "George Orwell",
            "auteur_id": auteur_id,
            "url_babelio": "https://www.babelio.com/livres/Orwell-1984/1234",
        }

        mock_auteurs_collection = MagicMock()
        mock_auteurs_collection.update_one.return_value = MagicMock(matched_count=1)

        def get_collection_side_effect(name):
            if name == "auteurs":
                return mock_auteurs_collection
            return MagicMock()

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_author_url_from_book_page"
            ) as mock_scrape_author,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock scrape_author_url_from_book_page pour retourner une URL
            async def mock_scrape_author_async(book_url):
                return "https://www.babelio.com/auteur/George-Orwell/5678"

            mock_scrape_author.side_effect = mock_scrape_author_async

            # Mock wait_rate_limit
            async def mock_wait_async():
                pass

            mock_wait.side_effect = mock_wait_async

            from scripts.migration_donnees.migrate_url_babelio import (
                process_one_book_author,
            )

            # Act
            result = await process_one_book_author(book_data, dry_run=False)

            # Assert
            assert result is not None, "Doit retourner un résultat"
            assert result["auteur_updated"] is True, "Auteur doit être mis à jour"
            assert result["titre"] == "1984"
            assert result["auteur"] == "George Orwell"
            assert result["status"] == "success"

            # Vérifier que l'auteur a été mis à jour
            mock_auteurs_collection.update_one.assert_called_once()
            update_call = mock_auteurs_collection.update_one.call_args
            assert update_call[0][0] == {"_id": auteur_id}
            assert (
                update_call[0][1]["$set"]["url_babelio"]
                == "https://www.babelio.com/auteur/George-Orwell/5678"
            )

    @pytest.mark.asyncio
    async def test_should_log_problematic_case_when_scraping_fails(self):
        """Test TDD: Logger le cas problématique quand scraping échoue.

        Scénario:
        1. Scraping de l'URL auteur échoue (retourne None)
        2. Logger le cas dans problematic_cases
        3. Retourner status="error"
        """
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        book_data = {
            "livre_id": livre_id,
            "titre": "Rock City Guide",
            "auteur": "Jean-Daniel Beauvallet",
            "auteur_id": auteur_id,
            "url_babelio": "https://www.babelio.com/livres/Beauvallet-Rock/1234",
        }

        mock_prob_collection = MagicMock()

        def get_collection_side_effect(name):
            if name == "babelio_problematic_cases":
                return mock_prob_collection
            return MagicMock()

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_author_url_from_book_page"
            ) as mock_scrape_author,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock scraping échoue
            async def mock_scrape_author_async(book_url):
                return None

            mock_scrape_author.side_effect = mock_scrape_author_async

            # Mock wait_rate_limit
            async def mock_wait_async():
                pass

            mock_wait.side_effect = mock_wait_async

            from scripts.migration_donnees.migrate_url_babelio import (
                process_one_book_author,
            )

            # Act
            result = await process_one_book_author(book_data, dry_run=False)

            # Assert
            assert result["auteur_updated"] is False
            assert result["status"] == "error"
            assert result["titre"] == "Rock City Guide"

            # Vérifier que le cas a été loggé
            mock_prob_collection.insert_one.assert_called_once()
            insert_call = mock_prob_collection.insert_one.call_args[0][0]
            assert insert_call["livre_id"] == str(livre_id)
            assert "Impossible de récupérer l'URL de l'auteur" in insert_call["raison"]

    @pytest.mark.asyncio
    async def test_should_not_call_mongodb_in_dry_run_mode(self):
        """Test TDD: En mode dry_run, ne pas appeler MongoDB.

        Scénario:
        1. dry_run=True
        2. Scraping réussit
        3. NE PAS mettre à jour MongoDB
        4. Retourner auteur_updated=False (simulé)
        """
        # Arrange
        book_data = {
            "livre_id": ObjectId(),
            "titre": "1984",
            "auteur": "George Orwell",
            "auteur_id": ObjectId(),
            "url_babelio": "https://www.babelio.com/livres/Orwell-1984/1234",
        }

        mock_auteurs_collection = MagicMock()

        def get_collection_side_effect(name):
            if name == "auteurs":
                return mock_auteurs_collection
            return MagicMock()

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_author_url_from_book_page"
            ) as mock_scrape_author,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock scraping réussit
            async def mock_scrape_author_async(book_url):
                return "https://www.babelio.com/auteur/George-Orwell/5678"

            mock_scrape_author.side_effect = mock_scrape_author_async

            # Mock wait_rate_limit
            async def mock_wait_async():
                pass

            mock_wait.side_effect = mock_wait_async

            from scripts.migration_donnees.migrate_url_babelio import (
                process_one_book_author,
            )

            # Act
            result = await process_one_book_author(book_data, dry_run=True)

            # Assert
            assert result["auteur_updated"] is False, (
                "Dry run ne doit PAS mettre à jour"
            )
            assert result["status"] == "success"

            # Vérifier que MongoDB n'a PAS été appelé
            mock_auteurs_collection.update_one.assert_not_called()
