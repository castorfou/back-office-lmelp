"""Un livre au titre courant doit être trouvé sur Babelio (Issue #341).

Problème business réel (épisode du 01/11/2026) :
- verify_book("L'héritage", "Jonathan Littell") cherche le titre seul.
- Babelio ne renvoie que les homonymes populaires (Paolini, Berry, Grisham,
  Ragde) : aucun n'est de Littell → not_found, alors que le livre existe
  (https://www.babelio.com/livres/Littell-LHeritage/2069632).
- Le repli existant ne se déclenchait que si la recherche ne renvoyait rien.

Correction : une recherche de repli « titre + auteur » quand la recherche par
titre renvoie des livres mais aucun de cet auteur.

Mocks : réponses réelles de aj_recherche.php capturées le 13/11/2026
(tests/fixtures/babelio_search_lheritage_littell.json).
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from back_office_lmelp.services.babelio_service import BabelioService


FIXTURE = Path(__file__).parent / "fixtures" / "babelio_search_lheritage_littell.json"
SEARCHES: dict[str, list[dict[str, Any]]] = json.loads(
    FIXTURE.read_text(encoding="utf-8")
)
TITLE = "L'héritage"
AUTHOR = "Jonathan Littell"
LITTELL_URL = "https://www.babelio.com/livres/Littell-LHeritage/2069632"


async def _real_search(term: str, babelio_cookies: str | None = None) -> list[Any]:
    # Comme le cache disque de search() : clé insensible à la casse
    by_key = {k.strip().lower(): v for k, v in SEARCHES.items()}
    return by_key.get(term.strip().lower(), [])


def _patched(service: BabelioService, search: AsyncMock) -> Any:
    """Mocke search() et tous les scrapings traversés par verify_book()."""
    return (
        patch.object(service, "search", new=search),
        patch.object(
            service, "fetch_publisher_from_url", new=AsyncMock(return_value=None)
        ),
        patch.object(
            service, "fetch_author_url_from_page", new=AsyncMock(return_value=None)
        ),
        patch.object(
            service, "fetch_full_title_from_url", new=AsyncMock(return_value=None)
        ),
        patch.object(
            service, "_scrape_author_from_book_page", new=AsyncMock(return_value=None)
        ),
    )


@pytest.mark.asyncio
async def test_common_title_is_found_with_title_and_author_fallback() -> None:
    service = BabelioService()
    search = AsyncMock(side_effect=_real_search)
    p1, p2, p3, p4, p5 = _patched(service, search)

    with p1, p2, p3, p4, p5:
        result = await service.verify_book(TITLE, AUTHOR)

    assert result["babelio_url"] == LITTELL_URL
    assert result["babelio_suggestion_author"] == AUTHOR
    assert result["status"] in ("verified", "corrected")


@pytest.mark.asyncio
async def test_fallback_is_a_single_title_and_author_search() -> None:
    service = BabelioService()
    search = AsyncMock(side_effect=_real_search)
    p1, p2, p3, p4, p5 = _patched(service, search)

    with p1, p2, p3, p4, p5:
        await service.verify_book(TITLE, AUTHOR)

    terms = [call.args[0] for call in search.await_args_list]
    assert terms == [TITLE, f"{TITLE} {AUTHOR}"]


@pytest.mark.asyncio
async def test_no_extra_request_when_title_search_already_has_the_author() -> None:
    # « L'Héritage » de John Grisham est dans la recherche par titre : rien de plus.
    service = BabelioService()
    search = AsyncMock(side_effect=_real_search)
    p1, p2, p3, p4, p5 = _patched(service, search)

    with p1, p2, p3, p4, p5:
        result = await service.verify_book(TITLE, "John Grisham")

    assert search.await_count == 1
    assert (
        result["babelio_url"] == "https://www.babelio.com/livres/Grisham-LHeritage/5999"
    )


@pytest.mark.asyncio
async def test_no_fallback_without_author() -> None:
    service = BabelioService()
    search = AsyncMock(side_effect=_real_search)
    p1, p2, p3, p4, p5 = _patched(service, search)

    with p1, p2, p3, p4, p5:
        await service.verify_book(TITLE, None)

    assert search.await_count == 1


@pytest.mark.asyncio
async def test_blocked_fallback_search_returns_blocked_403() -> None:
    # Classes lues dans le module à l'exécution : d'autres tests le rechargent
    # (importlib.reload), une classe importée en tête de fichier serait périmée.
    from back_office_lmelp.services import babelio_service as module

    async def blocked_on_fallback(
        term: str, babelio_cookies: str | None = None
    ) -> list[Any]:
        if term == TITLE:
            return SEARCHES[TITLE]
        raise module.BabelioBlockedError("403")

    service = module.BabelioService()
    search = AsyncMock(side_effect=blocked_on_fallback)
    p1, p2, p3, p4, p5 = _patched(service, search)

    with p1, p2, p3, p4, p5:
        result = await service.verify_book(TITLE, AUTHOR)

    assert result["status"] == "blocked_403"


@pytest.mark.asyncio
async def test_typographic_apostrophe_title_is_found() -> None:
    """Le livre en base s'écrit « L’Héritage » (apostrophe typographique) : c'est
    ce titre que la liaison Babelio cherche. Babelio écrit « L'Héritage ».

    La réponse de Babelio à la recherche « L’Héritage » n'a pas pu être capturée
    (403) : le repli ne doit dépendre ni de son contenu, ni de l'apostrophe.
    """
    service = BabelioService()
    search = AsyncMock(side_effect=_real_search)  # « L’Héritage » → [] (non capturé)
    p1, p2, p3, p4, p5 = _patched(service, search)

    with p1, p2, p3, p4, p5:
        result = await service.verify_book("L’Héritage", AUTHOR)

    assert result["babelio_url"] == LITTELL_URL
    terms = [call.args[0] for call in search.await_args_list]
    assert "L'Héritage Jonathan Littell" in terms
