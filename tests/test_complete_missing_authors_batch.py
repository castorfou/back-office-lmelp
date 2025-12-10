"""Tests TDD pour le traitement batch de complete_missing_authors() (Issue #124).

Problème business réel (production):
- complete_missing_authors() est appelé en boucle par MigrationRunner
- Entre chaque appel, les cas problématiques sont loggés
- MAIS la liste problematic_livre_ids n'est PAS rechargée
- Résultat: Le même livre est retraité indéfiniment

Logs production montrent:
- 04:30:22 - "❌ Impossible de récupérer l'URL auteur" + "Cas problématique loggé"
- 04:30:27 - MÊME message répété (5 secondes après)
- 04:30:28 - ENCORE le même livre traité

Solution proposée par l'utilisateur:
- Charger TOUS les livres à traiter en UNE FOIS au début
- Itérer sur cette liste pré-filtrée
- Garantit qu'un livre problématique ne sera traité qu'UNE FOIS par batch
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestCompleteMissingAuthorsBatch:
    """Tests pour le traitement batch (éviter retraitement)."""

    @pytest.mark.asyncio
    async def test_should_load_problematic_cases_before_each_query(self):
        """Test TDD: Charger problematic_cases AVANT chaque requête MongoDB.

        Scénario production:
        1. Premier appel: Livre A trouvé, scraping échoue, loggé
        2. Deuxième appel: Livre A NE DOIT PAS être retourné
        3. Le filtre MongoDB doit exclure Livre A

        Problème actuel:
        - problematic_livre_ids est chargé UNE FOIS au début de la fonction
        - Entre les appels, MongoDB est mis à jour mais pas le filtre
        """
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        livre_result = {
            "_id": livre_id,
            "titre": "Rock City Guide",
            "auteur_id": auteur_id,
            "url_babelio": "https://www.babelio.com/livres/Beauvallet-Rock-City-Guide/1808728",
            "auteur_info": {
                "_id": auteur_id,
                "nom": "Jean-Daniel Beauvallet",
            },
        }

        # Premier appel find(): liste vide (pas encore de cas problématiques)
        # Deuxième appel find(): liste avec le livre_id (déjà loggé)
        find_call_count = 0

        def mock_find_side_effect(*args, **kwargs):
            nonlocal find_call_count
            find_call_count += 1
            if find_call_count == 1:
                # Premier appel: aucun cas problématique
                return []
            else:
                # Deuxième appel: livre déjà loggé
                # CRITICAL: log_problematic_case() convertit en STRING (line 189)
                return [{"livre_id": str(livre_id)}]

        mock_prob_collection.find.side_effect = mock_find_side_effect

        # Premier appel aggregate(): retourne le livre
        # Deuxième appel aggregate(): Simuler le comportement MongoDB réel
        # MongoDB compare _id (ObjectId) avec $nin (list of strings) → NO MATCH → livre retourné
        def mock_aggregate_side_effect(pipeline):
            # Extraire le filtre $nin du premier $match
            first_match = pipeline[0]
            nin_filter = first_match.get("$match", {}).get("_id", {}).get("$nin", [])

            # Simuler MongoDB: comparer ObjectId avec strings (ne match jamais!)
            # MongoDB fait: livre_result["_id"] (ObjectId) in nin_filter (list of str)
            # ObjectId != str → toujours False → livre toujours retourné
            if livre_id in nin_filter:
                # Si on compare ObjectId == ObjectId (CORRECT)
                return iter([])  # Ne pas retourner le livre
            elif str(livre_id) in nin_filter:
                # Si on compare ObjectId avec str (BUG ACTUEL)
                # MongoDB ne trouve PAS de match → retourne le livre quand même!
                return iter([livre_result])
            else:
                # Pas de filtre → retourner le livre
                return iter([livre_result])

        mock_livres_collection.aggregate.side_effect = mock_aggregate_side_effect

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

            # Mock scraping échoue
            async def mock_scrape_author_async(book_url):
                return None

            mock_scrape_author.side_effect = mock_scrape_author_async

            from scripts.migration_donnees.migrate_url_babelio import (
                complete_missing_authors,
            )

            # Act - Premier appel
            result1 = await complete_missing_authors(dry_run=False)

            # Assert - Premier appel: livre traité, cas loggé
            assert result1 is not None
            assert result1["auteur_updated"] is False
            mock_prob_collection.insert_one.assert_called_once()

            # Assert - prob_collection.find() appelé AVANT l'aggregation
            assert mock_prob_collection.find.call_count == 1

            # Act - Deuxième appel (simulation du MigrationRunner qui reboucle)
            result2 = await complete_missing_authors(dry_run=False)

            # Assert - Deuxième appel
            # CRITICAL: prob_collection.find() doit être rappelé pour recharger la liste
            assert mock_prob_collection.find.call_count == 2, (
                "DOIT recharger problematic_cases avant chaque requête"
            )

            # Vérifier que le filtre MongoDB contient bien les IDs problématiques
            # Le deuxième appel aggregate() doit avoir un filtre avec le livre_id
            second_aggregate_call = mock_livres_collection.aggregate.call_args_list[1][
                0
            ][0]
            first_match = second_aggregate_call[0]
            assert "$match" in first_match
            assert "_id" in first_match["$match"]
            assert "$nin" in first_match["$match"]["_id"]

            # FIXED: log_problematic_case stores as STRING, but complete_missing_authors
            # now converts to ObjectId (line 592) before using in MongoDB filter
            problematic_ids = first_match["$match"]["_id"]["$nin"]
            assert livre_id in problematic_ids, (
                "Le filtre contient l'ID en ObjectId (converti depuis string)"
            )

            # Le livre ne doit PAS être retourné (exclu par $nin)
            # NOW WORKS because ObjectId(livre_id) == ObjectId(livre_id)
            assert result2 is None, "Le livre loggé ne doit plus être retourné"
