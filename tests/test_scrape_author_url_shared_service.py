"""Tests TDD (Issue #304, round 2) pour l'utilisation du singleton babelio_service
partagé dans scrape_author_url_from_book_page() / process_one_author().

Double bug racine réel observé :
1. scrape_author_url_from_book_page() créait sa PROPRE instance
   `BabelioService()` locale au lieu de recevoir le singleton partagé
   (`babelio_service` de babelio_service.py) déjà utilisé par les endpoints
   /api/babelio/status et /api/babelio/cookie — bug d'isolation similaire à
   celui déjà corrigé dans migration_runner.py (Phase 1). Une instance
   isolée ne partage ni le cookie stocké, ni l'état du circuit breaker.
2. Cette fonction appelait `session.get(book_url)` brut via
   `babelio_service._get_session()` au lieu du gateway centralisé
   `_fetch_page()` — même bug de headers/cookie manquants que pour les
   sites de vérification d'URL livre/auteur.
"""

from unittest.mock import AsyncMock, patch

import pytest

from scripts.migration_donnees.migrate_url_babelio import (
    process_one_author,
    scrape_author_url_from_book_page,
)


class TestScrapeAuthorUrlFromBookPageUsesSharedService:
    """scrape_author_url_from_book_page() doit recevoir le babelio_service
    partagé en paramètre et l'utiliser via _fetch_page(), sans jamais créer
    sa propre instance BabelioService()."""

    @pytest.mark.asyncio
    async def test_should_call_fetch_page_on_provided_service_not_new_instance(self):
        mock_babelio = AsyncMock()
        mock_babelio._fetch_page = AsyncMock(
            return_value=(
                '<html><a href="/auteur/George-Orwell/5678">George Orwell</a></html>'
            )
        )

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.BabelioService"
            ) as mock_babelio_class,
        ):
            mock_wait.side_effect = lambda: None

            result = await scrape_author_url_from_book_page(
                mock_babelio, "https://www.babelio.com/livres/Orwell-1984/1234"
            )

            # Ne doit JAMAIS créer sa propre instance — utiliser celle fournie
            mock_babelio_class.assert_not_called()

        mock_babelio._fetch_page.assert_called_once_with(
            "https://www.babelio.com/livres/Orwell-1984/1234"
        )
        assert result == "https://www.babelio.com/auteur/George-Orwell/5678"

    @pytest.mark.asyncio
    async def test_should_return_none_when_fetch_page_returns_none(self):
        mock_babelio = AsyncMock()
        mock_babelio._fetch_page = AsyncMock(return_value=None)

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
        ) as mock_wait:
            mock_wait.side_effect = lambda: None

            result = await scrape_author_url_from_book_page(
                mock_babelio, "https://www.babelio.com/livres/Inconnu/9999"
            )

        assert result is None


class TestProcessOneAuthorPassesSharedService:
    """process_one_author() doit propager le babelio_service partagé qu'il
    reçoit à scrape_author_url_from_book_page(), sans jamais en créer un
    nouveau lui-même."""

    @pytest.mark.asyncio
    async def test_should_forward_shared_service_to_scrape_author_url(self):
        from unittest.mock import MagicMock

        from bson import ObjectId

        auteur_id = ObjectId()
        livre_id = ObjectId()
        shared_babelio_service = AsyncMock()

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service"
            ) as mock_mongodb,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_author_url_from_book_page"
            ) as mock_scrape,
        ):
            mock_auteurs = MagicMock()
            mock_problematic = MagicMock()
            collections = {
                "auteurs": mock_auteurs,
                "babelio_problematic_cases": mock_problematic,
            }
            mock_mongodb.get_collection.side_effect = lambda name: collections.get(
                name, MagicMock()
            )
            mock_auteurs.update_one.return_value = MagicMock(matched_count=1)

            async def mock_scrape_async(*args, **kwargs):
                return "https://www.babelio.com/auteur/George-Orwell/5678"

            mock_scrape.side_effect = mock_scrape_async

            await process_one_author(
                author_data={
                    "auteur_id": auteur_id,
                    "nom": "George Orwell",
                    "livres": [
                        {
                            "livre_id": livre_id,
                            "titre": "1984",
                            "url_babelio": "https://www.babelio.com/livres/Orwell-1984/1234",
                        }
                    ],
                },
                babelio_service=shared_babelio_service,
            )

            mock_scrape.assert_called_once_with(
                shared_babelio_service,
                "https://www.babelio.com/livres/Orwell-1984/1234",
            )
