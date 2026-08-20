"""
Unit tests for ShopifyConfig domain object.
"""

import pytest

from __init__ import ShopifyConfig, ShopifyConfigurationError


def test_config_explicit_parameters():
    config = ShopifyConfig(
        shop="my-store",
        client_id="cid_123",
        client_secret="sec_456",
        api_version="2026-07",
    )
    assert config.shop_domain == "my-store.myshopify.com"
    assert config.client_id == "cid_123"
    assert config.client_secret == "sec_456"
    assert config.api_version == "2026-07"
    assert (
        config.token_endpoint == "https://my-store.myshopify.com/admin/oauth/access_token"
    )
    assert config.admin_api_base == "https://my-store.myshopify.com/admin/api/2026-07"


def test_config_env_fallback(mock_env):
    config = ShopifyConfig()
    assert config.shop_domain == "test-store.myshopify.com"
    assert config.client_id == "dummy_client_id"
    assert config.client_secret == "dummy_client_secret"
    assert config.api_version == "2026-07"


def test_config_missing_validation_raises():
    config = ShopifyConfig()
    with pytest.raises(ShopifyConfigurationError) as exc_info:
        config.validate()
    assert "SHOPIFY_SHOP is not configured" in str(exc_info.value)


def test_config_repr_masks_secret():
    config = ShopifyConfig(
        shop="my-store",
        client_id="cid_123",
        client_secret="super_secret_val",
    )
    repr_str = repr(config)
    assert "super_secret_val" not in repr_str
    assert "<redacted>" in repr_str
