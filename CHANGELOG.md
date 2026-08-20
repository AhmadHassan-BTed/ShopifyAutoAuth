# Changelog

All notable changes to `shopify_auth_adapter` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-20

### Added
- Enterprise production-grade refactoring with clean domain separation (`core`, `cache`, `auth`, `client`).
- Explicit protocol interfaces (`TokenCacheProtocol`, `AuthProviderProtocol`, `TokenManagerProtocol`) for dependency inversion.
- `ShopifyConfig` with automated environment configuration and validation.
- Thread-safe `InMemoryTokenCache` with double-checked locking and clock-skew margin protection (300 seconds buffer).
- `OAuth2ClientCredentialsProvider` implementing Shopify's OAuth 2.0 Client Credentials Grant endpoint call.
- Transparent `LiveToken` string proxy pattern that auto-refreshes headers without breaking static token assignment semantics.
- `ShopifyClient` high-level REST & GraphQL client with automatic 401 cache-invalidation and single retry loop.
- Full PEP 561 typing support (`py.typed`).
- GitHub Actions CI/CD, Dependabot, Pre-commit hooks, Docker containerization, and Makefile tooling.
- Complete documentation suite (`docs/architecture.md`, `docs/system-design.md`, `docs/security-architecture.md`, `docs/api-reference.md`).
