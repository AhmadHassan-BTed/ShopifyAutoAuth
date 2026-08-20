<div align="center">

# shopify_auth_adapter

### Enterprise-Grade Shopify OAuth 2.0 Client Credentials Adapter

*A zero-friction, production-hardened bridge connecting legacy Shopify applications to modern Client Credentials Grant authentication.*

[![CI Status](https://img.shields.io/github/actions/workflow/status/AhmadHassan-BTed/ShopifyAutoAuth/ci.yml?branch=main&style=for-the-badge&logo=github&label=CI)](https://github.com/AhmadHassan-BTed/ShopifyAutoAuth/actions)
[![PyPI Version](https://img.shields.io/pypi/v/shopify-auth-adapter?style=for-the-badge&logo=pypi&color=2b6cb0)](https://pypi.org/project/shopify-auth-adapter/)
[![Python Versions](https://img.shields.io/pypi/pyversions/shopify-auth-adapter?style=for-the-badge&logo=python)](https://pypi.org/project/shopify-auth-adapter/)
[![License](https://img.shields.io/github/license/AhmadHassan-BTed/ShopifyAutoAuth?style=for-the-badge&color=319795)](LICENSE)
[![Maintainer](https://img.shields.io/badge/Maintainer-Ahmad%20Hassan%20(B--Ted)-8a2be2?style=for-the-badge)](https://github.com/AhmadHassan-BTed)

---

</div>

## 🌐 Overview & Human Purpose

Following Shopify's mandatory authentication migration on **January 1, 2026**, static `shpat_xxx` custom app tokens were deprecated in favor of **OAuth 2.0 Client Credentials Grant** short-lived access tokens (RFC 6749 §4.4).

`shopify_auth_adapter` was engineered by **Ahmad Hassan (B-Ted)** to resolve the operational burden this change placed on development teams. Rather than requiring extensive refactoring of HTTP request headers or complex token lifecycle loops across codebase backends, this library provides an automated, thread-safe proxy layer.

Existing applications maintain static variable assignment syntax (`SHOPIFY_ACCESS_TOKEN = get_access_token()`), while under the hood, tokens are lazily acquired, cached in volatile RAM, and refreshed prior to expiration without runtime interruption.

---

## ⚡ Feature Matrix

| Domain | Capability | Architectural Mechanism |
| :--- | :--- | :--- |
| **Authentication** | OAuth 2.0 Client Credentials Grant | Automatic `POST /admin/oauth/access_token` exchange for Dev Dashboard apps. |
| **Concurrency** | Thundering Herd Protection | Re-entrant `threading.RLock` double-checked locking mechanism. |
| **Resilience** | Clock-Skew Mitigation | 300-second (5-minute) proactive expiration cutoff buffer. |
| **Header Integration**| Transparent `LiveToken` Proxy | Custom `str` subclass executing JIT encoding delegation during HTTP header resolution. |
| **Client Abstraction**| High-Level `ShopifyClient` | Integrated REST & GraphQL client with automatic 401 cache-invalidation and single retry. |
| **Security** | Zero Credential Leak Guarantee | String masking on `repr`, `str`, and tracebacks (`LiveToken(<masked>)`). |

---

## 🏛️ System Architecture & Domain Boundaries

The codebase follows domain-driven modularity principles with contract-based interfaces (`Protocol`) to guarantee zero coupling and total separation of concerns.

```mermaid
graph TD
    subgraph Client Application Layer
        App[Application Codebase]
        Env[Environment / .env File]
    end

    subgraph shopify_auth_adapter Package Domain
        Facade[shopify_auth_adapter Facade]
        Config[Core Domain: ShopifyConfig]
        Proxy[Auth Domain: LiveToken Proxy]
        Manager[Auth Domain: TokenManager]
        Cache[Cache Domain: InMemoryTokenCache]
        Provider[Auth Domain: OAuth2ClientCredentialsProvider]
        Client[Client Domain: ShopifyClient]
    end

    subgraph External Infrastructure
        ShopifyAuth[Shopify OAuth Endpoint]
        ShopifyAPI[Shopify Admin API Endpoint]
    end

    Env -->|Loads Config| Config
    App -->|1. Request Token| Facade
    Facade -->|Instantiates| Manager
    Manager -->|Injects Config & Cache| Provider
    
    App -->|2. Assigns Token| Proxy
    Proxy -->|3. Delegated .encode()| Manager
    Manager -->|4. Query Cache| Cache

    alt Token Missing or Expired
        Manager -->|5. Double-Checked Lock| Provider
        Provider -->|6. POST Credentials| ShopifyAuth
        ShopifyAuth -->> Provider: 200 OK (access_token, 86399s)
        Provider -->> Manager: Token Tuple
        Manager -->|7. Update Entry| Cache
    end

    App -->|8. Execute REST/GraphQL| Client
    Client -->|Attach Auth Header| Proxy
    Client -->|9. HTTP Request| ShopifyAPI
```

---

## 🔄 Request Lifecycle & Token Resolution

The diagram below illustrates the exact sequence executed when an HTTP request header formats the `LiveToken` string proxy:

```mermaid
sequenceDiagram
    autonumber
    participant Client as Application / HTTP Client (httpx/requests)
    participant Proxy as LiveToken Proxy
    participant Manager as TokenManager
    participant Cache as InMemoryTokenCache
    participant Provider as OAuth2ClientCredentialsProvider
    participant Shopify as Shopify OAuth Server

    Client->>Proxy: encode("latin-1") triggered during header formatting
    Proxy->>Manager: get_token()
    Manager->>Cache: get()
    
    alt Valid Cached Entry Found
        Cache-->>Manager: CachedToken Entry
    else Entry Expired or Absent
        Manager->>Manager: Acquire _refresh_lock (Double-Checked Lock)
        Manager->>Cache: get() [Second Check]
        alt Fetched by Concurrent Thread
            Cache-->>Manager: CachedToken Entry
        else Fetch Required
            Manager->>Provider: fetch_token()
            Provider->>Shopify: POST /admin/oauth/access_token
            Shopify-->>Provider: 200 OK {access_token, expires_in, scope}
            Provider-->>Manager: (access_token, expires_in, scope)
            Manager->>Cache: set(access_token, expires_in, scope)
        end
    end
    
    Manager-->>Proxy: Raw Token String
    Proxy-->>Client: UTF-8 / Latin-1 Encoded Token Bytes
```

---

## 📁 Repository Structure

```
shopify_auth_adapter_pkg/
├── .github/                       # GitHub Actions workflows & community templates
│   ├── ISSUE_TEMPLATE/            # Structured issue forms (bug_report.yml, etc.)
│   ├── workflows/                 # CI/CD pipelines (ci.yml, release.yml, security.yml)
│   ├── dependabot.yml             # Weekly dependency update configuration
│   └── PULL_REQUEST_TEMPLATE.md   # Standardized pull request template
├── docs/                          # In-depth technical documentation
│   ├── architecture.md            # Domain layout & Mermaid sequence diagrams
│   ├── system-design.md           # Token lifecycle, clock skew & locking mechanics
│   ├── security-architecture.md   # Security model & credential masking rules
│   └── api-reference.md           # Complete public Python API specification
├── shopify_auth_adapter/          # Primary Python package
│   ├── __init__.py                # Package facade (100% backward compatible)
│   ├── py.typed                   # PEP 561 static type marker
│   ├── core/                      # Core domain (config, constants, exceptions, protocols)
│   ├── cache/                     # Cache domain (model, memory cache implementation)
│   ├── auth/                      # Auth domain (OAuth2 provider, manager, LiveToken proxy)
│   └── client/                    # Client domain (ShopifyClient REST/GraphQL helper)
├── tests/                         # Test suite
│   ├── conftest.py                # Global pytest fixtures and mocks
│   ├── unit/                      # Unit tests grouped by domain module
│   └── integration/               # End-to-end integration tests
├── .editorconfig                  # Code formatting guidelines across editors
├── .env.example                   # Environment configuration template
├── .gitattributes                 # Git text normalization and path attributes
├── .gitignore                     # Minimal tracking exclusion rules
├── CHANGELOG.md                   # Keep a Changelog release history
├── CODE_OF_CONDUCT.md             # Contributor Covenant Code of Conduct
├── CONTRIBUTING.md                # Development setup & contributor guidelines
├── Dockerfile                     # Multi-stage container build file
├── docker-compose.yml             # Local docker development environment
├── LICENSE                        # MIT License
├── Makefile                       # Standardized command shortcuts
├── pyproject.toml                 # Packaging & tool configurations (hatchling, ruff, mypy)
├── ROADMAP.md                     # Project strategic goals
└── SUPPORT.md                     # Community help & support guidance
```

---

## 🚀 Usage Examples

### 1. Drop-In Helper (`get_access_token`)

`get_access_token()` requires no explicit parameters when environment variables are set:

```python
from shopify_auth_adapter import get_access_token

# Environment variables automatically parsed:
# SHOPIFY_SHOP, SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET

SHOPIFY_ACCESS_TOKEN = get_access_token()

# Standard HTTP request (token auto-refreshes before expiry):
headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
```

### 2. High-Level `ShopifyClient`

`ShopifyClient` handles URL construction, header attachment, and 401 error retries:

```python
from shopify_auth_adapter import ShopifyClient

client = ShopifyClient()

# REST Admin API
blogs = client.get("/blogs.json").json()["blogs"]

# GraphQL Admin API
query = """
query {
    shop {
        name
        email
    }
}
"""
shop_data = client.graphql(query)
```

---

## 🔍 Technical Deep Dives

<details>
<summary><b>⏱️ Clock-Skew Math & Expiration Buffer</b></summary>

<br />

Shopify Client Credentials Grant tokens carry a fixed duration of **86,399 seconds (~24 hours)**.

To prevent edge cases where a token is valid when read from cache but expires while in flight across the network, the expiration cutoff is calculated as:

$$\text{Cutoff} = T_{\text{expires\_at}} - 300\text{ seconds}$$

Any token within 5 minutes of expiration is treated as invalid, forcing a fresh token fetch prior to request dispatch.
</details>

<details>
<summary><b>🔒 Security Invariants & Token Masking</b></summary>

<br />

Credentials and raw access tokens are strictly protected against unintentional exposure in logs, error reports, and inspection tools:

- `repr(LiveToken)` returns `"LiveToken(<masked>)"`.
- `repr(ShopifyConfig)` outputs `client_secret=<redacted>`.
- `repr(CachedToken)` outputs `access_token=<redacted>`.
- Exception messages exclude credential strings under all circumstances.
</details>

<details>
<summary><b>🛠️ Development & Tooling Shortcuts</b></summary>

<br />

Common developer tasks are managed via the project `Makefile`:

```bash
# Install editable package with dev tools
make install

# Run linter and type checks
make lint
make typecheck

# Run full test suite with coverage
make test
```
</details>

---

## 🛠️ Build & CI/CD Pipeline

The project utilizes GitHub Actions for continuous quality verification and release automation:

```mermaid
flowchart LR
    Push[Code Push / Tag] --> Lint[Ruff Linter]
    Push --> TypeCheck[Mypy Strict Check]
    Push --> Test[Pytest Matrix 3.10-3.13]
    
    Lint --> Build[Hatchling Build]
    TypeCheck --> Build
    Test --> Build

    Build -->|Tag Push v*| OIDC[PyPI Trusted Publisher OIDC]
    OIDC --> PyPI[Publish to PyPI Registry]
```

---

## 🤝 Maintainer & Community

`shopify_auth_adapter` is maintained by **Ahmad Hassan (B-Ted)**.

Contributions from the open-source community are welcomed. Please review [CONTRIBUTING.md](CONTRIBUTING.md) for development setup instructions and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.

For security concerns, refer to the disclosure process in [SECURITY.md](SECURITY.md).

---

## 📄 License

This project is licensed under the terms of the [MIT License](LICENSE).
