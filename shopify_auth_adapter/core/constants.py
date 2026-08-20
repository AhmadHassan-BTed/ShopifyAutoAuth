"""
core.constants
==============
System-wide constants and default configurations for shopify_auth_adapter.
"""

from __future__ import annotations

# Latest stable Shopify Admin API version as of August 2026.
# Released July 1, 2026. Update when Shopify releases a newer stable version.
# Reference: https://shopify.dev/docs/api/usage/versioning
CURRENT_API_VERSION: str = "2026-07"

# Proactive token refresh margin in seconds (5 minutes).
# Prevents token expiration during transit or near-boundary execution.
CLOCK_SKEW_BUFFER_SECONDS: int = 300

# Default HTTP timeout for Shopify Admin API requests (30s overall, 10s connect)
DEFAULT_HTTP_TIMEOUT_SECONDS: float = 30.0
DEFAULT_CONNECT_TIMEOUT_SECONDS: float = 10.0

# Default HTTP timeout for token acquisition requests (10s overall, 5s connect)
DEFAULT_AUTH_TIMEOUT_SECONDS: float = 10.0
DEFAULT_AUTH_CONNECT_TIMEOUT_SECONDS: float = 5.0
