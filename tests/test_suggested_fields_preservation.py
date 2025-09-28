"""Test pour vérifier la préservation des champs suggested_author/suggested_title après validation manuelle."""

from unittest.mock import patch

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


def test_manually_validate_suggestion_should_preserve_suggested_fields():
    """
    Test GREEN phase : vérifie que les champs suggested_author/suggested_title sont préservés.

    Ce test vérifie que le fix fonctionne : quand un utilisateur corrige manuellement un livre,
    les corrections (suggested_author/suggested_title) SONT maintenant sauvegardées dans le cache.
    """
    # ARRANGE
    service = CollectionsManagementService()
    cache_id = ObjectId("64a1b2c3d4e5f6789abcdef0")  # pragma: allowlist secret
    author_id = ObjectId("64a1b2c3d4e5f6789abcdef1")  # pragma: allowlist secret
    book_id = ObjectId("64a1b2c3d4e5f6789abcdef2")  # pragma: allowlist secret

    # Données de validation avec champs suggested que l'utilisateur a corrigés
    validation_data = {
        "cache_id": str(cache_id),
        "auteur": "Auteur Original",
        "titre": "Titre Original",
        "editeur": "Éditeur Test",
        "user_validated_author": "Correction Utilisateur Auteur",
        "user_validated_title": "Correction Utilisateur Titre",
        "suggested_author": "Correction Utilisateur Auteur",  # Corrections de l'utilisateur
        "suggested_title": "Correction Utilisateur Titre",  # qui doivent être préservées
    }

    # ACT & ASSERT - Utiliser des mocks complets pour isoler le problème
    with (
        patch.object(service, "mongodb_service") as mock_mongodb,
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
        ) as mock_cache_service,
    ):
        # Setup des mocks avec collections pour éviter "Connexion MongoDB non établie"
        mock_mongodb.auteurs_collection = True
        mock_mongodb.livres_collection = True
        mock_mongodb.livresauteurs_cache_collection = True
        mock_mongodb.create_author_if_not_exists.return_value = author_id
        mock_mongodb.create_book_if_not_exists.return_value = book_id
        mock_mongodb.update_book_validation.return_value = True

        # Mock cache service
        mock_cache_service.mark_as_processed.return_value = True
        mock_cache_service.get_books_by_episode_oid.return_value = []  # For cache_id lookup

        # Appeler la méthode
        result = service.manually_validate_suggestion(validation_data)

        # Vérifications de base
        assert result["success"] is True

        # VÉRIFICATION DU FIX : Les champs suggested SONT maintenant transmis
        actual_call = mock_mongodb.update_book_validation.call_args_list[0]
        actual_metadata = actual_call[0][2]  # 3ème argument (metadata)

        # Ce qui DEVRAIT être transmis (avec les champs suggested) - maintenant implémenté
        expected_complete_behavior = {
            "validated_author": "Correction Utilisateur Auteur",
            "validated_title": "Correction Utilisateur Titre",
            "suggested_author": "Correction Utilisateur Auteur",  # ✅ MAINTENANT PRÉSENT !
            "suggested_title": "Correction Utilisateur Titre",  # ✅ MAINTENANT PRÉSENT !
        }

        # Cette assertion doit maintenant passer - le fix a été implémenté
        assert actual_metadata == expected_complete_behavior, (
            f"Fix confirmé: Les champs suggested sont transmis. Reçu: {actual_metadata}"
        )

        # Vérifier que les champs suggested sont présents dans les données d'entrée
        assert "suggested_author" in validation_data
        assert "suggested_title" in validation_data

        # Et sont maintenant utilisés par le backend
        assert "suggested_author" in actual_metadata
        assert "suggested_title" in actual_metadata

        print(
            "✅ Fix confirmé: Les champs suggested_author/suggested_title sont maintenant préservés!"
        )
