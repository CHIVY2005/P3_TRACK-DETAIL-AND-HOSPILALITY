"""Tiny thread-safe in-memory TTL cache for read-heavy dashboard endpoints.

Over a remote database (Supabase) every request pays real network latency, and the
frontend polls the same endpoints every few seconds. Caching the computed response for
a few seconds turns most of those polls (and tab switches) into instant, zero-query
responses while keeping staleness bounded by the TTL. Any write path calls
``invalidate_all`` so users never see stale data after an action they just took.
"""

import threading
import time
from typing import Any, Callable, Optional

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}

DEFAULT_TTL = 20.0


def get(key: str) -> Optional[Any]:
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            _store.pop(key, None)
            return None
        return value


def set(key: str, value: Any, ttl: float = DEFAULT_TTL) -> None:
    with _lock:
        _store[key] = (time.time() + ttl, value)


def invalidate_all() -> None:
    """Drop every cached entry. Called from write paths (seed, import, approve, reject)."""
    with _lock:
        _store.clear()


def cached(key: str, producer: Callable[[], Any], ttl: float = DEFAULT_TTL) -> Any:
    """Return a cached value for ``key`` or compute, store, and return it."""
    hit = get(key)
    if hit is not None:
        return hit
    value = producer()
    set(key, value, ttl)
    return value
