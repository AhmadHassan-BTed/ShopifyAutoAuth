"""
client.client
=============
ShopifyClient — high-level, authenticated REST and GraphQL Admin API client.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any, cast

import httpx

from shopify_auth_adapter.auth.manager import TokenManager, _get_default_manager
from shopify_auth_adapter.core.config import ShopifyConfig
from shopify_auth_adapter.core.constants import (
    DEFAULT_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_HTTP_TIMEOUT_SECONDS,
)
from shopify_auth_adapter.core.exceptions import (
    ShopifyAPIError,
    ShopifyAuthenticationError,
    ShopifyNetworkError,
    ShopifyRateLimitError,
)

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    connect=DEFAULT_CONNECT_TIMEOUT_SECONDS,
)


class ShopifyClient:
    """
    Authenticated client for Shopify Admin REST and GraphQL APIs.
    Attaches current valid access token automatically and invalidates cache + retries on 401.
    """

    def __init__(
        self,
        *,
        shop: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        api_version: str | None = None,
        timeout: httpx.Timeout = _DEFAULT_TIMEOUT,
        manager: TokenManager | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {
            k: v
            for k, v in {
                "shop": shop,
                "client_id": client_id,
                "client_secret": client_secret,
                "api_version": api_version,
            }.items()
            if v is not None
        }
        self._manager: TokenManager = manager or _get_default_manager(**kwargs)
        self._timeout: httpx.Timeout = timeout

    @property
    def config(self) -> ShopifyConfig:
        """The ShopifyConfig instance used by the underlying manager."""
        return self._manager.config

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """Send GET request to Shopify Admin REST API."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """Send POST request to Shopify Admin REST API."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        """Send PUT request to Shopify Admin REST API."""
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        """Send PATCH request to Shopify Admin REST API."""
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        """Send DELETE request to Shopify Admin REST API."""
        return self._request("DELETE", path, **kwargs)

    def graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute GraphQL query/mutation against Shopify Admin GraphQL API.
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        response = self._request(
            "POST",
            "graphql.json",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        body: dict[str, Any] = response.json()

        if "errors" in body and body["errors"]:
            raise ShopifyAPIError(
                f"Shopify GraphQL API returned errors: {body['errors']}"
            )

        data = body.get("data", body)
        return cast(dict[str, Any], data)

    def _build_url(self, path: str) -> str:
        base = self.config.admin_api_base
        path = path.lstrip("/")
        return f"{base}/{path}"

    def _auth_headers(self) -> dict[str, str]:
        return {"X-Shopify-Access-Token": self._manager.get_token()}

    def _request(
        self,
        method: str,
        path: str,
        *,
        _retry_on_401: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        url = self._build_url(path)
        caller_headers: dict[str, str] = kwargs.pop("headers", {})
        headers = {**self._auth_headers(), **caller_headers}

        logger.debug("shopify_auth_adapter: → %s %s", method.upper(), url)

        try:
            with httpx.Client(timeout=self._timeout) as http:
                response = http.request(method, url, headers=headers, **kwargs)
        except httpx.TimeoutException as exc:
            raise ShopifyNetworkError(
                f"Request timed out: {method.upper()} {url}"
            ) from exc
        except httpx.NetworkError as exc:
            raise ShopifyNetworkError(
                f"Network error during {method.upper()} {url}: {exc}"
            ) from exc

        logger.debug("shopify_auth_adapter: ← HTTP %d %s", response.status_code, url)

        if response.status_code == 401:
            if _retry_on_401:
                logger.warning(
                    "shopify_auth_adapter: received HTTP 401 — invalidating token cache and retrying once"
                )
                self._manager.invalidate()
                return self._request(method, path, _retry_on_401=False, **kwargs)
            raise ShopifyAuthenticationError(
                f"Shopify returned 401 Unauthorized for {method.upper()} {path} after token refresh."
            )

        if response.status_code == 403:
            raise ShopifyAuthenticationError(
                f"Shopify returned 403 Forbidden for {method.upper()} {path}."
            )

        if response.status_code == 429:
            retry_after: float | None = None
            raw = response.headers.get("Retry-After")
            if raw:
                with contextlib.suppress(ValueError):
                    retry_after = float(raw)
            raise ShopifyRateLimitError(
                f"Shopify rate limit hit for {method.upper()} {path} (HTTP 429). Retry after {retry_after}s.",
                retry_after=retry_after,
            )

        if response.is_error:
            raise ShopifyAPIError(
                f"Shopify Admin API returned HTTP {response.status_code} for {method.upper()} {path}. "
                f"Body (truncated): {response.text[:500]}"
            )

        return response

    def __repr__(self) -> str:
        return (
            f"ShopifyClient("
            f"shop={self.config.shop_domain!r}, "
            f"api_version={self.config.api_version!r})"
        )
