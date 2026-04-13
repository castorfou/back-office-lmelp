"""Tests pour le scraping du titre complet depuis les pages Babelio.

Vérifie que fetch_full_title_from_url() extrait correctement le titre
sans pollution par le nom de l'auteur.

Issue découverte: og:title contient "Titre - Auteur - Babelio"
Solution: Prioriser h1 qui contient juste "Titre"
"""

from unittest.mock import AsyncMock, patch

import pytest

from back_office_lmelp.services.babelio_service import BabelioService


@pytest.fixture
def babelio_service():
    """Fixture pour créer une instance du service Babelio."""
    return BabelioService()


@pytest.mark.asyncio
async def test_fetch_full_title_should_return_clean_title_without_author_name(
    babelio_service,
):
    """Test RED: fetch_full_title_from_url doit retourner 'Romance' et non 'Romance - Anne Goscinny'."""
    # GIVEN: URL de la page Romance
    url = "https://www.babelio.com/livres/Goscinny-Romance/1416257"

    # GIVEN: HTML mock de la page Babelio avec og:title pollué et h1 propre
    html_content = """
    <html>
    <head>
        <meta property="og:title" content="Romance - Anne Goscinny - Babelio">
    </head>
    <body>
        <h1>Romance</h1>
    </body>
    </html>
    """

    # Mock _fetch_page (gateway unifié)
    with patch.object(
        babelio_service, "_fetch_page", new=AsyncMock(return_value=html_content)
    ):
        # WHEN: On scrape le titre
        result = await babelio_service.fetch_full_title_from_url(url)

        # THEN: Le titre doit être "Romance" (propre, depuis h1)
        # et NON "Romance - Anne Goscinny" (pollué, depuis og:title)
        assert result == "Romance", (
            f"Le titre doit être extrait proprement depuis h1, "
            f"sans le nom de l'auteur. Attendu: 'Romance', Reçu: '{result}'"
        )


@pytest.mark.asyncio
async def test_fetch_full_title_should_handle_og_title_fallback_when_h1_missing(
    babelio_service,
):
    """Test: Si h1 est absent, utiliser og:title avec nettoyage."""
    # GIVEN: URL quelconque
    url = "https://www.babelio.com/livres/Test/123"

    # GIVEN: HTML avec seulement og:title (pattern "Titre - Babelio" sans auteur)
    html_content = """
    <html>
    <head>
        <meta property="og:title" content="Titre Test - Babelio">
    </head>
    <body>
    </body>
    </html>
    """

    # Mock _fetch_page (gateway unifié)
    with patch.object(
        babelio_service, "_fetch_page", new=AsyncMock(return_value=html_content)
    ):
        # WHEN: On scrape le titre
        result = await babelio_service.fetch_full_title_from_url(url)

        # THEN: Le titre doit être nettoyé de " - Babelio"
        assert result == "Titre Test"
