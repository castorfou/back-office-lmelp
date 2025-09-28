"""Test TDD pour le bug des champs suggested manquants pour les livres not_found."""

from unittest.mock import patch

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


def test_not_found_book_should_always_have_suggested_fields():
    """
    Test TDD RED phase: Les livres not_found DOIVENT avoir suggested_author/suggested_title.

    Reproduit le bug observé : Nin Antico n'a pas de champs suggested après validation.
    """
    # ARRANGE
    service = CollectionsManagementService()
    cache_id = ObjectId("68d7fa7f92d24efb2c41ab1a")  # pragma: allowlist secret
    author_id = ObjectId("68d152157e4140105a6977c2")  # pragma: allowlist secret
    book_id = ObjectId("68d7f68383ac9ac399ec8cfb")  # pragma: allowlist secret

    # Données typiques d'un livre not_found (reproduire exactement ce que le frontend envoie)
    book_data = {
        "cache_id": str(cache_id),
        "auteur": "Nin Antico",  # Données originales du cache
        "titre": "Une Obsession",
        "editeur": "Dargaud",
        # CRITICAL: Pour not_found, le frontend envoie peut-être différemment
        # Testons d'abord sans user_entered_* pour voir si c'est ça le problème
    }

    # ACT & ASSERT
    with (
        patch.object(service, "mongodb_service") as mock_mongodb,
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
        ) as mock_cache_service,
    ):
        # Setup mocks
        mock_mongodb.create_author_if_not_exists.return_value = author_id
        mock_mongodb.create_book_if_not_exists.return_value = book_id
        mock_mongodb.update_book_validation.return_value = True
        mock_cache_service.mark_as_processed.return_value = True

        # Act: Appeler la méthode unifiée
        result = service.handle_book_validation(book_data)

        # Assert: Comportement attendu
        assert result["success"] is True

        # CRITICAL: Vérifier que les champs suggested sont TOUJOURS présents
        call_args = mock_mongodb.update_book_validation.call_args[0]
        metadata = call_args[2]  # 3ème argument (metadata)

        # Ces assertions doivent passer pour corriger le bug
        assert "suggested_author" in metadata, (
            f"Bug confirmé: suggested_author manquant. Métadonnées: {metadata}"
        )
        assert "suggested_title" in metadata, (
            f"Bug confirmé: suggested_title manquant. Métadonnées: {metadata}"
        )

        # Pour not_found, suggested doit être = à la saisie utilisateur
        assert metadata["suggested_author"] == "Nin Antico"
        assert metadata["suggested_title"] == "Une Obsession"

        print(
            "✅ Fix appliqué: Les livres not_found ont maintenant des champs suggested!"
        )


def test_not_found_with_empty_user_entered_should_fallback_to_original():
    """
    Test TDD: Si user_entered est vide, fallback vers les données originales du cache.
    """
    # ARRANGE
    service = CollectionsManagementService()
    cache_id = ObjectId("68d7fa7f92d24efb2c41ab1a")  # pragma: allowlist secret
    author_id = ObjectId("68d152157e4140105a6977c2")  # pragma: allowlist secret
    book_id = ObjectId("68d7f68383ac9ac399ec8cfb")  # pragma: allowlist secret

    # Cas où user_entered est vide ou manquant
    book_data = {
        "cache_id": str(cache_id),
        "auteur": "Auteur Original Cache",
        "titre": "Titre Original Cache",
        "editeur": "Éditeur Original",
        # user_entered_* manquants ou vides
        "user_entered_author": "",  # Vide
        "user_entered_title": "",  # Vide
    }

    # ACT & ASSERT
    with (
        patch.object(service, "mongodb_service") as mock_mongodb,
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service"
        ) as mock_cache_service,
    ):
        # Setup mocks
        mock_mongodb.create_author_if_not_exists.return_value = author_id
        mock_mongodb.create_book_if_not_exists.return_value = book_id
        mock_mongodb.update_book_validation.return_value = True
        mock_cache_service.mark_as_processed.return_value = True

        # Act
        result = service.handle_book_validation(book_data)

        # Assert: Fallback vers les données originales du cache
        assert result["success"] is True

        call_args = mock_mongodb.update_book_validation.call_args[0]
        metadata = call_args[2]

        # Fallback vers les données originales du cache
        assert metadata["suggested_author"] == "Auteur Original Cache"
        assert metadata["suggested_title"] == "Titre Original Cache"
