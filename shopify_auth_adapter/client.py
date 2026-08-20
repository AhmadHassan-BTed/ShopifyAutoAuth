"""
client.py
=========
:class:`ShopifyClient` — a high-level, authenticated Shopify Admin API client.

This is an optional, higher-level interface on top of
:func:`~shopify_auth_adapter.auth.get_access_token`.  Use it when you want
automatic token management **and** clean request helpers, without having to
construct URLs or attach auth headers manually.

The lower-level :func:`~shopify_auth_adapter.auth.get_access_token` API
remains fully supported for applications that want to manage HTTP themselves.

Features
--------
* Automatic token acquisition and refresh (delegates to :class:`TokenManager`).
* On receipt of a 401 response, invalidates the cache and retries once.
* Typed error hierarchy: :class:`~shopify_auth_adapter.exceptions.ShopifyAuthenticationError`,
  :class:`~shopify_auth_adapter.exceptions.ShopifyAPIError`,
  :class:`~shopify_auth_adapter.exceptions.ShopifyNetworkError`.
* Convenience methods for REST and GraphQL Admin API.
* Configurable timeouts; uses ``httpx`` throughout.

Usage::

    from shopify_auth_adapter import ShopifyClient

    shopify = ShopifyClient()

    # REST Admin API
    response = shopify.get("/blogs.json")
    blogs = response.json()["blogs"]

    article_payload = {"article": {"title": "Hello", "body_html": "<p>World</p>"}}
    shopify.post(f"/blogs/{blog_id}/articles.json", json=article_payload)

    # GraphQL Admin API
    data = shopify.graphql(\"\"\"
        query {
          blogs(first: 10) {
            edges { node { id title } }
          }
        }
    \"\"\")
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from .auth import TokenManager, _get_default_manager
from .config import ShopifyConfig
from .exceptions import (
    ShopifyAPIError,
    ShopifyAuthenticationError,
    ShopifyNetworkError,
    ShopifyRateLimitError,
)

logger = logging.getLogger(__name__)

# Default timeout: 30 s overall, 10 s to establish the connection.
# Shopify's Admin API is generally fast but can be slow under high load.
_DEFAULT_TIMEOUT: httpx.Timeout = httpx.Timeout(30.0, connect=10.0)


class ShopifyClient:
    """
    Authenticated client for the Shopify Admin API.

    All methods automatically attach the current valid access token.  If
    the token has expired, it is silently refreshed before the request is
    sent.  A 401 response causes the cache to be invalidated and the
    request to be retried once with a fresh token.

    Parameters
    ----------
    shop:
        Myshopify store domain.  Falls back to ``SHOPIFY_SHOP``.
    client_id:
        OAuth client ID.  Falls back to ``SHOPIFY_CLIENT_ID``.
    client_secret:
        OAuth client secret.  Falls back to ``SHOPIFY_CLIENT_SECRET``.
    api_version:
        API version (e.g. ``"2026-07"``).  Falls back to
        ``SHOPIFY_API_VERSION`` or the current stable version.
    timeout:
        ``httpx.Timeout`` instance for all requests.

    Examples
    --------
    From environment variables::

        shopify = ShopifyClient()

    Explicit config::

        shopify = ShopifyClient(
            shop="my-store.myshopify.com",
            client_id="abc",
            client_secret="secret",
        )
    """

    def __init__(
        self,
        *,
        shop: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: httpx.Timeout = _DEFAULT_TIMEOUT,
    ) -> None:
        kwargs = {
            k: v
            for k, v in {
                "shop": shop,
                "client_id": client_id,
                "client_secret": client_secret,
                "api_version": api_version,
            }.items()
            if v is not None
        }
        self._manager: TokenManager = _get_default_manager(**kwargs)
        self._timeout: httpx.Timeout = timeout

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> ShopifyConfig:
        """The :class:`ShopifyConfig` used by this client."""
        return self._manager.config

    # ------------------------------------------------------------------
    # Public HTTP methods
    # ------------------------------------------------------------------

    def get(self, path: str, **kwargs) -> httpx.Response:
        """
        Send a GET request to the Shopify Admin REST API.

        Args:
            path:    API path relative to the versioned base URL,
                     e.g. ``"/blogs.json"`` or ``"blogs.json"``.
            **kwargs: Passed through to ``httpx.Client.request()``.

        Returns:
            ``httpx.Response``

        Raises:
            ShopifyAuthenticationError, ShopifyAPIError, ShopifyNetworkError
        """
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        """Send a POST request to the Shopify Admin REST API."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        """Send a PUT request to the Shopify Admin REST API."""
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs) -> httpx.Response:
        """Send a PATCH request to the Shopify Admin REST API."""
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        """Send a DELETE request to the Shopify Admin REST API."""
        return self._request("DELETE", path, **kwargs)

    def graphql(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the Shopify Admin GraphQL API.

        Args:
            query:     GraphQL query or mutation string.
            variables: Optional dict of GraphQL variables.

        Returns:
            The parsed ``data`` dict from the GraphQL response.

        Raises:
            ShopifyAPIError: If the response body contains a GraphQL
                ``errors`` field.

        Example::

            data = shopify.graphql(\"\"\"
                query {
                  blogs(first: 5) {
                    edges { node { id title } }
                  }
                }
            \"\"\")
            for edge in data["blogs"]["edges"]:
                print(edge["node"]["title"])
        """
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        response = self._request(
            "POST",
            "graphql.json",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        body: Dict[str, Any] = response.json()

        if "errors" in body and body["errors"]:
            raise ShopifyAPIError(
                f"Shopify GraphQL API returned errors: {body['errors']}"
            )

        return body.get("data", body)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        base = self.config.admin_api_base  # no trailing slash
        path = path.lstrip("/")
        return f"{base}/{path}"

    def _auth_headers(self) -> Dict[str, str]:
        """Return a fresh auth header dict (fetches token if needed)."""
        return {"X-Shopify-Access-Token": self._manager.get_token()}

    def _request(
        self,
        method: str,
        path: str,
        *,
        _retry_on_401: bool = True,
        **kwargs,
    ) -> httpx.Response:
        """
        Core request helper.

        Merges auth headers, sends the request, handles errors, and — on
        the first 401 — invalidates the token cache and retries once.
        """
        url = self._build_url(path)
        caller_headers: Dict[str, str] = kwargs.pop("headers", {})
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

        logger.debug(
            "shopify_auth_adapter: ← HTTP %d %s", response.status_code, url
        )

        # ---- 401: token may have been revoked or rotated externally ----
        if response.status_code == 401:
            if _retry_on_401:
                logger.warning(
                    "shopify_auth_adapter: received 401 from Shopify — "
                    "invalidating token cache and retrying once"
                )
                self._manager.invalidate()
                return self._request(
                    method, path, _retry_on_401=False, **kwargs
                )
            raise ShopifyAuthenticationError(
                f"Shopify returned 401 Unauthorized for "
                f"{method.upper()} {path} even after a token refresh. "
                "Verify your client credentials and that the app is installed "
                "on the target store."
            )

        if response.status_code == 403:
            raise ShopifyAuthenticationError(
                f"Shopify returned 403 Forbidden for {method.upper()} {path}. "
                "The app may be missing required access scopes. "
                "Check the app configuration in the Shopify Dev Dashboard."
            )

        if response.status_code == 429:
            retry_after: Optional[float] = None
            raw = response.headers.get("Retry-After")
            if raw:
                try:
                    retry_after = float(raw)
                except ValueError:
                    pass
            raise ShopifyRateLimitError(
                f"Shopify rate limit hit for {method.upper()} {path} "
                f"(HTTP 429). Retry after {retry_after} seconds.",
                retry_after=retry_after,
            )

        if response.is_error:
            raise ShopifyAPIError(
                f"Shopify Admin API returned HTTP {response.status_code} "
                f"for {method.upper()} {path}. "
                f"Response (truncated): {response.text[:500]}"
            )

        return response

    def __repr__(self) -> str:
        return (
            f"ShopifyClient("
            f"shop={self.config.shop_domain!r}, "
            f"api_version={self.config.api_version!r})"
        )
