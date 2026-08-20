# Public API Reference

Complete Python API specification for `shopify_auth_adapter`.

---

## 🛠️ Main Entry Points

### `get_access_token(...) -> LiveToken | str`
Returns a Shopify Admin API access token or auto-refreshing `LiveToken` proxy.

```python
from shopify_auth_adapter import get_access_token

token = get_access_token(
    shop="my-store.myshopify.com",  # Optional (falls back to SHOPIFY_SHOP env var)
    client_id="...",                 # Optional (falls back to SHOPIFY_CLIENT_ID env var)
    client_secret="...",             # Optional (falls back to SHOPIFY_CLIENT_SECRET env var)
    api_version="2026-07",           # Optional (defaults to CURRENT_API_VERSION)
    live=True                        # Return LiveToken proxy (default True) or plain str
)
```

---

## 🌐 Clients & Managers

### `class ShopifyClient`
High-level authenticated client for Shopify Admin REST & GraphQL APIs.

```python
from shopify_auth_adapter import ShopifyClient

shopify = ShopifyClient()

# REST API
response = shopify.get("/blogs.json")
response = shopify.post("/blogs/123/articles.json", json={...})

# GraphQL API
data = shopify.graphql("""
    query { shop { name } }
""")
```

### `class TokenManager`
Manages token lifecycle, caching, and double-checked refresh mechanics.

```python
from shopify_auth_adapter import TokenManager, ShopifyConfig

config = ShopifyConfig(shop="my-store.myshopify.com", client_id="...", client_secret="...")
manager = TokenManager(config=config)

token_str = manager.get_token()
manager.invalidate()
```

---

## ⚙️ Configuration & Protocols

### `class ShopifyConfig`
Value object holding configuration attributes and validation methods.

### `TokenCacheProtocol`, `AuthProviderProtocol`, `TokenManagerProtocol`
Abstract Python `Protocol` contracts for dependency injection and custom extension.
