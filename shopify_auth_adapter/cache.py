"""
cache.py
========
Thread-safe, in-memory token cache for Shopify access tokens.

Design notes
------------
Shopify Client Credentials tokens expire after 86 399 seconds (≈24 hours).
To guard against clock skew between this server and Shopify's servers, we
treat a token as expired :data:`CLOCK_SKEW_BUFFER_SECONDS` before its
declared ``expires_at`` timestamp.

The cache is intentionally kept **in-memory only**.  Persisting access tokens
to disk would require encryption and adds complexity that is not needed for the
single-process local applications this library targets.  Because refreshing
only requires client credentials (no user interaction), loss of the in-memory
cache simply triggers a new, silent, automated token fetch.

Thread safety
-------------
All public methods acquire :attr:`TokenCache._lock` (a :class:`threading.RLock`)
before reading or writing the cached token.  The double-checked locking pattern
in :class:`shopify_auth_adapter.auth.TokenManager` ensures that, under high
concurrency, exactly one thread performs the token fetch while others wait.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

# Refresh the token this many seconds before it actually expires.
# This prevents the edge case where the token is valid when we read it
# but has expired by the time the HTTP request reaches Shopify.
CLOCK_SKEW_BUFFER_SECONDS: int = 300  # 5 minutes


@dataclass
class CachedToken:
    """An access token together with its expiry metadata."""

    access_token: str
    expires_at: datetime  # timezone-aware UTC datetime
    scopes: str = field(default="")

    def is_valid(self) -> bool:
        """
        Return ``True`` if the token can still be used.

        Applies a :data:`CLOCK_SKEW_BUFFER_SECONDS` safety margin so that
        we proactively refresh slightly before the token actually expires.
        """
        cutoff = self.expires_at - timedelta(seconds=CLOCK_SKEW_BUFFER_SECONDS)
        return datetime.now(tz=timezone.utc) < cutoff

    def seconds_remaining(self) -> float:
        """Seconds until the token actually expires (may be negative if expired)."""
        delta = self.expires_at - datetime.now(tz=timezone.utc)
        return delta.total_seconds()

    def __repr__(self) -> str:
        # Never include the token value in repr
        return (
            f"CachedToken("
            f"access_token=<redacted>, "
            f"expires_at={self.expires_at.isoformat()}, "
            f"scopes={self.scopes!r})"
        )


class TokenCache:
    """
    Thread-safe, in-memory store for a single Shopify access token.

    Usage::

        cache = TokenCache()

        # Store a new token
        cache.set("tok_abc123", expires_in=86399, scopes="write_content")

        # Retrieve the token if still valid
        entry = cache.get()
        if entry:
            token = entry.access_token
        else:
            # token is missing or expired — fetch a new one
            ...

        # Force the next call to get() to return None
        cache.invalidate()
    """

    def __init__(self) -> None:
        self._entry: Optional[CachedToken] = None
        self._lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self) -> Optional[CachedToken]:
        """
        Return the cached token if one exists and is still valid;
        ``None`` otherwise.
        """
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
        """
        Store a new access token.

        Args:
            access_token: The raw token string returned by Shopify.
            expires_in:   Lifetime in seconds as reported by Shopify
                          (always 86 399 for client credentials tokens).
            scopes:       Comma-separated scope string from the response.

        Returns:
            The newly created :class:`CachedToken`.
        """
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
        """
        Discard the cached token.

        The next call to :meth:`get` will return ``None``, causing
        :class:`~shopify_auth_adapter.auth.TokenManager` to fetch a fresh
        token from Shopify.
        """
        with self._lock:
            self._entry = None

    def is_valid(self) -> bool:
        """Convenience method: ``True`` if there is a usable cached token."""
        return self.get() is not None

    def __repr__(self) -> str:
        with self._lock:
            if self._entry is None:
                return "TokenCache(empty)"
            return f"TokenCache(valid={self._entry.is_valid()}, {self._entry!r})"
