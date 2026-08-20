# System Design & Implementation Mechanics

This document provides a deep technical explanation of the token lifecycle mechanics, concurrency safety, and clock-skew mitigation strategies employed by `shopify_auth_adapter`.

---

## ⚡ Concurrency & Double-Checked Locking

Under heavy multi-threaded workloads (e.g. web servers handling hundreds of concurrent requests), multiple threads may detect an expired token simultaneously. Without protection, this creates a **thundering herd problem**, where multiple threads perform redundant HTTP requests to Shopify's token endpoint.

`shopify_auth_adapter` solves this using **Double-Checked Locking**:

```python
def get_token(self) -> str:
    # First check (lock-free)
    cached = self._cache.get()
    if cached is not None:
        return cached.access_token

    # Acquire lock for refresh
    with self._refresh_lock:
        # Second check inside lock (another thread may have refreshed while we waited)
        cached = self._cache.get()
        if cached is not None:
            return cached.access_token

        # Exactly ONE thread fetches from network
        return self._fetch_and_cache()
```

---

## ⏰ Clock-Skew Buffer Protection

Shopify Client Credentials Grant access tokens have a fixed lifetime of **86,399 seconds (24 hours)**. 

To prevent edge cases where a token is valid when read from cache but expires while the HTTP request is in transit across the network, `shopify_auth_adapter` enforces a **300-second (5-minute) proactive clock-skew buffer**:

$$\text{Expiration Cutoff} = T_{\text{expires\_at}} - 300\text{ seconds}$$

Any token whose remaining lifespan falls below 300 seconds is automatically treated as expired, triggering a background refresh before application requests fail.

---

## 🔄 Automatic 401 Cache Invalidation & Retry

If Shopify invalidates or rotates credentials out-of-band, an existing cached token will receive an **HTTP 401 Unauthorized** response from Shopify Admin API.

`ShopifyClient` handles this transparently:

1. Detects `HTTP 401 Unauthorized`.
2. Calls `TokenManager.invalidate()` to clear the cache.
3. Automatically executes a single retry request with a freshly acquired token.
4. If the retry also fails with 401, raises `ShopifyAuthenticationError`.
