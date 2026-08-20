"""
test_auth.py
============
Tests for TokenManager and get_access_token():

- Successful token fetch via Client Credentials Grant
- Cache hits (no extra HTTP calls)
- Expiry detection and automatic refresh
- 401 / 403 / network failures
- Concurrent access (thundering-herd prevention)
- Missing configuration
- Secret leakage prevention (tokens and client_secret must not appear
  in exception messages or log output)
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import MagicMock, patch, call

import httpx
import pytest
import respx

from shopify_auth_adapter.auth import TokenManager, get_access_token
from shopify_auth_adapter.cache import CachedToken
from shopify_auth_adapter.config import ShopifyConfig
from shopify_auth_adapter.exceptions import (
    ShopifyAuthenticationError,
    ShopifyConfigurationError,
    ShopifyNetworkError,
    ShopifyRateLimitError,
)
from shopify_auth_adapter._live_token import LiveToken

TOKEN_ENDPOINT = "https://test-store.myshopify.com/admin/oauth/access_token"
GOOD_TOKEN = "fake_access_token_abc123"
GOOD_RESPONSE = {
    "access_token": GOOD_TOKEN,
    "scope": "write_content,read_content",
    "expires_in": 86399,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_manager(extra: dict | None = None) -> TokenManager:
    kwargs = {
        "shop": "test-store.myshopify.com",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        **(extra or {}),
    }
    return TokenManager(ShopifyConfig(**kwargs))


# ---------------------------------------------------------------------------
# Successful token acquisition
# ---------------------------------------------------------------------------


class TestTokenFetch:
    @respx.mock
    def test_fetches_token_on_first_call(self):
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = make_manager()
        token = manager.get_token()
        assert token == GOOD_TOKEN

    @respx.mock
    def test_returns_plain_str(self):
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = make_manager()
        token = manager.get_token()
        assert isinstance(token, str)

    @respx.mock
    def test_sends_correct_grant_type_in_body(self):
        route = respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = make_manager()
        manager.get_token()

        request = route.calls.last.request
        body = request.content.decode()
        assert "grant_type=client_credentials" in body
        assert "client_id=test-client-id" in body
        assert "client_secret=test-client-secret" in body

    @respx.mock
    def test_credentials_not_in_url(self):
        """client_secret must never appear in the request URL."""
        route = respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = make_manager()
        manager.get_token()

        url = str(route.calls.last.request.url)
        assert "test-client-secret" not in url


# ---------------------------------------------------------------------------
# Cache behaviour
# ---------------------------------------------------------------------------


class TestCacheBehaviour:
    @respx.mock
    def test_second_call_uses_cache_no_extra_http(self):
        route = respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = make_manager()
        t1 = manager.get_token()
        t2 = manager.get_token()
        assert t1 == t2 == GOOD_TOKEN
        assert route.call_count == 1  # only one HTTP call

    @respx.mock
    def test_many_calls_only_one_http_request(self):
        route = respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = make_manager()
        for _ in range(20):
            manager.get_token()
        assert route.call_count == 1

    @respx.mock
    def test_expired_token_triggers_refresh(self):
        """After the cache is manually expired, a new token is fetched."""
        route = respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = make_manager()
        manager.get_token()  # call 1 → fetch

        # Manually expire the cached token
        manager._cache.invalidate()

        manager.get_token()  # call 2 → fetch again
        assert route.call_count == 2

    @respx.mock
    def test_invalidate_then_new_token_fetched(self):
        new_token = "new_token_after_invalidation"
        responses = [
            httpx.Response(200, json=GOOD_RESPONSE),
            httpx.Response(200, json={**GOOD_RESPONSE, "access_token": new_token}),
        ]
        respx.post(TOKEN_ENDPOINT).mock(side_effect=responses)

        manager = make_manager()
        first = manager.get_token()
        manager.invalidate()
        second = manager.get_token()

        assert first == GOOD_TOKEN
        assert second == new_token


# ---------------------------------------------------------------------------
# Authentication errors
# ---------------------------------------------------------------------------


class TestAuthErrors:
    @respx.mock
    def test_401_raises_authentication_error(self):
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )
        manager = make_manager()
        with pytest.raises(ShopifyAuthenticationError):
            manager.get_token()

    @respx.mock
    def test_403_raises_authentication_error(self):
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(403, json={"error": "forbidden"})
        )
        manager = make_manager()
        with pytest.raises(ShopifyAuthenticationError):
            manager.get_token()

    @respx.mock
    def test_429_raises_rate_limit_error(self):
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "30"},
                json={"error": "rate_limited"},
            )
        )
        manager = make_manager()
        with pytest.raises(ShopifyRateLimitError) as exc_info:
            manager.get_token()
        assert exc_info.value.retry_after == 30.0

    @respx.mock
    def test_500_raises_authentication_error(self):
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        manager = make_manager()
        with pytest.raises(ShopifyAuthenticationError):
            manager.get_token()

    @respx.mock
    def test_missing_access_token_in_response_raises(self):
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json={"scope": "read_content"})
        )
        manager = make_manager()
        with pytest.raises(ShopifyAuthenticationError) as exc_info:
            manager.get_token()
        assert "access_token" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Network errors
# ---------------------------------------------------------------------------


class TestNetworkErrors:
    @respx.mock
    def test_timeout_raises_network_error(self):
        respx.post(TOKEN_ENDPOINT).mock(side_effect=httpx.TimeoutException("timed out"))
        manager = make_manager()
        with pytest.raises(ShopifyNetworkError):
            manager.get_token()

    @respx.mock
    def test_connect_error_raises_network_error(self):
        respx.post(TOKEN_ENDPOINT).mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        manager = make_manager()
        with pytest.raises(ShopifyNetworkError):
            manager.get_token()


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class TestConfigurationErrors:
    def test_missing_shop_raises(self):
        with pytest.raises(ShopifyConfigurationError) as exc_info:
            TokenManager(ShopifyConfig(client_id="x", client_secret="y"))
        assert "SHOPIFY_SHOP" in str(exc_info.value)

    def test_missing_client_id_raises(self):
        with pytest.raises(ShopifyConfigurationError) as exc_info:
            TokenManager(ShopifyConfig(shop="s", client_secret="y"))
        assert "SHOPIFY_CLIENT_ID" in str(exc_info.value)

    def test_missing_client_secret_raises(self):
        with pytest.raises(ShopifyConfigurationError) as exc_info:
            TokenManager(ShopifyConfig(shop="s", client_id="x"))
        assert "SHOPIFY_CLIENT_SECRET" in str(exc_info.value)

    def test_get_access_token_without_env_raises(self):
        """get_access_token() with no args and no env vars must raise."""
        with pytest.raises(ShopifyConfigurationError):
            get_access_token()

    def test_get_access_token_from_env(self, shopify_env):
        """get_access_token() reads config from environment variables."""
        # We only check that a LiveToken is returned; we don't make real HTTP calls.
        live = get_access_token()
        assert isinstance(live, LiveToken)

    def test_get_access_token_with_explicit_args(self):
        live = get_access_token(
            shop="my-store",
            client_id="id",
            client_secret="sec",
        )
        assert isinstance(live, LiveToken)


# ---------------------------------------------------------------------------
# Security – no secrets in exceptions or logs
# ---------------------------------------------------------------------------


class TestSecretLeakage:
    @respx.mock
    def test_client_secret_not_in_401_exception(self):
        secret = "MY-SUPER-SECRET-DO-NOT-LOG"
        respx.post(
            f"https://test-store.myshopify.com/admin/oauth/access_token"
        ).mock(return_value=httpx.Response(401))

        manager = TokenManager(
            ShopifyConfig(
                shop="test-store",
                client_id="id",
                client_secret=secret,
            )
        )
        with pytest.raises(ShopifyAuthenticationError) as exc_info:
            manager.get_token()
        assert secret not in str(exc_info.value)

    @respx.mock
    def test_access_token_not_in_info_logs(self, caplog):
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = make_manager()

        with caplog.at_level(logging.DEBUG, logger="shopify_auth_adapter"):
            manager.get_token()

        for record in caplog.records:
            assert GOOD_TOKEN not in record.getMessage(), (
                f"Access token found in log record: {record.getMessage()!r}"
            )

    @respx.mock
    def test_client_secret_not_in_info_logs(self, caplog):
        secret = "MUST-NOT-APPEAR-IN-LOGS"
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = TokenManager(
            ShopifyConfig(shop="test-store", client_id="id", client_secret=secret)
        )

        with caplog.at_level(logging.DEBUG, logger="shopify_auth_adapter"):
            manager.get_token()

        for record in caplog.records:
            assert secret not in record.getMessage(), (
                f"Client secret found in log record: {record.getMessage()!r}"
            )


# ---------------------------------------------------------------------------
# Concurrency – thundering-herd prevention
# ---------------------------------------------------------------------------


class TestConcurrency:
    @respx.mock
    def test_concurrent_requests_trigger_only_one_fetch(self):
        """
        When N threads call get_token() simultaneously on a cold cache,
        only a single HTTP request should be made.  The other N-1 threads
        wait on the refresh lock and then read from cache.
        """
        route = respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = make_manager()

        results: List[str] = []
        errors: List[Exception] = []

        def worker():
            try:
                results.append(manager.get_token())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        assert all(r == GOOD_TOKEN for r in results)
        # Only one real HTTP call despite 20 concurrent threads
        assert route.call_count == 1

    @respx.mock
    def test_concurrent_reads_after_warm_cache(self):
        """Concurrent reads against a warm cache produce no extra HTTP calls."""
        route = respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=GOOD_RESPONSE)
        )
        manager = make_manager()
        manager.get_token()  # warm the cache
        assert route.call_count == 1

        errors: List[Exception] = []

        def worker():
            try:
                t = manager.get_token()
                assert t == GOOD_TOKEN
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert route.call_count == 1  # still only the initial fetch


# ---------------------------------------------------------------------------
# get_access_token() module-level function
# ---------------------------------------------------------------------------


class TestGetAccessTokenFunction:
    def test_returns_live_token_by_default(self, shopify_env):
        result = get_access_token()
        assert isinstance(result, LiveToken)

    def test_live_false_raises_without_network(self, shopify_env):
        """
        With live=False, get_token() is called immediately.
        Without a mock, this raises ShopifyNetworkError (no real Shopify).
        """
        with pytest.raises((ShopifyNetworkError, ShopifyAuthenticationError)):
            get_access_token(live=False)

    @respx.mock
    def test_live_false_returns_plain_str(self, shopify_env):
        respx.post(
            "https://test-store.myshopify.com/admin/oauth/access_token"
        ).mock(return_value=httpx.Response(200, json=GOOD_RESPONSE))
        result = get_access_token(live=False)
        assert isinstance(result, str)
        assert not isinstance(result, LiveToken)
        assert result == GOOD_TOKEN

    @respx.mock
    def test_explicit_args_create_independent_manager(self, shopify_env):
        """Passing explicit kwargs should not share the default manager."""
        route = respx.post(
            "https://other-store.myshopify.com/admin/oauth/access_token"
        ).mock(return_value=httpx.Response(200, json=GOOD_RESPONSE))

        live = get_access_token(
            shop="other-store",
            client_id="other-id",
            client_secret="other-secret",
            live=False,
        )
        assert route.call_count == 1
