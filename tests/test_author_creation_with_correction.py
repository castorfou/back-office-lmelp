"""
Tests pour la création d'auteurs avec correction de nom (suggested_author).

Bug identifié: Quand un livre est validé avec une correction d'auteur
(ex: "Adrien Bosque" → "Adrien Bosc"), l'auteur est créé en base avec
le nom ORIGINAL ("Adrien Bosque") au lieu du nom CORRIGÉ ("Adrien Bosc").
"""

from unittest.mock import patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestAuthorCreationWithCorrection:
    """Tests de création d'auteurs avec correction de nom."""

    def test_verified_book_creates_author_with_corrected_name(self):
        """
        Test qu'un livre verified avec suggested_author crée l'auteur avec le nom corrigé.

        Scénario:
        - Livre extrait: "Adrien Bosque / L'invention de Tristan"
        - Babelio corrige: "Adrien Bosc / L'invention de Tristan"
        - Validation: status=verified, suggested_author="Adrien Bosc"
        - Résultat attendu: Auteur créé avec nom="Adrien Bosc" ✅ (PAS "Adrien Bosque" ❌)
        """
        client = TestClient(app)
        episode_oid = "6865f9a8a1418e3d7c63d081"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "686c494628b9e451c1cee330"  # pragma: allowlist secret
        )

        with (
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb_service,
        ):
            # Mock: cache service
            cache_id = ObjectId("68d3eb092f32bb8c43063f91")  # pragma: allowlist secret
            mock_cache_service.create_cache_entry.return_value = cache_id

            # Mock: mongodb service
            author_id = ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret
            book_id = ObjectId("507f1f77bcf86cd799439012")  # pragma: allowlist secret
            mock_mongodb_service.create_author_if_not_exists.return_value = author_id
            mock_mongodb_service.create_book_if_not_exists.return_value = book_id

            # Simuler une réponse de validation avec correction d'auteur
            response = client.post(
                "/api/set-validation-results",
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

    def test_verified_book_without_correction_uses_original_name(self):
        """
        Test qu'un livre verified SANS correction utilise le nom original.

        Scénario:
        - Livre extrait: "Victoria Mas / L'orpheline du temple"
        - Babelio valide: status=verified, confidence=1.0, pas de correction
        - Résultat attendu: Auteur créé avec nom="Victoria Mas"
        """
        client = TestClient(app)
        episode_oid = "6865f9a8a1418e3d7c63d081"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "686c494628b9e451c1cee330"  # pragma: allowlist secret
        )

        with (
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb_service,
        ):
            # Mock: cache service
            cache_id = ObjectId("68d3eb092f32bb8c43063f91")  # pragma: allowlist secret
            mock_cache_service.create_cache_entry.return_value = cache_id

            # Mock: mongodb service
            author_id = ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret
            book_id = ObjectId("507f1f77bcf86cd799439012")  # pragma: allowlist secret
            mock_mongodb_service.create_author_if_not_exists.return_value = author_id
            mock_mongodb_service.create_book_if_not_exists.return_value = book_id

            response = client.post(
                "/api/set-validation-results",
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

    def test_verified_book_creates_livre_with_corrected_title(self):
        """
        Test qu'un livre verified avec suggested_title crée le livre avec le titre corrigé.

        Scénario:
        - Livre extrait: "Amélie Nothomb / Tant mieu"
        - Babelio corrige: "Amélie Nothomb / Tant mieux"
        - Résultat attendu: Livre créé avec titre="Tant mieux" ✅
        """
        client = TestClient(app)
        episode_oid = "6865f9a8a1418e3d7c63d081"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "686c494628b9e451c1cee330"  # pragma: allowlist secret
        )

        with (
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service"
            ) as mock_cache_service,
            patch("back_office_lmelp.app.mongodb_service") as mock_mongodb_service,
        ):
            # Mock: cache service
            cache_id = ObjectId("68d3eb092f32bb8c43063f91")  # pragma: allowlist secret
            mock_cache_service.create_cache_entry.return_value = cache_id

            # Mock: mongodb service
            author_id = ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret
            book_id = ObjectId("507f1f77bcf86cd799439012")  # pragma: allowlist secret
            mock_mongodb_service.create_author_if_not_exists.return_value = author_id
            mock_mongodb_service.create_book_if_not_exists.return_value = book_id

            response = client.post(
                "/api/set-validation-results",
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
