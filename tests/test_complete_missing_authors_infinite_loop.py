"""Tests TDD pour éviter la boucle infinie dans complete_missing_authors() (Issue #124).

Problème business réel:
- Jean-Daniel Beauvallet apparaît 4 fois dans les logs "Auteur non complété"
- Le même livre "Rock City Guide" est traité en boucle
- Cause: Le livre a une URL Babelio, mais le scraping de l'URL auteur échoue
- Le cas n'est PAS loggé dans problematic_cases
- Résultat: La requête MongoDB retourne toujours le même livre

Solution:
- Logger le cas problématique quand scrape_author_url_from_book_page() échoue
- Ajouter un filtre dans le pipeline pour exclure les cas déjà loggés
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestCompleteMissingAuthorsInfiniteLoop:
    """Tests pour éviter la boucle infinie dans complete_missing_authors()."""

    @pytest.mark.asyncio
    async def test_should_log_problematic_case_when_scraping_author_url_fails(self):
        """Test TDD: Logger le cas problématique quand le scraping de l'URL auteur échoue.

        Scénario réel (production):
        1. Livre "Rock City Guide" a une url_babelio
        2. L'auteur "Jean-Daniel Beauvallet" n'a PAS d'url_babelio
        3. scrape_author_url_from_book_page() échoue (retourne None)
        4. complete_missing_authors() doit logger le cas dans problematic_cases
        5. Le prochain appel ne doit PAS retourner ce livre
        """
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        # Résultat du pipeline - livre avec URL mais auteur sans URL
        livre_result = {
            "_id": livre_id,
            "titre": "Rock City Guide : Les villes qui ont marqué l'histoire de la musique",
            "auteur_id": auteur_id,
            "url_babelio": "https://www.babelio.com/livres/Beauvallet-Rock-City-Guide/1234",
            "auteur_info": {
                "_id": auteur_id,
                "nom": "Jean-Daniel Beauvallet",
                # Pas de url_babelio
            },
        }

        # Premier appel: retourner le livre
        # Deuxième appel: ne plus le retourner (car loggé dans problematic_cases)
        call_count = 0

        def mock_aggregate_cursor():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Premier appel: retourner le livre
                yield livre_result
            # Deuxième appel: ne rien retourner (livre exclu)

        mock_livres_collection.aggregate.return_value = mock_aggregate_cursor()

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_author_url_from_book_page"
            ) as mock_scrape_author,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock scrape_author_url_from_book_page pour retourner None (échec)
            async def mock_scrape_author_async(book_url):
                return None  # Échec du scraping

            mock_scrape_author.side_effect = mock_scrape_author_async

            from scripts.migration_donnees.migrate_url_babelio import (
                complete_missing_authors,
            )

            # Act - Premier appel (scraping échoue)
            result1 = await complete_missing_authors(dry_run=False)

            # Assert - Premier appel
            assert result1 is not None, "Doit retourner un résultat"
            assert result1["auteur_updated"] is False, (
                "Auteur ne doit PAS être mis à jour"
            )
            assert result1["status"] == "error"
            assert (
                result1["titre"]
                == "Rock City Guide : Les villes qui ont marqué l'histoire de la musique"
            )
            assert result1["auteur"] == "Jean-Daniel Beauvallet"

            # Assert - Le cas doit être loggé dans problematic_cases
            mock_prob_collection.insert_one.assert_called_once()
            insert_call = mock_prob_collection.insert_one.call_args[0][0]
            assert insert_call["livre_id"] == str(livre_id)  # Converti en string
            assert (
                insert_call["titre_attendu"]
                == "Rock City Guide : Les villes qui ont marqué l'histoire de la musique"
            )
            assert insert_call["auteur"] == "Jean-Daniel Beauvallet"
            assert "Failed to scrape author URL" in insert_call["raison"]

            # Act - Deuxième appel (le livre ne doit plus être retourné)
            result2 = await complete_missing_authors(dry_run=False)

            # Assert - Deuxième appel
            assert result2 is None, (
                "Le livre loggé ne doit plus être retourné (boucle évitée)"
            )

    @pytest.mark.asyncio
    async def test_pipeline_should_exclude_problematic_cases(self):
        """Test TDD: Le pipeline MongoDB doit exclure les livres loggés dans problematic_cases.

        Scénario:
        1. Livre "Rock City Guide" déjà loggé dans problematic_cases
        2. Le pipeline $match doit ajouter un filtre pour exclure ce livre
        3. complete_missing_authors() doit retourner None
        """
        # Arrange
        livre_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_prob_collection = MagicMock()

        # Cas problématique déjà loggé
        mock_prob_collection.find.return_value = [
            {
                "livre_id": livre_id,
                "titre": "Rock City Guide",
                "reason": "Failed to scrape author URL",
            }
        ]

        # Mock pipeline qui ne retourne rien (livre exclu)
        def mock_empty_aggregate_cursor():
            return
            yield  # Never reached

        mock_livres_collection.aggregate.return_value = mock_empty_aggregate_cursor()

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

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
            assert result is None, "Aucun livre ne doit être retourné (tous exclus)"

            # Vérifier que aggregate() a été appelé avec un filtre $nin pour _id
            aggregate_call = mock_livres_collection.aggregate.call_args[0][0]
            # Le premier $match doit filtrer les IDs problématiques
            first_match = aggregate_call[0]
            assert "$match" in first_match
            assert "_id" in first_match["$match"]
            assert "$nin" in first_match["$match"]["_id"]
            assert livre_id in first_match["$match"]["_id"]["$nin"]
