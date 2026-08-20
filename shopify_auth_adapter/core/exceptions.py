"""
core.exceptions
===============
Custom exception hierarchy for shopify_auth_adapter.

Hierarchy
---------
ShopifyAuthAdapterError          (base)
├── ShopifyConfigurationError    – missing or invalid configuration
├── ShopifyAuthenticationError   – credentials rejected by Shopify (401/403)
├── ShopifyNetworkError          – connectivity / timeout problems
└── ShopifyAPIError              – unexpected HTTP response from Shopify API
    └── ShopifyRateLimitError    – 429 Too Many Requests

Security Invariant
------------------
No exception in this hierarchy will ever expose access tokens or client secrets.
"""
from __future__ import annotations


class ShopifyAuthAdapterError(Exception):
    """Base class for all shopify_auth_adapter errors."""


class ShopifyConfigurationError(ShopifyAuthAdapterError):
    """Raised when required configuration parameters are missing or invalid."""


class ShopifyAuthenticationError(ShopifyAuthAdapterError):
    """
    Raised when Shopify rejects authentication credentials.

    Common causes:
    - Incorrect client_id or client_secret
    - Target store app uninstallation
    - Missing access scopes
    """


class ShopifyNetworkError(ShopifyAuthAdapterError):
    """Raised when network connectivity or request timeouts occur."""


class ShopifyAPIError(ShopifyAuthAdapterError):
    """Raised when the Shopify API returns an unhandled non-2xx status code."""


class ShopifyRateLimitError(ShopifyAPIError):
    """
    Raised when Shopify returns 429 Too Many Requests.

    Attributes:
        retry_after: Seconds to wait before retrying, if supplied by Shopify.
    """

    def __init__(
        self, message: str, retry_after: float | None = None
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
