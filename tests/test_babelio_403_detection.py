"""Tests TDD pour la détection explicite des 403 Babelio (Issue #251).

Problème identifié :
- Quand Babelio renvoie 403 (anti-bot, cookie manquant/expiré), search() et
  _fetch_page() loggaient un warning puis retournaient []/None — indistinguable
  d'un "vraiment pas trouvé sur Babelio". L'utilisateur n'avait aucun signal
  qu'il devait rafraîchir son cookie jstsToken.

Solution :
- Nouvelle exception BabelioBlockedError levée sur HTTP 403.
- verify_author()/verify_book() la capturent et renvoient status='blocked_403'
  au lieu de 'not_found', pour que le frontend puisse afficher une alerte
  distincte de "livre non trouvé sur Babelio".
"""

from unittest.mock import AsyncMock, patch

import pytest

import back_office_lmelp.services.babelio_service as babelio_module
from back_office_lmelp.services.babelio_service import (
    BabelioBlockedError,
    BabelioService,
)


@pytest.fixture
def service():
    return BabelioService()


# ============================================================
# 1. search() doit lever BabelioBlockedError sur 403
# ============================================================


def _send_returning(status: int) -> AsyncMock:
    """Simule le point de sortie HTTP unique de BabelioService."""
    return AsyncMock(
        return_value=babelio_module.BabelioResponse(status=status, body=b"")
    )


@pytest.mark.asyncio
async def test_search_raises_blocked_error_on_403(service):
    """search() doit lever BabelioBlockedError si Babelio renvoie 403."""
    with (
        patch.object(service, "_send", new=_send_returning(403)),
        pytest.raises(BabelioBlockedError),
    ):
        await service.search("Boualem Sansal")


@pytest.mark.asyncio
async def test_search_still_returns_empty_for_non_403_errors(service):
    """search() doit toujours retourner [] pour les erreurs non-403 (503, etc.)."""
    with patch.object(service, "_send", new=_send_returning(503)):
        result = await service.search("Boualem Sansal")

    assert result == []


# ============================================================
# 2. _fetch_page() doit lever BabelioBlockedError sur 403
# ============================================================


@pytest.mark.asyncio
async def test_fetch_page_raises_blocked_error_on_403(service):
    """_fetch_page doit lever BabelioBlockedError si Babelio renvoie 403."""
    with (
        patch.object(service, "_send", new=_send_returning(403)),
        pytest.raises(BabelioBlockedError),
    ):
        await service._fetch_page("https://www.babelio.com/livres/Test/1")


@pytest.mark.asyncio
async def test_fetch_page_still_returns_none_for_non_403_errors(service):
    """_fetch_page doit toujours retourner None pour les erreurs non-403."""
    with patch.object(service, "_send", new=_send_returning(503)):
        result = await service._fetch_page("https://www.babelio.com/livres/Test/1")

    assert result is None


# ============================================================
# 3. verify_author()/verify_book() doivent renvoyer status='blocked_403'
# ============================================================


@pytest.mark.asyncio
async def test_verify_author_returns_blocked_403_status(service):
    """verify_author() doit renvoyer status='blocked_403' quand search() est bloqué."""
    with patch.object(
        service, "search", new=AsyncMock(side_effect=BabelioBlockedError("403"))
    ):
        result = await service.verify_author("Boualem Sansal")

    assert result["status"] == "blocked_403"
    assert result["original"] == "Boualem Sansal"
    assert result["error_message"] is not None


@pytest.mark.asyncio
async def test_verify_book_returns_blocked_403_status(service):
    """verify_book() doit renvoyer status='blocked_403' quand search() est bloqué."""
    with patch.object(
        service, "search", new=AsyncMock(side_effect=BabelioBlockedError("403"))
    ):
        result = await service.verify_book("La Légende", "Boualem Sansal")

    assert result["status"] == "blocked_403"
    assert result["original_title"] == "La Légende"
    assert result["error_message"] is not None


@pytest.mark.asyncio
async def test_verify_book_returns_blocked_403_when_scraping_blocked(service):
    """verify_book() doit renvoyer status='blocked_403' si search() réussit mais
    le scraping de la page livre (fetch_author_url_from_page) est bloqué par Babelio.
    """
    book_result = {
        "type": "livres",
        "titre": "Murmuration",
        "nom": "Silhol",
        "prenoms": "Léa",
        "url": "/livres/Silhol-Murmuration/12345",
        "ca_copies": "10",
        "ca_note": "4.0",
    }

    with (
        patch.object(service, "search", new=AsyncMock(return_value=[book_result])),
        # verify_book() scrape aussi éditeur et titre complet avant l'URL
        # auteur : sans ces mocks, vraies requêtes HTTP vers Babelio (timeout CI)
        patch.object(
            service, "fetch_publisher_from_url", new=AsyncMock(return_value=None)
        ),
        patch.object(
            service, "fetch_full_title_from_url", new=AsyncMock(return_value=None)
        ),
        patch.object(
            service,
            "fetch_author_url_from_page",
            new=AsyncMock(side_effect=BabelioBlockedError("403 scraping")),
        ),
    ):
        result = await service.verify_book("Murmuration", "Léa Silhol")

    assert result["status"] == "blocked_403"
