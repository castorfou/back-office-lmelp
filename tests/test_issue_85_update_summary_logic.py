"""TDD: Test the _update_summary_with_correction() logic for Issue #85.

This tests the specific method that decides WHETHER to update the summary.
The problem is in the condition that prevents updates when is_summary_corrected=True.
"""

from unittest.mock import Mock, patch

from bson import ObjectId


def test_red_update_summary_with_correction_called_with_babelio_publisher():
    """
    RED TEST: _update_summary_with_correction() should be called
    when babelio_publisher is provided, even if is_summary_corrected=True.

    Current (BUGGY) behavior:
    - If is_summary_corrected=True, _update_summary_with_correction() is SKIPPED
    - Even if babelio_publisher needs to be applied!

    Expected (FIXED) behavior:
    - If babelio_publisher is provided AND different from editeur,
      _update_summary_with_correction() should be CALLED regardless of is_summary_corrected
    """

    from back_office_lmelp.services.collections_management_service import (
        CollectionsManagementService,
    )

    original_summary = """## LIVRES
| Emmanuel Carrère | Kolkhoze | POL |
"""

    avis_critique_id = ObjectId()
    cache_id = ObjectId()

    # Mock MongoDB
    mock_mongodb = Mock()
    mock_mongodb.get_avis_critique_by_id.return_value = {
        "_id": avis_critique_id,
        "summary": original_summary,
    }
    mock_mongodb.update_avis_critique = Mock(return_value=True)

    # Create service with mocked MongoDB
    service = CollectionsManagementService()
    service.mongodb_service = mock_mongodb

    # Mock _update_summary_with_correction to track if it's called
    original_update_summary = service._update_summary_with_correction
    update_summary_calls = []

    def mock_update_summary_method(**kwargs):
        update_summary_calls.append(kwargs)
        return original_update_summary(**kwargs)

    service._update_summary_with_correction = mock_update_summary_method

    # Mock cache service
    with patch(
        "back_office_lmelp.services.collections_management_service.livres_auteurs_cache_service"
    ) as mock_cache:
        # KEY: Simulate production scenario
        mock_cache.is_summary_corrected.return_value = True  # Already corrected
        mock_cache.mark_summary_corrected.return_value = True

        print("\n" + "=" * 80)
        print(
            "📋 SCENARIO: babelio_publisher arrives after summary was already corrected"
        )
        print("=" * 80)
        print("  is_summary_corrected(cache_id): True")
        print("  babelio_publisher: 'P.O.L.'")
        print("  original editeur: 'POL'")

        # Act: Call _update_summary_with_correction directly
        # This is the internal method that decides whether to update
        try:
            service._update_summary_with_correction(
                avis_critique_id=str(avis_critique_id),
                original_author="Emmanuel Carrère",
                original_title="Kolkhoze",
                corrected_author="Emmanuel Carrère",
                corrected_title="Kolkhoze",
                cache_id=cache_id,
                original_publisher="POL",
                corrected_publisher="P.O.L.",  # Babelio enrichment
            )
            print("\n✅ _update_summary_with_correction() executed")
        except Exception as e:
            print(f"\n❌ _update_summary_with_correction() failed: {e}")
            raise

        # Assert: Check if MongoDB was updated
        if mock_mongodb.update_avis_critique.called:
            print("✅ update_avis_critique WAS called")
            call_args = mock_mongodb.update_avis_critique.call_args[0]
            updates = call_args[1]

            if "summary" in updates:
                updated_summary = updates["summary"]
                print("✅ Summary was updated")

                if "| P.O.L. |" in updated_summary:
                    print("✅ GREEN: Summary contains enriched publisher 'P.O.L.'")
                    print("✅ Babelio enrichment was APPLIED!")
                else:
                    print("❌ RED: Summary does NOT contain 'P.O.L.'")
                    print("❌ Enrichment was NOT applied")
                    raise AssertionError("Babelio enrichment not in summary")
            else:
                print(f"❌ summary not in updates: {list(updates.keys())}")
        else:
            print("❌ update_avis_critique was NOT called")
            print("   Summary update was SKIPPED!")
            print("\n   This is the BUG!")
            print("   The condition prevents the call when is_summary_corrected=True")
            raise AssertionError(
                "Summary update was skipped - Babelio enrichment ignored"
            )
