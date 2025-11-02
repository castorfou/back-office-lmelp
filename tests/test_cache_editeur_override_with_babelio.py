"""Test TDD: Simulates the ACTUAL production bug (Issue #85).

RED PHASE: This test reproduces the exact production scenario.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

from bson import ObjectId


def test_green_both_editeur_and_babelio_publisher_coexist_separately():
    """
    GREEN PHASE (CORRECTED): babelio_publisher and editeur are SEPARATE fields.

    THE FIX (Issue #85):
    livres_auteurs_cache_service.py now keeps both fields separate:
    - editeur: Original transcribed value from markdown (e.g., "POL")
    - babelio_publisher: Enriched value from Babelio (e.g., "P.O.L.")

    CORRECT BEHAVIOR:
    When mark_as_processed() receives metadata with babelio_publisher,
    the cache stores BOTH fields without overwriting editeur.

    Frontend can then:
    1. Display babelio_publisher if available (enriched value)
    2. Fall back to editeur if babelio_publisher is missing
    """
    from back_office_lmelp.services.livres_auteurs_cache_service import (
        LivresAuteursCacheService,
    )

    cache_id = ObjectId("68f57f3497c9ca8cb481ecad")  # pragma: allowlist secret
    author_id = ObjectId("68e47439f4ac0655e1de7d6e")  # pragma: allowlist secret
    book_id = ObjectId("68e47439f4ac0655e1de7d6f")  # pragma: allowlist secret

    # Cache document BEFORE
    cache_doc = {
        "_id": cache_id,
        "avis_critique_id": ObjectId(
            "68bddf38d79eae6a485abdaf"  # pragma: allowlist secret
        ),
        "episode_oid": "68bd9ed3582cf994fb66f1d6",  # pragma: allowlist secret
        "auteur": "Emmanuel Carrère",
        "titre": "Kolkhoze",
        "editeur": "POL",  # Original transcribed value
        "programme": True,
        "status": "verified",
        "babelio_url": "https://www.babelio.com/livres/Carrere-Kolkhoze/1839593",
        "babelio_publisher": "P.O.L.",  # Enriched value from Babelio
        "created_at": datetime(2025, 10, 20, 1, 53, 13, 449000),
        "updated_at": datetime(2025, 10, 20, 1, 53, 13, 452000),
    }

    # Metadata WITH babelio_publisher (passed from app.py)
    metadata = {
        "babelio_publisher": "P.O.L.",
    }

    with patch(
        "back_office_lmelp.services.livres_auteurs_cache_service.mongodb_service"
    ) as mock_mongodb:
        mock_collection = MagicMock()
        mock_mongodb.get_collection.return_value = mock_collection

        # Mock update_one to mutate the document
        def mock_update_one(filter_dict, update_dict):
            print(
                f"\nDEBUG - update_one called with $set keys: {list(update_dict.get('$set', {}).keys())}"
            )
            if "$set" in update_dict:
                cache_doc.update(update_dict["$set"])
            return MagicMock(modified_count=1)

        mock_collection.update_one.side_effect = mock_update_one

        # Act - Call WITH metadata
        service = LivresAuteursCacheService()
        result = service.mark_as_processed(
            cache_id, author_id, book_id, metadata=metadata
        )

        # Assert
        assert result is True

        # GREEN ASSERTION: Both fields coexist
        print("\nDEBUG - Cache AFTER mark_as_processed:")
        print(f"  editeur: {cache_doc.get('editeur')} (unchanged)")
        print(f"  babelio_publisher: {cache_doc.get('babelio_publisher')} (added)")

        # ✅ GREEN: editeur remains unchanged (original transcribed value)
        assert cache_doc["editeur"] == "POL", (
            f"editeur should remain 'POL' (original transcribed): {cache_doc['editeur']}"
        )

        # ✅ GREEN: babelio_publisher is stored separately
        assert cache_doc.get("babelio_publisher") == "P.O.L.", (
            f"babelio_publisher should be 'P.O.L.' (enriched): {cache_doc.get('babelio_publisher')}"
        )

        print("\n✅ GREEN TEST PASSES - Both fields coexist separately!")
