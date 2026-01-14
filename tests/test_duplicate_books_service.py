"""
Tests pour le service de détection et fusion des doublons de livres.

Approche TDD incrémentale (Issue #178):
1. Test d'intégration de haut niveau (business problem)
2. Tests de validation (auteur_id check)
3. Tests de scraping Babelio
4. Implémentation fonction par fonction
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from bson import ObjectId

from back_office_lmelp.services.duplicate_books_service import DuplicateBooksService


@pytest.fixture
def mock_mongodb_service():
    """Mock du MongoDB service avec collections"""
    mock_service = Mock()
    mock_service.livres_collection = Mock()
    mock_service.auteurs_collection = Mock()
    mock_service.get_collection = Mock()
    return mock_service


@pytest.fixture
def mock_babelio_service():
    """Mock du Babelio service"""
    mock_service = Mock()
    mock_service.fetch_full_title_from_url = AsyncMock()
    mock_service.fetch_publisher_from_url = AsyncMock()
    return mock_service


@pytest.fixture
def duplicate_books_service(mock_mongodb_service, mock_babelio_service):
    """Instance du service avec mocks"""
    return DuplicateBooksService(
        mongodb_service=mock_mongodb_service, babelio_service=mock_babelio_service
    )


class TestMergeDuplicateGroup:
    """
    Tests pour la fusion d'un groupe de doublons.

    Business Problem: Fusionner 2 livres avec même url_babelio mais episodes différents.
    """

    @pytest.mark.asyncio
    async def test_merge_should_union_episodes_and_avis(
        self, duplicate_books_service, mock_mongodb_service, mock_babelio_service
    ):
        """
        Test d'intégration RED: La fusion doit unir episodes et avis_critiques.

        Business Problem:
            Deux doublons ont des episodes différents:
            - Livre 1: ["ep1", "ep2"]
            - Livre 2: ["ep2", "ep3"]  (ep2 en commun)

            Après fusion, le livre primaire doit contenir TOUS les episodes
            sans doublons: ["ep1", "ep2", "ep3"]

        CRITICAL: Utiliser VRAIES données MongoDB (types réels).
        - created_at: datetime, pas string
        - episodes/avis_critiques: Arrays de strings
        - _id: ObjectId
        """
        # Setup: 2 livres doublons avec episodes différents
        book_id_1 = ObjectId("6942ea3dd81dde3040c84363")
        book_id_2 = ObjectId("6942ece9d81dde3040c84388")
        auteur_id = ObjectId("6942ea3dd81dde3040c84362")

        mock_book_1 = {
            "_id": book_id_1,
            "titre": "Le grand jabadao",
            "auteur_id": auteur_id,
            "editeur": "Le Dilettante",
            "url_babelio": "https://www.babelio.com/livres/Coatalem-Le-grand-jabadao/1382347",
            "episodes": ["ep1", "ep2"],
            "avis_critiques": ["av1"],
            "created_at": datetime(2025, 12, 17, 17, 37, 1, tzinfo=UTC),  # Plus ancien
            "updated_at": datetime(2025, 12, 17, 17, 52, 38, tzinfo=UTC),
        }

        mock_book_2 = {
            "_id": book_id_2,
            "titre": "Le Grand Jabadao",  # Variation de casse
            "auteur_id": auteur_id,  # MÊME auteur
            "editeur": "Grasset",
            "url_babelio": "https://www.babelio.com/livres/Coatalem-Le-grand-jabadao/1382347",
            "episodes": ["ep2", "ep3"],  # ep2 en commun, ep3 nouveau
            "avis_critiques": ["av2"],
            "created_at": datetime(2025, 12, 17, 18, 0, 0, tzinfo=UTC),  # Plus récent
            "updated_at": datetime(2025, 12, 17, 18, 0, 0, tzinfo=UTC),
        }

        # Mock MongoDB find: retourne les 2 livres
        mock_mongodb_service.livres_collection.find.return_value = [
            mock_book_1,
            mock_book_2,
        ]

        # Mock Babelio scraping: retourne données officielles
        mock_babelio_service.fetch_full_title_from_url.return_value = "Le Grand Jabadao"
        mock_babelio_service.fetch_publisher_from_url.return_value = "Grasset"

        # Mock MongoDB update (pas d'erreur)
        mock_mongodb_service.livres_collection.update_one.return_value = Mock(
            matched_count=1
        )

        # Mock MongoDB delete
        mock_mongodb_service.livres_collection.delete_many.return_value = Mock(
            deleted_count=1
        )

        # Mock auteurs collection
        mock_mongodb_service.auteurs_collection.update_one.return_value = Mock(
            matched_count=1
        )

        # Mock history collection
        mock_history_collection = Mock()
        mock_history_collection.insert_one.return_value = Mock()
        mock_mongodb_service.get_collection.return_value = mock_history_collection

        # Execute: Fusionner les 2 livres
        result = await duplicate_books_service.merge_duplicate_group(
            url_babelio="https://www.babelio.com/livres/Coatalem-Le-grand-jabadao/1382347",
            book_ids=[str(book_id_1), str(book_id_2)],
        )

        # Assert: Business expectation
        assert result["success"] is True, (
            f"Merge should succeed. Error: {result.get('error')}"
        )

        # Livre primaire: le plus ancien (book_id_1)
        assert result["primary_book_id"] == str(book_id_1), (
            "Should keep oldest book as primary"
        )

        # Doublons supprimés: book_id_2
        assert result["deleted_book_ids"] == [str(book_id_2)], (
            "Should delete duplicate books"
        )

        # Episodes fusionnés: ep1, ep2, ep3 (3 uniques, pas 4)
        assert result["episodes_merged"] == 3, (
            "Should merge 3 unique episodes (ep1, ep2, ep3), not 4"
        )

        # Avis critiques fusionnés: av1, av2 (2 uniques)
        assert result["avis_critiques_merged"] == 2, (
            "Should merge 2 unique avis_critiques (av1, av2)"
        )

        # Données Babelio utilisées
        assert result["merged_data"]["titre"] == "Le Grand Jabadao", (
            "Should use official Babelio title"
        )
        assert result["merged_data"]["editeur"] == "Grasset", (
            "Should use official Babelio publisher"
        )

        # Vérifier que MongoDB update_one a été appelé avec $addToSet
        mock_mongodb_service.livres_collection.update_one.assert_called_once()
        update_call_args = mock_mongodb_service.livres_collection.update_one.call_args
        assert "$addToSet" in update_call_args[0][1], (
            "Should use $addToSet for merging arrays"
        )


class TestValidateDuplicateGroup:
    """
    Tests pour la validation d'un groupe de doublons.

    CRITICAL: auteur_id doit être identique pour tous les doublons.
    """

    @pytest.mark.asyncio
    async def test_should_reject_different_auteur_ids(
        self, duplicate_books_service, mock_mongodb_service
    ):
        """
        Test RED: Rejeter fusion si auteur_id différent.

        Business Rule:
            Les doublons DOIVENT avoir le même auteur_id.
            Si auteur_id différent → doublons invalides → REJETER.

        Example:
            - Livre 1: auteur_id = ObjectId('aaa...')
            - Livre 2: auteur_id = ObjectId('bbb...')
            → Validation échoue avec erreur explicite
        """
        # Setup: 2 livres avec auteur_id DIFFÉRENT
        book_id_1 = ObjectId("6942ea3dd81dde3040c84363")
        book_id_2 = ObjectId("6942ece9d81dde3040c84388")
        auteur_id_1 = ObjectId("6942ea3dd81dde3040c84362")
        auteur_id_2 = ObjectId("777777777777777777777777")  # DIFFÉRENT! (24 chars hex)

        mock_book_1 = {
            "_id": book_id_1,
            "titre": "Livre 1",
            "auteur_id": auteur_id_1,
            "url_babelio": "https://www.babelio.com/test",
            "episodes": [],
            "avis_critiques": [],
            "created_at": datetime(2025, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2025, 1, 1, tzinfo=UTC),
        }

        mock_book_2 = {
            "_id": book_id_2,
            "titre": "Livre 2",
            "auteur_id": auteur_id_2,  # DIFFÉRENT de book_1!
            "url_babelio": "https://www.babelio.com/test",
            "episodes": [],
            "avis_critiques": [],
            "created_at": datetime(2025, 1, 2, tzinfo=UTC),
            "updated_at": datetime(2025, 1, 2, tzinfo=UTC),
        }

        # Mock MongoDB find
        mock_mongodb_service.livres_collection.find.return_value = [
            mock_book_1,
            mock_book_2,
        ]

        # Execute: Valider le groupe
        result = await duplicate_books_service.validate_duplicate_group(
            url_babelio="https://www.babelio.com/test",
            book_ids=[str(book_id_1), str(book_id_2)],
        )

        # Assert: Validation échoue
        assert result["valid"] is False, "Validation should fail when auteur_id differs"

        assert len(result["errors"]) > 0, "Should return at least one error"

        assert "auteur_id" in result["errors"][0].lower(), (
            "Error message should mention auteur_id"
        )

        assert result["auteur_id"] is None, (
            "Should not return auteur_id when validation fails"
        )


class TestBabelioIntegration:
    """
    Tests pour l'intégration avec le service Babelio.
    """

    @pytest.mark.asyncio
    async def test_should_use_babelio_official_data(
        self, duplicate_books_service, mock_mongodb_service, mock_babelio_service
    ):
        """
        Test RED: Utiliser données officielles de Babelio.

        Business Value:
            Babelio est la source de vérité pour titre/éditeur.
            Ignorer les variations locales, utiliser données officielles.

        Example:
            - Local: "Le grand jabadao" (minuscule)
            - Babelio: "Le Grand Jabadao" (majuscule)
            → Utiliser version Babelio
        """
        # Setup: 1 livre avec titre local différent
        book_id = ObjectId("6942ea3dd81dde3040c84363")
        auteur_id = ObjectId("6942ea3dd81dde3040c84362")

        mock_book = {
            "_id": book_id,
            "titre": "le grand jabadao",  # Minuscule (local)
            "auteur_id": auteur_id,
            "editeur": "Le Dilettante",  # Différent de Babelio
            "url_babelio": "https://www.babelio.com/livres/Coatalem-Le-grand-jabadao/1382347",
            "episodes": [],
            "avis_critiques": [],
            "created_at": datetime(2025, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2025, 1, 1, tzinfo=UTC),
        }

        # Mock MongoDB
        mock_mongodb_service.livres_collection.find.return_value = [mock_book]
        mock_mongodb_service.livres_collection.update_one.return_value = Mock(
            matched_count=1
        )
        mock_mongodb_service.livres_collection.delete_many.return_value = Mock(
            deleted_count=0
        )
        mock_mongodb_service.auteurs_collection.update_one.return_value = Mock(
            matched_count=1
        )

        mock_history_collection = Mock()
        mock_history_collection.insert_one.return_value = Mock()
        mock_mongodb_service.get_collection.return_value = mock_history_collection

        # Mock Babelio: retourne données officielles
        mock_babelio_service.fetch_full_title_from_url.return_value = "Le Grand Jabadao"
        mock_babelio_service.fetch_publisher_from_url.return_value = "Grasset"

        # Execute
        result = await duplicate_books_service.merge_duplicate_group(
            url_babelio="https://www.babelio.com/livres/Coatalem-Le-grand-jabadao/1382347",
            book_ids=[str(book_id)],
        )

        # Assert: Données Babelio utilisées (pas données locales)
        assert result["success"] is True
        assert result["merged_data"]["titre"] == "Le Grand Jabadao", (
            "Should use Babelio title (not local 'le grand jabadao')"
        )
        assert result["merged_data"]["editeur"] == "Grasset", (
            "Should use Babelio publisher (not local 'Le Dilettante')"
        )

        # Vérifier que les méthodes Babelio ont été appelées
        mock_babelio_service.fetch_full_title_from_url.assert_called_once_with(
            "https://www.babelio.com/livres/Coatalem-Le-grand-jabadao/1382347"
        )
        mock_babelio_service.fetch_publisher_from_url.assert_called_once_with(
            "https://www.babelio.com/livres/Coatalem-Le-grand-jabadao/1382347"
        )


class TestFindDuplicateGroups:
    """
    Tests pour la détection des groupes de doublons.
    """

    @pytest.mark.asyncio
    async def test_should_find_duplicate_groups_by_url(
        self, duplicate_books_service, mock_mongodb_service
    ):
        """
        Test: Trouver tous les groupes avec même url_babelio.

        Business Logic:
            Utiliser aggregation MongoDB pour grouper par url_babelio.
            Retourner seulement les groupes avec count > 1.
        """
        # Mock MongoDB aggregate: retourne 2 groupes de doublons
        mock_aggregate_result = [
            {
                "_id": "https://www.babelio.com/livres/book1",
                "count": 2,
                "book_ids": [
                    ObjectId("111111111111111111111111"),
                    ObjectId("222222222222222222222222"),
                ],
                "titres": ["Titre 1", "Titre 1 bis"],
                "auteur_ids": [
                    ObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
                    ObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
                ],
            },
            {
                "_id": "https://www.babelio.com/livres/book2",
                "count": 3,
                "book_ids": [
                    ObjectId("333333333333333333333333"),
                    ObjectId("444444444444444444444444"),
                    ObjectId("555555555555555555555555"),
                ],
                "titres": ["Titre 2", "Titre 2 v2", "Titre 2 v3"],
                "auteur_ids": [
                    ObjectId("bbbbbbbbbbbbbbbbbbbbbbbb"),
                    ObjectId("bbbbbbbbbbbbbbbbbbbbbbbb"),
                    ObjectId("bbbbbbbbbbbbbbbbbbbbbbbb"),
                ],
            },
        ]

        assert mock_mongodb_service.livres_collection is not None, (
            "livres_collection must be initialized"
        )
        mock_mongodb_service.livres_collection.aggregate.return_value = (
            mock_aggregate_result
        )

        # Execute
        result = await duplicate_books_service.find_duplicate_groups_by_url()

        # Assert
        assert len(result) == 2, "Should return 2 duplicate groups"

        # Premier groupe
        assert result[0]["url_babelio"] == "https://www.babelio.com/livres/book1"
        assert result[0]["count"] == 2
        assert len(result[0]["book_ids"]) == 2

        # Deuxième groupe
        assert result[1]["url_babelio"] == "https://www.babelio.com/livres/book2"
        assert result[1]["count"] == 3
        assert len(result[1]["book_ids"]) == 3

        # Vérifier que l'aggregation a été appelée
        mock_mongodb_service.livres_collection.aggregate.assert_called_once()


class TestGetDuplicateStatistics:
    """
    Tests pour les statistiques des doublons.
    """

    @pytest.mark.asyncio
    async def test_should_calculate_statistics(
        self, duplicate_books_service, mock_mongodb_service
    ):
        """
        Test: Calculer les statistiques pour le dashboard.

        Statistics:
            - total_groups: Nombre de groupes de doublons
            - total_duplicates: Nombre total de livres en doublon
        """
        # Mock aggregate: 2 groupes de doublons
        mock_aggregate_result = [
            {"_id": "url1", "count": 2},
            {"_id": "url2", "count": 3},
        ]

        assert mock_mongodb_service.livres_collection is not None, (
            "livres_collection must be initialized"
        )
        mock_mongodb_service.livres_collection.aggregate.return_value = (
            mock_aggregate_result
        )

        # Execute
        result = await duplicate_books_service.get_duplicate_statistics()

        # Assert
        assert result["total_groups"] == 2, "Should have 2 duplicate groups"
        assert result["total_duplicates"] == 3, (
            "Should have 3 duplicate books "
            "(2-1=1 from first group + 3-1=2 from second group)"
        )
