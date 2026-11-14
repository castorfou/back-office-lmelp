"""Un cookie Babelio trop vieux ne doit jamais être envoyé.

Babelio répond 403 à un cookie jstsToken expiré, et ses 403 se transforment en
ban IP pare-feu (~24 h) en quelques minutes. Le serveur date donc le cookie à
son enregistrement et refuse d'appeler Babelio au-delà de
BABELIO_COOKIE_MAX_AGE_SEC, sans émettre la moindre requête.
"""

from unittest.mock import AsyncMock, patch

import pytest

import back_office_lmelp.services.babelio_service as babelio_module


# Classes lues dans le module à l'exécution : tests/test_babelio_service.py
# recharge ce module (importlib.reload), ce qui recrée BabelioBlockedError.


@pytest.fixture
def stale_cookie_service(monkeypatch):
    monkeypatch.setenv("BABELIO_COOKIE_MAX_AGE_SEC", "0")
    service = babelio_module.BabelioService()
    service.min_interval = 0
    service.set_cookie("jstsToken=<REDACTED>")
    return service


@pytest.mark.asyncio
async def test_search_with_stale_cookie_sends_no_request(stale_cookie_service):
    send = AsyncMock(side_effect=AssertionError("requête HTTP émise"))
    with (
        patch.object(stale_cookie_service, "_send", new=send),
        pytest.raises(babelio_module.BabelioBlockedError),
    ):
        await stale_cookie_service.search("Ni de lait, ni de laine")
    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_page_with_stale_cookie_sends_no_request(stale_cookie_service):
    send = AsyncMock(side_effect=AssertionError("requête HTTP émise"))
    with (
        patch.object(stale_cookie_service, "_send", new=send),
        pytest.raises(babelio_module.BabelioBlockedError),
    ):
        await stale_cookie_service._fetch_page(
            "https://www.babelio.com/livres/Salasc-Ni-de-lait-ni-de-laine/1641697"
        )
    send.assert_not_awaited()
