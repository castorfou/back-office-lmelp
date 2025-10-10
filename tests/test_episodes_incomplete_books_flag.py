"""Tests TDD pour le flag has_incomplete_books dans l'API episodes.

Objectif: Identifier visuellement les épisodes avec livres non validés (status != mongo).
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from back_office_lmelp.app import app


@pytest.mark.asyncio
class TestEpisodesIncompleteBooks:
    """Tests pour le flag has_incomplete_books."""

    async def test_should_set_has_incomplete_books_true_when_non_mongo_books_exist(
        self,
    ):
        """Le flag has_incomplete_books doit être true si au moins un livre n'est pas au status mongo."""
        episode_oid = "507f1f77bcf86cd799439020"  # pragma: allowlist secret

        mock_avis_critiques = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439029"),  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "summary": "Test avis critique",
            }
        ]

        mock_episode = {
            "_id": episode_oid,
            "date": datetime(2025, 1, 12),
            "titre": "Les nouvelles pages du polar",
            "titre_corrige": None,
        }

        # Cas: 2 livres mongo, 1 livre suggested (incomplet)
        mock_cached_books = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439021"),
                "episode_oid": episode_oid,
                "auteur": "Albert Camus",
                "titre": "L'Étranger",
                "status": "mongo",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439022"),
                "episode_oid": episode_oid,
                "auteur": "Simone de Beauvoir",
                "titre": "Le Deuxième Sexe",
                "status": "mongo",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439023"),
                "episode_oid": episode_oid,
                "auteur": "Jean-Paul Sartre",
                "titre": "La Nausée",
                "status": "suggested",  # Livre non validé
            },
        ]

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
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
                response = await client.get("/api/episodes-with-reviews")

        assert response.status_code == 200
        episodes = response.json()
        assert len(episodes) > 0

        episode = episodes[0]
        assert episode["has_incomplete_books"] is True

    async def test_should_set_has_incomplete_books_false_when_all_books_mongo(self):
        """Le flag has_incomplete_books doit être false si tous les livres sont au status mongo."""
        episode_oid = "507f1f77bcf86cd799439024"  # pragma: allowlist secret

        mock_avis_critiques = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439030"),  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "summary": "Test avis critique",
            }
        ]

        mock_episode = {
            "_id": episode_oid,
            "date": datetime(2025, 1, 15),
            "titre": "Spécial rentrée littéraire",
            "titre_corrige": None,
        }

        # Cas: Tous les livres sont validés (status mongo)
        mock_cached_books = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439025"),
                "episode_oid": episode_oid,
                "auteur": "Amélie Nothomb",
                "titre": "Stupeur et tremblements",
                "status": "mongo",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439026"),
                "episode_oid": episode_oid,
                "auteur": "Michel Houellebecq",
                "titre": "Les Particules élémentaires",
                "status": "mongo",
            },
        ]

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
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
                response = await client.get("/api/episodes-with-reviews")

        assert response.status_code == 200
        episodes = response.json()
        assert len(episodes) > 0

        episode = episodes[0]
        assert episode["has_incomplete_books"] is False

    async def test_should_set_has_incomplete_books_false_when_no_cached_books(self):
        """Le flag has_incomplete_books doit être false si aucun livre en cache."""
        episode_oid = "507f1f77bcf86cd799439027"  # pragma: allowlist secret

        mock_avis_critiques = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439031"),  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "summary": "Test avis critique",
            }
        ]

        mock_episode = {
            "_id": episode_oid,
            "date": datetime(2025, 1, 18),
            "titre": "Littérature contemporaine",
            "titre_corrige": None,
        }

        # Cas: Aucun livre en cache
        mock_cached_books = []

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
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
                response = await client.get("/api/episodes-with-reviews")

        assert response.status_code == 200
        episodes = response.json()
        assert len(episodes) > 0

        episode = episodes[0]
        assert episode["has_incomplete_books"] is False

    async def test_should_handle_mixed_statuses_correctly(self):
        """Test avec différents statuts: not_found, suggested, verified, mongo."""
        episode_oid = "507f1f77bcf86cd799439028"  # pragma: allowlist secret

        mock_avis_critiques = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439032"),  # pragma: allowlist secret
                "episode_oid": episode_oid,
                "summary": "Test avis critique",
            }
        ]

        mock_episode = {
            "_id": episode_oid,
            "date": datetime(2025, 1, 20),
            "titre": "Polar et thriller",
            "titre_corrige": None,
        }

        # Mélange de tous les statuts possibles
        mock_cached_books = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439029"),
                "episode_oid": episode_oid,
                "status": "not_found",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439030"),
                "episode_oid": episode_oid,
                "status": "suggested",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439031"),
                "episode_oid": episode_oid,
                "status": "verified",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439032"),
                "episode_oid": episode_oid,
                "status": "mongo",
            },
        ]

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
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
                response = await client.get("/api/episodes-with-reviews")

        assert response.status_code == 200
        episodes = response.json()
        assert len(episodes) > 0

        episode = episodes[0]
        # Au moins un livre n'est pas "mongo" → has_incomplete_books = True
        assert episode["has_incomplete_books"] is True
