"""Test TDD RÉEL: Le summary markdown en MongoDB contient-il "P.O.L."? (Issue #85)

Ce test vérifie que quand on valide un livre avec babelio_publisher enrichi,
le markdown du summary en MongoDB est RÉELLEMENT mis à jour avec l'éditeur enrichi.
"""

from unittest.mock import Mock, patch

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


class TestSummaryUpdatedWithBabelioPublisherInMongoDB:
    """Test du vrai comportement: MongoDB reçoit-il le summary mis à jour?"""

    def test_summary_markdown_in_mongodb_contains_enriched_publisher(self):
        """
        RED TEST: Quand on valide un livre avec babelio_publisher,
        le summary markdown SAUVEGARDÉ en MongoDB doit contenir l'éditeur enrichi.

        GIVEN:
          - Livre avec editeur="POL" (du markdown)
          - Enrichi par Babelio en "P.O.L."
          - Utilisateur clique Valider
          - L'avis_critique en MongoDB a le summary original avec "POL"

        WHEN:
          - handle_book_validation() est appelé avec babelio_publisher="P.O.L."

        THEN:
          - update_avis_critique() est appelé
          - L'argument "summary" contient "P.O.L." (pas "POL")
          - Le markdown a été réellement modifié
        """
        # Arrange
        service = CollectionsManagementService()

        # Summary original en MongoDB avec "POL"
        original_summary = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 07 sept. 2025

| Auteur | Titre | Éditeur | Avis détaillés |
|--------|-------|---------|----------------|
| Emmanuel Carrère | Kolkhoze | POL | Excellente critique |
"""

        # Mock du MongoDB
        mock_mongodb = Mock()
        mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",
            "episode_oid": "68bd9ed3582cf994fb66f1d6",
            "summary": original_summary,
        }
        mock_mongodb.create_author_if_not_exists.return_value = ObjectId()
        mock_mongodb.create_book_if_not_exists.return_value = ObjectId()
        mock_mongodb.update_avis_critique = Mock(return_value=True)

        service.mongodb_service = mock_mongodb
        service._mock_mongodb = mock_mongodb

        # Book data avec babelio_publisher enrichi
        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",
            "avis_critique_id": "507f1f77bcf86cd799439012",
            "episode_oid": "68bd9ed3582cf994fb66f1d6",
            "auteur": "Emmanuel Carrère",
            "titre": "Kolkhoze",
            "editeur": "POL",  # Original du markdown
            "user_validated_author": "Emmanuel Carrère",  # Pas de correction
            "user_validated_title": "Kolkhoze",
            "babelio_publisher": "P.O.L.",  # ✅ Enrichissement
        }

        # Patcher le cache service
        with patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
        ) as mock_cache:
            mock_cache.mark_as_processed.return_value = True
            mock_cache.is_summary_corrected.return_value = False
            mock_cache.mark_summary_corrected.return_value = True

            # Act: Appeler le service de validation
            service.handle_book_validation(book_data)

            # Assert: Vérifier que update_avis_critique a été appelé
            assert mock_mongodb.update_avis_critique.called, (
                "❌ FAIL: update_avis_critique n'a pas été appelé"
            )

            # RED TEST: Vérifier le contenu du summary mis à jour
            call_args = mock_mongodb.update_avis_critique.call_args[0]
            updated_data = call_args[1]

            print("\n📊 update_avis_critique appelé avec:")
            print(f"  - avis_critique_id: {call_args[0]}")
            print(f"  - update keys: {list(updated_data.keys())}")

            # RED TEST CRITIQUE: Le summary a-t-il été mis à jour?
            assert "summary" in updated_data, (
                "❌ FAIL: 'summary' n'est pas dans l'update!"
            )

            updated_summary = updated_data["summary"]

            print(
                f"\n📝 Summary MD original contient 'POL'? {('POL' in original_summary)}"
            )
            print(
                f"📝 Summary MD updated contient 'P.O.L.'? {('P.O.L.' in updated_summary)}"
            )
            print(
                f"📝 Summary MD updated contient 'POL'? {('| POL |' in updated_summary)}"
            )

            # RED TEST: Vérifier que le summary a RÉELLEMENT changé
            if "P.O.L." not in updated_summary:
                print(
                    "\n❌ CRITICAL FAIL: Le summary n'a pas été mis à jour avec 'P.O.L.'!"
                )
                print(f"Summary reçu:\n{updated_summary}\n")
                raise AssertionError("Le summary n'a pas été mis à jour avec l'éditeur enrichi")

            if "| POL |" in updated_summary:
                print(
                    "\n⚠️ WARNING: Le summary contient toujours 'POL' (pas remplacé par 'P.O.L.')"
                )

            # Vérifier la ligne complète du tableau
            assert "| Emmanuel Carrère | Kolkhoze | P.O.L. |" in updated_summary, (
                "❌ FAIL: La ligne du livre ne contient pas 'P.O.L.' enrichi"
            )

            print("\n✅ SUCCESS: Summary markdown contient l'éditeur enrichi 'P.O.L.'")
