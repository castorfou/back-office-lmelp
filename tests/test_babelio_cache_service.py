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


# ─────────────────────────────────────────────
# New features: list_entries, invalidate, page cache
# ─────────────────────────────────────────────


def test_list_entries_empty(tmp_path):
    """list_entries() returns empty list when cache is empty."""
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    entries = cache.list_entries()
    assert entries == []


def test_list_entries_returns_metadata(tmp_path):
    """list_entries() returns one entry per cached item with required fields."""
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    cache.set_cached("Michel Houellebecq", [{"type": "auteurs"}], search_type="search")
    entries = cache.list_entries()
    assert len(entries) == 1
    entry = entries[0]
    assert "id" in entry  # unique identifier for invalidation
    assert "key" in entry  # human-readable term/URL
    assert "search_type" in entry  # "search" or "page"
    assert "timestamp" in entry  # epoch float
    assert "size_bytes" in entry  # response size
    assert "expired" in entry  # bool


def test_list_entries_sorted_by_date_desc(tmp_path):
    """list_entries() returns entries sorted newest first."""
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    cache.set_cached("first", {"v": 1}, search_type="search")
    time.sleep(0.05)
    cache.set_cached("second", {"v": 2}, search_type="search")

    entries = cache.list_entries()
    assert len(entries) == 2
    assert entries[0]["key"] == "second"
    assert entries[1]["key"] == "first"


def test_invalidate_removes_entry(tmp_path):
    """invalidate(entry_id) removes the cache file."""
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    cache.set_cached("to-remove", {"data": "x"}, search_type="search")

    entries = cache.list_entries()
    assert len(entries) == 1
    entry_id = entries[0]["id"]

    result = cache.invalidate(entry_id)
    assert result is True
    assert cache.list_entries() == []
    assert cache.get_cached("to-remove") is None


def test_invalidate_nonexistent_returns_false(tmp_path):
    """invalidate() returns False if the entry_id doesn't exist."""
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    result = cache.invalidate("nonexistent-id")
    assert result is False


def test_invalidate_all(tmp_path):
    """invalidate_all() removes all cache files and returns count."""
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    cache.set_cached("term1", {"v": 1}, search_type="search")
    cache.set_cached("term2", {"v": 2}, search_type="search")
    cache.set_cached("https://www.babelio.com/livres/X/123", "html", search_type="page")

    count = cache.invalidate_all()
    assert count == 3
    assert cache.list_entries() == []


def test_page_cache_set_and_get(tmp_path):
    """Page HTML responses can be cached using search_type='page' and URL as key."""
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    url = "https://www.babelio.com/livres/Houellebecq-Les-particules-elementaires/1770"
    html = "<html><body>Test page</body></html>"

    assert cache.get_cached(url, search_type="page") is None
    cache.set_cached(url, html, search_type="page")

    got = cache.get_cached(url, search_type="page")
    assert isinstance(got, dict)
    assert got.get("data") == html


def test_page_cache_separate_from_search_cache(tmp_path):
    """search_type='page' and search_type='search' keys don't collide."""
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
    key = "same-key"
    cache.set_cached(key, {"search": True}, search_type="search")
    cache.set_cached(key, "html content", search_type="page")

    search_result = cache.get_cached(key, search_type="search")
    page_result = cache.get_cached(key, search_type="page")

    assert search_result["data"] == {"search": True}
    assert page_result["data"] == "html content"

    entries = cache.list_entries()
    assert len(entries) == 2


def test_list_entries_shows_expired(tmp_path):
    """list_entries() marks expired entries with expired=True."""
    cache = BabelioCacheService(cache_dir=tmp_path, ttl_hours=(1 / 3600))
    cache.set_cached("old-entry", {"v": 1}, search_type="search")
    time.sleep(1.1)

    entries = cache.list_entries()
    assert len(entries) == 1
    assert entries[0]["expired"] is True
