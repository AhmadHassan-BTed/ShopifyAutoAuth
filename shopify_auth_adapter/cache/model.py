"""
cache.model
===========
Value object representing a cached access token entry and its expiration metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from shopify_auth_adapter.core.constants import CLOCK_SKEW_BUFFER_SECONDS


@dataclass
class CachedToken:
    """An access token entry stored with expiration metadata."""

    access_token: str
    expires_at: datetime  # timezone-aware UTC datetime
    scopes: str = field(default="")

    def is_valid(self) -> bool:
        """
        Check if the token entry is still valid for use.

        Applies a clock-skew safety margin (CLOCK_SKEW_BUFFER_SECONDS) to prevent
        using tokens near expiration.
        """
        cutoff = self.expires_at - timedelta(seconds=CLOCK_SKEW_BUFFER_SECONDS)
        return datetime.now(tz=timezone.utc) < cutoff

    def seconds_remaining(self) -> float:
        """Calculate exact seconds remaining until actual token expiry."""
        delta = self.expires_at - datetime.now(tz=timezone.utc)
        return delta.total_seconds()

    def __repr__(self) -> str:
        # Mask access token to maintain security invariant
        return (
            f"CachedToken("
            f"access_token=<redacted>, "
            f"expires_at={self.expires_at.isoformat()}, "
            f"scopes={self.scopes!r})"
        )
