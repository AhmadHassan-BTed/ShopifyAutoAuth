"""
auth.py
=======
Core authentication logic for shopify_auth_adapter.

:class:`TokenManager` acquires Shopify Admin API access tokens using the
**OAuth 2.0 Client Credentials Grant** and caches them in-memory with
automatic refresh before expiry.

:func:`get_access_token` is the primary public API: it returns a
:class:`~shopify_auth_adapter._live_token.LiveToken` proxy that can be
assigned as a module-level constant and automatically refreshes the
underlying token when it is about to expire.

Shopify authentication mechanism
---------------------------------
As of January 1, 2026, Shopify no longer allows creating Custom Apps with
permanent ``shpat_xxx`` tokens in the store admin.  New apps created via the
**Shopify Dev Dashboard** use the **Client Credentials Grant** to obtain
access tokens programmatically.

Flow (RFC 6749 §4.4):

    POST https://{shop}.myshopify.com/admin/oauth/access_token
    Content-Type: application/x-www-form-urlencoded

    grant_type=client_credentials
    client_id={client_id}
    client_secret={client_secret}

Response::

    {
      "access_token": "f85632530bf277ec9ac6f649fc327f17",
      "scope": "write_content,read_content",
      "expires_in": 86399        # always 24 hours
    }

The token is refreshed by repeating the same request — there is no
``refresh_token`` in this flow.

Official Shopify documentation:
    https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

import httpx

from ._live_token import LiveToken
from .cache import TokenCache
from .config import ShopifyConfig
from .exceptions import (
    ShopifyAuthenticationError,
    ShopifyNetworkError,
    ShopifyRateLimitError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton manager (used by the convenience function)
# ---------------------------------------------------------------------------
_default_manager: Optional["TokenManager"] = None
_default_manager_lock: threading.Lock = threading.Lock()


# ---------------------------------------------------------------------------
# TokenManager
# ---------------------------------------------------------------------------


class TokenManager:
    """
    Manages the full lifecycle of a Shopify Admin API access token.

    * Fetches a new token on first use (or after expiry) via the
      Client Credentials Grant.
    * Caches the token in memory and reuses it until it nears expiry.
    * Implements double-checked locking so that, under high concurrency,
      exactly **one** thread performs the HTTP fetch while others wait.
    * Automatically invalidates the cache on 401 responses (handled by
      :class:`~shopify_auth_adapter.client.ShopifyClient`).

    Args:
        config: A :class:`~shopify_auth_adapter.config.ShopifyConfig`
                instance.  If ``None``, a config is constructed from
                environment variables.
        **kwargs: Convenience keyword arguments passed directly to
                  :class:`~shopify_auth_adapter.config.ShopifyConfig`
                  (e.g. ``shop=``, ``client_id=``, ``client_secret=``).
                  Ignored if *config* is provided.

    Example::

        manager = TokenManager(
            shop="my-store.myshopify.com",
            client_id="abc",
            client_secret="secret",
        )
        token: str = manager.get_token()
    """

    # httpx timeout: 10 s total, 5 s for initial connect
    _TIMEOUT: httpx.Timeout = httpx.Timeout(10.0, connect=5.0)

    def __init__(
        self,
        config: Optional[ShopifyConfig] = None,
        **kwargs,
    ) -> None:
        if config is not None:
            self.config = config
        else:
            self.config = ShopifyConfig(**kwargs)

        self.config.validate()
        self._cache: TokenCache = TokenCache()
        # Lock prevents thundering-herd: only one thread fetches when expired
        self._refresh_lock: threading.Lock = threading.Lock()

        logger.info(
            "shopify_auth_adapter: TokenManager initialised for %s (API %s)",
            self.config.shop_domain,
            self.config.api_version,
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_token(self) -> str:
        """
        Return the current valid access token as a plain ``str``.

        If the cached token is still valid it is returned immediately
        (no network call).  If the token is missing or within the
        clock-skew buffer of expiry, a new token is fetched from Shopify.

        Thread-safe.

        Returns:
            The raw Shopify access token string.

        Raises:
            ShopifyAuthenticationError: If Shopify rejects the credentials.
            ShopifyNetworkError: If the token endpoint is unreachable.
        """
        cached = self._cache.get()
        if cached is not None:
            logger.debug(
                "shopify_auth_adapter: using cached token "
                "(%.0f s remaining before proactive refresh)",
                cached.seconds_remaining(),
            )
            return cached.access_token

        # Double-checked locking: prevents multiple simultaneous fetches
        with self._refresh_lock:
            # Re-check inside the lock — another thread may have just fetched
            cached = self._cache.get()
            if cached is not None:
                return cached.access_token

            return self._fetch_and_cache()

    def get_live_token(self) -> LiveToken:
        """
        Return a :class:`~shopify_auth_adapter._live_token.LiveToken` proxy.

        The returned object is a ``str`` subclass that calls
        :meth:`get_token` every time it is encoded into bytes (i.e. every
        time it is used in an HTTP header), so it always carries the current
        valid token — even if the original token has since expired and been
        refreshed.

        Use this for module-level assignment::

            SHOPIFY_ACCESS_TOKEN = manager.get_live_token()

        Returns:
            A :class:`~shopify_auth_adapter._live_token.LiveToken` instance.
        """
        return LiveToken(self)

    def invalidate(self) -> None:
        """
        Discard the cached token.

        The next call to :meth:`get_token` (or any use of the
        :class:`~shopify_auth_adapter._live_token.LiveToken`) will trigger
        a fresh token fetch.

        Typically called by
        :class:`~shopify_auth_adapter.client.ShopifyClient` when Shopify
        returns a 401 response.
        """
        self._cache.invalidate()
        logger.info("shopify_auth_adapter: token cache invalidated")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_and_cache(self) -> str:
        """
        Perform the Client Credentials Grant HTTP request and cache the
        returned token.

        Must be called while holding ``_refresh_lock``.

        Raises:
            ShopifyAuthenticationError: 401 or 403 from Shopify.
            ShopifyNetworkError:        Network-level failure.
            ShopifyRateLimitError:      429 from Shopify.
        """
        logger.info(
            "shopify_auth_adapter: fetching new access token via "
            "Client Credentials Grant for %s",
            self.config.shop_domain,
        )

        try:
            with httpx.Client(timeout=self._TIMEOUT) as http:
                response = http.post(
                    self.config.token_endpoint,
                    # Credentials sent in the request *body*, never in the URL
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
                f"Request to Shopify token endpoint timed out "
                f"({self.config.token_endpoint}). "
                f"Check your network connection and firewall rules."
            ) from exc
        except httpx.NetworkError as exc:
            raise ShopifyNetworkError(
                f"Network error contacting Shopify token endpoint "
                f"({self.config.token_endpoint}): {exc}"
            ) from exc

        self._raise_for_auth_errors(response)

        data: dict = response.json()
        access_token: str = data.get("access_token", "")
        expires_in: int = int(data.get("expires_in", 86399))
        scopes: str = data.get("scope", "")

        if not access_token:
            raise ShopifyAuthenticationError(
                "Shopify token endpoint returned a success response but "
                "the JSON body contained no 'access_token' field. "
                f"Raw response (truncated): {response.text[:300]}"
            )

        self._cache.set(access_token, expires_in, scopes)

        logger.info(
            "shopify_auth_adapter: new token cached "
            "(scopes=%r, expires_in=%d s)",
            scopes,
            expires_in,
        )
        # Deliberately do NOT log the token itself
        return access_token

    @staticmethod
    def _raise_for_auth_errors(response: httpx.Response) -> None:
        """
        Translate Shopify HTTP error codes into typed exceptions.

        Secrets and tokens are never included in error messages.
        """
        status = response.status_code

        if status == 401:
            raise ShopifyAuthenticationError(
                "Shopify rejected the client credentials (HTTP 401). "
                "Verify that SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET "
                "are correct for the Dev Dashboard app."
            )

        if status == 403:
            raise ShopifyAuthenticationError(
                "Shopify denied access (HTTP 403). "
                "Ensure the app is installed on the target store and that "
                "the required access scopes are configured."
            )

        if status == 429:
            retry_after: Optional[float] = None
            raw = response.headers.get("Retry-After")
            if raw:
                try:
                    retry_after = float(raw)
                except ValueError:
                    pass
            raise ShopifyRateLimitError(
                f"Shopify rate limit hit on token endpoint (HTTP 429). "
                f"Retry-After: {retry_after} seconds.",
                retry_after=retry_after,
            )

        if not response.is_success:
            raise ShopifyAuthenticationError(
                f"Shopify token endpoint returned unexpected HTTP {status}. "
                f"Response (truncated): {response.text[:300]}"
            )


# ---------------------------------------------------------------------------
# Module-level convenience API
# ---------------------------------------------------------------------------


def _get_default_manager(**kwargs) -> TokenManager:
    """
    Return (or lazily create) the module-level default :class:`TokenManager`.

    If *kwargs* contains explicit values, a **new** :class:`TokenManager`
    is created with those values (useful for one-off overrides in scripts).
    Otherwise the shared singleton is returned.
    """
    global _default_manager

    if kwargs:
        # Explicit config provided — always create a new dedicated manager
        return TokenManager(**kwargs)

    with _default_manager_lock:
        if _default_manager is None:
            _default_manager = TokenManager()
        return _default_manager


def _reset_default_manager() -> None:
    """
    Reset the module-level default manager to ``None``.

    **Intended for tests only.**  Calling this in production will cause
    the next call to :func:`get_access_token` to create a new manager
    (and discard the cached token).
    """
    global _default_manager
    with _default_manager_lock:
        _default_manager = None


def get_access_token(
    shop: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    api_version: Optional[str] = None,
    *,
    live: bool = True,
) -> "LiveToken | str":
    """
    Return a Shopify Admin API access token.

    This is the primary public API of ``shopify_auth_adapter``.  It is
    designed as a drop-in replacement for a hard-coded ``shpat_xxx`` token::

        # Before (legacy permanent token — no longer possible for new apps):
        SHOPIFY_ACCESS_TOKEN = "shpat_xxxxxx"

        # After (Client Credentials Grant, auto-refreshes every 24 hours):
        from shopify_auth_adapter import get_access_token
        SHOPIFY_ACCESS_TOKEN = get_access_token()

    When ``live=True`` (the default) the returned :class:`LiveToken` proxy
    will silently re-fetch the token when it is about to expire, so long as
    your code uses ``SHOPIFY_ACCESS_TOKEN`` directly in HTTP header dicts
    rather than capturing its value into a separate variable.

    Parameters
    ----------
    shop:
        Myshopify store domain — ``"my-store"`` or
        ``"my-store.myshopify.com"``.  Falls back to the
        ``SHOPIFY_SHOP`` environment variable.
    client_id:
        OAuth client ID from the Shopify Dev Dashboard.  Falls back to
        ``SHOPIFY_CLIENT_ID``.
    client_secret:
        OAuth client secret from the Shopify Dev Dashboard.  Falls back
        to ``SHOPIFY_CLIENT_SECRET``.
        **Never hard-code this value; use an environment variable.**
    api_version:
        Shopify Admin API version (e.g. ``"2026-07"``).  Falls back to
        ``SHOPIFY_API_VERSION`` or the current stable version.
    live:
        If ``True`` (default) return a :class:`LiveToken` proxy that
        auto-refreshes.  If ``False`` return a plain ``str`` snapshot
        of the token as it is right now.

    Returns
    -------
    LiveToken | str
        A :class:`LiveToken` proxy (when ``live=True``) or a plain ``str``
        (when ``live=False``).

    Raises
    ------
    ShopifyConfigurationError
        If required configuration is missing.
    ShopifyAuthenticationError
        If Shopify rejects the credentials on first use.
    ShopifyNetworkError
        If the token endpoint is unreachable on first use.

    Examples
    --------
    Simplest usage (all config from environment variables)::

        from shopify_auth_adapter import get_access_token

        SHOPIFY_ACCESS_TOKEN = get_access_token()

        headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
        response = requests.get(
            "https://my-store.myshopify.com/admin/api/2026-07/blogs.json",
            headers=headers,
        )

    With explicit arguments::

        SHOPIFY_ACCESS_TOKEN = get_access_token(
            shop="my-store.myshopify.com",
            client_id="abc123",
            client_secret="super-secret",
        )
    """
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

    manager = _get_default_manager(**kwargs)
    return manager.get_live_token() if live else manager.get_token()
