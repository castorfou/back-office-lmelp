import time
from pathlib import Path

from back_office_lmelp.services.babelio_cache_service import BabelioCacheService


def test_cache_set_and_get(tmp_path):
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)

    term = "Test Term"
    data = {"ok": True, "items": [1, 2, 3]}

    assert cache.get_cached(term) is None

    cache.set_cached(term, data)

    got = cache.get_cached(term)
    assert isinstance(got, dict)
    # The service stores wrapper {"ts":..., "data":...}
    assert got.get("data") == data


def test_cache_expiry(tmp_path):
    cache = BabelioCacheService(
        cache_dir=tmp_path, ttl_hours=(1 / 3600)
    )  # ttl 1 second

    term = "expire-me"
    cache.set_cached(term, {"v": 1})

    got = cache.get_cached(term)
    assert got is not None

    # Wait for expiry
    time.sleep(1.1)

    got2 = cache.get_cached(term)
    assert got2 is None


def test_cleanup_expired(tmp_path):
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=(1 / 3600))
    term = "to-clean"
    cache.set_cached(term, {"v": 42})

    # ensure file exists
    files_before = list(Path(tmp_path).iterdir())
    assert files_before

    time.sleep(1.1)

    removed = cache.cleanup_expired()
    assert removed >= 1
