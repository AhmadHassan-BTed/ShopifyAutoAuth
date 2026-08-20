"""
exceptions.py
=============
All custom exceptions raised by shopify_auth_adapter.

Hierarchy
---------
ShopifyAuthAdapterError          (base)
├── ShopifyConfigurationError    – missing/invalid configuration
├── ShopifyAuthenticationError   – Shopify rejected credentials (401/403)
├── ShopifyNetworkError          – connectivity / timeout problems
└── ShopifyAPIError              – Shopify returned an unexpected HTTP error
    └── ShopifyRateLimitError    – 429 Too Many Requests

Security note
-------------
No exception message in this module ever contains an access token
or client secret. If you add new exceptions, maintain this invariant.
"""


class ShopifyAuthAdapterError(Exception):
    """Base class for all shopify_auth_adapter errors."""


class ShopifyConfigurationError(ShopifyAuthAdapterError):
    """
    Raised when required configuration is missing or invalid.

    Example::

        ShopifyConfigurationError:
        SHOPIFY_CLIENT_ID is not configured.
        Set the SHOPIFY_CLIENT_ID environment variable or pass
        client_id= to get_access_token() / ShopifyClient().
    """


class ShopifyAuthenticationError(ShopifyAuthAdapterError):
    """
    Raised when Shopify rejects the authentication attempt.

    Common causes:
    - Wrong client_id or client_secret
    - App not installed on the target store
    - Insufficient access scopes

    HTTP status codes that map to this exception: 401, 403.
    """


class ShopifyNetworkError(ShopifyAuthAdapterError):
    """
    Raised when the request to Shopify cannot be completed
    due to a network-level problem (timeout, DNS failure, etc.).
    """


class ShopifyAPIError(ShopifyAuthAdapterError):
    """
    Raised when the Shopify API returns an unexpected HTTP error
    (anything other than 2xx, 401, or 403).
    """


class ShopifyRateLimitError(ShopifyAPIError):
    """
    Raised when Shopify returns 429 Too Many Requests.

    Attributes:
        retry_after: seconds to wait before retrying, if provided by Shopify.
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after
