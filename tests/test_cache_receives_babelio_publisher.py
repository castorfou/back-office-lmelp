"""Test TDD: Le cache reçoit-il babelio_publisher pour que le frontend puisse l'afficher?

C'est l'issue RÉELLE: le summary en BD est mis à jour correctement,
MAIS le cache (qui est retourné au frontend) ne contient pas babelio_publisher!
"""

from unittest.mock import Mock

from bson import ObjectId

from back_office_lmelp.services.livres_auteurs_cache_service import (
    LivresAuteursCacheService,
)


class TestCacheReceivesBabelioPublisher:
    """Test du vrai problème: le cache reçoit-il babelio_publisher?"""

    def test_cache_should_store_babelio_publisher_for_frontend(self):
        """
        RED TEST: Quand mark_as_processed() reçoit babelio_publisher,
        le cache doit le stocker SÉPARÉMENT pour que le frontend le reçoive.

        GIVEN:
          - Livre enrichi: editeur="POL" (du markdown) + babelio_publisher="P.O.L."
          - mark_as_processed() appelé avec metadata["babelio_publisher"]="P.O.L."

        WHEN:
          - update_validation_status() enregistre les données en MongoDB

        THEN:
          - Le cache doit contenir BOTH editeur ET babelio_publisher
          - Pas d'écrasement de editeur
          - Le frontend reçoit les deux champs
        """
        # Arrange
        service = LivresAuteursCacheService()
        cache_id = ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret

        # Mock du MongoDB collection
        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection = Mock()
        mock_collection.update_one.return_value = mock_result
        service.mongodb_service = Mock()
        service.mongodb_service.get_collection.return_value = mock_collection

        # Metadata avec babelio_publisher enrichi
        metadata = {
            "babelio_publisher": "P.O.L.",
        }

        # Act: Appeler mark_as_processed avec babelio_publisher
        result = service.mark_as_processed(
            cache_id=cache_id,
            author_id=ObjectId(),
            book_id=ObjectId(),
            metadata=metadata,
        )

        # Assert: Vérifier what MongoDB reçoit réellement
        assert mock_collection.update_one.called

        call_args = mock_collection.update_one.call_args[0]
        filter_dict = call_args[0]
        update_dict = call_args[1]["$set"]

        print("\n🔍 Cache update_one appelé avec:")
        print(f"  Filter: {filter_dict}")
        print(f"  Update keys: {list(update_dict.keys())}")

        # RED TEST: Afficher les champs mis à jour
        print("\n📋 Champs dans l'update:")
        for key in sorted(update_dict.keys()):
            print(f"  - {key}: {update_dict[key]}")

        # RED TEST CRITIQUE: babelio_publisher est-il présent?
        if "babelio_publisher" in update_dict:
            print("\n✅ babelio_publisher PRÉSENT dans l'update")
            print(f"   Valeur: {update_dict['babelio_publisher']}")
        else:
            print("\n❌ BUG FOUND: babelio_publisher MANQUANT dans l'update!")

        # RED TEST: editeur a-t-il été écrasé?
        if "editeur" in update_dict:
            print(f"\n⚠️ editeur MIS À JOUR: {update_dict['editeur']}")
            if update_dict["editeur"] == "P.O.L.":
                print("   ❌ BUG: editeur a été écrasé avec babelio_publisher!")

        # RED TEST: Vérifier que editeur n'a PAS été écrasé
        # (Actuellement ce test va ÉCHOUER car il Y A UN BUG ligne 252 du cache_service)
        if "editeur" in update_dict and update_dict.get("editeur") == "P.O.L.":
            print("\n🔴 RED TEST ÉCHOUÉ: editeur a été écrasé!")
            print("   Le frontend reçoit editeur='P.O.L.' au lieu de editeur='POL'")
            print("   Les deux champs ne sont PAS distincts!")
            assert False, (
                "❌ BUG CONFIRMÉ: editeur a été écrasé avec babelio_publisher!"
            )
