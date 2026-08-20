"""
core.config
===========
Configuration value object and validation logic for Shopify authentication.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from core.constants import CURRENT_API_VERSION
from core.exceptions import ShopifyConfigurationError


@dataclass
class ShopifyConfig:
    """
    Holds all configuration parameters required to authenticate with the Shopify Admin API.

    Parameters are populated from environment variables when not supplied explicitly.
    Explicit parameters override environment variables.
    """

    shop: str | None = field(default=None)
    client_id: str | None = field(default=None)
    client_secret: str | None = field(default=None)
    api_version: str | None = field(default=None)

    def __post_init__(self) -> None:
        self.shop = self.shop or os.environ.get("SHOPIFY_SHOP")
        self.client_id = self.client_id or os.environ.get("SHOPIFY_CLIENT_ID")
        self.client_secret = self.client_secret or os.environ.get("SHOPIFY_CLIENT_SECRET")
        self.api_version = (
            self.api_version
            or os.environ.get("SHOPIFY_API_VERSION")
            or CURRENT_API_VERSION
        )

    def validate(self) -> None:
        """
        Validate that all required configuration fields exist.

        Raises:
            ShopifyConfigurationError: If any required parameter is missing.
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
                "  You can find the Client ID on the Settings page of your app in Shopify Dev Dashboard."
            )
        if not self.client_secret:
            problems.append(
                "SHOPIFY_CLIENT_SECRET is not configured.\n"
                "  Set the SHOPIFY_CLIENT_SECRET environment variable.\n"
                "  WARNING: Never commit this value to source control."
            )

        if problems:
            raise ShopifyConfigurationError(
                "shopify_auth_adapter configuration error(s):\n\n"
                + "\n\n".join(f"  • {p}" for p in problems)
            )

    @property
    def shop_domain(self) -> str:
        """Fully-qualified myshopify.com domain string."""
        shop = (self.shop or "").strip().lower()
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"
        return shop

    @property
    def token_endpoint(self) -> str:
        """Full HTTPS URL for Shopify OAuth access token grant."""
        return f"https://{self.shop_domain}/admin/oauth/access_token"

    @property
    def admin_api_base(self) -> str:
        """Base URL for Shopify Admin API endpoint for the configured API version."""
        return f"https://{self.shop_domain}/admin/api/{self.api_version}"

    def __repr__(self) -> str:
        return (
            f"ShopifyConfig("
            f"shop={self.shop_domain!r}, "
            f"client_id={self.client_id!r}, "
            f"client_secret=<redacted>, "
            f"api_version={self.api_version!r})"
        )
