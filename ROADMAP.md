# Project Roadmap

This document outlines the strategic vision and upcoming milestones for `shopify_auth_adapter`.

---

## 🎯 Current Milestone: v1.0.0 (Production Stable)

- [x] Full OAuth 2.0 Client Credentials Grant implementation.
- [x] In-memory thread-safe token caching with clock-skew buffer protection.
- [x] High-level REST and GraphQL `ShopifyClient`.
- [x] Enterprise domain-driven architecture & PEP 561 typing.
- [x] Community governance, CI/CD, and security policy.

---

## 🚀 Near-Term Goals (v1.1.0)

- [ ] **Async Support (`asyncio`)**: Provide native `AsyncShopifyClient` and `AsyncTokenManager` using `httpx.AsyncClient`.
- [ ] **Custom Cache Backends**: Provide plugin interface and built-in implementations for external distributed caches (e.g., Redis, Memcached) for multi-process deployments.
- [ ] **Metrics Hooks**: Provide optional callbacks/hooks for Prometheus / OpenTelemetry telemetry on token refreshes and rate limits.

---

## 🔭 Future Horizons (v2.0.0)

- [ ] Multi-store credential vault manager for SaaS applications handling hundreds of Shopify stores concurrently.
- [ ] Automated Webhook secret verification helpers.
