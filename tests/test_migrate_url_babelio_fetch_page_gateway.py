"""Tests TDD (Issue #304, round 2) pour l'utilisation du gateway _fetch_page().

Bug racine réel observé : plusieurs fonctions de scraping de pages Babelio
dans migrate_url_babelio.py appelaient `babelio_service._get_session()` puis
`session.get(url)` directement, au lieu de passer par
`babelio_service._fetch_page(url)` (le gateway centralisé). Cette session
brute est créée avec des headers d'API AJAX (Content-Type: application/json,
X-Requested-With: XMLHttpRequest) et SANS le cookie jstsToken stocké côté
serveur — Babelio détectait et bloquait ces requêtes en 403, alors même que
la requête précédente sur la même page (verify_book()/
fetch_author_url_from_page(), qui passent par _fetch_page) avait réussi avec
les bons headers de page + le cookie.
"""

from unittest.mock import AsyncMock, patch

import pytest

from scripts.migration_donnees.migrate_url_babelio import scrape_title_from_page


class TestScrapeTitleFromPageUsesFetchPage:
    """Tests pour scrape_title_from_page() — doit utiliser _fetch_page()."""

    @pytest.mark.asyncio
    async def test_should_call_fetch_page_not_raw_session_get(self):
        """scrape_title_from_page() doit appeler babelio_service._fetch_page(url),
        pas un appel brut session.get(url) sans cookie ni bons headers.
        """
        mock_babelio = AsyncMock()
        mock_babelio._fetch_page = AsyncMock(
            return_value="<html><h1>Le Petit Prince</h1></html>"
        )

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
        ) as mock_wait:
            mock_wait.side_effect = lambda: None

            result = await scrape_title_from_page(
                mock_babelio, "https://www.babelio.com/livres/Saint-Exupery/1234"
            )

        mock_babelio._fetch_page.assert_called_once_with(
            "https://www.babelio.com/livres/Saint-Exupery/1234"
        )
        assert result == "Le Petit Prince"

    @pytest.mark.asyncio
    async def test_should_return_none_when_fetch_page_returns_none(self):
        """Si _fetch_page() retourne None (échec HTTP non-403), le titre
        scrapé doit aussi être None — comportement inchangé pour l'appelant.
        """
        mock_babelio = AsyncMock()
        mock_babelio._fetch_page = AsyncMock(return_value=None)

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
        ) as mock_wait:
            mock_wait.side_effect = lambda: None

            result = await scrape_title_from_page(
                mock_babelio, "https://www.babelio.com/livres/Inconnu/9999"
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_should_return_none_when_fetch_page_raises_blocked_403(self):
        """Un blocage 403 pendant le scraping du titre ne doit pas laisser
        fuiter l'exception à l'appelant — retourner None comme pour tout
        autre échec (le statut blocked_403 global est déjà géré par l'appel
        à _fetch_page() de l'ÉTAPE 1 juste avant, dans migrate_one_book_and_author).
        """
        from back_office_lmelp.services.babelio_service import BabelioBlockedError

        mock_babelio = AsyncMock()
        mock_babelio._fetch_page = AsyncMock(side_effect=BabelioBlockedError("403"))

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
        ) as mock_wait:
            mock_wait.side_effect = lambda: None

            result = await scrape_title_from_page(
                mock_babelio, "https://www.babelio.com/livres/Bloque/1111"
            )

        assert result is None
