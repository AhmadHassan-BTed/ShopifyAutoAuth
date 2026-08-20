"""
Unit tests for LiveToken proxy.
"""
import httpx
import respx

from shopify_auth_adapter import LiveToken, TokenManager


@respx.mock
def test_live_token_encode_delegation(dummy_config):
    respx.post(dummy_config.token_endpoint).respond(
        status_code=200,
        json={"access_token": "live_tok_val", "expires_in": 3600},
    )

    manager = TokenManager(config=dummy_config)
    live_token = LiveToken(manager)

    # Calling encode() should fetch token and encode
    assert live_token.encode("latin-1") == b"live_tok_val"
    assert str(live_token) == "live_tok_val"
    assert repr(live_token) == "LiveToken(<masked>)"


@respx.mock
def test_live_token_in_httpx_headers(dummy_config):
    respx.post(dummy_config.token_endpoint).respond(
        status_code=200,
        json={"access_token": "header_tok_123", "expires_in": 3600},
    )

    manager = TokenManager(config=dummy_config)
    live_token = LiveToken(manager)

    headers = httpx.Headers({"X-Shopify-Access-Token": live_token})
    assert headers["X-Shopify-Access-Token"] == "header_tok_123"
