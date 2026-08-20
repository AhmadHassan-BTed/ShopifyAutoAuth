"""
Unit tests for OAuth2ClientCredentialsProvider.
"""

import pytest
import respx

from shopify_auth_adapter import (
    OAuth2ClientCredentialsProvider,
    ShopifyAuthenticationError,
    ShopifyRateLimitError,
)


@respx.mock
def test_provider_fetch_token_success(dummy_config):
    respx.post(dummy_config.token_endpoint).respond(
        status_code=200,
        json={
            "access_token": "tok_xyz789",
            "expires_in": 86399,
            "scope": "read_orders,write_products",
        },
    )

    provider = OAuth2ClientCredentialsProvider(dummy_config)
    token, expires_in, scopes = provider.fetch_token()

    assert token == "tok_xyz789"
    assert expires_in == 86399
    assert scopes == "read_orders,write_products"


@respx.mock
def test_provider_fetch_token_401_unauthorized(dummy_config):
    respx.post(dummy_config.token_endpoint).respond(status_code=401)
    provider = OAuth2ClientCredentialsProvider(dummy_config)

    with pytest.raises(ShopifyAuthenticationError) as exc:
        provider.fetch_token()
    assert "rejected client credentials" in str(exc.value)


@respx.mock
def test_provider_fetch_token_429_rate_limit(dummy_config):
    respx.post(dummy_config.token_endpoint).respond(
        status_code=429, headers={"Retry-After": "15"}
    )
    provider = OAuth2ClientCredentialsProvider(dummy_config)

    with pytest.raises(ShopifyRateLimitError) as exc:
        provider.fetch_token()
    assert exc.value.retry_after == 15.0
