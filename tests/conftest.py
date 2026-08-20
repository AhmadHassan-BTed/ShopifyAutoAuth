"""
conftest.py
===========
Shared pytest fixtures for shopify_auth_adapter tests.

All tests run in isolation:
- Environment variables are cleared before each test.
- The module-level default TokenManager is reset before each test.
- No real HTTP calls are made (use ``respx`` to mock httpx).
"""
from __future__ import annotations

import pytest

import shopify_auth_adapter
from shopify_auth_adapter import _reset_default_manager
from shopify_auth_adapter.cache import TokenCache
from shopify_auth_adapter.config import ShopifyConfig
from shopify_auth_adapter.auth import TokenManager


# ---------------------------------------------------------------------------
# Environment isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Remove all Shopify environment variables before every test.

    This prevents secrets that happen to be present on the developer's machine
    from leaking into unit tests and causing misleading results.
    """
    for key in (
        "SHOPIFY_SHOP",
        "SHOPIFY_CLIENT_ID",
        "SHOPIFY_CLIENT_SECRET",
        "SHOPIFY_API_VERSION",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def reset_global_manager() -> None:
    """
    Reset the module-level singleton TokenManager before and after every test.

    Without this, tests that call ``get_access_token()`` would share state.
    """
    _reset_default_manager()
    yield
    _reset_default_manager()


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def shopify_env(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Set canonical test environment variables and return them as a dict."""
    env = {
        "SHOPIFY_SHOP": "test-store.myshopify.com",
        "SHOPIFY_CLIENT_ID": "test-client-id-abc123",
        "SHOPIFY_CLIENT_SECRET": "test-client-secret-xyz789",
        "SHOPIFY_API_VERSION": "2026-07",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env


@pytest.fixture
def test_config() -> ShopifyConfig:
    """Return a fully populated ShopifyConfig for tests."""
    return ShopifyConfig(
        shop="test-store.myshopify.com",
        client_id="test-client-id-abc123",
        client_secret="test-client-secret-xyz789",
        api_version="2026-07",
    )


@pytest.fixture
def token_manager(test_config: ShopifyConfig) -> TokenManager:
    """Return a TokenManager wired to the test config."""
    return TokenManager(config=test_config)


@pytest.fixture
def token_response() -> dict:
    """A realistic Shopify token endpoint success response body."""
    return {
        "access_token": "fake_token_abc123def456",
        "scope": "write_content,read_content",
        "expires_in": 86399,
    }


@pytest.fixture
def expired_token_response() -> dict:
    """Same as token_response but marks expires_in as 0 (for manual tests)."""
    return {
        "access_token": "fake_token_abc123def456",
        "scope": "write_content,read_content",
        "expires_in": 0,
    }


@pytest.fixture
def fresh_cache(token_response: dict) -> TokenCache:
    """Return a TokenCache pre-populated with a fresh valid token."""
    cache = TokenCache()
    cache.set(
        token_response["access_token"],
        token_response["expires_in"],
        token_response["scope"],
    )
    return cache
