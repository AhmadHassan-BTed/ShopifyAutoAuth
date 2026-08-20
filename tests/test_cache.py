"""
test_cache.py
=============
Tests for TokenCache: get/set/invalidate, expiry logic, clock-skew buffer,
and thread safety.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from shopify_auth_adapter.cache import (
    CachedToken,
    TokenCache,
    CLOCK_SKEW_BUFFER_SECONDS,
)


class TestCachedToken:
    """Unit tests for CachedToken.is_valid() and helpers."""

    def _make_token(self, seconds_from_now: float) -> CachedToken:
        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            seconds=seconds_from_now
        )
        return CachedToken(
            access_token="tok",
            expires_at=expires_at,
            scopes="read_content",
        )

    def test_far_future_token_is_valid(self):
        token = self._make_token(86399)
        assert token.is_valid() is True

    def test_expired_token_is_not_valid(self):
        token = self._make_token(-1)
        assert token.is_valid() is False

    def test_token_within_skew_buffer_is_not_valid(self):
        """A token expiring within CLOCK_SKEW_BUFFER_SECONDS should not be used."""
        token = self._make_token(CLOCK_SKEW_BUFFER_SECONDS - 10)
        assert token.is_valid() is False

    def test_token_just_outside_skew_buffer_is_valid(self):
        """A token expiring just after the buffer should still be considered valid."""
        token = self._make_token(CLOCK_SKEW_BUFFER_SECONDS + 10)
        assert token.is_valid() is True

    def test_seconds_remaining_positive_for_fresh_token(self):
        token = self._make_token(3600)
        assert token.seconds_remaining() > 0

    def test_seconds_remaining_negative_for_expired_token(self):
        token = self._make_token(-100)
        assert token.seconds_remaining() < 0

    def test_repr_does_not_contain_token_value(self):
        token = self._make_token(3600)
        token.access_token = "super-secret-token"
        # repr should not expose the actual token value
        assert "super-secret-token" not in repr(token)
        assert "<redacted>" in repr(token)


class TestTokenCache:
    """Unit tests for TokenCache."""

    def test_initially_empty(self):
        cache = TokenCache()
        assert cache.get() is None
        assert cache.is_valid() is False

    def test_set_then_get_returns_entry(self):
        cache = TokenCache()
        entry = cache.set("my_token", 86399, "write_content")
        retrieved = cache.get()
        assert retrieved is not None
        assert retrieved.access_token == "my_token"
        assert retrieved.scopes == "write_content"

    def test_set_returns_cached_token(self):
        cache = TokenCache()
        result = cache.set("tok", 86399)
        assert isinstance(result, CachedToken)
        assert result.access_token == "tok"

    def test_is_valid_after_set(self):
        cache = TokenCache()
        cache.set("tok", 86399)
        assert cache.is_valid() is True

    def test_invalidate_clears_entry(self):
        cache = TokenCache()
        cache.set("tok", 86399)
        cache.invalidate()
        assert cache.get() is None
        assert cache.is_valid() is False

    def test_expired_token_not_returned(self):
        """set() with expires_in=0 produces an immediately expired token."""
        cache = TokenCache()
        cache.set("tok", 0)
        # By the time we read it, it's expired (0 seconds from now)
        assert cache.get() is None

    def test_overwrite_replaces_previous_entry(self):
        cache = TokenCache()
        cache.set("first_token", 86399)
        cache.set("second_token", 86399)
        entry = cache.get()
        assert entry is not None
        assert entry.access_token == "second_token"

    def test_get_does_not_return_expired_without_invalidate(self):
        """
        Verify that get() respects the skew buffer even without explicit invalidation.
        We simulate an expired token by patching datetime.now.
        """
        cache = TokenCache()
        cache.set("tok", CLOCK_SKEW_BUFFER_SECONDS - 5)
        # Token is set to expire within the skew buffer → should not be returned
        assert cache.get() is None


class TestTokenCacheThreadSafety:
    """Verify TokenCache is safe under concurrent read/write access."""

    def test_concurrent_reads_all_succeed(self):
        cache = TokenCache()
        cache.set("shared_token", 86399)

        errors = []

        def reader():
            try:
                for _ in range(100):
                    entry = cache.get()
                    assert entry is not None
                    assert entry.access_token == "shared_token"
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"

    def test_concurrent_writes_do_not_corrupt_state(self):
        cache = TokenCache()
        errors = []

        def writer(n: int):
            try:
                for _ in range(50):
                    cache.set(f"token_{n}", 86399)
                    time.sleep(0)  # yield to other threads
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        # Cache must still be in a valid state
        assert cache.is_valid() is True

    def test_concurrent_read_write_invalidate(self):
        cache = TokenCache()
        errors = []

        def reader():
            for _ in range(200):
                # get() may return None (if invalidated) — both are valid
                result = cache.get()
                assert result is None or isinstance(result.access_token, str)

        def writer():
            for i in range(50):
                cache.set(f"token_{i}", 86399)
                time.sleep(0)
                cache.invalidate()
                time.sleep(0)

        threads = (
            [threading.Thread(target=reader) for _ in range(10)]
            + [threading.Thread(target=writer) for _ in range(5)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
