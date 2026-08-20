# Security Architecture & Masking Model

This document outlines the security invariants and credential protection mechanisms implemented across `shopify_auth_adapter`.

---

## 🔒 Core Security Invariants

### 1. Zero Credential Leakage in Logs & Tracebacks
Neither client secrets nor access tokens are ever rendered in plain text by `__repr__`, `__str__`, or exception messages.

- `ShopifyConfig.__repr__`:
  ```python
  ShopifyConfig(shop='my-store.myshopify.com', client_id='abc', client_secret=<redacted>, api_version='2026-07')
  ```
- `CachedToken.__repr__`:
  ```python
  CachedToken(access_token=<redacted>, expires_at=2026-08-21T12:00:00+00:00, scopes='read_products')
  ```
- `LiveToken.__repr__`:
  ```python
  LiveToken(<masked>)
  ```

### 2. In-Memory Token Lifetime Security
Access tokens are retained exclusively in volatile system RAM (`InMemoryTokenCache`). Tokens are never serialized, written to disk, or stored in temp files.

### 3. Strict TLS/HTTPS Transport
All HTTP requests for token acquisition and Admin API operations enforce TLS (HTTPS). Certificate validation is mandatory and cannot be disabled.

### 4. Credential Isolation
Credentials (`client_secret`, `access_token`) are transmitted exclusively in HTTP POST request bodies or `X-Shopify-Access-Token` request headers. Credentials are never placed in URL query parameters.
