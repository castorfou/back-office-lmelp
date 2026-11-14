"""Un timeout de connexion vers Babelio ouvre le circuit breaker.

Babelio bannit une IP au niveau pare-feu : les paquets sont ignorés, la
connexion TCP n'aboutit jamais. Ce ban ne produit ni 403 ni captcha, seulement
un timeout de connexion. Continuer d'envoyer des requêtes pendant un ban ne sert
à rien : la première ouvre le circuit, les suivantes ne partent plus.
"""

from unittest.mock import AsyncMock, patch

import pytest

import back_office_lmelp.services.babelio_service as babelio_module


# Classes lues dans le module à l'exécution : tests/test_babelio_service.py
# recharge ce module (importlib.reload), ce qui recrée BabelioBlockedError.

# Adresse réservée à la documentation (RFC 5737) : la connexion n'aboutit jamais
UNREACHABLE_URL = "http://192.0.2.1/livres/A/1"


@pytest.fixture
def service():
    service = babelio_module.BabelioService()
    service.min_interval = 0
    return service


def _connect_timeout() -> AsyncMock:
    return AsyncMock(
        side_effect=babelio_module.BabelioConnectTimeoutError("Connection timed out")
    )


@pytest.mark.asyncio
async def test_search_connection_timeout_blocks_following_requests(service):
    with patch.object(service, "_send", new=_connect_timeout()) as send:
        with pytest.raises(TimeoutError):
            await service.search("L'oiseau des Français")
        with pytest.raises(babelio_module.BabelioBlockedError):
            await service.search("Ni de lait, ni de laine")
    assert send.await_count == 1


@pytest.mark.asyncio
async def test_fetch_page_connection_timeout_blocks_following_requests(service):
    with patch.object(service, "_send", new=_connect_timeout()) as send:
        with pytest.raises(TimeoutError):
            await service._fetch_page("https://www.babelio.com/livres/A/1")
        with pytest.raises(babelio_module.BabelioBlockedError):
            await service._fetch_page("https://www.babelio.com/livres/B/2")
    assert send.await_count == 1


@pytest.mark.asyncio
async def test_real_transport_reports_connection_timeout(service):
    """curl_cffi signale « Connection timed out » par un Timeout générique."""
    service.connect_timeout_sec = 0.5
    try:
        await service._send("GET", UNREACHABLE_URL, headers={})
    except babelio_module.BabelioConnectTimeoutError:
        return
    except Exception as e:  # réseau qui refuse au lieu d'ignorer (CI, sandbox)
        pytest.skip(f"Adresse injoignable sans timeout dans cet environnement: {e}")
    pytest.fail("La connexion vers une adresse muette aurait dû expirer")
