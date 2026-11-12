"""Un timeout de connexion vers Babelio ouvre le circuit breaker.

Babelio bannit une IP au niveau pare-feu : les paquets sont ignorés, la
connexion TCP n'aboutit jamais. Ce ban ne produit ni 403 ni captcha, seulement
un timeout de connexion. Continuer d'envoyer des requêtes pendant un ban ne sert
à rien : la première ouvre le circuit, les suivantes ne partent plus.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

import back_office_lmelp.services.babelio_service as babelio_module


# Classes lues dans le module à l'exécution : tests/test_babelio_service.py
# recharge ce module (importlib.reload), ce qui recrée BabelioBlockedError.


class _TimingOutRequest:
    """Requête aiohttp dont la connexion expire, comme lors d'un ban IP."""

    async def __aenter__(self):
        raise aiohttp.ConnectionTimeoutError("Connection timeout to host")

    async def __aexit__(self, *args):
        return False


class _TimingOutSession:
    def __init__(self, *args, **kwargs):
        self.calls = 0

    def post(self, url, **kwargs):
        self.calls += 1
        return _TimingOutRequest()

    def get(self, url, **kwargs):
        self.calls += 1
        return _TimingOutRequest()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    @property
    def closed(self):
        return False

    async def close(self):
        pass


@pytest.fixture
def service():
    service = babelio_module.BabelioService()
    service.min_interval = 0
    return service


@pytest.mark.asyncio
async def test_search_connection_timeout_blocks_following_requests(service):
    session = _TimingOutSession()
    with patch.object(service, "_get_session", new=AsyncMock(return_value=session)):
        with pytest.raises(TimeoutError):
            await service.search("L'oiseau des Français")
        with pytest.raises(babelio_module.BabelioBlockedError):
            await service.search("Ni de lait, ni de laine")
    assert session.calls == 1


@pytest.mark.asyncio
async def test_fetch_page_connection_timeout_blocks_following_requests(service):
    session = _TimingOutSession()
    client_session = MagicMock(return_value=session)
    with patch(
        "back_office_lmelp.services.babelio_service.aiohttp.ClientSession",
        client_session,
    ):
        with pytest.raises(TimeoutError):
            await service._fetch_page("https://www.babelio.com/livres/A/1")
        with pytest.raises(babelio_module.BabelioBlockedError):
            await service._fetch_page("https://www.babelio.com/livres/B/2")
    assert session.calls == 1
