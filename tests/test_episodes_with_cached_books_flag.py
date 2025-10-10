"""
Tests pour vérifier le flag has_cached_books dans /api/episodes-with-reviews.

Ce flag indique si un épisode a déjà été affiché (présence dans livresauteurs_cache).
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from bson import ObjectId


@pytest.mark.asyncio
class TestEpisodesWithCachedBooksFlag:
    """Tests du flag has_cached_books pour indiquer les épisodes déjà affichés."""

    async def test_should_set_has_cached_books_true_when_cache_exists(self):
        """Le flag has_cached_books doit être true si l'épisode a des livres en cache."""
        from httpx import ASGITransport, AsyncClient

        from back_office_lmelp.app import app

        episode_oid = "507f1f77bcf86cd799439020"  # pragma: allowlist secret

        # Simuler des données existantes
        mock_avis_critiques = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439021"),  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "summary": "Test avis critique",
            }
        ]

        mock_episode = {
            "_id": episode_oid,  # String ID pour sérialisation
            "date": datetime(2025, 1, 12),
            "titre": "Les nouvelles pages du polar",
            "titre_corrige": None,
        }

        # Simuler des livres en cache pour cet épisode
        mock_cached_books = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439022"),  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "auteur": "Guillaume Lebrun",
                "titre": "Ravagés de splendeur",
            }
        ]

        with (
            patch(
                "back_office_lmelp.app.memory_guard.check_memory_limit",
                return_value=None,
            ),
            patch(
                "back_office_lmelp.app.mongodb_service.get_all_critical_reviews",
                return_value=mock_avis_critiques,
            ),
            patch(
                "back_office_lmelp.app.mongodb_service.get_episode_by_id",
                return_value=mock_episode,
            ),
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service.get_books_by_episode_oid",
                return_value=mock_cached_books,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/episodes-with-reviews")

        assert response.status_code == 200
        episodes = response.json()
        assert len(episodes) == 1

        # Vérifier que has_cached_books est présent et à true
        episode = episodes[0]
        assert "has_cached_books" in episode
        assert episode["has_cached_books"] is True

    async def test_should_set_has_cached_books_false_when_no_cache(self):
        """Le flag has_cached_books doit être false si l'épisode n'a pas de livres en cache."""
        from httpx import ASGITransport, AsyncClient

        from back_office_lmelp.app import app

        episode_oid = "507f1f77bcf86cd799439023"  # pragma: allowlist secret

        mock_avis_critiques = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439024"),  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "summary": "Test avis critique",
            }
        ]

        mock_episode = {
            "_id": episode_oid,  # String ID pour sérialisation
            "date": datetime(2025, 1, 5),
            "titre": "Littérature contemporaine",
            "titre_corrige": None,
        }

        # Simuler aucun livre en cache pour cet épisode
        with (
            patch(
                "back_office_lmelp.app.memory_guard.check_memory_limit",
                return_value=None,
            ),
            patch(
                "back_office_lmelp.app.mongodb_service.get_all_critical_reviews",
                return_value=mock_avis_critiques,
            ),
            patch(
                "back_office_lmelp.app.mongodb_service.get_episode_by_id",
                return_value=mock_episode,
            ),
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service.get_books_by_episode_oid",
                return_value=[],  # Cache vide
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/episodes-with-reviews")

        assert response.status_code == 200
        episodes = response.json()
        assert len(episodes) == 1

        # Vérifier que has_cached_books est présent et à false
        episode = episodes[0]
        assert "has_cached_books" in episode
        assert episode["has_cached_books"] is False

    async def test_should_handle_multiple_episodes_with_mixed_cache_status(self):
        """Doit gérer correctement plusieurs épisodes avec statuts cache différents."""
        from httpx import ASGITransport, AsyncClient

        from back_office_lmelp.app import app

        episode_oid_1 = "507f1f77bcf86cd799439025"  # pragma: allowlist secret
        episode_oid_2 = "507f1f77bcf86cd799439026"  # pragma: allowlist secret

        mock_avis_critiques = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439027"),  # pragma: allowlist secret
                "episode_oid": episode_oid_1,
                "summary": "Avis 1",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439028"),  # pragma: allowlist secret
                "episode_oid": episode_oid_2,
                "summary": "Avis 2",
            },
        ]

        mock_episodes = {
            episode_oid_1: {
                "_id": episode_oid_1,  # String ID pour sérialisation
                "date": datetime(2025, 1, 12),
                "titre": "Avec cache",
                "titre_corrige": None,
            },
            episode_oid_2: {
                "_id": episode_oid_2,  # String ID pour sérialisation
                "date": datetime(2025, 1, 5),
                "titre": "Sans cache",
                "titre_corrige": None,
            },
        }

        # Mock pour get_books_by_episode_oid qui retourne différents résultats selon episode_oid
        def mock_get_cached_books(episode_oid):
            if episode_oid == episode_oid_1:
                return [{"auteur": "Test", "titre": "Livre"}]  # A du cache
            return []  # Pas de cache

        with (
            patch(
                "back_office_lmelp.app.memory_guard.check_memory_limit",
                return_value=None,
            ),
            patch(
                "back_office_lmelp.app.mongodb_service.get_all_critical_reviews",
                return_value=mock_avis_critiques,
            ),
            patch(
                "back_office_lmelp.app.mongodb_service.get_episode_by_id",
                side_effect=lambda oid: mock_episodes.get(oid),
            ),
            patch(
                "back_office_lmelp.app.livres_auteurs_cache_service.get_books_by_episode_oid",
                side_effect=mock_get_cached_books,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/episodes-with-reviews")

        assert response.status_code == 200
        episodes = response.json()
        assert len(episodes) == 2

        # Vérifier que les flags sont corrects pour chaque épisode
        # Note: les épisodes sont triés par date décroissante
        episode_avec_cache = next(e for e in episodes if e["titre"] == "Avec cache")
        episode_sans_cache = next(e for e in episodes if e["titre"] == "Sans cache")

        assert episode_avec_cache["has_cached_books"] is True
        assert episode_sans_cache["has_cached_books"] is False
