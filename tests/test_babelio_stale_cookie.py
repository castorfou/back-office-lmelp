"""Un cookie Babelio trop vieux ne doit jamais être envoyé.

Babelio répond 403 à un cookie jstsToken expiré, et ses 403 se transforment en
ban IP pare-feu (~24 h) en quelques minutes. Le serveur date donc le cookie à
son enregistrement et refuse d'appeler Babelio au-delà de
BABELIO_COOKIE_MAX_AGE_SEC, sans émettre la moindre requête.
"""

from unittest.mock import MagicMock, patch

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
    client_session = MagicMock(side_effect=AssertionError("requête HTTP émise"))
    with (
        patch(
            "back_office_lmelp.services.babelio_service.aiohttp.ClientSession",
            client_session,
        ),
        pytest.raises(babelio_module.BabelioBlockedError),
    ):
        await stale_cookie_service.search("Ni de lait, ni de laine")
    client_session.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_page_with_stale_cookie_sends_no_request(stale_cookie_service):
    client_session = MagicMock(side_effect=AssertionError("requête HTTP émise"))
    with (
        patch(
            "back_office_lmelp.services.babelio_service.aiohttp.ClientSession",
            client_session,
        ),
        pytest.raises(babelio_module.BabelioBlockedError),
    ):
        await stale_cookie_service._fetch_page(
            "https://www.babelio.com/livres/Salasc-Ni-de-lait-ni-de-laine/1641697"
        )
    client_session.assert_not_called()
