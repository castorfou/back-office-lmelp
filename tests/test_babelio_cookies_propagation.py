"""Gateway Babelio unifié : rate limiting et cookie serveur (Issue #245, #350).

- Toutes les méthodes de scraping passent par `_fetch_page(url)`, rate-limitée.
- Le seul cookie envoyé est celui du serveur (`set_cookie`) : un cookie fourni
  par le client échappait au contrôle d'âge et provoquait des 403 (ban IP).
  Voir aussi tests/test_babelio_server_cookie_only.py.
"""

from unittest.mock import AsyncMock, patch

import pytest

from back_office_lmelp.services.babelio_service import BabelioResponse, BabelioService


@pytest.fixture
def service():
    return BabelioService()


# ============================================================
# 1. Tests pour _get_page_headers
# ============================================================


def test_get_page_headers_returns_browser_like_headers(service):
    """_get_page_headers doit retourner des headers navigateur Firefox."""
    headers = service._get_page_headers()
    assert "User-Agent" in headers
    assert "Firefox" in headers["User-Agent"]
    assert "Sec-Fetch-Dest" in headers
    assert "Sec-Fetch-Mode" in headers


def test_get_page_headers_adds_stored_cookie(service):
    """_get_page_headers injecte le cookie stocké côté serveur."""
    cookies = "disclaimer=1; p=FR; my_session=abc123"
    service.set_cookie(cookies)
    headers = service._get_page_headers()
    assert headers["Cookie"] == cookies


def test_get_page_headers_no_cookie_without_stored_cookie(service):
    """Sans cookie serveur, _get_page_headers n'ajoute pas de Cookie header."""
    headers = service._get_page_headers()
    assert "Cookie" not in headers


# ============================================================
# 2. Tests pour _fetch_page (gateway unifié)
# ============================================================


def _send_returning(status: int, body: str = "") -> AsyncMock:
    """Simule le point de sortie HTTP unique de BabelioService."""
    return AsyncMock(
        return_value=BabelioResponse(status=status, body=body.encode("cp1252"))
    )


@pytest.mark.asyncio
async def test_fetch_page_returns_html_on_success(service):
    """_fetch_page doit retourner le HTML de la page."""
    html = "<html><body><h1>Titre</h1></body></html>"

    with patch.object(service, "_send", new=_send_returning(200, html)):
        result = await service._fetch_page("https://www.babelio.com/livres/Test/1")

    assert result == html


@pytest.mark.asyncio
async def test_fetch_page_returns_none_on_non_200(service):
    """_fetch_page doit retourner None si le statut HTTP n'est pas 200 (hors 403,
    qui a son propre comportement dédié — voir test_babelio_403_detection.py).
    """
    with patch.object(service, "_send", new=_send_returning(503)):
        result = await service._fetch_page("https://www.babelio.com/livres/Test/1")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_page_passes_stored_cookie_in_headers(service):
    """_fetch_page envoie le cookie stocké côté serveur."""
    cookies = "disclaimer=1; p=FR; session=xyz"
    service.set_cookie(cookies)
    send = _send_returning(200, "<html><body>ok</body></html>")

    with patch.object(service, "_send", new=send):
        await service._fetch_page("https://www.babelio.com/livres/Test/1")

    method, url, headers = send.await_args.args
    assert (method, url) == ("GET", "https://www.babelio.com/livres/Test/1")
    assert headers["Cookie"] == cookies


@pytest.mark.asyncio
async def test_fetch_page_applies_rate_limiting(service):
    """_fetch_page doit respecter min_interval entre deux appels consécutifs."""
    import time

    service.min_interval = 0.1  # Court pour le test
    call_times = []

    async def fake_send(*args, **kwargs):
        call_times.append(time.time())
        return BabelioResponse(status=200, body=b"<html><body>ok</body></html>")

    with patch.object(service, "_send", new=AsyncMock(side_effect=fake_send)):
        await service._fetch_page("https://www.babelio.com/livres/T1/1")
        await service._fetch_page("https://www.babelio.com/livres/T2/2")

    assert len(call_times) == 2
    interval = call_times[1] - call_times[0]
    assert interval >= service.min_interval - 0.05  # Tolérance 50ms


# ============================================================
# 3. Les 4 méthodes de scraping passent par _fetch_page
# ============================================================


@pytest.mark.asyncio
async def test_fetch_full_title_uses_fetch_page_gateway(service):
    """fetch_full_title_from_url doit déléguer à _fetch_page."""
    html = "<html><body><h1>Mon Titre</h1></body></html>"

    with patch.object(service, "_fetch_page", new=AsyncMock(return_value=html)):
        result = await service.fetch_full_title_from_url(
            "https://www.babelio.com/livres/Test/1"
        )
        service._fetch_page.assert_called_once_with(
            "https://www.babelio.com/livres/Test/1"
        )
    assert result == "Mon Titre"


@pytest.mark.asyncio
async def test_fetch_publisher_uses_fetch_page_gateway(service):
    """fetch_publisher_from_url doit déléguer à _fetch_page."""
    html = '<html><body><a class="tiny_links dark" href="/editeur/Gallimard/1">Gallimard</a></body></html>'

    with patch.object(service, "_fetch_page", new=AsyncMock(return_value=html)):
        result = await service.fetch_publisher_from_url(
            "https://www.babelio.com/livres/Test/1"
        )
        service._fetch_page.assert_called_once_with(
            "https://www.babelio.com/livres/Test/1"
        )
    assert result == "Gallimard"


@pytest.mark.asyncio
async def test_fetch_author_url_uses_fetch_page_gateway(service):
    """fetch_author_url_from_page doit déléguer à _fetch_page."""
    html = '<html><body><a href="/auteur/Houellebecq/1">Michel Houellebecq</a></body></html>'

    with patch.object(service, "_fetch_page", new=AsyncMock(return_value=html)):
        result = await service.fetch_author_url_from_page(
            "https://www.babelio.com/livres/Test/1"
        )
        service._fetch_page.assert_called_once_with(
            "https://www.babelio.com/livres/Test/1"
        )
    assert "Houellebecq" in result


@pytest.mark.asyncio
async def test_scrape_author_uses_fetch_page_gateway(service):
    """_scrape_author_from_book_page doit déléguer à _fetch_page."""
    html = '<html><body><a class="livre_auteur" href="/auteur/Houellebecq/1">Michel Houellebecq</a></body></html>'

    with patch.object(service, "_fetch_page", new=AsyncMock(return_value=html)):
        result = await service._scrape_author_from_book_page(
            "https://www.babelio.com/livres/Test/1"
        )
        service._fetch_page.assert_called_once_with(
            "https://www.babelio.com/livres/Test/1"
        )
    assert result == "Michel Houellebecq"
