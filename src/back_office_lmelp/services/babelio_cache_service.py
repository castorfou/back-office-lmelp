import contextlib
import hashlib
import json
import time
from pathlib import Path
from typing import Any


class BabelioCacheService:
    """Disk-backed cache for Babelio HTTP results (search AJAX and page scraping).

    Each cache entry is a JSON file named by the sha256 of ``search_type:key``.
    Files contain ``{"ts": <epoch_seconds>, "key": <str>, "search_type": <str>, "data": ...}``.
    TTL is expressed in hours (default 24).

    search_type values:
      - ``"search"`` — AJAX search results (``/aj_recherche.php``)
      - ``"page"``   — Scraped page HTML (keyed by URL)
    """

    def __init__(
        self, cache_dir: Path | str = "/tmp/babelio_cache", ttl_hours: float = 24.0
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = float(ttl_hours)
        self.ttl_seconds = self.ttl_hours * 3600.0

    # ── internal helpers ───────────────────────────────────────────────────

    def _entry_id(self, key: str, search_type: str | None = None) -> str:
        """Stable hex-digest used as the cache file stem and public entry id."""
        raw = key if search_type is None else f"{search_type}:{key}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _key_to_path(self, key: str, search_type: str | None = None) -> Path:
        return self.cache_dir / f"{self._entry_id(key, search_type)}.json"

    def _id_to_path(self, entry_id: str) -> Path:
        return self.cache_dir / f"{entry_id}.json"

    def _is_expired(self, ts: float) -> bool:
        return (time.time() - ts) > self.ttl_seconds

    # ── public CRUD API ────────────────────────────────────────────────────

    def get_cached(self, key: str, search_type: str | None = None) -> Any | None:
        """Return the stored wrapper dict ``{"ts": float, "data": any}`` or None if missing/expired.

        Backward-compat: the old signature accepted ``term`` + optional ``search_type``
        and the wrapper was ``{"ts": ..., "data": ...}``.  We keep that shape but also
        store ``key`` and ``search_type`` for ``list_entries()``.
        """
        path = self._key_to_path(key, search_type)
        if not path.exists():
            return None

        try:
            raw = path.read_text(encoding="utf-8")
            obj = json.loads(raw)
            ts = float(obj.get("ts", 0))
            if self._is_expired(ts):
                with contextlib.suppress(Exception):
                    path.unlink()
                return None
            return obj
        except Exception:
            with contextlib.suppress(Exception):
                path.unlink()
            return None

    def set_cached(self, key: str, data: Any, search_type: str | None = None) -> None:
        """Atomically write a cache entry.

        Stores ``{"ts": float, "key": str, "search_type": str|None, "data": data}``.
        """
        path = self._key_to_path(key, search_type)
        tmp = path.with_suffix(path.suffix + ".tmp")
        wrapper = {
            "ts": time.time(),
            "key": key,
            "search_type": search_type,
            "data": data,
        }
        try:
            tmp.write_text(json.dumps(wrapper, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except Exception:
            with contextlib.suppress(Exception):
                if tmp.exists():
                    tmp.unlink()

    # ── management API ─────────────────────────────────────────────────────

    def list_entries(self) -> list[dict[str, Any]]:
        """Return metadata for all cache files, sorted newest-first.

        Each entry dict has:
          ``id``          – sha256 hex-digest (use for ``invalidate()``)
          ``key``         – original term or URL
          ``search_type`` – "search" | "page" | None
          ``timestamp``   – epoch float of when the entry was cached
          ``size_bytes``  – size of the raw JSON file in bytes
          ``expired``     – True if the entry is past its TTL
        """
        entries: list[dict[str, Any]] = []
        now = time.time()
        for p in self.cache_dir.iterdir():
            if not p.is_file() or p.suffix != ".json":
                continue
            try:
                raw = p.read_text(encoding="utf-8")
                obj = json.loads(raw)
                ts = float(obj.get("ts", 0))
                entries.append(
                    {
                        "id": p.stem,
                        "key": obj.get("key", p.stem),
                        "search_type": obj.get("search_type"),
                        "timestamp": ts,
                        "size_bytes": len(raw.encode("utf-8")),
                        "expired": (now - ts) > self.ttl_seconds,
                    }
                )
            except Exception:
                continue
        entries.sort(key=lambda e: e["timestamp"], reverse=True)
        return entries

    def invalidate(self, entry_id: str) -> bool:
        """Remove a single cache entry by its hex-digest id.

        Returns True if the file existed and was removed, False otherwise.
        """
        path = self._id_to_path(entry_id)
        if path.exists():
            with contextlib.suppress(Exception):
                path.unlink()
                return True
        return False

    def invalidate_all(self) -> int:
        """Remove all cache files and return the count removed."""
        removed = 0
        for p in self.cache_dir.iterdir():
            if not p.is_file() or p.suffix != ".json":
                continue
            with contextlib.suppress(Exception):
                p.unlink()
                removed += 1
        return removed

    def cleanup_expired(self) -> int:
        """Remove expired cache files and return count removed."""
        removed = 0
        now = time.time()
        for p in self.cache_dir.iterdir():
            if not p.is_file() or p.suffix != ".json":
                continue
            try:
                raw = p.read_text(encoding="utf-8")
                obj = json.loads(raw)
                ts = float(obj.get("ts", 0))
                if (now - ts) > self.ttl_seconds:
                    p.unlink()
                    removed += 1
            except Exception:
                try:
                    p.unlink()
                    removed += 1
                except Exception:
                    pass
        return removed
