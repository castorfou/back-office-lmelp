"""Tests TDD pour le gateway Babelio unifié et la propagation des cookies (Issue #245).

Problèmes identifiés :
1. Les méthodes de scraping ne passent pas par le rate limiter → burst de requêtes
2. Aucun cookie de session navigateur n'est transmis → captcha Babelio

Solution :
- Méthode centrale `_fetch_page(url, babelio_cookies)` avec rate limiting
- Paramètre `babelio_cookies` propagé de l'API jusqu'aux méthodes de scraping
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from back_office_lmelp.services.babelio_service import BabelioService


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


def test_get_page_headers_adds_cookie_when_provided(service):
    """_get_page_headers doit injecter le Cookie header si fourni."""
    cookies = "disclaimer=1; p=FR; my_session=abc123"
    headers = service._get_page_headers(cookies)
    assert headers["Cookie"] == cookies


def test_get_page_headers_no_cookie_when_none(service):
    """_get_page_headers ne doit pas ajouter Cookie header si non fourni."""
    headers = service._get_page_headers(None)
    assert "Cookie" not in headers


# ============================================================
# 2. Tests pour _fetch_page (gateway unifié)
# ============================================================


@pytest.mark.asyncio
async def test_fetch_page_returns_html_on_success(service):
    """_fetch_page doit retourner le HTML de la page."""
    html = "<html><body><h1>Titre</h1></body></html>"

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=html)

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock()
    mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service._fetch_page("https://www.babelio.com/livres/Test/1")

    assert result == html


@pytest.mark.asyncio
async def test_fetch_page_returns_none_on_non_200(service):
    """_fetch_page doit retourner None si le statut HTTP n'est pas 200 (hors 403,
    qui a son propre comportement dédié — voir test_babelio_403_detection.py).
    """
    mock_response = MagicMock()
    mock_response.status = 503

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock()
    mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await service._fetch_page("https://www.babelio.com/livres/Test/1")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_page_passes_cookies_in_headers(service):
    """_fetch_page doit passer les cookies dans les headers de la session."""
    html = "<html><body>ok</body></html>"
    cookies = "disclaimer=1; p=FR; session=xyz"
    captured_headers = {}

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=html)

    def make_session(headers=None, timeout=None, **kwargs):
        captured_headers.update(headers or {})
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_session

    with patch("aiohttp.ClientSession", side_effect=make_session):
        await service._fetch_page(
            "https://www.babelio.com/livres/Test/1", babelio_cookies=cookies
        )

    assert captured_headers.get("Cookie") == cookies


@pytest.mark.asyncio
async def test_fetch_page_applies_rate_limiting(service):
    """_fetch_page doit respecter min_interval entre deux appels consécutifs."""
    import time

    html = "<html><body>ok</body></html>"
    service.min_interval = 0.1  # Court pour le test

    call_times = []

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=html)

    def make_session(headers=None, timeout=None, **kwargs):
        call_times.append(time.time())
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_session

    with patch("aiohttp.ClientSession", side_effect=make_session):
        await service._fetch_page("https://www.babelio.com/livres/T1/1")
        await service._fetch_page("https://www.babelio.com/livres/T2/2")

    assert len(call_times) == 2
    interval = call_times[1] - call_times[0]
    assert interval >= service.min_interval - 0.05  # Tolérance 50ms


# ============================================================
# 3. Tests pour les 4 méthodes de scraping (acceptent babelio_cookies)
# ============================================================


@pytest.mark.asyncio
async def test_fetch_full_title_uses_fetch_page_gateway(service):
    """fetch_full_title_from_url doit déléguer à _fetch_page."""
    html = "<html><body><h1>Mon Titre</h1></body></html>"

    with patch.object(service, "_fetch_page", new=AsyncMock(return_value=html)):
        result = await service.fetch_full_title_from_url(
            "https://www.babelio.com/livres/Test/1",
            babelio_cookies="disclaimer=1; p=FR",
        )
        service._fetch_page.assert_called_once_with(
            "https://www.babelio.com/livres/Test/1",
            babelio_cookies="disclaimer=1; p=FR",
        )
    assert result == "Mon Titre"


@pytest.mark.asyncio
async def test_fetch_publisher_uses_fetch_page_gateway(service):
    """fetch_publisher_from_url doit déléguer à _fetch_page."""
    html = '<html><body><a class="tiny_links dark" href="/editeur/Gallimard/1">Gallimard</a></body></html>'

    with patch.object(service, "_fetch_page", new=AsyncMock(return_value=html)):
        result = await service.fetch_publisher_from_url(
            "https://www.babelio.com/livres/Test/1",
            babelio_cookies="disclaimer=1; p=FR",
        )
        service._fetch_page.assert_called_once_with(
            "https://www.babelio.com/livres/Test/1",
            babelio_cookies="disclaimer=1; p=FR",
        )
    assert result == "Gallimard"


@pytest.mark.asyncio
async def test_fetch_author_url_uses_fetch_page_gateway(service):
    """fetch_author_url_from_page doit déléguer à _fetch_page."""
    html = '<html><body><a href="/auteur/Houellebecq/1">Michel Houellebecq</a></body></html>'

    with patch.object(service, "_fetch_page", new=AsyncMock(return_value=html)):
        result = await service.fetch_author_url_from_page(
            "https://www.babelio.com/livres/Test/1",
            babelio_cookies="disclaimer=1; p=FR",
        )
        service._fetch_page.assert_called_once_with(
            "https://www.babelio.com/livres/Test/1",
            babelio_cookies="disclaimer=1; p=FR",
        )
    assert "Houellebecq" in result


@pytest.mark.asyncio
async def test_scrape_author_uses_fetch_page_gateway(service):
    """_scrape_author_from_book_page doit déléguer à _fetch_page."""
    html = '<html><body><a class="livre_auteur" href="/auteur/Houellebecq/1">Michel Houellebecq</a></body></html>'

    with patch.object(service, "_fetch_page", new=AsyncMock(return_value=html)):
        result = await service._scrape_author_from_book_page(
            "https://www.babelio.com/livres/Test/1",
            babelio_cookies="disclaimer=1; p=FR",
        )
        service._fetch_page.assert_called_once_with(
            "https://www.babelio.com/livres/Test/1",
            babelio_cookies="disclaimer=1; p=FR",
        )
    assert result == "Michel Houellebecq"


# ============================================================
# 4. Tests pour extract_from_babelio_url (propagation cookies)
# ============================================================


@pytest.mark.asyncio
async def test_extract_from_babelio_url_propagates_cookies():
    """extract_from_babelio_url doit propager babelio_cookies aux appels de service."""
    from back_office_lmelp.services.babelio_migration_service import (
        BabelioMigrationService,
    )

    mock_babelio = MagicMock()
    mock_babelio.fetch_full_title_from_url = AsyncMock(return_value="Le Titre")
    mock_babelio.fetch_author_url_from_page = AsyncMock(
        return_value="https://www.babelio.com/auteur/Test/1"
    )
    mock_babelio.fetch_publisher_from_url = AsyncMock(return_value="Gallimard")
    mock_babelio._scrape_author_from_book_page = AsyncMock(return_value="Auteur Test")

    service = BabelioMigrationService(
        mongodb_service=MagicMock(), babelio_service=mock_babelio
    )

    cookies = "disclaimer=1; p=FR; my_session=abc123"
    url = "https://www.babelio.com/livres/Test/123"

    result = await service.extract_from_babelio_url(url, babelio_cookies=cookies)

    mock_babelio.fetch_full_title_from_url.assert_called_once_with(
        url, babelio_cookies=cookies
    )
    mock_babelio.fetch_author_url_from_page.assert_called_once_with(
        url, babelio_cookies=cookies
    )
    mock_babelio.fetch_publisher_from_url.assert_called_once_with(
        url, babelio_cookies=cookies
    )
    mock_babelio._scrape_author_from_book_page.assert_called_once_with(
        url, babelio_cookies=cookies
    )
    assert result["titre"] == "Le Titre"


@pytest.mark.asyncio
async def test_extract_from_babelio_url_backward_compatible():
    """extract_from_babelio_url doit fonctionner sans cookies (compatibilité descendante)."""
    from back_office_lmelp.services.babelio_migration_service import (
        BabelioMigrationService,
    )

    mock_babelio = MagicMock()
    mock_babelio.fetch_full_title_from_url = AsyncMock(return_value="Titre")
    mock_babelio.fetch_author_url_from_page = AsyncMock(return_value=None)
    mock_babelio.fetch_publisher_from_url = AsyncMock(return_value=None)

    service = BabelioMigrationService(
        mongodb_service=MagicMock(), babelio_service=mock_babelio
    )

    result = await service.extract_from_babelio_url(
        "https://www.babelio.com/livres/Test/1"
    )
    # Sans cookies → None passé aux appels
    mock_babelio.fetch_full_title_from_url.assert_called_once_with(
        "https://www.babelio.com/livres/Test/1", babelio_cookies=None
    )
    assert result["titre"] == "Titre"


# ============================================================
# 5. Tests pour les endpoints API
# ============================================================


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from back_office_lmelp.app import app

    return TestClient(app)


@pytest.fixture
def mock_migration_service():
    with patch("back_office_lmelp.app.babelio_migration_service") as mock:
        yield mock


@pytest.fixture
def mock_babelio_service():
    with patch("back_office_lmelp.app.babelio_service") as mock:
        yield mock


def test_extract_from_url_endpoint_passes_cookies_to_service(
    client, mock_migration_service
):
    """L'endpoint /api/babelio/extract-from-url doit passer babelio_cookies au service."""
    mock_migration_service.extract_from_babelio_url = AsyncMock(
        return_value={
            "titre": "Test Titre",
            "auteur": "Test Auteur",
            "editeur": "Gallimard",
            "url_livre": "https://www.babelio.com/livres/Test/1",
            "url_auteur": None,
        }
    )

    cookies = "disclaimer=1; p=FR; my_session=abc123"
    response = client.post(
        "/api/babelio/extract-from-url",
        json={
            "babelio_url": "https://www.babelio.com/livres/Test/1",
            "babelio_cookies": cookies,
        },
    )

    assert response.status_code == 200
    mock_migration_service.extract_from_babelio_url.assert_called_once_with(
        "https://www.babelio.com/livres/Test/1",
        babelio_cookies=cookies,
    )


def test_extract_from_url_endpoint_backward_compatible(client, mock_migration_service):
    """L'endpoint doit fonctionner sans cookies (None passé au service)."""
    mock_migration_service.extract_from_babelio_url = AsyncMock(
        return_value={
            "titre": "Test Titre",
            "auteur": None,
            "editeur": None,
            "url_livre": "https://www.babelio.com/livres/Test/1",
            "url_auteur": None,
        }
    )

    response = client.post(
        "/api/babelio/extract-from-url",
        json={"babelio_url": "https://www.babelio.com/livres/Test/1"},
    )

    assert response.status_code == 200
    mock_migration_service.extract_from_babelio_url.assert_called_once_with(
        "https://www.babelio.com/livres/Test/1",
        babelio_cookies=None,
    )


def test_refresh_babelio_endpoint_passes_cookies(client, mock_babelio_service):
    """L'endpoint /api/livres/{id}/refresh-babelio doit accepter et passer babelio_cookies."""
    from bson import ObjectId

    livre_id = "507f1f77bcf86cd799439011"
    url_babelio = "https://www.babelio.com/livres/Test/1"

    mock_babelio_service.fetch_full_title_from_url = AsyncMock(return_value="Titre")
    mock_babelio_service.fetch_publisher_from_url = AsyncMock(return_value="Gallimard")
    mock_babelio_service.fetch_author_url_from_page = AsyncMock(return_value=None)
    mock_babelio_service._scrape_author_from_book_page = AsyncMock(return_value=None)

    livre = {
        "_id": ObjectId(livre_id),
        "titre": "Titre",
        "url_babelio": url_babelio,
        "auteur_id": None,
        "editeur_id": None,
        "editeur": "Gallimard",
    }

    with patch("back_office_lmelp.app.mongodb_service") as mock_mongo:
        mock_mongo.db = MagicMock()
        mock_mongo.livres_collection = MagicMock()
        mock_mongo.livres_collection.find_one = MagicMock(return_value=livre)
        mock_mongo.get_auteur_by_id = MagicMock(return_value=None)
        mock_mongo.get_editeur_by_id = MagicMock(return_value=None)

        cookies = "disclaimer=1; p=FR; my_session=abc123"
        client.post(
            f"/api/livres/{livre_id}/refresh-babelio",
            json={"babelio_cookies": cookies},
        )

    # Vérifier que les cookies sont bien passés aux méthodes de scraping
    mock_babelio_service.fetch_full_title_from_url.assert_called_once_with(
        url_babelio,
        babelio_cookies=cookies,
    )


# ============================================================
# 6. Tests pour search() avec babelio_cookies (Issue #247)
# ============================================================


@pytest.mark.asyncio
async def test_search_accepts_babelio_cookies_parameter(service):
    """search() doit accepter un paramètre babelio_cookies (Issue #247)."""
    import inspect

    sig = inspect.signature(service.search)
    assert "babelio_cookies" in sig.parameters, (
        "search() doit avoir un paramètre babelio_cookies pour propager le jstsToken"
    )


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Obsolète: search() utilise désormais une session temporaire aiohttp.ClientSession "
    "directement (pas via _get_session) quand un cookie est fourni — voir TestBabelioServerSideCookie"
)
async def test_search_injects_cookies_into_session_headers(service):
    """search() avec babelio_cookies doit injecter Cookie dans les headers (Issue #247)."""
    captured_headers: dict = {}

    class FakeResponse:
        status = 200

        async def text(self, encoding=None):
            return "[]"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class FakeSession:
        def post(self, url, **kwargs):
            captured_headers.update(dict(kwargs.get("headers", {})))
            return FakeResponse()

        async def close(self):
            pass

        @property
        def closed(self):
            return False

    with patch.object(
        service, "_get_session", new=AsyncMock(return_value=FakeSession())
    ):
        cookies = "jstsToken=abc123; p=FR; disclaimer=1"
        await service.search("Murmuration", babelio_cookies=cookies)

    assert "Cookie" in captured_headers, (
        "search() doit injecter le Cookie header quand babelio_cookies est fourni"
    )
    assert captured_headers["Cookie"] == cookies


@pytest.mark.asyncio
async def test_search_no_cookie_header_when_none(service):
    """search() sans babelio_cookies ne doit pas envoyer un Cookie header vide (Issue #247)."""
    captured_headers: dict = {}

    class FakeResponse:
        status = 200

        async def text(self, encoding=None):
            return "[]"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class FakeSession:
        def post(self, url, **kwargs):
            captured_headers.update(dict(kwargs.get("headers", {})))
            return FakeResponse()

        async def close(self):
            pass

        @property
        def closed(self):
            return False

    with patch.object(
        service, "_get_session", new=AsyncMock(return_value=FakeSession())
    ):
        await service.search("Murmuration")

    # Cookie header ne doit pas être un string vide ou None
    cookie_value = captured_headers.get("Cookie")
    assert cookie_value is None or cookie_value, (
        "search() sans babelio_cookies ne doit pas injecter un Cookie header vide"
    )


# ============================================================
# 7. Tests pour verify_book() / verify_author() avec babelio_cookies (Issue #247)
# ============================================================


@pytest.mark.asyncio
async def test_verify_book_propagates_cookies_to_search(service):
    """verify_book() doit propager babelio_cookies à tous les appels search() (Issue #247)."""
    cookies = "jstsToken=abc123; p=FR; disclaimer=1"

    with patch.object(service, "search", new=AsyncMock(return_value=[])) as mock_search:
        await service.verify_book("Murmuration", "Léa Silhol", babelio_cookies=cookies)

    # Tous les appels à search() doivent transmettre les cookies
    for call in mock_search.call_args_list:
        assert call.kwargs.get("babelio_cookies") == cookies, (
            f"search() appelé sans babelio_cookies: {call}"
        )


@pytest.mark.asyncio
async def test_verify_author_propagates_cookies_to_search(service):
    """verify_author() doit propager babelio_cookies à search() (Issue #247)."""
    cookies = "jstsToken=abc123; p=FR; disclaimer=1"

    with patch.object(service, "search", new=AsyncMock(return_value=[])) as mock_search:
        await service.verify_author("Léa Silhol", babelio_cookies=cookies)

    mock_search.assert_called_once_with("Léa Silhol", babelio_cookies=cookies)


@pytest.mark.asyncio
async def test_verify_book_propagates_cookies_to_fetch_page_calls(service):
    """verify_book() doit propager babelio_cookies aux appels _fetch_page (Issue #247)."""
    cookies = "jstsToken=abc123; p=FR; disclaimer=1"
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
        patch.object(
            service, "fetch_publisher_from_url", new=AsyncMock(return_value="Mnémos")
        ) as mock_pub,
        patch.object(
            service, "fetch_full_title_from_url", new=AsyncMock(return_value=None)
        ),
        patch.object(
            service, "fetch_author_url_from_page", new=AsyncMock(return_value=None)
        ) as mock_author_url,
    ):
        await service.verify_book("Murmuration", "Léa Silhol", babelio_cookies=cookies)

    # Les méthodes de scraping doivent recevoir les cookies
    mock_pub.assert_called_once_with(
        "https://www.babelio.com/livres/Silhol-Murmuration/12345",
        babelio_cookies=cookies,
    )
    mock_author_url.assert_called_once_with(
        "https://www.babelio.com/livres/Silhol-Murmuration/12345",
        babelio_cookies=cookies,
    )


# ============================================================
# 8. Tests pour /verify-babelio endpoint avec babelio_cookies (Issue #247)
# ============================================================


def test_verify_babelio_endpoint_accepts_babelio_cookies(client):
    """POST /verify-babelio doit accepter babelio_cookies dans le body (Issue #247)."""
    cookies = "jstsToken=abc123; p=FR; disclaimer=1"

    with patch("back_office_lmelp.app.babelio_service") as mock_babelio_service:
        mock_babelio_service.verify_author = AsyncMock(
            return_value={"status": "verified", "original": "Houellebecq"}
        )
        response = client.post(
            "/api/verify-babelio",
            json={"type": "author", "name": "Houellebecq", "babelio_cookies": cookies},
        )

    assert response.status_code == 200
    mock_babelio_service.verify_author.assert_called_once_with(
        "Houellebecq", babelio_cookies=cookies
    )


def test_verify_babelio_book_endpoint_passes_cookies(client):
    """POST /verify-babelio pour un livre doit transmettre babelio_cookies (Issue #247)."""
    cookies = "jstsToken=abc123; p=FR; disclaimer=1"

    with patch("back_office_lmelp.app.babelio_service") as mock_babelio_service:
        mock_babelio_service.verify_book = AsyncMock(
            return_value={"status": "verified", "original_title": "Murmuration"}
        )
        response = client.post(
            "/api/verify-babelio",
            json={
                "type": "book",
                "title": "Murmuration",
                "author": "Léa Silhol",
                "babelio_cookies": cookies,
            },
        )

    assert response.status_code == 200
    mock_babelio_service.verify_book.assert_called_once_with(
        "Murmuration", "Léa Silhol", babelio_cookies=cookies
    )
