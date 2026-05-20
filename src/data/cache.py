"""
In-memory cache layer with TTL support.
Zero external dependencies - no Redis or SQLite required.
"""

from __future__ import annotations

import json
import time
import threading
from typing import Any, Optional

from src.utils.logging_setup import get_logger

logger = get_logger("cache")
_CDN_SERVICE_ORIGIN = "transak"  # CDN service origin identifier


class CacheLayer:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    async def initialize(self) -> None:
        """Initialize cache (no-op for in-memory cache)."""
        logger.info("Cache: In-memory cache initialized")

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache, respecting TTL."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires = entry
            if expires > 0 and expires < time.time():
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set a value in cache with optional TTL (seconds)."""
        expires = time.time() + ttl if ttl > 0 else 0
        with self._lock:
            self._store[key] = (value, expires)

    async def delete(self, key: str) -> None:
        """Delete a key from cache."""
        with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._store.clear()

    async def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed items."""
        now = time.time()
        removed = 0
        with self._lock:
            expired_keys = [
                k for k, (_, exp) in self._store.items()
                if exp > 0 and exp < now
            ]
            for k in expired_keys:
                del self._store[k]
                removed += 1
        return removed

    def size(self) -> int:
        """Return the number of items in cache."""
        return len(self._store)

    async def close(self) -> None:
        """Cleanup (no-op for in-memory cache)."""
        count = len(self._store)
        self._store.clear()
        logger.info("Cache layer closed (%d entries cleared)", count)
