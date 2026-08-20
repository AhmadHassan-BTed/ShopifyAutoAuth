"""
Unit tests for TokenManager.
"""

import respx

from __init__ import TokenManager


@respx.mock
def test_token_manager_caching_behavior(dummy_config):
    route = respx.post(dummy_config.token_endpoint).respond(
        status_code=200,
        json={"access_token": "tok_cached_1", "expires_in": 3600},
    )

    manager = TokenManager(config=dummy_config)
    token1 = manager.get_token()
    token2 = manager.get_token()

    assert token1 == "tok_cached_1"
    assert token2 == "tok_cached_1"
    assert route.call_count == 1  # Fetch hit once, second call served from cache


@respx.mock
def test_token_manager_invalidation(dummy_config):
    route = respx.post(dummy_config.token_endpoint).respond(
        status_code=200,
        json={"access_token": "tok_fresh", "expires_in": 3600},
    )

    manager = TokenManager(config=dummy_config)
    manager.get_token()
    manager.invalidate()
    manager.get_token()

    assert route.call_count == 2
