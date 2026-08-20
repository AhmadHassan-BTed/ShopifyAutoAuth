"""
Integration end-to-end tests for shopify_auth_adapter.
"""
import respx

from shopify_auth_adapter import ShopifyClient, get_access_token


@respx.mock
def test_end_to_end_drop_in_helper(mock_env):
    respx.post("https://test-store.myshopify.com/admin/oauth/access_token").respond(
        status_code=200,
        json={"access_token": "e2e_tok_999", "expires_in": 86399, "scope": "read_products"},
    )

    token = get_access_token()
    assert str(token) == "e2e_tok_999"
    assert token.encode("utf-8") == b"e2e_tok_999"


@respx.mock
def test_end_to_end_client_flow(mock_env):
    respx.post("https://test-store.myshopify.com/admin/oauth/access_token").respond(
        status_code=200,
        json={"access_token": "e2e_tok_888", "expires_in": 86399},
    )
    respx.get("https://test-store.myshopify.com/admin/api/2026-07/products.json").respond(
        status_code=200,
        json={"products": [{"id": 101, "title": "Widget"}]},
    )

    client = ShopifyClient()
    response = client.get("/products.json")
    assert response.status_code == 200
    assert response.json()["products"][0]["title"] == "Widget"
