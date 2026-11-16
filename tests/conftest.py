"""Configuration pytest pour les tests du Back-Office LMELP."""

import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import ExitStack
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from back_office_lmelp.app import app
from back_office_lmelp.services.babelio_service import babelio_service


@pytest.fixture(autouse=True)
def _reset_babelio_circuit_breaker():
    """Réinitialise le circuit breaker du singleton babelio_service avant
    chaque test.

    `babelio_service` est un singleton module-level partagé par TOUTE la
    session pytest. Si un test omet de mocker une méthode de scraping
    réellement traversée (cf. règle CLAUDE.md sur pytest-timeout, Issue
    #290), un vrai appel réseau vers babelio.com peut recevoir un vrai 403
    et ouvrir `_circuit_open = True` — cet état reste alors ouvert pour
    TOUS les tests suivants de la session, même sans rapport avec Babelio,
    faisant échouer silencieusement leur propre logique d'auto-processing
    (Issue #295 : 3 tests touchés par cette fuite d'état).

    Cette fixture ne dispense pas de corriger le mock incomplet à la
    source — elle protège seulement les tests suivants d'un effet de bord
    qu'un test mal mocké continuera de produire.
    """
    babelio_service._circuit_open = False
    babelio_service._circuit_reason = None
    yield
    babelio_service._circuit_open = False
    babelio_service._circuit_reason = None


# Modules qui peuvent détenir un singleton babelio_service : tests/test_babelio_service.py
# recharge babelio_service (nouveau singleton), et certains tests importent via `src.`
_BABELIO_SINGLETON_MODULES = (
    "back_office_lmelp.services.babelio_service",
    "back_office_lmelp.utils.migration_runner",
    "src.back_office_lmelp.services.babelio_service",
    "src.back_office_lmelp.utils.migration_runner",
)


@pytest.fixture(autouse=True)
def pgx_location_forgotten():
    """Chaque test démarre sans « dernière adresse de PGX » (Issue #362).

    pgx_service la garde en mémoire de module : sans remise à zéro, l'adresse
    trouvée par un test serait essayée en premier par le suivant. Passe par
    sys.modules (et toutes ses copies, `src.` compris) sans importer le module.
    """
    for name in (
        "back_office_lmelp.services.pgx_service",
        "src.back_office_lmelp.services.pgx_service",
    ):
        module = sys.modules.get(name)
        if module is not None:
            module._last_pgx_address = None
    yield


@pytest.fixture(autouse=True)
def babelio_reachable():
    """Essai TCP Babelio réussi, sans réseau, pour tous les tests (Issue #351).

    MigrationRunner.start_migration() vérifie que Babelio est joignable avant
    de lancer la migration : sans ce patch, chaque test qui la démarre ferait
    une vraie connexion vers www.babelio.com, qui réussit en local mais
    expire en CI. Autouse pour qu'un nouveau test ne puisse pas l'oublier.
    Les tests de l'essai lui-même créent leur propre BabelioService().

    N'importe aucun module : importer migration_runner dès le premier test
    lui ferait garder le singleton d'avant le rechargement de babelio_service.
    Patche chaque singleton déjà chargé ; un module importé pendant le test
    prend le singleton courant, lui aussi patché.
    """
    singletons = {}
    for module_name in _BABELIO_SINGLETON_MODULES:
        service = getattr(sys.modules.get(module_name), "babelio_service", None)
        if service is not None:
            singletons[id(service)] = service

    probe = AsyncMock(return_value="reachable")
    with ExitStack() as stack:
        for service in singletons.values():
            stack.enter_context(patch.object(service, "probe_reachability", new=probe))
        yield probe


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_mongodb_service():
    """Create a mock MongoDB service for tests."""
    # Patch à la fois le service source ET les références dans app.py
    with (
        patch(
            "back_office_lmelp.services.mongodb_service.mongodb_service"
        ) as mock_service_source,
        patch("back_office_lmelp.app.mongodb_service", mock_service_source),
    ):
        mock_service_source.connect = MagicMock(return_value=True)
        mock_service_source.disconnect = MagicMock()
        mock_service_source.create_author_if_not_exists = MagicMock()
        mock_service_source.create_book_if_not_exists = MagicMock()
        # Ajouter les méthodes de recherche pour l'endpoint advanced-search
        mock_service_source.search_episodes = MagicMock(
            return_value={"episodes": [], "total_count": 0}
        )
        mock_service_source.search_auteurs = MagicMock(
            return_value={"auteurs": [], "total_count": 0}
        )
        mock_service_source.search_livres = MagicMock(
            return_value={"livres": [], "total_count": 0}
        )
        mock_service_source.search_editeurs = MagicMock(
            return_value={"editeurs": [], "total_count": 0}
        )
        mock_service_source.search_emissions = MagicMock(
            return_value={"emissions": [], "total_count": 0}
        )
        mock_service_source.search_critical_reviews_for_authors_books = MagicMock(
            return_value={"editeurs": []}
        )
        yield mock_service_source


@pytest.fixture
def client(mock_mongodb_service):
    """Create a test client for the FastAPI app."""
    yield TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def sample_episode_data() -> dict[str, Any]:
    """Sample episode data for testing."""
    return {
        "titre": "Test Episode Title",
        "date": "2025-08-30T10:59:59.000+00:00",
        "description": "Original test description",
        "description_corrigee": None,
        "url": "https://example.com/test-episode",
        "audio_rel_filename": "test/episode.mp3",
        "transcription": "Test transcription content",
        "type": "test",
        "duree": 1800,
    }


@pytest.fixture
def sample_episode_id() -> str:
    """Sample episode ID for testing."""
    return "507f1f77bcf86cd799439011"  # pragma: allowlist secret
