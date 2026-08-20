"""
shopify_auth_adapter
====================
Shopify Admin API authentication adapter for Python.

Implements the **OAuth 2.0 Client Credentials Grant** (the only correct
mechanism for new Dev Dashboard apps as of 2026) to obtain short-lived
access tokens that are cached in memory and automatically refreshed before
expiry.
"""

from shopify_auth_adapter.auth import (
    LiveToken,
    OAuth2ClientCredentialsProvider,
    TokenManager,
    _get_default_manager,
    _reset_default_manager,
    get_access_token,
)
from shopify_auth_adapter.cache import CachedToken, InMemoryTokenCache, TokenCache
from shopify_auth_adapter.client import ShopifyClient
from shopify_auth_adapter.core import (
    CLOCK_SKEW_BUFFER_SECONDS,
    CURRENT_API_VERSION,
    AuthProviderProtocol,
    ShopifyAPIError,
    ShopifyAuthAdapterError,
    ShopifyAuthenticationError,
    ShopifyConfig,
    ShopifyConfigurationError,
    ShopifyNetworkError,
    ShopifyRateLimitError,
    TokenCacheProtocol,
    TokenManagerProtocol,
)

__version__ = "1.0.0"

__all__ = [
    # Public API
    "get_access_token",
    "TokenManager",
    "ShopifyClient",
    "LiveToken",
    # Configuration & Constants
    "ShopifyConfig",
    "CURRENT_API_VERSION",
    "CLOCK_SKEW_BUFFER_SECONDS",
    # Cache
    "CachedToken",
    "InMemoryTokenCache",
    "TokenCache",
    # Auth Provider
    "OAuth2ClientCredentialsProvider",
    # Protocols / Interfaces
    "TokenCacheProtocol",
    "AuthProviderProtocol",
    "TokenManagerProtocol",
    # Exceptions
    "ShopifyAuthAdapterError",
    "ShopifyConfigurationError",
    "ShopifyAuthenticationError",
    "ShopifyAPIError",
    "ShopifyNetworkError",
    "ShopifyRateLimitError",
    # Testing utilities
    "_get_default_manager",
    "_reset_default_manager",
]
