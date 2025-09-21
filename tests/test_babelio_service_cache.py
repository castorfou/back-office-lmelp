import asyncio

from back_office_lmelp.services.babelio_cache_service import BabelioCacheService
from back_office_lmelp.services.babelio_service import BabelioService


def test_babelio_service_uses_disk_cache(tmp_path):
    """TDD: when a BabelioCacheService is attached to the service, search() should
    return cached data and avoid performing network calls.

    This test is expected to fail until `BabelioService` is updated to consult
    an injected `cache_service` attribute.
    """
    term = "Cached Term"
    expected = [{"id": "1", "type": "auteurs", "nom": "Cached"}]

    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    # write cache for both raw term and lowercased key to be resilient
    cache.set_cached(term, expected)
    cache.set_cached(term.strip().lower(), expected)

    service = BabelioService()

    # attach the disk cache instance (integration point to implement)
    service.cache_service = cache

    # prevent network usage: _get_session should not be called
    async def _fail_network(*args, **kwargs):
        raise RuntimeError("network should not be called when cache hit")

    service._get_session = _fail_network

    # call search synchronously via asyncio.run
    result = asyncio.run(service.search(term))

    assert result == expected
