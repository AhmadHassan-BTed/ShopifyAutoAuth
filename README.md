<div align="center">

<img src="https://raw.githubusercontent.com/AhmadHassan-BTed/ShopifyAutoAuth/main/docs/assets/banner-16-9.png" alt="ShopifyAutoAuth Banner" width="100%">

<h1 align="center">ShopifyAutoAuth</h1>

<h3 align="center">Enterprise-Grade Shopify OAuth 2.0 Client Credentials Adapter</h3>

<p align="center">
  <em>A zero-friction, production-hardened bridge connecting legacy Shopify applications to modern Client Credentials Grant authentication.</em>
</p>

[![CI Status](https://img.shields.io/github/actions/workflow/status/AhmadHassan-BTed/ShopifyAutoAuth/ci.yml?branch=main&style=for-the-badge&logo=github&label=CI)](https://github.com/AhmadHassan-BTed/ShopifyAutoAuth/actions)
[![PyPI Version](https://img.shields.io/pypi/v/shopify-auth-adapter?style=for-the-badge&logo=pypi&color=2b6cb0)](https://pypi.org/project/shopify-auth-adapter/)
[![Python Versions](https://img.shields.io/pypi/pyversions/shopify-auth-adapter?style=for-the-badge&logo=python)](https://pypi.org/project/shopify-auth-adapter/)
[![License](https://img.shields.io/github/license/AhmadHassan-BTed/ShopifyAutoAuth?style=for-the-badge&color=319795)](LICENSE)
[![Maintainer](https://img.shields.io/badge/Maintainer-Ahmad%20Hassan%20(B--Ted)-8a2be2?style=for-the-badge)](https://github.com/AhmadHassan-BTed)

---

</div>

## Overview

Following Shopify's mandatory authentication migration on **January 1, 2026**, static `shpat_xxx` custom app tokens were deprecated in favor of **OAuth 2.0 Client Credentials Grant** short-lived access tokens (RFC 6749 §4.4).

`shopify_auth_adapter` provides a transparent authentication proxy. Existing applications can preserve their variable assignment patterns while under the hood tokens are acquired, cached in volatile RAM, and refreshed prior to expiration without runtime interruption.

### Migration: Before vs After

```python
# BEFORE (Deprecated static token):
SHOPIFY_ACCESS_TOKEN = "shpat_xxxxxxxxxxxxxxxxxxxxxxxx"

# AFTER (Automatic OAuth 2.0 token with auto-refresh):
from shopify_auth_adapter import get_access_token

SHOPIFY_ACCESS_TOKEN = get_access_token()
```

---

## Quick Start

> 📘 For framework integration examples (FastAPI, Flask, Celery) and detailed error handling, see the **[Developer & Integration Guide](docs/usage-guide.md)**.

### Installation

```bash
pip install shopify-auth-adapter
```

### Setting Up Credentials

You can supply your Shopify Dev Dashboard credentials in **any of 3 ways**:

#### Option A: In a `.env` file (Recommended for Local Dev)
Create a `.env` file in your project root:
```env
SHOPIFY_SHOP=your-store.myshopify.com
SHOPIFY_CLIENT_ID=your_client_id
SHOPIFY_CLIENT_SECRET=your_client_secret
```

#### Option B: Environment Variables (Production / Docker / Cloud)
Set variables in your terminal or deployment environment:
```bash
export SHOPIFY_SHOP="your-store.myshopify.com"
export SHOPIFY_CLIENT_ID="your_client_id"
export SHOPIFY_CLIENT_SECRET="your_client_secret"
```

#### Option C: Pass Directly in Python Code
```python
from shopify_auth_adapter import get_access_token

token = get_access_token(
    shop="your-store.myshopify.com",
    client_id="your_client_id",
    client_secret="your_client_secret",
)
```

---

### Testing Credentials

You can verify your Dev Dashboard credentials and store connection instantly by running the included tester script:

```bash
python examples/test_credentials.py
```

---

### Usage Examples

#### 1. Drop-In Token Helper

```python
import httpx

from shopify_auth_adapter import get_access_token

# Automatically reads credentials from .env or environment variables:
headers = {"X-Shopify-Access-Token": get_access_token()}
response = httpx.get(
    "https://your-store.myshopify.com/admin/api/2026-07/shop.json",
    headers=headers,
)
```

#### 2. High-Level Shopify Client

```python
from shopify_auth_adapter import ShopifyClient

# Automatically attaches tokens and retries on 401:
client = ShopifyClient()

# REST API call
blogs = client.get("/blogs.json").json()["blogs"]

# GraphQL API call
shop_info = client.graphql("""
    query {
        shop {
            name
            email
        }
    }
""")
```

---

## Feature Matrix

| Domain | Capability | Architectural Mechanism |
| :--- | :--- | :--- |
| **Authentication** | OAuth 2.0 Client Credentials Grant | Automatic `POST /admin/oauth/access_token` exchange for Dev Dashboard apps. |
| **Concurrency** | Thundering Herd Protection | Re-entrant `threading.RLock` double-checked locking mechanism. |
| **Resilience** | Clock-Skew Mitigation | 300-second (5-minute) proactive expiration cutoff buffer. |
| **Header Integration**| Transparent `LiveToken` Proxy | Custom `str` subclass executing JIT encoding delegation during HTTP header resolution. |
| **Client Abstraction**| High-Level `ShopifyClient` | Integrated REST & GraphQL client with automatic 401 cache-invalidation and single retry. |
| **Security** | Zero Credential Leak Guarantee | String masking on `repr`, `str`, and tracebacks (`LiveToken(<masked>)`). |

---

## System Architecture & Domain Boundaries

The codebase follows domain-driven modularity principles with contract-based interfaces (`Protocol`) to guarantee zero coupling and total separation of concerns.

```mermaid
flowchart TD
    subgraph AppLayer["Client Application Layer"]
        App["Application Codebase"]
        Env["Environment Config (.env)"]
    end

    subgraph PkgDomain["shopify_auth_adapter Package"]
        Facade["API Facade"]
        Config["ShopifyConfig"]
        Proxy["LiveToken Proxy"]
        Manager["TokenManager"]
        Cache["InMemoryTokenCache"]
        Provider["OAuth2ClientCredentialsProvider"]
        Client["ShopifyClient"]
    end

    subgraph ExtInfra["External Infrastructure"]
        ShopifyAuth["Shopify OAuth Endpoint"]
        ShopifyAPI["Shopify Admin API"]
    end

    Env --> Config
    App --> Facade
    Facade --> Manager
    Manager --> Provider
    
    App --> Proxy
    Proxy --> Manager
    Manager --> Cache
    Manager --> Provider
    Provider --> ShopifyAuth

    App --> Client
    Client --> Proxy
    Client --> ShopifyAPI
```

---

## Request Lifecycle & Token Resolution

The diagram below illustrates the exact sequence executed when an HTTP request header formats the `LiveToken` string proxy:

```mermaid
sequenceDiagram
    autonumber
    participant App as Client Application
    participant Proxy as LiveToken Proxy
    participant Manager as TokenManager
    participant Cache as InMemoryTokenCache
    participant Provider as OAuth2Provider
    participant Shopify as Shopify Server

    App->>Proxy: Header resolution (.encode)
    Proxy->>Manager: get_token()
    Manager->>Cache: get()
    
    alt Cache Hit (Valid Token)
        Cache-->>Manager: CachedToken
    else Cache Miss / Expired
        Manager->>Manager: Acquire Lock
        Manager->>Provider: fetch_token()
        Provider->>Shopify: POST /admin/oauth/access_token
        Shopify-->>Provider: 200 OK Token Response
        Provider-->>Manager: access_token
        Manager->>Cache: set()
    end
    
    Manager-->>Proxy: access_token string
    Proxy-->>App: Encoded Token Bytes
```

---

## Repository Structure

```
ShopifyAutoAuth/
├── src/
│   └── shopify_auth_adapter/      # Primary Python package
│       ├── auth/                  # OAuth2 provider, token manager, LiveToken proxy
│       ├── cache/                 # In-memory token cache implementation
│       ├── client/                # ShopifyClient REST and GraphQL helper
│       └── core/                  # Configuration, constants, exceptions, protocols
├── docs/                          # In-depth technical documentation
├── tests/                         # Unit and integration test suite
├── .github/                       # GitHub Actions workflows & community templates
├── pyproject.toml                 # Packaging & tool configurations
└── README.md                      # Project overview & documentation
```

---

## Technical Deep Dives

<details>
<summary><b>Clock-Skew Math & Expiration Buffer</b></summary>

<br />

Shopify Client Credentials Grant tokens carry a fixed duration of **86,399 seconds (~24 hours)**.

To prevent edge cases where a token is valid when read from cache but expires while in flight across the network, the expiration cutoff is calculated as:

$$\text{Cutoff} = T_{\text{expiry}} - 300\text{ seconds}$$

Any token within 5 minutes of expiration is treated as invalid, forcing a fresh token fetch prior to request dispatch.
</details>

<details>
<summary><b>Security Invariants & Token Masking</b></summary>

<br />

Credentials and raw access tokens are strictly protected against unintentional exposure in logs, error reports, and inspection tools:

- `repr(LiveToken)` returns `"LiveToken(<masked>)"`.
- `repr(ShopifyConfig)` outputs `client_secret=<redacted>`.
- `repr(CachedToken)` outputs `access_token=<redacted>`.
- Exception messages exclude credential strings under all circumstances.
</details>

<details>
<summary><b>Development & Tooling Shortcuts</b></summary>

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

## Build & CI/CD Pipeline

The project utilizes GitHub Actions for continuous quality verification and release automation:

```mermaid
flowchart LR
    Push["Code Push / Tag"] --> Lint["Ruff Linter"]
    Push --> TypeCheck["Mypy Strict Check"]
    Push --> Test["Pytest Suite"]
    
    Lint --> Build["Hatchling Build"]
    TypeCheck --> Build
    Test --> Build

    Build --> PyPI["Publish to PyPI Registry"]
```

---

## License

This project is licensed under the terms of the [MIT License](LICENSE).

---

<div align="center">

**Engineered by Ahmad Hassan (B-Ted)**

[GitHub Profile](https://github.com/AhmadHassan-BTed) • [PyPI Package](https://pypi.org/project/shopify-auth-adapter/) • [LinkedIn](https://www.linkedin.com/in/ahmad-hassan-52ab4225b/)

</div>
