"""
test_config.py
==============
Tests for ShopifyConfig: environment variable resolution, validation,
derived properties, and security (no secrets in repr).
"""
from __future__ import annotations

import pytest

from shopify_auth_adapter.config import ShopifyConfig, CURRENT_API_VERSION
from shopify_auth_adapter.exceptions import ShopifyConfigurationError


class TestShopifyConfigFromEnv:
    """Config picks up values from environment variables."""

    def test_reads_all_env_vars(self, monkeypatch):
        monkeypatch.setenv("SHOPIFY_SHOP", "env-store.myshopify.com")
        monkeypatch.setenv("SHOPIFY_CLIENT_ID", "env-client-id")
        monkeypatch.setenv("SHOPIFY_CLIENT_SECRET", "env-secret")
        monkeypatch.setenv("SHOPIFY_API_VERSION", "2026-04")

        cfg = ShopifyConfig()
        assert cfg.shop == "env-store.myshopify.com"
        assert cfg.client_id == "env-client-id"
        assert cfg.client_secret == "env-secret"
        assert cfg.api_version == "2026-04"

    def test_explicit_args_override_env(self, monkeypatch):
        monkeypatch.setenv("SHOPIFY_SHOP", "env-store")
        monkeypatch.setenv("SHOPIFY_CLIENT_ID", "env-id")
        monkeypatch.setenv("SHOPIFY_CLIENT_SECRET", "env-secret")

        cfg = ShopifyConfig(
            shop="explicit-store",
            client_id="explicit-id",
            client_secret="explicit-secret",
        )
        assert cfg.shop == "explicit-store"
        assert cfg.client_id == "explicit-id"
        assert cfg.client_secret == "explicit-secret"

    def test_default_api_version_when_no_env(self):
        """Falls back to CURRENT_API_VERSION when nothing is set."""
        cfg = ShopifyConfig(
            shop="s", client_id="c", client_secret="x"
        )
        assert cfg.api_version == CURRENT_API_VERSION

    def test_env_api_version_used(self, monkeypatch):
        monkeypatch.setenv("SHOPIFY_API_VERSION", "2026-04")
        cfg = ShopifyConfig(shop="s", client_id="c", client_secret="x")
        assert cfg.api_version == "2026-04"

    def test_explicit_api_version_overrides_env(self, monkeypatch):
        monkeypatch.setenv("SHOPIFY_API_VERSION", "2026-04")
        cfg = ShopifyConfig(
            shop="s", client_id="c", client_secret="x", api_version="2025-07"
        )
        assert cfg.api_version == "2025-07"


class TestShopifyConfigValidation:
    """validate() raises clear errors for missing required fields."""

    def test_valid_config_does_not_raise(self):
        cfg = ShopifyConfig(
            shop="my-store",
            client_id="id",
            client_secret="secret",
        )
        cfg.validate()  # must not raise

    def test_missing_shop_raises(self):
        cfg = ShopifyConfig(client_id="id", client_secret="secret")
        with pytest.raises(ShopifyConfigurationError) as exc_info:
            cfg.validate()
        assert "SHOPIFY_SHOP" in str(exc_info.value)

    def test_missing_client_id_raises(self):
        cfg = ShopifyConfig(shop="store", client_secret="secret")
        with pytest.raises(ShopifyConfigurationError) as exc_info:
            cfg.validate()
        assert "SHOPIFY_CLIENT_ID" in str(exc_info.value)

    def test_missing_client_secret_raises(self):
        cfg = ShopifyConfig(shop="store", client_id="id")
        with pytest.raises(ShopifyConfigurationError) as exc_info:
            cfg.validate()
        assert "SHOPIFY_CLIENT_SECRET" in str(exc_info.value)

    def test_all_missing_raises_with_all_fields_mentioned(self):
        cfg = ShopifyConfig()
        with pytest.raises(ShopifyConfigurationError) as exc_info:
            cfg.validate()
        msg = str(exc_info.value)
        assert "SHOPIFY_SHOP" in msg
        assert "SHOPIFY_CLIENT_ID" in msg
        assert "SHOPIFY_CLIENT_SECRET" in msg


class TestShopifyConfigDerivedProperties:
    """Derived URL properties produce correct values."""

    def test_shop_domain_appends_myshopify(self):
        cfg = ShopifyConfig(shop="my-store", client_id="x", client_secret="y")
        assert cfg.shop_domain == "my-store.myshopify.com"

    def test_shop_domain_preserves_full_domain(self):
        cfg = ShopifyConfig(
            shop="my-store.myshopify.com",
            client_id="x",
            client_secret="y",
        )
        assert cfg.shop_domain == "my-store.myshopify.com"

    def test_shop_domain_normalises_to_lowercase(self):
        cfg = ShopifyConfig(shop="MY-STORE", client_id="x", client_secret="y")
        assert cfg.shop_domain == "my-store.myshopify.com"

    def test_token_endpoint(self):
        cfg = ShopifyConfig(
            shop="my-store", client_id="x", client_secret="y"
        )
        assert cfg.token_endpoint == (
            "https://my-store.myshopify.com/admin/oauth/access_token"
        )

    def test_admin_api_base(self):
        cfg = ShopifyConfig(
            shop="my-store",
            client_id="x",
            client_secret="y",
            api_version="2026-07",
        )
        assert cfg.admin_api_base == (
            "https://my-store.myshopify.com/admin/api/2026-07"
        )


class TestShopifyConfigSecurity:
    """client_secret must never appear in repr or str."""

    def test_repr_does_not_contain_secret(self):
        secret = "super-secret-do-not-expose"
        cfg = ShopifyConfig(shop="s", client_id="id", client_secret=secret)
        assert secret not in repr(cfg)
        assert secret not in str(cfg)

    def test_repr_contains_redacted_marker(self):
        cfg = ShopifyConfig(shop="s", client_id="id", client_secret="sec")
        assert "<redacted>" in repr(cfg)
