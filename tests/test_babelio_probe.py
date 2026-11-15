"""Essai de connexion TCP vers Babelio, sans requête HTTP (Issue #351).

Un ban IP Babelio est un blocage pare-feu : la connexion TCP n'aboutit jamais.
Ouvrir une connexion puis la fermer aussitôt suffit à savoir si l'IP est
bannie, sans rien envoyer que les journaux HTTP de Babelio pourraient voir.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

import back_office_lmelp.services.babelio_service as babelio_module


# Adresse réservée à la documentation (RFC 5737) : la connexion n'aboutit jamais
UNREACHABLE_HOST = "192.0.2.1"


@pytest.fixture
def service():
    service = babelio_module.BabelioService()
    service.min_interval = 0
    return service


@pytest_asyncio.fixture
async def local_server():
    """Vrai serveur TCP local qui note ce qu'il reçoit de chaque connexion."""
    received: list[bytes] = []

    async def handle(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        received.append(await reader.read())
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    yield port, received
    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_probe_reports_reachable_on_open_port(service, local_server):
    port, received = local_server

    result = await service.probe_reachability(
        timeout_sec=2, host="127.0.0.1", port=port
    )

    assert result == "reachable"
    # Laisser le serveur constater la fermeture : aucun octet envoyé
    for _ in range(50):
        if received:
            break
        await asyncio.sleep(0.01)
    assert received == [b""]


@pytest.mark.asyncio
async def test_probe_reports_unreachable_on_silent_address(service):
    """Adresse muette : timeout de connexion, ou refus selon l'environnement.

    Les deux disent la même chose : la connexion n'aboutit pas.
    """
    result = await service.probe_reachability(
        timeout_sec=0.3, host=UNREACHABLE_HOST, port=443
    )

    assert result == "unreachable"


@pytest.mark.asyncio
async def test_probe_reports_unreachable_on_refused_connection(service, local_server):
    port, _ = local_server
    # Port fermé : récupérer un port libre en ouvrant puis fermant un serveur
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    closed_port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()

    result = await service.probe_reachability(
        timeout_sec=1, host="127.0.0.1", port=closed_port
    )

    assert result == "unreachable"


@pytest.mark.asyncio
async def test_probe_never_sends_http(service, local_server):
    port, _ = local_server
    with patch.object(service, "_send", new=AsyncMock()) as send:
        await service.probe_reachability(timeout_sec=1, host="127.0.0.1", port=port)
        await service.probe_reachability(
            timeout_sec=0.3, host=UNREACHABLE_HOST, port=443
        )

    send.assert_not_awaited()
    assert service.get_recent_requests() == []


@pytest.mark.asyncio
async def test_probe_targets_babelio_https_port_by_default(service):
    with patch.object(
        babelio_module.asyncio, "open_connection", new=AsyncMock()
    ) as open_connection:
        open_connection.side_effect = OSError("refusé")
        await service.probe_reachability(timeout_sec=1)

    open_connection.assert_awaited_once_with("www.babelio.com", 443)


@pytest.mark.asyncio
async def test_probe_records_last_result(service, local_server):
    port, _ = local_server
    assert service.get_last_probe() is None

    await service.probe_reachability(timeout_sec=1, host="127.0.0.1", port=port)

    last = service.get_last_probe()
    assert last is not None
    assert last["reachable"] is True
    assert isinstance(last["checked_at"], float)


# ── Disjoncteur ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unreachable_probe_opens_circuit_as_ip_ban(service):
    await service.probe_reachability(timeout_sec=0.3, host=UNREACHABLE_HOST, port=443)

    assert service._circuit_open is True
    assert service.get_circuit_reason() == "connect_timeout"


@pytest.mark.asyncio
async def test_reachable_probe_closes_circuit_opened_by_connect_timeout(
    service, local_server
):
    port, _ = local_server
    service._open_circuit_on_connection_timeout()

    await service.probe_reachability(timeout_sec=1, host="127.0.0.1", port=port)

    assert service._circuit_open is False
    assert service.get_circuit_reason() is None


@pytest.mark.asyncio
async def test_reachable_probe_keeps_circuit_opened_by_403(service, local_server):
    """Un 403 vient du cookie : seul un cookie frais referme le disjoncteur."""
    port, _ = local_server
    response = babelio_module.BabelioResponse(status=403, body=b"Forbidden")
    with (
        patch.object(service, "_send", new=AsyncMock(return_value=response)),
        pytest.raises(babelio_module.BabelioBlockedError),
    ):
        await service._fetch_page("https://www.babelio.com/livres/A/1")
    assert service.get_circuit_reason() == "http_403"

    await service.probe_reachability(timeout_sec=1, host="127.0.0.1", port=port)

    assert service._circuit_open is True
    assert service.get_circuit_reason() == "http_403"


@pytest.mark.asyncio
async def test_search_403_records_http_403_reason(service):
    response = babelio_module.BabelioResponse(status=403, body=b"Forbidden")
    with (
        patch.object(service, "_send", new=AsyncMock(return_value=response)),
        pytest.raises(babelio_module.BabelioBlockedError),
    ):
        await service.search("Le Mage du Kremlin")

    assert service._circuit_open is True
    assert service.get_circuit_reason() == "http_403"


@pytest.mark.asyncio
async def test_connection_timeout_records_connect_timeout_reason(service):
    send = AsyncMock(
        side_effect=babelio_module.BabelioConnectTimeoutError("Connection timed out")
    )
    with patch.object(service, "_send", new=send), pytest.raises(TimeoutError):
        await service.search("Le Mage du Kremlin")

    assert service.get_circuit_reason() == "connect_timeout"


def test_set_cookie_clears_circuit_reason(service):
    service._open_circuit_on_connection_timeout()

    service.set_cookie("jstsToken=abc")

    assert service._circuit_open is False
    assert service.get_circuit_reason() is None


@pytest.mark.asyncio
async def test_blocked_error_after_ip_ban_does_not_ask_for_a_cookie(service):
    """Changer le cookie ne lève pas un ban IP : le message ne doit pas le suggérer."""
    service._open_circuit_on_connection_timeout()

    with pytest.raises(babelio_module.BabelioBlockedError) as exc:
        await service.search("Le Mage du Kremlin")

    assert "IP bannie" in str(exc.value)
    assert "cookie" not in str(exc.value).replace("inutile de changer le cookie", "")


@pytest.mark.asyncio
async def test_blocked_error_after_403_asks_for_a_fresh_cookie(service):
    service._open_circuit("http_403")

    with pytest.raises(babelio_module.BabelioBlockedError) as exc:
        await service._fetch_page("https://www.babelio.com/livres/A/1")

    assert "cookie frais" in str(exc.value)
