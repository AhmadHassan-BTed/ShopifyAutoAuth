"""
Unit tests for CachedToken and InMemoryTokenCache.
"""
from datetime import datetime, timedelta, timezone

from shopify_auth_adapter.cache import CachedToken, InMemoryTokenCache
from shopify_auth_adapter.core.constants import CLOCK_SKEW_BUFFER_SECONDS


def test_cached_token_validity():
    # Valid token expiring in 1000 seconds
    expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=1000)
    token = CachedToken(access_token="tok_123", expires_at=expires_at)
    assert token.is_valid() is True

    # Expired token (within clock skew cutoff)
    expires_near = datetime.now(tz=timezone.utc) + timedelta(seconds=CLOCK_SKEW_BUFFER_SECONDS - 10)
    token_near = CachedToken(access_token="tok_near", expires_at=expires_near)
    assert token_near.is_valid() is False


def test_cached_token_repr_masks_secret():
    token = CachedToken(
        access_token="secret_token_val",
        expires_at=datetime.now(tz=timezone.utc) + timedelta(seconds=1000),
    )
    assert "secret_token_val" not in repr(token)
    assert "<redacted>" in repr(token)


def test_in_memory_cache_lifecycle():
    cache = InMemoryTokenCache()
    assert cache.get() is None

    entry = cache.set("tok_abc", expires_in=3600, scopes="read_products")
    assert entry.access_token == "tok_abc"
    assert cache.is_valid() is True
    assert cache.get().access_token == "tok_abc"

    cache.invalidate()
    assert cache.get() is None
    assert cache.is_valid() is False
