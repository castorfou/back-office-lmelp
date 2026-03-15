"""Tests TDD pour les fonctionnalités de couvertures (Issue #238).

Tests pour :
- get_migration_status() inclut les statistiques couvertures
- get_books_pending_covers() retourne les livres avec url_babelio mais sans url_cover
- save_cover_url() sauvegarde url_cover dans MongoDB
"""

from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from back_office_lmelp.services.babelio_migration_service import (
    BabelioMigrationService,
)


class TestCoverStats:
    """Tests pour les statistiques de couvertures dans get_migration_status()."""

    @pytest.fixture
    def mock_mongodb_service(self):
        """Mock du service MongoDB."""
        mock = MagicMock()
        mock.db = MagicMock()
        return mock

    @pytest.fixture
    def mock_babelio_service(self):
        """Mock du service Babelio."""
        return MagicMock()

    @pytest.fixture
    def migration_service(self, mock_mongodb_service, mock_babelio_service):
        """Instance du service de migration avec mocks."""
        return BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

    def test_get_migration_status_includes_cover_stats(
        self, migration_service, mock_mongodb_service
    ):
        """RED Test: get_migration_status() doit inclure les stats des couvertures.

        Scénario business :
        - 100 livres total
        - 80 avec url_babelio (liés Babelio)
        - 30 avec url_cover (couvertures déjà trouvées)
        - 10 avec babelio_not_found (pas de couverture possible)
        - 40 en attente de couverture (80 - 30 - 10)
        """
        mock_livres = MagicMock()
        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()

        mock_mongodb_service.db.__getitem__.side_effect = lambda name: {
            "livres": mock_livres,
            "auteurs": mock_auteurs,
            "babelio_problematic_cases": mock_problematic,
        }[name]

        # Comptes livres classiques
        mock_livres.count_documents.side_effect = lambda q: {
            frozenset(): 100,
            frozenset([("url_babelio", {"$exists": True, "$ne": None})].copy()): 80,
            frozenset([("babelio_not_found", True)].copy()): 10,
        }.get(frozenset((k, str(v)) for k, v in q.items()), 0)

        # Mock count_documents avec correspondance flexible
        def count_docs(query):
            keys = set(query.keys())
            if not keys:
                return 100
            if (
                "url_cover" in keys
                and "url_babelio" not in keys
                and "babelio_not_found" not in keys
            ):
                # covers_with_url query: {"url_cover": {"$exists": True, "$ne": None}}
                return 30
            if "url_babelio" in keys and len(keys) == 1:
                # migrated_count query
                return 80
            if "babelio_not_found" in keys and len(keys) == 1:
                return 10
            if "url_babelio" in keys and "$or" in keys:
                # covers_pending: {"url_babelio": ..., "$or": [url_cover absent ou None]}
                return 40
            return 0

        mock_livres.count_documents.side_effect = count_docs
        mock_livres.find_one.return_value = None
        mock_auteurs.count_documents.return_value = 0
        mock_problematic.count_documents.return_value = 0

        status = migration_service.get_migration_status()

        # Vérifier que les stats couvertures sont présentes
        assert "covers_with_url" in status, "Status doit contenir covers_with_url"
        assert "covers_pending" in status, "Status doit contenir covers_pending"
        assert "covers_not_applicable" in status, (
            "Status doit contenir covers_not_applicable"
        )
        assert "covers_total" in status, "Status doit contenir covers_total"


class TestGetBooksPendingCovers:
    """Tests pour get_books_pending_covers()."""

    @pytest.fixture
    def mock_mongodb_service(self):
        mock = MagicMock()
        mock.db = MagicMock()
        return mock

    @pytest.fixture
    def mock_babelio_service(self):
        return MagicMock()

    @pytest.fixture
    def migration_service(self, mock_mongodb_service, mock_babelio_service):
        return BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

    def test_get_books_pending_covers_returns_books_with_babelio_url_but_no_cover(
        self, migration_service, mock_mongodb_service
    ):
        """RED Test: get_books_pending_covers() retourne les livres avec url_babelio mais sans url_cover.

        Scénario :
        - 3 livres avec url_babelio mais sans url_cover → doivent être retournés
        - 2 livres avec url_babelio ET url_cover → ne doivent PAS être retournés
        """
        mock_livres = MagicMock()
        mock_mongodb_service.db.__getitem__.return_value = mock_livres

        pending_books = [
            {
                "_id": ObjectId("674e9a8f1234567890abcde1"),
                "titre": "Livre A",
                "url_babelio": "https://www.babelio.com/livres/A/1",
            },
            {
                "_id": ObjectId("674e9a8f1234567890abcde2"),
                "titre": "Livre B",
                "url_babelio": "https://www.babelio.com/livres/B/2",
            },
            {
                "_id": ObjectId("674e9a8f1234567890abcde3"),
                "titre": "Livre C",
                "url_babelio": "https://www.babelio.com/livres/C/3",
            },
        ]
        mock_livres.find.return_value = iter(pending_books)

        result = migration_service.get_books_pending_covers()

        # Vérifier que la méthode retourne une liste
        assert isinstance(result, list)
        # Vérifier que les livres retournés ont bien url_babelio
        for book in result:
            assert "url_babelio" in book
            assert book["url_babelio"] is not None
        # Vérifier que 3 livres sont retournés
        assert len(result) == 3

    def test_get_books_pending_covers_serializes_objectid(
        self, migration_service, mock_mongodb_service
    ):
        """RED Test: get_books_pending_covers() doit sérialiser les ObjectId en string.

        Scénario : les _id MongoDB sont ObjectId, mais l'API doit retourner des strings
        pour être JSON-serializable.
        """
        mock_livres = MagicMock()
        mock_mongodb_service.db.__getitem__.return_value = mock_livres

        book_id = ObjectId("674e9a8f1234567890abcde1")
        mock_livres.find.return_value = iter(
            [
                {
                    "_id": book_id,
                    "titre": "Livre A",
                    "url_babelio": "https://www.babelio.com/livres/A/1",
                }
            ]
        )

        result = migration_service.get_books_pending_covers()

        assert len(result) == 1
        # L'_id doit être une string, pas un ObjectId
        assert isinstance(result[0]["_id"], str), "_id doit être sérialisé en string"


class TestSaveCoverUrl:
    """Tests pour save_cover_url()."""

    @pytest.fixture
    def mock_mongodb_service(self):
        mock = MagicMock()
        mock.db = MagicMock()
        return mock

    @pytest.fixture
    def mock_babelio_service(self):
        return MagicMock()

    @pytest.fixture
    def migration_service(self, mock_mongodb_service, mock_babelio_service):
        return BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

    def test_save_cover_url_updates_mongodb(
        self, migration_service, mock_mongodb_service
    ):
        """RED Test: save_cover_url() doit sauvegarder url_cover dans MongoDB.

        Scénario :
        - Un livre existe avec l'ID donné
        - save_cover_url() est appelé avec l'ID et une URL de couverture
        - MongoDB doit être mis à jour avec {"url_cover": url_cover}
        """
        mock_livres = MagicMock()
        mock_mongodb_service.db.__getitem__.return_value = mock_livres

        livre_id = "674e9a8f1234567890abcde1"
        url_cover = "https://www.babelio.com/couv/CVT_Simone-monet_42.jpg"

        mock_update_result = MagicMock()
        mock_update_result.matched_count = 1
        mock_livres.update_one.return_value = mock_update_result

        result = migration_service.save_cover_url(livre_id, url_cover)

        # Vérifier que le résultat est True (succès)
        assert result is True

        # Vérifier que update_one a été appelé avec les bons paramètres
        mock_livres.update_one.assert_called_once()
        call_args = mock_livres.update_one.call_args
        # Premier arg : filtre avec _id
        filter_arg = call_args[0][0]
        assert "_id" in filter_arg
        # Deuxième arg : update avec $set url_cover
        update_arg = call_args[0][1]
        assert "$set" in update_arg
        assert "url_cover" in update_arg["$set"]
        assert update_arg["$set"]["url_cover"] == url_cover

    def test_save_cover_url_returns_false_for_invalid_id(
        self, migration_service, mock_mongodb_service
    ):
        """RED Test: save_cover_url() retourne False pour un ID invalide."""
        mock_livres = MagicMock()
        mock_mongodb_service.db.__getitem__.return_value = mock_livres

        invalid_id = "not-a-valid-object-id"
        url_cover = "https://www.babelio.com/couv/CVT_test_42.jpg"

        result = migration_service.save_cover_url(invalid_id, url_cover)

        assert result is False
        # update_one ne doit pas être appelé avec un ID invalide
        mock_livres.update_one.assert_not_called()

    def test_save_cover_url_returns_false_if_livre_not_found(
        self, migration_service, mock_mongodb_service
    ):
        """RED Test: save_cover_url() retourne False si le livre n'existe pas."""
        mock_livres = MagicMock()
        mock_mongodb_service.db.__getitem__.return_value = mock_livres

        livre_id = "674e9a8f1234567890abcde1"
        url_cover = "https://www.babelio.com/couv/CVT_test_42.jpg"

        mock_update_result = MagicMock()
        mock_update_result.matched_count = 0  # Livre non trouvé
        mock_livres.update_one.return_value = mock_update_result

        result = migration_service.save_cover_url(livre_id, url_cover)

        assert result is False
