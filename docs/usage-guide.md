# ShopifyAutoAuth — User Integration & Developer Guide

*A complete step-by-step guide for integrating `shopify_auth_adapter` into Python applications, web frameworks, and background workers.*

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuring Credentials](#configuring-credentials)
5. [Core Usage Patterns](#core-usage-patterns)
   - [Pattern 1: Drop-In Token Helper](#pattern-1-drop-in-token-helper)
   - [Pattern 2: High-Level ShopifyClient (REST & GraphQL)](#pattern-2-high-level-shopifyclient-rest--graphql)
6. [Framework Integration Examples](#framework-integration-examples)
   - [FastAPI](#fastapi)
   - [Flask](#flask)
   - [Celery / Background Tasks](#celery--background-tasks)
7. [Error Handling & Resilience](#error-handling--resilience)
8. [Logging & Debugging](#logging--debugging)
9. [Verifying Connection](#verifying-connection)

---

## ⚡ The 1-Line Solution

To upgrade any Python application to Shopify's modern OAuth 2.0 authentication, replace your old `shpat_xxx` string with **`get_access_token()`**:

```python
from shopify_auth_adapter import get_access_token

SHOPIFY_ACCESS_TOKEN = get_access_token()
```

That's it! Everything else (fetching tokens via OAuth 2.0, storing in RAM, auto-refreshing before 24-hour expiration) happens automatically.

---

## Prerequisites

- **Python**: Version 3.10, 3.11, 3.12, or 3.13.
- **Shopify Dev Dashboard App**: An app created in your Shopify Partner / Dev Dashboard with **Client Credentials Grant** enabled.
- **App Credentials**:
  - `SHOPIFY_SHOP`: Your store domain (e.g., `my-store.myshopify.com`).
  - `SHOPIFY_CLIENT_ID`: Found on your app settings page.
  - `SHOPIFY_CLIENT_SECRET`: Found on your app settings page.

---

## Installation

Install the package directly from PyPI via `pip`:

```bash
pip install shopify-auth-adapter
```

If you plan to use `.env` files for local development, install with the optional `dotenv` extra:

```bash
pip install "shopify-auth-adapter[dotenv]"
```

---

## Configuring Credentials

You can supply your Shopify credentials in **any of 3 ways**:

### Option A: `.env` File (Recommended for Local Development)
Create a `.env` file in your project root directory:

```env
SHOPIFY_SHOP=my-store.myshopify.com
SHOPIFY_CLIENT_ID=19aa0d16dbac4e89d2dde9c3d47107ab
SHOPIFY_CLIENT_SECRET=shpss_xxxxxxxxxxxxxxxxxxxxxxxx
```

### Option B: Environment Variables (Recommended for Production / Cloud / Docker)
Set environment variables in your server environment:

```bash
export SHOPIFY_SHOP="my-store.myshopify.com"
export SHOPIFY_CLIENT_ID="19aa0d16dbac4e89d2dde9c3d47107ab"
export SHOPIFY_CLIENT_SECRET="shpss_xxxxxxxxxxxxxxxxxxxxxxxx"
```

### Option C: Pass Directly in Python Code
Pass parameters directly when calling functions or instantiating clients:

```python
from shopify_auth_adapter import get_access_token

token = get_access_token(
    shop="my-store.myshopify.com",
    client_id="19aa0d16dbac4e89d2dde9c3d47107ab",
    client_secret="shpss_xxxxxxxxxxxxxxxxxxxxxxxx",
)
```

---

## Core Usage Patterns

### Pattern 1: Drop-In Token Helper

Use `get_access_token()` to obtain a live token string proxy that automatically attaches to any HTTP library (`httpx`, `requests`, `aiohttp`, `urllib3`):

```python
import httpx
from shopify_auth_adapter import get_access_token

# Transparently fetches and refreshes tokens before expiration:
headers = {"X-Shopify-Access-Token": get_access_token()}

response = httpx.get(
    "https://my-store.myshopify.com/admin/api/2026-07/shop.json",
    headers=headers,
)

print(response.json())
```

### Pattern 2: High-Level ShopifyClient (REST & GraphQL)

`ShopifyClient` provides a high-level wrapper with automatic header injection and single 401 retry resilience:

```python
from shopify_auth_adapter import ShopifyClient

client = ShopifyClient()

# REST API GET Request
products = client.get("/products.json").json()["products"]

# REST API POST Request
new_product = client.post(
    "/products.json",
    json={
        "product": {
            "title": "New Collection Item",
            "vendor": "Scentspired",
        }
    },
).json()

# GraphQL Query
graphql_response = client.graphql("""
    query {
        shop {
            name
            email
            domain
        }
    }
""")

print(graphql_response["data"]["shop"])
```

---

## Framework Integration Examples

### FastAPI

```python
from fastapi import FastAPI, HTTPException
from shopify_auth_adapter import ShopifyClient, ShopifyAuthAdapterError

app = FastAPI(title="Shopify Integration Service")
shopify = ShopifyClient()


@app.get("/api/products")
def get_products():
    try:
        response = shopify.get("/products.json")
        return response.json()
    except ShopifyAuthAdapterError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

### Flask

```python
from flask import Flask, jsonify
from shopify_auth_adapter import ShopifyClient

app = Flask(__name__)
shopify = ShopifyClient()


@app.route("/shop-info")
def shop_info():
    res = shopify.get("/shop.json")
    return jsonify(res.json())
```

### Celery / Background Tasks

```python
from celery import Celery
from shopify_auth_adapter import ShopifyClient

celery_app = Celery("tasks", broker="redis://localhost:6379/0")
shopify = ShopifyClient()


@celery_app.task
def sync_inventory_task():
    products = shopify.get("/products.json").json().get("products", [])
    # Process inventory sync logic
    return len(products)
```

---

## Error Handling & Resilience

`shopify_auth_adapter` provides a structured exception hierarchy so applications can handle errors cleanly without parsing raw HTTP tracebacks:

| Exception Class | Trigger Condition | Recommended Action |
| :--- | :--- | :--- |
| `ShopifyConfigurationError` | Missing `.env` / missing environment variables | Check credentials in `.env` or env vars |
| `ShopifyAuthenticationError` | Invalid Client ID or Secret (HTTP 401/403) | Re-check credentials in Dev Dashboard |
| `ShopifyRateLimitError` | Rate limit hit (HTTP 429) | Wait for `retry_after` seconds |
| `ShopifyAPIError` | Non-200 Admin API response | Inspect error payload |

### Exception Catching Example:

```python
from shopify_auth_adapter import (
    ShopifyAuthenticationError,
    ShopifyConfigurationError,
    ShopifyRateLimitError,
    get_access_token,
)

try:
    token = get_access_token()
except ShopifyConfigurationError as e:
    print(f"Configuration missing: {e}")
except ShopifyAuthenticationError as e:
    print(f"Authentication failed: {e}")
except ShopifyRateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds.")
```

---

## Logging & Debugging

Enable standard Python logging to inspect token handshakes, RAM cache hits, and background refreshes:

```python
import logging

# Enable DEBUG logs for shopify_auth_adapter
logging.basicConfig(level=logging.DEBUG)
```

---

## Verifying Connection

Run the interactive tester script included in the repository to test your setup:

```bash
python examples/test_credentials.py
```

---

*Documentation maintained by Ahmad Hassan (B-Ted)*
