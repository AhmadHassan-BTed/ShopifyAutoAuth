"""
core.protocols
==============
Abstract Python protocols defining explicit contracts for caching, authentication,
and management services within shopify_auth_adapter.

Enforces contract-based programming, zero coupling, and complete dependency inversion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cache.model import CachedToken


@runtime_checkable
class TokenCacheProtocol(Protocol):
    """Contract for token cache implementations."""

    def get(self) -> CachedToken | None:
        """Return a valid cached token entry if available; None otherwise."""
        ...

    def set(self, access_token: str, expires_in: int, scopes: str = "") -> CachedToken:
        """Store a new token with its expiration lifetime in seconds."""
        ...

    def invalidate(self) -> None:
        """Discard any cached token entry."""
        ...

    def is_valid(self) -> bool:
        """Return True if a usable non-expired token exists in cache."""
        ...


@runtime_checkable
class AuthProviderProtocol(Protocol):
    """Contract for OAuth authentication providers fetching raw tokens."""

    def fetch_token(self) -> tuple[str, int, str]:
        """
        Execute token acquisition call.

        Returns:
            Tuple of (access_token, expires_in_seconds, scopes)
        """
        ...


@runtime_checkable
class TokenManagerProtocol(Protocol):
    """Contract for high-level token lifecycle management."""

    def get_token(self) -> str:
        """Return a valid access token string (refreshing if necessary)."""
        ...

    def invalidate(self) -> None:
        """Invalidate currently cached token."""
        ...
