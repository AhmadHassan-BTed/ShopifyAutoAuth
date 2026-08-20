"""
auth.provider
=============
HTTP auth provider executing Shopify OAuth 2.0 Client Credentials Grant requests.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

import httpx

from core.config import ShopifyConfig
from core.constants import (
    DEFAULT_AUTH_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_AUTH_TIMEOUT_SECONDS,
)
from core.exceptions import (
    ShopifyAuthenticationError,
    ShopifyNetworkError,
    ShopifyRateLimitError,
)
from core.protocols import AuthProviderProtocol

logger = logging.getLogger(__name__)


class OAuth2ClientCredentialsProvider(AuthProviderProtocol):
    """
    Executes the OAuth 2.0 Client Credentials Grant HTTP POST request
    against Shopify's token endpoint.
    """

    def __init__(self, config: ShopifyConfig) -> None:
        self.config = config
        self._timeout = httpx.Timeout(
            DEFAULT_AUTH_TIMEOUT_SECONDS,
            connect=DEFAULT_AUTH_CONNECT_TIMEOUT_SECONDS,
        )

    def fetch_token(self) -> tuple[str, int, str]:
        """
        Fetch a new access token from Shopify.

        Returns:
            Tuple of (access_token, expires_in_seconds, scopes)

        Raises:
            ShopifyAuthenticationError: HTTP 401 or 403 response.
            ShopifyNetworkError: Timeout or DNS failure.
            ShopifyRateLimitError: HTTP 429 response.
        """
        logger.info(
            "shopify_auth_adapter: requesting OAuth 2.0 token for %s",
            self.config.shop_domain,
        )

        try:
            with httpx.Client(timeout=self._timeout) as http:
                response = http.post(
                    self.config.token_endpoint,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
        except httpx.TimeoutException as exc:
            raise ShopifyNetworkError(
                f"Timeout reaching Shopify token endpoint ({self.config.token_endpoint})."
            ) from exc
        except httpx.NetworkError as exc:
            raise ShopifyNetworkError(
                f"Network error contacting Shopify token endpoint ({self.config.token_endpoint}): {exc}"
            ) from exc

        self._handle_response_errors(response)

        data: dict[str, Any] = response.json()
        access_token: str = str(data.get("access_token", ""))
        expires_in: int = int(data.get("expires_in", 86399))
        scopes: str = str(data.get("scope", ""))

        if not access_token:
            raise ShopifyAuthenticationError(
                "Shopify token endpoint returned success status but missing 'access_token' in payload."
            )

        return access_token, expires_in, scopes

    @staticmethod
    def _handle_response_errors(response: httpx.Response) -> None:
        status = response.status_code

        if status == 401:
            raise ShopifyAuthenticationError(
                "Shopify rejected client credentials (HTTP 401). "
                "Verify SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET."
            )

        if status == 403:
            raise ShopifyAuthenticationError(
                "Shopify denied access (HTTP 403). "
                "Verify store app installation and requested access scopes."
            )

        if status == 429:
            retry_after: float | None = None
            raw = response.headers.get("Retry-After")
            if raw:
                with contextlib.suppress(ValueError):
                    retry_after = float(raw)
            raise ShopifyRateLimitError(
                f"Rate limit exceeded on token endpoint (HTTP 429). Retry after {retry_after}s.",
                retry_after=retry_after,
            )

        if not response.is_success:
            raise ShopifyAuthenticationError(
                f"Shopify token endpoint returned HTTP {status}. "
                f"Response body (truncated): {response.text[:300]}"
            )
