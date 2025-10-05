"""
Tests pour la création d'auteurs avec correction de nom (suggested_author).

Bug identifié: Quand un livre est validé avec une correction d'auteur
(ex: "Adrien Bosque" → "Adrien Bosc"), l'auteur est créé en base avec
le nom ORIGINAL ("Adrien Bosque") au lieu du nom CORRIGÉ ("Adrien Bosc").
"""

from bson import ObjectId


class TestAuthorCreationWithCorrection:
    """Tests de création d'auteurs avec correction de nom."""

    def test_verified_book_creates_author_with_corrected_name(
        self, client, mock_mongodb_service
    ):
        """
        Test qu'un livre verified avec suggested_author crée l'auteur avec le nom corrigé.

        Scénario:
        - Livre extrait: "Adrien Bosque / L'invention de Tristan"
        - Babelio corrige: "Adrien Bosc / L'invention de Tristan"
        - Validation: status=verified, suggested_author="Adrien Bosc"
        - Résultat attendu: Auteur créé avec nom="Adrien Bosc" ✅ (PAS "Adrien Bosque" ❌)
        """
        # Créer un mock d'épisode avec avis_critique_id
        episode_oid = "6865f9a8a1418e3d7c63d081"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "686c494628b9e451c1cee330"  # pragma: allowlist secret
        )

        # Simuler une réponse de validation avec correction d'auteur
        response = client.post(
            "/api/livres-auteurs/set-validation-results",
            json={
                "episode_oid": episode_oid,
                "avis_critique_id": str(avis_critique_id),
                "books": [
                    {
                        "auteur": "Adrien Bosque",  # Nom ORIGINAL (incorrect)
                        "titre": "L'invention de Tristan",
                        "editeur": "Stock",
                        "programme": False,
                        "validation_status": "verified",
                        "suggested_author": "Adrien Bosc",  # Nom CORRIGÉ par Babelio
                        "suggested_title": "L'invention de Tristan",
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Vérifier que create_author_if_not_exists a été appelé avec le nom CORRIGÉ
        mock_mongodb_service.create_author_if_not_exists.assert_called_once_with(
            "Adrien Bosc"  # ✅ Nom corrigé, PAS "Adrien Bosque"
        )

    def test_verified_book_without_correction_uses_original_name(
        self, client, mock_mongodb_service
    ):
        """
        Test qu'un livre verified SANS correction utilise le nom original.

        Scénario:
        - Livre extrait: "Victoria Mas / L'orpheline du temple"
        - Babelio valide: status=verified, confidence=1.0, pas de correction
        - Résultat attendu: Auteur créé avec nom="Victoria Mas"
        """
        episode_oid = "6865f9a8a1418e3d7c63d081"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "686c494628b9e451c1cee330"  # pragma: allowlist secret
        )

        response = client.post(
            "/api/livres-auteurs/set-validation-results",
            json={
                "episode_oid": episode_oid,
                "avis_critique_id": str(avis_critique_id),
                "books": [
                    {
                        "auteur": "Victoria Mas",
                        "titre": "L'orpheline du temple",
                        "editeur": "Albin Michel",
                        "programme": True,
                        "validation_status": "verified",
                        # Pas de suggested_author → utiliser l'original
                    }
                ],
            },
        )

        assert response.status_code == 200

        # Vérifier que l'auteur est créé avec le nom original (pas de correction)
        mock_mongodb_service.create_author_if_not_exists.assert_called_once_with(
            "Victoria Mas"
        )

    def test_verified_book_creates_livre_with_corrected_title(
        self, client, mock_mongodb_service
    ):
        """
        Test qu'un livre verified avec suggested_title crée le livre avec le titre corrigé.

        Scénario:
        - Livre extrait: "Amélie Nothomb / Tant mieu"
        - Babelio corrige: "Amélie Nothomb / Tant mieux"
        - Résultat attendu: Livre créé avec titre="Tant mieux" ✅
        """
        episode_oid = "6865f9a8a1418e3d7c63d081"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "686c494628b9e451c1cee330"  # pragma: allowlist secret
        )

        # Mock du create_author_if_not_exists pour retourner un ObjectId
        author_id = ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret
        mock_mongodb_service.create_author_if_not_exists.return_value = author_id

        response = client.post(
            "/api/livres-auteurs/set-validation-results",
            json={
                "episode_oid": episode_oid,
                "avis_critique_id": str(avis_critique_id),
                "books": [
                    {
                        "auteur": "Amélie Nothomb",
                        "titre": "Tant mieu",  # Titre ORIGINAL (faute)
                        "editeur": "Albin Michel",
                        "programme": False,
                        "validation_status": "verified",
                        "suggested_author": "Amélie Nothomb",
                        "suggested_title": "Tant mieux",  # Titre CORRIGÉ
                    }
                ],
            },
        )

        assert response.status_code == 200

        # Vérifier que create_book_if_not_exists a été appelé avec le titre corrigé
        call_args = mock_mongodb_service.create_book_if_not_exists.call_args
        assert call_args is not None
        book_data = call_args[0][0]  # Premier argument
        assert book_data["titre"] == "Tant mieux"  # ✅ Titre corrigé

    def test_manual_validation_uses_suggested_author_as_fallback(
        self, client, mock_mongodb_service
    ):
        """
        Test que handle_book_validation utilise suggested_author si user_validated_author est vide.

        Scénario edge case:
        - Un livre avec status='suggested' a suggested_author="Adrien Bosc"
        - L'utilisateur valide sans modifier les champs (user_validated_author vide/null)
        - Le système doit utiliser suggested_author comme fallback, PAS auteur original
        """
        # Mock du create_author_if_not_exists
        author_id = ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret
        mock_mongodb_service.create_author_if_not_exists.return_value = author_id

        # Simuler une validation manuelle sans user_validated (champs vides)
        response = client.post(
            "/api/livres-auteurs/validate-suggestion",
            json={
                "cache_id": "68d81f6d92d24efb2c41ab5d",
                "episode_oid": "6865f9a8a1418e3d7c63d081",
                "avis_critique_id": "686c494628b9e451c1cee330",
                "auteur": "Adrien Bosque",  # Original (incorrect)
                "titre": "L'invention de Tristan",
                "editeur": "Stock",
                "suggested_author": "Adrien Bosc",  # Correction de Babelio
                "suggested_title": "L'invention de Tristan",
                # user_validated_author et user_validated_title sont None/absents
            },
        )

        assert response.status_code == 200

        # Vérifier que suggested_author est utilisé comme fallback
        mock_mongodb_service.create_author_if_not_exists.assert_called_once_with(
            "Adrien Bosc"  # ✅ Doit utiliser suggested, PAS "Adrien Bosque"
        )
