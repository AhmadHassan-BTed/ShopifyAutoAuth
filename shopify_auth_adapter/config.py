"""
config.py
=========
Configuration for shopify_auth_adapter.

Reads from environment variables or explicit constructor arguments.
Explicit arguments take precedence over environment variables.

Supported environment variables
--------------------------------
SHOPIFY_SHOP            e.g. "my-store.myshopify.com" or "my-store"
SHOPIFY_CLIENT_ID       Client ID from the Dev Dashboard app settings page
SHOPIFY_CLIENT_SECRET   Client Secret from the Dev Dashboard app settings page
SHOPIFY_API_VERSION     e.g. "2026-07"  (defaults to CURRENT_API_VERSION)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from .exceptions import ShopifyConfigurationError

# ---------------------------------------------------------------------------
# The latest stable Shopify Admin API version as of August 2026.
# Released July 1, 2026.  Update this when Shopify releases a newer stable
# version (next: 2026-10, due October 1, 2026).
# Reference: https://shopify.dev/docs/api/usage/versioning
# ---------------------------------------------------------------------------
CURRENT_API_VERSION: str = "2026-07"


@dataclass
class ShopifyConfig:
    """
    Holds all configuration required to authenticate with the Shopify Admin API.

    Parameters are read from environment variables when not supplied explicitly.

    Args:
        shop:          Myshopify domain. Accepts "my-store" or
                       "my-store.myshopify.com".
        client_id:     OAuth client ID from the Shopify Dev Dashboard.
        client_secret: OAuth client secret from the Shopify Dev Dashboard.
                       **Never log or expose this value.**
        api_version:   Shopify Admin API version string (e.g. ``"2026-07"``).
                       Defaults to :data:`CURRENT_API_VERSION`.

    Raises:
        ShopifyConfigurationError: If any required value is missing after
            consulting both explicit arguments and environment variables.
    """

    shop: Optional[str] = field(default=None)
    client_id: Optional[str] = field(default=None)
    client_secret: Optional[str] = field(default=None)
    api_version: Optional[str] = field(default=None)

    def __post_init__(self) -> None:
        # Fill in from environment if not explicitly provided
        self.shop = self.shop or os.environ.get("SHOPIFY_SHOP")
        self.client_id = self.client_id or os.environ.get("SHOPIFY_CLIENT_ID")
        self.client_secret = self.client_secret or os.environ.get(
            "SHOPIFY_CLIENT_SECRET"
        )
        self.api_version = (
            self.api_version
            or os.environ.get("SHOPIFY_API_VERSION")
            or CURRENT_API_VERSION
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Raise :class:`ShopifyConfigurationError` if any required field
        is missing, with a clear human-readable message for each problem.

        Call this before making any network requests.
        """
        problems: list[str] = []

        if not self.shop:
            problems.append(
                "SHOPIFY_SHOP is not configured.\n"
                "  Set the SHOPIFY_SHOP environment variable (e.g. my-store.myshopify.com)\n"
                "  or pass shop= to get_access_token() / ShopifyClient()."
            )
        if not self.client_id:
            problems.append(
                "SHOPIFY_CLIENT_ID is not configured.\n"
                "  Set the SHOPIFY_CLIENT_ID environment variable.\n"
                "  You can find the Client ID on the Settings page of your\n"
                "  app in the Shopify Dev Dashboard."
            )
        if not self.client_secret:
            problems.append(
                "SHOPIFY_CLIENT_SECRET is not configured.\n"
                "  Set the SHOPIFY_CLIENT_SECRET environment variable.\n"
                "  You can find the Client Secret on the Settings page of\n"
                "  your app in the Shopify Dev Dashboard.\n"
                "  WARNING: Never commit this value to source control."
            )

        if problems:
            raise ShopifyConfigurationError(
                "shopify_auth_adapter configuration error(s):\n\n"
                + "\n\n".join(f"  • {p}" for p in problems)
            )

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def shop_domain(self) -> str:
        """
        Returns the fully-qualified myshopify.com domain.

        Appends ``.myshopify.com`` if the value does not already contain it.
        """
        shop = (self.shop or "").strip().lower()
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"
        return shop

    @property
    def token_endpoint(self) -> str:
        """Shopify OAuth token endpoint for this store."""
        return f"https://{self.shop_domain}/admin/oauth/access_token"

    @property
    def admin_api_base(self) -> str:
        """Base URL for Admin REST API calls, including the version segment."""
        return f"https://{self.shop_domain}/admin/api/{self.api_version}"

    def __repr__(self) -> str:
        # Never expose client_secret in repr
        return (
            f"ShopifyConfig("
            f"shop={self.shop_domain!r}, "
            f"client_id={self.client_id!r}, "
            f"client_secret=<redacted>, "
            f"api_version={self.api_version!r})"
        )
