"""Tests TDD pour la refactorisation batch de complete_missing_authors() (Issue #124).

Problème actuel:
- complete_missing_authors() traite UN livre, puis est rappelé en boucle
- Entre chaque appel, risque de retraiter le même livre si erreur

Solution batch:
- complete_missing_authors() retourne TOUS les livres à traiter
- MigrationRunner itère sur la liste
- Chaque livre traité UNE FOIS max, pas de re-requête MongoDB
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestCompleteMissingAuthorsBatchRefactor:
    """Tests pour la nouvelle approche batch."""

    @pytest.mark.asyncio
    async def test_should_return_list_of_all_books_to_process(self):
        """Test TDD: complete_missing_authors() doit retourner TOUS les livres.

        Scénario:
        1. MongoDB contient 3 livres avec auteurs à compléter
        2. complete_missing_authors() doit retourner une liste de 3 éléments
        3. Chaque élément contient: livre_id, titre, auteur, url_babelio
        """
        # Arrange
        livre1_id = ObjectId()
        livre2_id = ObjectId()
        livre3_id = ObjectId()
        auteur1_id = ObjectId()
        auteur2_id = ObjectId()
        auteur3_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_prob_collection = MagicMock()

        # MongoDB retourne 3 livres
        livres_results = [
            {
                "_id": livre1_id,
                "titre": "1984",
                "auteur_id": auteur1_id,
                "url_babelio": "https://www.babelio.com/livres/Orwell-1984/1234",
                "auteur_info": {"_id": auteur1_id, "nom": "George Orwell"},
            },
            {
                "_id": livre2_id,
                "titre": "Animal Farm",
                "auteur_id": auteur2_id,
                "url_babelio": "https://www.babelio.com/livres/Orwell-Animal/5678",
                "auteur_info": {"_id": auteur2_id, "nom": "George Orwell"},
            },
            {
                "_id": livre3_id,
                "titre": "Brave New World",
                "auteur_id": auteur3_id,
                "url_babelio": "https://www.babelio.com/livres/Huxley-Brave/9012",
                "auteur_info": {"_id": auteur3_id, "nom": "Aldous Huxley"},
            },
        ]

        # Mock curseur synchrone qui retourne les 3 livres
        def mock_aggregate_cursor():
            yield from livres_results

        mock_livres_collection.aggregate.return_value = mock_aggregate_cursor()

        # Pas de cas problématiques
        mock_prob_collection.find.return_value = []

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
                get_all_books_to_complete,
            )

            # Act
            books_to_process = await get_all_books_to_complete()

            # Assert
            assert books_to_process is not None, "Doit retourner une liste"
            assert len(books_to_process) == 3, "Doit retourner les 3 livres"

            # Vérifier le premier livre
            assert books_to_process[0]["livre_id"] == livre1_id
            assert books_to_process[0]["titre"] == "1984"
            assert books_to_process[0]["auteur"] == "George Orwell"
            assert books_to_process[0]["auteur_id"] == auteur1_id
            assert (
                books_to_process[0]["url_babelio"]
                == "https://www.babelio.com/livres/Orwell-1984/1234"
            )

            # Vérifier que MongoDB a été appelé UNE SEULE FOIS
            assert mock_livres_collection.aggregate.call_count == 1

    @pytest.mark.asyncio
    async def test_should_exclude_problematic_cases_from_batch(self):
        """Test TDD: La liste batch doit exclure les cas problématiques.

        Scénario:
        1. MongoDB contient 3 livres
        2. 1 livre est dans problematic_cases
        3. get_all_books_to_complete() doit retourner seulement 2 livres
        """
        # Arrange
        livre1_id = ObjectId()
        livre2_id = ObjectId()
        livre3_id = ObjectId()  # Ce livre est problématique

        mock_livres_collection = MagicMock()
        mock_prob_collection = MagicMock()

        # MongoDB retourne 2 livres (livre3 exclu par $nin)
        livres_results = [
            {
                "_id": livre1_id,
                "titre": "1984",
                "auteur_id": ObjectId(),
                "url_babelio": "https://www.babelio.com/livres/Orwell-1984/1234",
                "auteur_info": {"_id": ObjectId(), "nom": "George Orwell"},
            },
            {
                "_id": livre2_id,
                "titre": "Animal Farm",
                "auteur_id": ObjectId(),
                "url_babelio": "https://www.babelio.com/livres/Orwell-Animal/5678",
                "auteur_info": {"_id": ObjectId(), "nom": "George Orwell"},
            },
        ]

        def mock_aggregate_cursor():
            yield from livres_results

        mock_livres_collection.aggregate.return_value = mock_aggregate_cursor()

        # Livre3 est dans problematic_cases
        mock_prob_collection.find.return_value = [{"livre_id": str(livre3_id)}]

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
                get_all_books_to_complete,
            )

            # Act
            books_to_process = await get_all_books_to_complete()

            # Assert
            assert len(books_to_process) == 2, "Doit exclure le livre problématique"
            assert all(book["livre_id"] != livre3_id for book in books_to_process), (
                "Livre3 ne doit PAS être dans la liste"
            )

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_no_books(self):
        """Test TDD: Retourner liste vide quand aucun livre à traiter.

        Scénario:
        1. Aucun livre à compléter
        2. get_all_books_to_complete() doit retourner []
        """
        # Arrange
        mock_livres_collection = MagicMock()
        mock_prob_collection = MagicMock()

        # MongoDB ne retourne rien
        def mock_empty_aggregate_cursor():
            return
            yield  # Never reached

        mock_livres_collection.aggregate.return_value = mock_empty_aggregate_cursor()
        mock_prob_collection.find.return_value = []

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
                get_all_books_to_complete,
            )

            # Act
            books_to_process = await get_all_books_to_complete()

            # Assert
            assert books_to_process == [], "Doit retourner liste vide"
