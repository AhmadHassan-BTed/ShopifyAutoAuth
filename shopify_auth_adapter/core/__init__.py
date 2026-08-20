"""
core package facade
"""

from shopify_auth_adapter.core.config import ShopifyConfig
from shopify_auth_adapter.core.constants import (
    CLOCK_SKEW_BUFFER_SECONDS,
    CURRENT_API_VERSION,
    DEFAULT_AUTH_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_AUTH_TIMEOUT_SECONDS,
    DEFAULT_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_HTTP_TIMEOUT_SECONDS,
)
from shopify_auth_adapter.core.exceptions import (
    ShopifyAPIError,
    ShopifyAuthAdapterError,
    ShopifyAuthenticationError,
    ShopifyConfigurationError,
    ShopifyNetworkError,
    ShopifyRateLimitError,
)
from shopify_auth_adapter.core.protocols import (
    AuthProviderProtocol,
    TokenCacheProtocol,
    TokenManagerProtocol,
)

__all__ = [
    "ShopifyConfig",
    "CURRENT_API_VERSION",
    "CLOCK_SKEW_BUFFER_SECONDS",
    "DEFAULT_HTTP_TIMEOUT_SECONDS",
    "DEFAULT_CONNECT_TIMEOUT_SECONDS",
    "DEFAULT_AUTH_TIMEOUT_SECONDS",
    "DEFAULT_AUTH_CONNECT_TIMEOUT_SECONDS",
    "ShopifyAuthAdapterError",
    "ShopifyConfigurationError",
    "ShopifyAuthenticationError",
    "ShopifyNetworkError",
    "ShopifyAPIError",
    "ShopifyRateLimitError",
    "TokenCacheProtocol",
    "AuthProviderProtocol",
    "TokenManagerProtocol",
]
