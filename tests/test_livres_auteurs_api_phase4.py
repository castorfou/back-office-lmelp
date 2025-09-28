"""Tests TDD pour l'API cache-first /livres-auteurs (Issue #66 - Phase 4)."""

from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


client = TestClient(app)


class TestLivresAuteursApiPhase4:
    """Tests pour l'API cache-first /livres-auteurs."""

    def test_api_livres_auteurs_cache_hit_returns_cached_data(self):
        """Test TDD: API utilise le cache quand les données sont disponibles."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        # Mock des données en cache pour cet épisode (système simplifié)
        cached_books = [
            {
                "_id": "68d3eb092f32bb8c43063f89",  # pragma: allowlist secret
                "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "auteur": "Maria Pourchet",
                "titre": "Tressaillir",
                "editeur": "Stock",
                "programme": True,
                "status": "verified",  # Système simplifié : un seul champ status
                "created_at": "2024-09-14T10:00:00Z",
            },
            {
                "_id": "68d3eb092f32bb8c43063f90",  # pragma: allowlist secret
                "avis_critique_id": "68c718a16e51b9428ab88066",  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "auteur": "Emmanuel Carrère",
                "titre": "Kolkhoze",
                "editeur": "POL",
                "programme": False,
                "status": "suggested",  # Système simplifié : un seul champ status
                "suggested_author": "Emmanuel Carrère",  # Ajouté seulement si fourni (NoSQL)
                "suggested_title": "Kolkhoze",  # Ajouté seulement si fourni (NoSQL)
                "created_at": "2024-09-14T10:00:00Z",
            },
        ]

        with patch(
            "back_office_lmelp.app.livres_auteurs_cache_service"
        ) as mock_cache_service:
            # Mock: le cache contient des données pour cet épisode
            mock_cache_service.get_books_by_episode_oid.return_value = cached_books

            # Mock: récupération de l'avis critique par episode_oid
            with patch("back_office_lmelp.app.mongodb_service") as mock_mongodb:
                mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                    {
                        "_id": avis_critique_id,
                        "episode_oid": episode_oid,
                        "summary": "test",
                    }
                ]

                # Mock du service de formatage
                with patch(
                    "back_office_lmelp.app.books_extraction_service"
                ) as mock_extraction:
                    # Mock: formatage retourne les données du cache telles quelles
                    mock_extraction.format_books_for_simplified_display.return_value = (
                        cached_books
                    )

                    # Act
                    response = client.get(
                        f"/api/livres-auteurs?episode_oid={episode_oid}"
                    )

                    # Assert
                    assert response.status_code == 200
                    books = response.json()

                    assert len(books) == 2
                    assert books[0]["auteur"] == "Maria Pourchet"
                    assert books[0]["titre"] == "Tressaillir"
                    assert books[0]["status"] == "verified"  # Nouveau système simplifié
                    assert books[1]["auteur"] == "Emmanuel Carrère"
                    assert (
                        books[1]["status"] == "suggested"
                    )  # Nouveau système simplifié
                    assert books[1]["suggested_author"] == "Emmanuel Carrère"

                    # Vérifier que le cache a été consulté
                    mock_cache_service.get_books_by_episode_oid.assert_called_once_with(
                        episode_oid
                    )

                    # Vérifier que l'extraction N'A PAS été appelée (cache hit)
                    mock_extraction.extract_books_from_reviews.assert_not_called()

                    # Vérifier que le formatage a été appelé avec les données du cache
                    mock_extraction.format_books_for_simplified_display.assert_called_once_with(
                        cached_books
                    )

    # TEST REMOVED: test_api_livres_auteurs_cache_miss_triggers_extraction
    # Reason: API no longer creates cache entries or calls Babelio - workflow moved to frontend
    def _test_api_livres_auteurs_cache_miss_triggers_extraction_OBSOLETE(self):
        """Test TDD: API fait l'extraction quand le cache est vide."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        # Mock des livres extraits (avant vérification Babelio - système simplifié)
        extracted_books = [
            {
                "episode_oid": episode_oid,
                "auteur": "Nouveau Auteur",
                "titre": "Nouveau Livre",
                "editeur": "Nouveau Editeur",
                "programme": True,
                # Note: status sera ajouté par l'endpoint après vérification Babelio
            }
        ]

        with patch(
            "back_office_lmelp.app.livres_auteurs_cache_service"
        ) as mock_cache_service:
            # Mock: le cache est vide pour cet avis critique
            mock_cache_service.get_books_by_episode_oid.return_value = []

            with patch("back_office_lmelp.app.mongodb_service") as mock_mongodb:
                # Mock: récupération de l'avis critique
                mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                    {
                        "_id": avis_critique_id,
                        "episode_oid": episode_oid,
                        "summary": "test",
                    }
                ]

                # Mock: service d'extraction
                with patch(
                    "back_office_lmelp.app.books_extraction_service"
                ) as mock_extraction:
                    mock_extraction.extract_books_from_reviews = AsyncMock(
                        return_value=extracted_books
                    )
                    # Mock du formatage avec ajout du statut (comme le fait vraiment l'endpoint)
                    formatted_books = extracted_books.copy()
                    formatted_books[0]["status"] = (
                        "verified"  # Ajouté par l'endpoint après vérification
                    )
                    mock_extraction.format_books_for_simplified_display.return_value = (
                        formatted_books
                    )

                    # Mock: services Babelio pour vérification
                    with patch("back_office_lmelp.app.babelio_service") as mock_babelio:
                        mock_babelio.verify_author = AsyncMock(
                            return_value={"status": "verified"}
                        )
                        mock_babelio.verify_book = AsyncMock(
                            return_value={"status": "verified"}
                        )

                        # Mock: sauvegarde dans le cache après extraction
                        mock_cache_service.create_cache_entry.return_value = ObjectId(
                            "68d3eb092f32bb8c43063f91"  # pragma: allowlist secret
                        )  # pragma: allowlist secret

                        # Act
                        response = client.get(
                            f"/api/livres-auteurs?episode_oid={episode_oid}"
                        )

                        # Assert
                        assert response.status_code == 200
                        books = response.json()

                        assert len(books) == 1
                        assert books[0]["auteur"] == "Nouveau Auteur"
                        assert books[0]["titre"] == "Nouveau Livre"
                        assert (
                            books[0]["status"] == "verified"
                        )  # Nouveau système simplifié

                        # Vérifier que le cache était consulté en premier
                        mock_cache_service.get_books_by_episode_oid.assert_called_once_with(
                            episode_oid
                        )

                        # Vérifier que l'extraction a été déclenchée (cache miss)
                        mock_extraction.extract_books_from_reviews.assert_called_once()

                        # Vérifier que les résultats ont été sauvés dans le cache
                        # Note: le statut unifié "status" est maintenant ajouté par l'endpoint (système simplifié)
                        expected_book_data = extracted_books[0].copy()
                        expected_book_data["status"] = (
                            "verified"  # Nouveau système unifié
                        )
                        mock_cache_service.create_cache_entry.assert_called_once_with(
                            avis_critique_id, expected_book_data
                        )

    # TEST REMOVED: test_api_livres_auteurs_auto_processing_after_extraction
    # Reason: API no longer does auto-processing - workflow moved to frontend
    def _test_api_livres_auteurs_auto_processing_after_extraction_OBSOLETE(self):
        """Test TDD: API déclenche l'auto-processing des livres verified après extraction."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_id = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        # Mock d'un livre verified extrait
        extracted_verified_book = {
            "episode_oid": episode_oid,
            "auteur": "Auteur Verified",
            "titre": "Livre Verified",
            "editeur": "Editeur Test",
            "programme": True,
            # Note: status sera ajouté par l'endpoint après vérification Babelio
        }

        with patch(
            "back_office_lmelp.app.livres_auteurs_cache_service"
        ) as mock_cache_service:
            # Cache miss initial
            mock_cache_service.get_books_by_episode_oid.return_value = []

            with patch("back_office_lmelp.app.mongodb_service") as mock_mongodb:
                mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                    {"_id": avis_critique_id, "episode_oid": episode_oid}
                ]

                with patch(
                    "back_office_lmelp.app.books_extraction_service"
                ) as mock_extraction:
                    mock_extraction.extract_books_from_reviews = AsyncMock(
                        return_value=[extracted_verified_book]
                    )
                    mock_extraction.format_books_for_simplified_display.return_value = [
                        extracted_verified_book
                    ]

                    # Mock: services Babelio pour vérification
                    with patch("back_office_lmelp.app.babelio_service") as mock_babelio:
                        mock_babelio.verify_author = AsyncMock(
                            return_value={"status": "verified"}
                        )
                        mock_babelio.verify_book = AsyncMock(
                            return_value={"status": "verified"}
                        )

                        # Mock: création de cache entry
                        cache_entry_id = ObjectId(
                            "68d3eb092f32bb8c43063f91"  # pragma: allowlist secret
                        )  # pragma: allowlist secret
                        mock_cache_service.create_cache_entry.return_value = (
                            cache_entry_id
                        )

                        # Mock: auto-processing des verified (via mongodb_service)
                        mock_mongodb.create_author_if_not_exists.return_value = (
                            ObjectId(
                                "67a79b615b03b52d8c51db29"  # pragma: allowlist secret
                            )
                        )  # pragma: allowlist secret
                        mock_mongodb.create_book_if_not_exists.return_value = ObjectId(
                            "68d3eb092f32bb8c43063f76"  # pragma: allowlist secret
                        )

                        # Act
                        response = client.get(
                            f"/api/livres-auteurs?episode_oid={episode_oid}"
                        )

                        # Assert
                        assert response.status_code == 200

                        # Vérifier que le cache a été créé
                        mock_cache_service.create_cache_entry.assert_called_once()

                        # Vérifier que l'auto-processing a été déclenché pour les verified
                        mock_mongodb.create_author_if_not_exists.assert_called_once_with(
                            "Auteur Verified"
                        )
                        mock_mongodb.create_book_if_not_exists.assert_called_once()

                        # Vérifier que le cache entry a été marqué comme traité
                        mock_cache_service.mark_as_processed.assert_called_once_with(
                            cache_entry_id,
                            ObjectId(
                                "67a79b615b03b52d8c51db29"  # pragma: allowlist secret
                            ),
                            ObjectId(
                                "68d3eb092f32bb8c43063f76"  # pragma: allowlist secret
                            ),
                        )

    def test_api_livres_auteurs_handles_multiple_avis_critiques(self):
        """Test TDD: API gère plusieurs avis critiques avec cache partiel."""
        # Cas où certains avis critiques sont en cache, d'autres non
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret
        avis_critique_1 = ObjectId(
            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
        )  # pragma: allowlist secret
        avis_critique_2 = ObjectId(
            "68c718a16e51b9428ab88067"  # pragma: allowlist secret
        )  # pragma: allowlist secret

        # Mock: cache global contient les données pour cet épisode
        cached_books = [
            {"auteur": "Auteur Cached", "titre": "Livre Cached"},
            {"auteur": "Auteur Cached 2", "titre": "Livre Cached 2"},
        ]

        with patch(
            "back_office_lmelp.app.livres_auteurs_cache_service"
        ) as mock_cache_service:
            mock_cache_service.get_books_by_episode_oid.return_value = cached_books

            with patch("back_office_lmelp.app.mongodb_service") as mock_mongodb:
                # Mock: plusieurs avis critiques pour l'épisode
                mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                    {"_id": avis_critique_1, "episode_oid": episode_oid},
                    {"_id": avis_critique_2, "episode_oid": episode_oid},
                ]

                with patch(
                    "back_office_lmelp.app.books_extraction_service"
                ) as mock_extraction:
                    # Mock: formatage des données cachées
                    mock_extraction.format_books_for_simplified_display.return_value = (
                        cached_books
                    )

                    # Act
                    response = client.get(
                        f"/api/livres-auteurs?episode_oid={episode_oid}"
                    )

                    # Assert
                    assert response.status_code == 200
                    books = response.json()

                    assert len(books) == 2
                    # Vérifier que les données du cache sont retournées
                    authors = [book["auteur"] for book in books]
                    assert "Auteur Cached" in authors
                    assert "Auteur Cached 2" in authors

                    # Vérifier que le cache a été consulté une fois pour l'épisode
                    mock_cache_service.get_books_by_episode_oid.assert_called_once_with(
                        episode_oid
                    )

                    # Vérifier que l'extraction N'A PAS été appelée (cache hit global)
                    mock_extraction.extract_books_from_reviews.assert_not_called()

    # TEST REMOVED: test_api_livres_auteurs_error_handling_cache_fallback
    # Reason: API no longer has complex cache/extraction fallback with Babelio calls
    def _test_api_livres_auteurs_error_handling_cache_fallback_OBSOLETE(self):
        """Test TDD: API utilise le fallback extraction si le cache échoue."""
        episode_oid = "68c707ad6e51b9428ab87e9e"  # pragma: allowlist secret

        with patch(
            "back_office_lmelp.app.livres_auteurs_cache_service"
        ) as mock_cache_service:
            # Mock: erreur dans le cache service
            mock_cache_service.get_books_by_episode_oid.side_effect = Exception(
                "Cache error"
            )

            with patch("back_office_lmelp.app.mongodb_service") as mock_mongodb:
                mock_mongodb.get_critical_reviews_by_episode_oid.return_value = [
                    {
                        "_id": ObjectId(
                            "68c718a16e51b9428ab88066"  # pragma: allowlist secret
                        ),
                        "episode_oid": episode_oid,
                    }
                ]

                with patch(
                    "back_office_lmelp.app.books_extraction_service"
                ) as mock_extraction:
                    # Mock: extraction fonctionne normalement en fallback
                    mock_extraction.extract_books_from_reviews = AsyncMock(
                        return_value=[
                            {"auteur": "Auteur Fallback", "titre": "Livre Fallback"}
                        ]
                    )
                    mock_extraction.format_books_for_simplified_display.return_value = [
                        {"auteur": "Auteur Fallback", "titre": "Livre Fallback"}
                    ]

                    # Act
                    response = client.get(
                        f"/api/livres-auteurs?episode_oid={episode_oid}"
                    )

                    # Assert
                    assert response.status_code == 200
                    books = response.json()

                    assert len(books) == 1
                    assert books[0]["auteur"] == "Auteur Fallback"

                    # Vérifier que l'extraction a été utilisée comme fallback
                    mock_extraction.extract_books_from_reviews.assert_called_once()
