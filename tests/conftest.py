"""
Global pytest fixtures for shopify_auth_adapter test suite.
"""
from __future__ import annotations

import pytest

from shopify_auth_adapter import ShopifyConfig, _reset_default_manager


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset global TokenManager singleton before and after every test."""
    _reset_default_manager()
    yield
    _reset_default_manager()


@pytest.fixture
def mock_env(monkeypatch):
    """Fixture providing populated dummy environment variables."""
    monkeypatch.setenv("SHOPIFY_SHOP", "test-store.myshopify.com")
    monkeypatch.setenv("SHOPIFY_CLIENT_ID", "dummy_client_id")
    monkeypatch.setenv("SHOPIFY_CLIENT_SECRET", "dummy_client_secret")
    monkeypatch.setenv("SHOPIFY_API_VERSION", "2026-07")


@pytest.fixture
def dummy_config():
    """Fixture providing a validated ShopifyConfig instance."""
    return ShopifyConfig(
        shop="test-store.myshopify.com",
        client_id="dummy_client_id",
        client_secret="dummy_client_secret",
        api_version="2026-07",
    )
