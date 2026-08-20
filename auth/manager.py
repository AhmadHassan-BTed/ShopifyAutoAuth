"""
auth.manager
============
Thread-safe TokenManager implementing double-checked locking token refresh lifecycle.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from auth.provider import OAuth2ClientCredentialsProvider
from auth.proxy import LiveToken
from cache.memory import InMemoryTokenCache
from core.config import ShopifyConfig
from core.protocols import (
    AuthProviderProtocol,
    TokenCacheProtocol,
    TokenManagerProtocol,
)

logger = logging.getLogger(__name__)

# Module-level singleton default manager
_default_manager: TokenManager | None = None
_default_manager_lock: threading.Lock = threading.Lock()


class TokenManager(TokenManagerProtocol):
    """
    Manages access token lifecycle:
    - Checks cache for valid token.
    - Uses double-checked locking under high concurrency to prevent thundering herd calls.
    - Delegates HTTP token acquisition to AuthProviderProtocol.
    """

    def __init__(
        self,
        config: ShopifyConfig | None = None,
        cache: TokenCacheProtocol | None = None,
        provider: AuthProviderProtocol | None = None,
        **kwargs: Any,
    ) -> None:
        if config is not None:
            self.config = config
        else:
            self.config = ShopifyConfig(**kwargs)

        self.config.validate()

        self._cache: TokenCacheProtocol = cache or InMemoryTokenCache()
        self._provider: AuthProviderProtocol = (
            provider or OAuth2ClientCredentialsProvider(self.config)
        )
        self._refresh_lock: threading.Lock = threading.Lock()

        logger.info(
            "shopify_auth_adapter: TokenManager initialized for store %s (API version %s)",
            self.config.shop_domain,
            self.config.api_version,
        )

    def get_token(self) -> str:
        """
        Return current valid access token. Performs network fetch if token is expired or absent.
        """
        cached = self._cache.get()
        if cached is not None:
            logger.debug(
                "shopify_auth_adapter: using cached token (%.0f s remaining)",
                cached.seconds_remaining(),
            )
            return cached.access_token

        # Double-checked locking
        with self._refresh_lock:
            cached = self._cache.get()
            if cached is not None:
                return cached.access_token

            return self._fetch_and_cache()

    def get_live_token(self) -> LiveToken:
        """Return a LiveToken proxy bound to this manager."""
        return LiveToken(self)

    def invalidate(self) -> None:
        """Discard currently cached token entry."""
        self._cache.invalidate()
        logger.info("shopify_auth_adapter: token cache invalidated")

    def _fetch_and_cache(self) -> str:
        token, expires_in, scopes = self._provider.fetch_token()
        self._cache.set(token, expires_in, scopes)
        logger.info(
            "shopify_auth_adapter: new access token acquired and cached (expires_in=%ds, scopes=%r)",
            expires_in,
            scopes,
        )
        return token


def _get_default_manager(**kwargs: Any) -> TokenManager:
    """Return (or lazily create) the default singleton TokenManager."""
    global _default_manager

    if kwargs:
        return TokenManager(**kwargs)

    with _default_manager_lock:
        if _default_manager is None:
            _default_manager = TokenManager()
        return _default_manager


def _reset_default_manager() -> None:
    """Reset default TokenManager singleton (used for tests)."""
    global _default_manager
    with _default_manager_lock:
        _default_manager = None


def get_access_token(
    shop: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    api_version: str | None = None,
    *,
    live: bool = True,
) -> LiveToken | str:
    """
    Public entrypoint to retrieve a Shopify access token or LiveToken proxy.
    """
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

    manager = _get_default_manager(**kwargs)
    return manager.get_live_token() if live else manager.get_token()
