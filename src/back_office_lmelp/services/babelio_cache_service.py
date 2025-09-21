import contextlib
import hashlib
import json
import time
from pathlib import Path
from typing import Any


class BabelioCacheService:
    """Simple disk-backed cache for Babelio results.

    Each cache entry is stored as a JSON file named by the sha256 of the
    lookup key. Files contain an object {"ts": <epoch_seconds>, "data": ...}.
    TTL is expressed in hours (default caller supplies 24).
    """

    def __init__(
        self, cache_dir: Path | str = "/tmp/babelio_cache", ttl_hours: float = 24.0
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = float(ttl_hours) * 3600.0

    def _key_to_path(self, term: str, search_type: str | None = None) -> Path:
        key = term if search_type is None else f"{search_type}:{term}"
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.json"

    def get_cached(self, term: str, search_type: str | None = None) -> Any | None:
        """Return cached data wrapper or None if missing/expired.

        The stored wrapper is {'ts': <float>, 'data': <any>}.
        """
        path = self._key_to_path(term, search_type)
        if not path.exists():
            return None

        try:
            raw = path.read_text(encoding="utf-8")
            obj = json.loads(raw)
            ts = float(obj.get("ts", 0))
            if (time.time() - ts) > self.ttl_seconds:
                with contextlib.suppress(Exception):
                    path.unlink()
                return None
            return obj
        except Exception:
            # On any parse/read error treat as cache miss
            with contextlib.suppress(Exception):
                path.unlink()
            return None

    def set_cached(self, term: str, data: Any, search_type: str | None = None) -> None:
        """Atomically write the cache file for term.

        Stores wrapper {'ts': <float>, 'data': data}.
        """
        path = self._key_to_path(term, search_type)
        tmp = path.with_suffix(path.suffix + ".tmp")
        wrapper = {"ts": time.time(), "data": data}
        try:
            tmp.write_text(json.dumps(wrapper, ensure_ascii=False), encoding="utf-8")
            # atomic replace
            tmp.replace(path)
        except Exception:
            # best-effort, ignore write errors
            with contextlib.suppress(Exception):
                if tmp.exists():
                    tmp.unlink()

    def cleanup_expired(self) -> int:
        """Remove expired cache files and return count removed."""
        removed = 0
        now = time.time()
        for p in self.cache_dir.iterdir():
            if not p.is_file():
                continue
            if p.suffix != ".json":
                continue
            try:
                raw = p.read_text(encoding="utf-8")
                obj = json.loads(raw)
                ts = float(obj.get("ts", 0))
                if (now - ts) > self.ttl_seconds:
                    p.unlink()
                    removed += 1
            except Exception:
                # if file is unparseable, remove it
                try:
                    p.unlink()
                    removed += 1
                except Exception:
                    pass
        return removed
