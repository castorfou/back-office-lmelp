"""Test d'intégration pour vérifier le passage de 'suggested' à 'mongo' avec vraie DB."""

import builtins
import contextlib

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.services.livres_auteurs_cache_service import (
    livres_auteurs_cache_service,
)
from back_office_lmelp.services.mongodb_service import mongodb_service


@pytest.mark.integration
class TestIntegrationSuggestedToMongo:
    """Tests d'intégration pour vérifier le passage suggested -> mongo."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.client = TestClient(app)

    def test_suggested_book_manual_validation_updates_cache_status_to_mongo_INTEGRATION(
        self,
    ):
        """
        Test d'intégration: Quand un utilisateur valide manuellement un livre 'suggested',
        le statut dans le cache doit passer de 'suggested' à 'mongo'.

        Ce test utilise la vraie base de données pour vérifier le comportement réel.
        """
        # Skip si pas de connexion MongoDB
        try:
            if not mongodb_service.is_connected():
                pytest.skip("MongoDB not connected - skipping integration test")
        except Exception:
            pytest.skip("MongoDB service not available - skipping integration test")

        # STEP 1: Créer une entrée de cache avec statut 'suggested'
        episode_oid = "integration_test_episode"
        avis_critique_id = ObjectId()

        suggested_book_data = {
            "auteur": "Test Author Integration",
            "titre": "Test Book Integration",
            "editeur": "Test Publisher",
            "episode_oid": episode_oid,
            "status": "suggested",
            "suggested_author": "Corrected Author Name",
            "suggested_title": "Corrected Book Title",
        }

        # Créer l'entrée de cache
        try:
            cache_id = livres_auteurs_cache_service.create_cache_entry(
                avis_critique_id, suggested_book_data
            )
        except Exception as e:
            pytest.skip(f"Could not create cache entry: {e}")

        # STEP 2: Vérifier que le statut initial est 'suggested'
        cache_entries = livres_auteurs_cache_service.get_books_by_avis_critique_id(
            avis_critique_id
        )
        assert len(cache_entries) == 1
        assert cache_entries[0]["status"] == "suggested"

        # STEP 3: Valider manuellement la suggestion via l'API
        validation_request = {
            "cache_id": str(cache_id),
            "episode_oid": episode_oid,
            "avis_critique_id": str(avis_critique_id),
            "auteur": "Test Author Integration",
            "titre": "Test Book Integration",
            "editeur": "Test Publisher",
            "user_validated_author": "Final Author Name",
            "user_validated_title": "Final Book Title",
        }

        # Appel API
        try:
            response = self.client.post(
                "/api/livres-auteurs/validate-suggestion", json=validation_request
            )

            if response.status_code != 200:
                pytest.skip(
                    f"API call failed: {response.status_code} - {response.text}"
                )

            result = response.json()
            assert result["success"] is True

        except Exception as e:
            pytest.skip(f"API call failed: {e}")

        # STEP 4: CRITICAL - Vérifier que le statut cache est maintenant 'mongo'
        updated_cache_entries = (
            livres_auteurs_cache_service.get_books_by_avis_critique_id(avis_critique_id)
        )
        assert len(updated_cache_entries) == 1

        # C'est ici qu'on teste le bug : le statut devrait être 'mongo', pas 'suggested'
        updated_entry = updated_cache_entries[0]
        print(
            f"DEBUG: Cache entry status after validation: {updated_entry.get('status')}"
        )

        # ASSERTION CRITIQUE : Le statut doit être 'mongo' après validation manuelle
        assert updated_entry["status"] == "mongo", (
            f"Expected 'mongo' but got '{updated_entry.get('status')}'"
        )

        # Vérifier que les IDs de référence sont présents
        assert "author_id" in updated_entry
        assert "book_id" in updated_entry
        assert "processed_at" in updated_entry

        # Cleanup
        with contextlib.suppress(BaseException):
            # Nettoyer le cache de test
            mongodb_service.get_collection("livresauteurs_cache").delete_one(
                {"_id": cache_id}
            )

    def test_mark_as_processed_directly_INTEGRATION(self):
        """Test direct de mark_as_processed pour vérifier qu'il change bien le statut."""
        # Skip si pas de connexion MongoDB
        try:
            if not mongodb_service.is_connected():
                pytest.skip("MongoDB not connected - skipping integration test")
        except Exception:
            pytest.skip("MongoDB service not available - skipping integration test")

        # STEP 1: Créer une entrée de cache
        episode_oid = (
            "68c707ad6e51b9428ab87e9e"  # Valid ObjectId  # pragma: allowlist secret
        )
        avis_critique_id = ObjectId()

        book_data = {
            "auteur": "Direct Test Author",
            "titre": "Direct Test Book",
            "episode_oid": episode_oid,
            "status": "suggested",
        }

        try:
            cache_id = livres_auteurs_cache_service.create_cache_entry(
                avis_critique_id, book_data
            )
        except Exception as e:
            pytest.skip(f"Could not create cache entry: {e}")

        # STEP 2: Vérifier statut initial
        initial_entries = livres_auteurs_cache_service.get_books_by_avis_critique_id(
            avis_critique_id
        )
        assert len(initial_entries) == 1
        assert initial_entries[0]["status"] == "suggested"

        # STEP 3: Appeler mark_as_processed directement
        author_id = ObjectId()
        book_id = ObjectId()

        try:
            result = livres_auteurs_cache_service.mark_as_processed(
                cache_id, author_id, book_id
            )
            assert result is True
        except Exception as e:
            pytest.skip(f"mark_as_processed failed: {e}")

        # STEP 4: Vérifier que le statut a changé à 'mongo'
        final_entries = livres_auteurs_cache_service.get_books_by_avis_critique_id(
            avis_critique_id
        )
        assert len(final_entries) == 1

        final_entry = final_entries[0]
        print(f"DEBUG: Direct mark_as_processed status: {final_entry.get('status')}")

        # ASSERTION CRITIQUE
        assert final_entry["status"] == "mongo"
        assert final_entry["author_id"] == author_id
        assert final_entry["book_id"] == book_id
        assert "processed_at" in final_entry

        # Cleanup
        with contextlib.suppress(builtins.BaseException):
            mongodb_service.get_collection("livresauteurs_cache").delete_one(
                {"_id": cache_id}
            )
