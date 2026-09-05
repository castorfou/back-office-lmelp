"""Tests TDD pour la sélection de livres en cache par statut/_id (Issue #282).

Bug racine: `auto_process_verified_books()` (bouton "Traiter") sélectionnait
les livres via `mongodb_service.get_books_by_validation_status()`, qui
interroge le champ legacy `validation_status`/`biblio_verification_status`
— jamais peuplé par le flux d'écriture actif (`create_cache_entry`, champ
`status` unique). Ces nouvelles méthodes interrogent le bon champ.
"""

from unittest.mock import patch

from bson import ObjectId

from back_office_lmelp.services.livres_auteurs_cache_service import (
    LivresAuteursCacheService,
)


class TestGetBooksByStatus:
    """Tests TDD pour get_books_by_status() (tous épisodes confondus)."""

    def test_get_books_by_status_should_query_status_field(self):
        """Doit interroger le champ `status` (pas `validation_status` legacy)."""
        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_cursor = [
                {"_id": ObjectId(), "auteur": "A", "titre": "T", "status": "verified"}
            ]
            mock_mongodb.get_collection.return_value.find.return_value = mock_cursor

            service = LivresAuteursCacheService()
            result = service.get_books_by_status("verified")

            mock_mongodb.get_collection.return_value.find.assert_called_once_with(
                {"status": "verified"}
            )
            assert result == mock_cursor


class TestGetCacheEntryById:
    """Tests TDD pour get_cache_entry_by_id() (ciblage d'un livre précis)."""

    def test_get_cache_entry_by_id_should_return_matching_document(self):
        """Doit retourner le document dont `_id` correspond."""
        cache_id = ObjectId("64f1234567890abcdef99999")  # pragma: allowlist secret
        expected_doc = {
            "_id": cache_id,
            "auteur": "A",
            "titre": "T",
            "status": "verified",
        }

        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.find_one.return_value = (
                expected_doc
            )

            service = LivresAuteursCacheService()
            result = service.get_cache_entry_by_id(cache_id)

            mock_mongodb.get_collection.return_value.find_one.assert_called_once_with(
                {"_id": cache_id}
            )
            assert result == expected_doc

    def test_get_cache_entry_by_id_should_return_none_when_not_found(self):
        """Doit retourner None si aucune entrée ne correspond."""
        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
        ) as mock_mongodb:
            mock_mongodb.get_collection.return_value.find_one.return_value = None

            service = LivresAuteursCacheService()
            result = service.get_cache_entry_by_id(ObjectId())

            assert result is None
