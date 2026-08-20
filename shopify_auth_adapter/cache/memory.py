"""
cache.memory
============
Thread-safe, in-memory token cache implementation adhering to TokenCacheProtocol.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from shopify_auth_adapter.cache.model import CachedToken
from shopify_auth_adapter.core.protocols import TokenCacheProtocol


class InMemoryTokenCache(TokenCacheProtocol):
    """
    Thread-safe in-memory storage for a single Shopify access token.
    Uses re-entrant locking (threading.RLock) for thread safety under high concurrency.
    """

    def __init__(self) -> None:
        self._entry: CachedToken | None = None
        self._lock: threading.RLock = threading.RLock()

    def get(self) -> CachedToken | None:
        """Return the cached token entry if valid; None otherwise."""
        with self._lock:
            if self._entry is not None and self._entry.is_valid():
                return self._entry
            return None

    def set(
        self,
        access_token: str,
        expires_in: int,
        scopes: str = "",
    ) -> CachedToken:
        """Store a new token entry with calculated UTC expiration timestamp."""
        with self._lock:
            expires_at = datetime.now(tz=timezone.utc) + timedelta(
                seconds=expires_in
            )
            self._entry = CachedToken(
                access_token=access_token,
                expires_at=expires_at,
                scopes=scopes,
            )
            return self._entry

    def invalidate(self) -> None:
        """Discard current token entry."""
        with self._lock:
            self._entry = None

    def is_valid(self) -> bool:
        """Convenience method: True if a valid token entry exists."""
        return self.get() is not None

    def __repr__(self) -> str:
        with self._lock:
            if self._entry is None:
                return "InMemoryTokenCache(empty)"
            return f"InMemoryTokenCache(valid={self._entry.is_valid()}, {self._entry!r})"


# Backward-compatible alias for existing imports
TokenCache = InMemoryTokenCache
