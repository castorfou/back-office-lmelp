"""TDD: Test that set_validation_results updates summary markdown with Babelio publisher.

RED TEST: This test should FAIL until we implement summary update in set_validation_results.

SCENARIO:
1. Frontend sends set-validation-results with babelio_publisher enrichment
2. Backend should update the avis_critique summary markdown
3. The old publisher (POL) should be replaced with enriched publisher (P.O.L.)
"""

from unittest.mock import patch

import pytest
from bson import ObjectId


def test_red_set_validation_results_should_update_summary_with_babelio_publisher():
    """
    🔴 RED TEST: set_validation_results should update summary markdown when babelio_publisher is provided.

    GIVEN:
    - Avis critique with summary: "| Emmanuel Carrère | Kolkhoze | POL |"
    - Validation result with babelio_publisher: "P.O.L."

    WHEN:
    - set_validation_results is called with verified status and babelio_publisher

    THEN:
    - Summary should be updated to: "| Emmanuel Carrère | Kolkhoze | P.O.L. |"
    """
    from fastapi.testclient import TestClient

    from back_office_lmelp.app import app

    client = TestClient(app)

    # Arrange
    avis_critique_id = str(ObjectId())
    episode_oid = "68bd9ed3582cf994fb66f1d6"  # pragma: allowlist secret

    original_summary = """## LIVRES
| Emmanuel Carrère | Kolkhoze | POL |
"""

    # Mock the services
    with (
        patch("back_office_lmelp.app.livres_auteurs_cache_service") as mock_cache,
        patch("back_office_lmelp.app.mongodb_service") as mock_mongodb,
        patch("back_office_lmelp.app.memory_guard") as mock_memory,
    ):
        # Setup mocks
        mock_memory.check_memory_limit.return_value = None
        mock_cache.create_cache_entry.return_value = ObjectId()

        mock_mongodb.create_author_if_not_exists.return_value = ObjectId()
        mock_mongodb.create_book_if_not_exists.return_value = ObjectId()

        # Mock get_avis_critique_by_id to return the original summary
        mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": ObjectId(avis_critique_id),
            "summary": original_summary,
        }

        # Mock update_avis_critique to capture what gets updated
        updated_data = {}

        def mock_update(avis_id, update_dict):
            updated_data.update(update_dict)
            return True

        mock_mongodb.update_avis_critique.side_effect = mock_update

        # Act: Call set_validation_results with babelio_publisher
        request_data = {
            "episode_oid": episode_oid,
            "avis_critique_id": avis_critique_id,
            "books": [
                {
                    "auteur": "Emmanuel Carrère",
                    "titre": "Kolkhoze",
                    "editeur": "POL",
                    "programme": True,
                    "validation_status": "verified",
                    "suggested_author": "Emmanuel Carrère",
                    "suggested_title": "Kolkhoze",
                    "babelio_url": "https://www.babelio.com/livres/Carrere-Kolkhoze/1839593",
                    "babelio_publisher": "P.O.L.",  # 🔴 KEY: Babelio enrichment
                }
            ],
        }

        response = client.post("/api/set-validation-results", json=request_data)

        # Assert
        assert response.status_code == 200
        print("\n🔴 RED TEST - What was updated in avis_critique:")
        print(f"   Updated data keys: {list(updated_data.keys())}")
        print(f"   Updated data: {updated_data}")

        # 🔴 This assertion SHOULD FAIL currently because summary is not being updated
        if "summary" in updated_data:
            updated_summary = updated_data["summary"]
            print("\n✅ GREEN: Summary WAS updated!")
            print(f"   Original: {original_summary}")
            print(f"   Updated:  {updated_summary}")

            # Verify the publisher was updated
            assert "P.O.L." in updated_summary, (
                "Summary should contain enriched publisher P.O.L."
            )
            assert "POL" not in updated_summary or "P.O.L." in updated_summary, (
                "Summary should have P.O.L. instead of POL"
            )
        else:
            print("\n🔴 RED: Summary was NOT updated!")
            print(
                "   Only 'editeur' field was updated, but summary markdown is still unchanged"
            )
            pytest.fail(
                "Summary markdown should be updated with babelio_publisher "
                "but currently only the editeur field is updated"
            )
