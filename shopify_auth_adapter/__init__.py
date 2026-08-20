"""
shopify_auth_adapter
====================
Shopify Admin API authentication adapter for Python.

Implements the **OAuth 2.0 Client Credentials Grant** (the only correct
mechanism for new Dev Dashboard apps as of 2026) to obtain short-lived
access tokens that are cached in memory and automatically refreshed before
expiry.

Why not a permanent ``shpat_xxx`` token?
-----------------------------------------
Since **January 1, 2026**, Shopify no longer allows creating Custom Apps with
permanent static tokens in the store admin.  All new apps must use the
**Shopify Dev Dashboard** and the Client Credentials OAuth 2.0 flow.  Tokens
now expire after **24 hours** and must be programmatically refreshed.

This library handles that refresh transparently so your existing code requires
minimal changes.

Quick start
-----------
Install::

    pip install shopify-auth-adapter

Set environment variables::

    SHOPIFY_SHOP=my-store.myshopify.com
    SHOPIFY_CLIENT_ID=<client id from Dev Dashboard>
    SHOPIFY_CLIENT_SECRET=<client secret from Dev Dashboard>

Drop-in replacement::

    from shopify_auth_adapter import get_access_token

    # Before:
    SHOPIFY_ACCESS_TOKEN = "shpat_xxxxxxxxx"

    # After (no other changes required):
    SHOPIFY_ACCESS_TOKEN = get_access_token()

Or use the higher-level client::

    from shopify_auth_adapter import ShopifyClient

    shopify = ShopifyClient()
    response = shopify.get("/blogs.json")

Official Shopify docs:
    https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant
"""

from .auth import get_access_token, TokenManager, _reset_default_manager
from .client import ShopifyClient
from .config import ShopifyConfig, CURRENT_API_VERSION
from .exceptions import (
    ShopifyAuthAdapterError,
    ShopifyConfigurationError,
    ShopifyAuthenticationError,
    ShopifyAPIError,
    ShopifyNetworkError,
    ShopifyRateLimitError,
)
from ._live_token import LiveToken

__version__ = "1.0.0"
__all__ = [
    # Public API
    "get_access_token",
    "TokenManager",
    "ShopifyClient",
    # Configuration
    "ShopifyConfig",
    "CURRENT_API_VERSION",
    # Token proxy
    "LiveToken",
    # Exceptions
    "ShopifyAuthAdapterError",
    "ShopifyConfigurationError",
    "ShopifyAuthenticationError",
    "ShopifyAPIError",
    "ShopifyNetworkError",
    "ShopifyRateLimitError",
    # Test utilities (not for production use)
    "_reset_default_manager",
]
