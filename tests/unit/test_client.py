"""
Unit tests for ShopifyClient.
"""
import httpx
import respx

from shopify_auth_adapter import ShopifyClient


@respx.mock
def test_shopify_client_rest_get(dummy_config):
    respx.post(dummy_config.token_endpoint).respond(
        status_code=200,
        json={"access_token": "tok_client_1", "expires_in": 3600},
    )
    respx.get(f"{dummy_config.admin_api_base}/blogs.json").respond(
        status_code=200,
        json={"blogs": [{"id": 1, "title": "Test Blog"}]},
    )

    client = ShopifyClient(
        shop="test-store.myshopify.com",
        client_id="dummy_client_id",
        client_secret="dummy_client_secret",
    )

    resp = client.get("/blogs.json")
    assert resp.status_code == 200
    assert resp.json()["blogs"][0]["title"] == "Test Blog"


@respx.mock
def test_shopify_client_graphql_query(dummy_config):
    respx.post(dummy_config.token_endpoint).respond(
        status_code=200,
        json={"access_token": "tok_client_2", "expires_in": 3600},
    )
    respx.post(f"{dummy_config.admin_api_base}/graphql.json").respond(
        status_code=200,
        json={"data": {"shop": {"name": "My Shopify Store"}}},
    )

    client = ShopifyClient(
        shop="test-store.myshopify.com",
        client_id="dummy_client_id",
        client_secret="dummy_client_secret",
    )

    data = client.graphql("{ shop { name } }")
    assert data["shop"]["name"] == "My Shopify Store"


@respx.mock
def test_shopify_client_401_retry_logic(dummy_config):
    # Mock token fetch endpoint
    respx.post(dummy_config.token_endpoint).respond(
        status_code=200,
        json={"access_token": "tok_revoked", "expires_in": 3600},
    )

    blogs_route = respx.get(f"{dummy_config.admin_api_base}/blogs.json")
    # First call fails with 401, second retry succeeds
    blogs_route.side_effect = [
        httpx.Response(401, json={"errors": "Invalid token"}),
        httpx.Response(200, json={"blogs": []}),
    ]

    client = ShopifyClient(
        shop="test-store.myshopify.com",
        client_id="dummy_client_id",
        client_secret="dummy_client_secret",
    )

    resp = client.get("/blogs.json")
    assert resp.status_code == 200
    assert blogs_route.call_count == 2
