"""
test_client.py
==============
Tests for ShopifyClient:

- GET / POST / PUT / PATCH / DELETE
- Correct URL construction (versioned base + path)
- Auth header attached to every request
- 401 triggers cache invalidation + single retry
- Second 401 raises ShopifyAuthenticationError
- 403 raises ShopifyAuthenticationError (no retry)
- 429 raises ShopifyRateLimitError
- 5xx raises ShopifyAPIError
- Network failures raise ShopifyNetworkError
- GraphQL success and error cases
- ShopifyClient.__repr__ safe (no secrets)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import httpx
import pytest
import respx

from shopify_auth_adapter import ShopifyClient
from shopify_auth_adapter.config import ShopifyConfig
from shopify_auth_adapter.auth import TokenManager
from shopify_auth_adapter.exceptions import (
    ShopifyAPIError,
    ShopifyAuthenticationError,
    ShopifyNetworkError,
    ShopifyRateLimitError,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHOP = "test-store.myshopify.com"
API_VERSION = "2026-07"
BASE_URL = f"https://{SHOP}/admin/api/{API_VERSION}"
TOKEN_ENDPOINT = f"https://{SHOP}/admin/oauth/access_token"
GOOD_TOKEN = "good_access_token_xyz"


# ---------------------------------------------------------------------------
# Fixture: a ShopifyClient backed by a pre-warmed mock manager
# ---------------------------------------------------------------------------


@pytest.fixture
def warmed_client() -> ShopifyClient:
    """
    Return a ShopifyClient whose TokenManager already has a cached token.
    No real HTTP calls are made to the token endpoint.
    """
    config = ShopifyConfig(
        shop=SHOP,
        client_id="test-id",
        client_secret="test-secret",
        api_version=API_VERSION,
    )
    manager = TokenManager(config=config)
    # Pre-warm the cache so get_token() never hits the network in these tests
    manager._cache.set(GOOD_TOKEN, 86399, "write_content,read_content")

    client = ShopifyClient(
        shop=SHOP,
        client_id="test-id",
        client_secret="test-secret",
        api_version=API_VERSION,
    )
    # Replace the manager with our pre-warmed one
    client._manager = manager
    return client


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------


class TestUrlConstruction:
    def test_path_with_leading_slash(self, warmed_client):
        with respx.mock:
            route = respx.get(f"{BASE_URL}/blogs.json").mock(
                return_value=httpx.Response(200, json={"blogs": []})
            )
            warmed_client.get("/blogs.json")
        assert route.called

    def test_path_without_leading_slash(self, warmed_client):
        with respx.mock:
            route = respx.get(f"{BASE_URL}/blogs.json").mock(
                return_value=httpx.Response(200, json={"blogs": []})
            )
            warmed_client.get("blogs.json")
        assert route.called

    def test_nested_path(self, warmed_client):
        with respx.mock:
            route = respx.get(f"{BASE_URL}/blogs/123/articles.json").mock(
                return_value=httpx.Response(200, json={"articles": []})
            )
            warmed_client.get("/blogs/123/articles.json")
        assert route.called


# ---------------------------------------------------------------------------
# Auth header
# ---------------------------------------------------------------------------


class TestAuthHeader:
    def test_auth_header_attached_to_get(self, warmed_client):
        with respx.mock:
            route = respx.get(f"{BASE_URL}/blogs.json").mock(
                return_value=httpx.Response(200, json={})
            )
            warmed_client.get("/blogs.json")
        request = route.calls.last.request
        assert request.headers["X-Shopify-Access-Token"] == GOOD_TOKEN

    def test_auth_header_attached_to_post(self, warmed_client):
        with respx.mock:
            route = respx.post(f"{BASE_URL}/blogs.json").mock(
                return_value=httpx.Response(201, json={})
            )
            warmed_client.post("/blogs.json", json={"blog": {"title": "Test"}})
        request = route.calls.last.request
        assert request.headers["X-Shopify-Access-Token"] == GOOD_TOKEN


# ---------------------------------------------------------------------------
# HTTP methods
# ---------------------------------------------------------------------------


class TestHttpMethods:
    @respx.mock
    def test_get(self, warmed_client):
        route = respx.get(f"{BASE_URL}/blogs.json").mock(
            return_value=httpx.Response(200, json={"blogs": [{"id": 1}]})
        )
        resp = warmed_client.get("/blogs.json")
        assert resp.status_code == 200
        assert resp.json()["blogs"][0]["id"] == 1

    @respx.mock
    def test_post(self, warmed_client):
        route = respx.post(f"{BASE_URL}/blogs.json").mock(
            return_value=httpx.Response(201, json={"blog": {"id": 42}})
        )
        resp = warmed_client.post("/blogs.json", json={"blog": {"title": "New"}})
        assert resp.status_code == 201
        assert resp.json()["blog"]["id"] == 42

    @respx.mock
    def test_put(self, warmed_client):
        route = respx.put(f"{BASE_URL}/blogs/1.json").mock(
            return_value=httpx.Response(200, json={"blog": {"id": 1}})
        )
        resp = warmed_client.put("/blogs/1.json", json={"blog": {"title": "Updated"}})
        assert resp.status_code == 200

    @respx.mock
    def test_patch(self, warmed_client):
        route = respx.patch(f"{BASE_URL}/blogs/1.json").mock(
            return_value=httpx.Response(200, json={})
        )
        warmed_client.patch("/blogs/1.json", json={"blog": {"title": "Patched"}})
        assert route.called

    @respx.mock
    def test_delete(self, warmed_client):
        route = respx.delete(f"{BASE_URL}/blogs/1.json").mock(
            return_value=httpx.Response(200, json={})
        )
        warmed_client.delete("/blogs/1.json")
        assert route.called


# ---------------------------------------------------------------------------
# 401 retry-once behaviour
# ---------------------------------------------------------------------------


class TestUnauthorisedRetry:
    @respx.mock
    def test_401_then_success_retries_once(self, warmed_client):
        """
        On a 401, the client should:
        1. Invalidate the token cache.
        2. Fetch a new token.
        3. Retry the original request once.
        """
        new_token = "refreshed_token_999"
        # First call: 401. Second call (after token refresh): 200.
        api_route = respx.get(f"{BASE_URL}/blogs.json").mock(
            side_effect=[
                httpx.Response(401),
                httpx.Response(200, json={"blogs": []}),
            ]
        )
        # Token refresh call
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": new_token,
                    "scope": "write_content",
                    "expires_in": 86399,
                },
            )
        )

        resp = warmed_client.get("/blogs.json")
        assert resp.status_code == 200
        assert api_route.call_count == 2  # first attempt + retry

        # Second request must carry the new token
        second_request = api_route.calls[-1].request
        assert second_request.headers["X-Shopify-Access-Token"] == new_token

    @respx.mock
    def test_401_twice_raises_authentication_error(self, warmed_client):
        """Two consecutive 401s must raise ShopifyAuthenticationError."""
        respx.get(f"{BASE_URL}/blogs.json").mock(
            return_value=httpx.Response(401)
        )
        # Provide a new token for the retry so it doesn't fail at fetch time
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "second_token",
                    "scope": "write_content",
                    "expires_in": 86399,
                },
            )
        )

        with pytest.raises(ShopifyAuthenticationError):
            warmed_client.get("/blogs.json")


# ---------------------------------------------------------------------------
# 403 / 429 / 5xx error cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    @respx.mock
    def test_403_raises_authentication_error(self, warmed_client):
        respx.get(f"{BASE_URL}/blogs.json").mock(
            return_value=httpx.Response(403)
        )
        with pytest.raises(ShopifyAuthenticationError):
            warmed_client.get("/blogs.json")

    @respx.mock
    def test_403_does_not_retry(self, warmed_client):
        """403 is a permissions error, not a token expiry — must not retry."""
        route = respx.get(f"{BASE_URL}/blogs.json").mock(
            return_value=httpx.Response(403)
        )
        with pytest.raises(ShopifyAuthenticationError):
            warmed_client.get("/blogs.json")
        assert route.call_count == 1  # no retry

    @respx.mock
    def test_429_raises_rate_limit_error(self, warmed_client):
        respx.get(f"{BASE_URL}/blogs.json").mock(
            return_value=httpx.Response(
                429, headers={"Retry-After": "15"}, json={}
            )
        )
        with pytest.raises(ShopifyRateLimitError) as exc_info:
            warmed_client.get("/blogs.json")
        assert exc_info.value.retry_after == 15.0

    @respx.mock
    def test_500_raises_api_error(self, warmed_client):
        respx.get(f"{BASE_URL}/blogs.json").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(ShopifyAPIError):
            warmed_client.get("/blogs.json")

    @respx.mock
    def test_timeout_raises_network_error(self, warmed_client):
        respx.get(f"{BASE_URL}/blogs.json").mock(
            side_effect=httpx.TimeoutException("timed out")
        )
        with pytest.raises(ShopifyNetworkError):
            warmed_client.get("/blogs.json")

    @respx.mock
    def test_connect_error_raises_network_error(self, warmed_client):
        respx.get(f"{BASE_URL}/blogs.json").mock(
            side_effect=httpx.ConnectError("refused")
        )
        with pytest.raises(ShopifyNetworkError):
            warmed_client.get("/blogs.json")


# ---------------------------------------------------------------------------
# GraphQL
# ---------------------------------------------------------------------------


class TestGraphQL:
    GRAPHQL_URL = f"{BASE_URL}/graphql.json"

    @respx.mock
    def test_graphql_success_returns_data(self, warmed_client):
        respx.post(self.GRAPHQL_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "blogs": {
                            "edges": [{"node": {"id": "gid://shopify/Blog/1", "title": "My Blog"}}]
                        }
                    }
                },
            )
        )
        data = warmed_client.graphql("{ blogs(first: 1) { edges { node { id title } } } }")
        assert data["blogs"]["edges"][0]["node"]["title"] == "My Blog"

    @respx.mock
    def test_graphql_sends_correct_content_type(self, warmed_client):
        route = respx.post(self.GRAPHQL_URL).mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        warmed_client.graphql("{ shop { name } }")
        request = route.calls.last.request
        assert "application/json" in request.headers["content-type"]

    @respx.mock
    def test_graphql_sends_variables(self, warmed_client):
        route = respx.post(self.GRAPHQL_URL).mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        warmed_client.graphql("query($id: ID!) { blog(id: $id) { title } }", variables={"id": "1"})
        import json
        body = json.loads(route.calls.last.request.content)
        assert body["variables"] == {"id": "1"}

    @respx.mock
    def test_graphql_errors_raise_api_error(self, warmed_client):
        respx.post(self.GRAPHQL_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "errors": [{"message": "Field 'badField' doesn't exist"}],
                    "data": None,
                },
            )
        )
        with pytest.raises(ShopifyAPIError) as exc_info:
            warmed_client.graphql("{ badField }")
        assert "badField" in str(exc_info.value)

    @respx.mock
    def test_graphql_attaches_auth_header(self, warmed_client):
        route = respx.post(self.GRAPHQL_URL).mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        warmed_client.graphql("{ shop { name } }")
        assert route.calls.last.request.headers["X-Shopify-Access-Token"] == GOOD_TOKEN


# ---------------------------------------------------------------------------
# repr safety
# ---------------------------------------------------------------------------


class TestClientRepr:
    def test_repr_does_not_expose_secret(self, warmed_client):
        r = repr(warmed_client)
        assert "test-secret" not in r

    def test_repr_contains_shop_and_version(self, warmed_client):
        r = repr(warmed_client)
        assert SHOP in r
        assert API_VERSION in r
