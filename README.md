# shopify_auth_adapter

A production-quality Python library that provides a compatibility layer between
existing Shopify applications (written around a static `shpat_xxx` token) and
**Shopify's current 2026 authentication mechanism** — the
**OAuth 2.0 Client Credentials Grant**.

---

## Contents

1. [What This Library Does](#what-this-library-does)
2. [Why Not a Legacy `shpat_xxx` Token?](#why-not-a-legacy-shpat_xxx-token)
3. [Current Shopify Authentication (August 2026)](#current-shopify-authentication-august-2026)
4. [Architecture](#architecture)
5. [Installation](#installation)
6. [Environment Variables](#environment-variables)
7. [Creating and Configuring the Shopify App](#creating-and-configuring-the-shopify-app)
8. [Required Access Scopes](#required-access-scopes)
9. [Minimal Usage](#minimal-usage)
10. [Existing Application Migration](#existing-application-migration)
11. [Higher-Level Client (ShopifyClient)](#higher-level-client-shopifyclient)
12. [Token Lifetime and Automatic Renewal](#token-lifetime-and-automatic-renewal)
13. [Security Considerations](#security-considerations)
14. [API Reference](#api-reference)
15. [Running the Tests](#running-the-tests)
16. [Troubleshooting](#troubleshooting)
17. [Official Shopify Documentation References](#official-shopify-documentation-references)

---

## What This Library Does

`shopify_auth_adapter` bridges the gap between the **old** pattern of hard-coding
a permanent Shopify access token and **Shopify's current 2026 authentication model**,
which uses short-lived (24-hour) tokens obtained via OAuth 2.0.

It provides:

- **`get_access_token()`** — a drop-in replacement for a hard-coded `shpat_xxx`
  string that automatically fetches, caches, and refreshes tokens.
- **`LiveToken`** — a `str` subclass that transparently refreshes the token when
  it is about to expire, so `SHOPIFY_ACCESS_TOKEN = get_access_token()` works as
  a module-level assignment without manual token rotation.
- **`ShopifyClient`** — a higher-level `httpx`-based client that attaches auth
  headers automatically and retries on 401.

---

## Why Not a Legacy `shpat_xxx` Token?

**Since January 1, 2026, Shopify removed the ability to create new Custom Apps
with permanent static access tokens from the store admin.**

Older tutorials and Stack Overflow answers describe a workflow where you navigate
to **Settings → Apps and sales channels → Develop apps → Create an app**, configure
scopes, and copy a `shpat_xxx` token that never expires. **This workflow no longer
produces permanent tokens for newly created apps.** Any app created after
January 2026 obtains tokens via the OAuth 2.0 Client Credentials Grant, and those
tokens expire every 24 hours.

Attempting to hard-code a token obtained via the new flow would require your team
to manually update it every day — an operational anti-pattern that introduces
service outages and encourages insecure secret-handling practices.

`shopify_auth_adapter` automates the token lifecycle so your application code
does not change.

---

## Current Shopify Authentication (August 2026)

### The Mechanism: Client Credentials Grant (RFC 6749 §4.4)

For **server-to-server integrations where the app and the store are owned by the
same organisation**, Shopify supports the OAuth 2.0 **Client Credentials Grant**.

```
POST https://{shop}.myshopify.com/admin/oauth/access_token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={client_id}
&client_secret={client_secret}
```

**Successful response:**

```json
{
  "access_token": "f85632530bf277ec9ac6f649fc327f17",
  "scope": "write_content,read_content",
  "expires_in": 86399
}
```

Key properties:

| Property | Value |
|----------|-------|
| Grant type | `client_credentials` |
| Token lifetime | 86 399 seconds ≈ 24 hours |
| Refresh mechanism | Re-issue the same POST request — there is **no** `refresh_token` |
| User interaction required? | **No** |
| Suitable for server-side automation? | **Yes** |

### Why Not the Authorization Code Flow?

The Authorization Code Flow (the "install the app" OAuth flow that redirects the
user to a Shopify consent screen) is designed for **third-party apps** that are
installed on stores you do not own. It is not appropriate for an internal automation
tool running against your own store, because:

- It requires a browser-based redirect to an OAuth consent page on every token
  refresh (or a refresh-token mechanism that Shopify does not provide for Admin API tokens).
- It is architecturally suited to multi-store SaaS products, not single-store scripts.

### Why Not Token Exchange?

Token Exchange is used by apps built on Shopify's **Hydrogen** storefront framework
to exchange Shopify's customer session tokens for Admin API tokens. It does not apply
to server-side Python scripts that use the Admin API.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Your existing application               │
│                                                         │
│  SHOPIFY_ACCESS_TOKEN = get_access_token()              │
│  headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN} │
│  requests.get(url, headers=headers)                     │
└────────────────────────┬────────────────────────────────┘
                         │  LiveToken.encode("latin-1")
                         │  called by requests/httpx at send time
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  shopify_auth_adapter                    │
│                                                         │
│  LiveToken (str subclass)                               │
│    └─► TokenManager.get_token()                         │
│              ├─ TokenCache.get()   ←── in-memory cache  │
│              │     (valid?)                             │
│              ├── YES → return cached token (no HTTP)    │
│              └── NO  → POST /admin/oauth/access_token   │
│                         (Client Credentials Grant)      │
│                         → TokenCache.set(token, 86399)  │
│                         → return new token              │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
              Shopify Admin API
```

---

## Installation

```bash
pip install shopify-auth-adapter
```

With optional `.env` file loading:

```bash
pip install "shopify-auth-adapter[dotenv]"
```

For development (includes test tools):

```bash
git clone https://github.com/your-org/shopify-auth-adapter.git
cd shopify-auth-adapter
pip install -e ".[dev]"
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SHOPIFY_SHOP` | ✅ | Your store domain, e.g. `my-store.myshopify.com` |
| `SHOPIFY_CLIENT_ID` | ✅ | Client ID from your Dev Dashboard app |
| `SHOPIFY_CLIENT_SECRET` | ✅ | Client Secret from your Dev Dashboard app **(treat as a password)** |
| `SHOPIFY_API_VERSION` | ❌ | API version, e.g. `2026-07`. Defaults to the current stable version |

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

To load `.env` automatically, add this at the top of your application entry point:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Creating and Configuring the Shopify App

> **Important:** Follow these steps exactly. Do **not** use the legacy "Custom App"
> path in the store admin if it is available — that flow may produce tokens with
> different characteristics depending on your store's plan.

### Step 1 — Access the Shopify Dev Dashboard

1. Go to [https://partners.shopify.com](https://partners.shopify.com) and sign in
   with your Shopify Partner account.
2. If you do not have a Partner account, create one at no cost — it is separate
   from your store account.

### Step 2 — Create an App

1. In the Partner Dashboard, click **Apps** in the left navigation.
2. Click **Create app**.
3. Choose **Create app manually**.
4. Give the app a name (e.g. `Blog Content Manager`).
5. Click **Create**.

### Step 3 — Copy Your Credentials

On the app's **Settings** page:

- Copy the **Client ID** → set as `SHOPIFY_CLIENT_ID`.
- Click **Reveal client secret**, copy it → set as `SHOPIFY_CLIENT_SECRET`.

> The Client ID is not sensitive. The Client Secret **is** — store it in your
> `.env` file and never commit it.

### Step 4 — Configure Access Scopes

1. In the app, go to **Configuration**.
2. Under **Admin API integration**, click **Configure**.
3. Enable the scopes required by your application (see
   [Required Access Scopes](#required-access-scopes) below).
4. Click **Save**.

### Step 5 — Install the App on Your Store

1. Go to **Test your app** (or **Distribution → Select stores**).
2. Select your store and click **Install**.
3. Review the requested permissions and click **Install app**.

The Client Credentials Grant only works for stores on which the app is installed.

### Step 6 — Verify

Run a quick test from your project directory:

```bash
SHOPIFY_SHOP=my-store.myshopify.com \
SHOPIFY_CLIENT_ID=your-client-id \
SHOPIFY_CLIENT_SECRET=your-client-secret \
python -c "
from shopify_auth_adapter import ShopifyClient
shopify = ShopifyClient()
r = shopify.get('/blogs.json')
print(r.status_code, r.json())
"
```

---

## Required Access Scopes

For managing Shopify **blog content** (articles, blogs, comments, pages):

| Scope | Access |
|-------|--------|
| `read_content` | Read articles, blogs, comments, pages, and redirects |
| `write_content` | Create, update, and delete articles, blogs, comments, pages, and redirects |

Configure both scopes in Step 4 above.

For a complete list of all Shopify Admin API scopes:
[https://shopify.dev/docs/api/usage/access-scopes](https://shopify.dev/docs/api/usage/access-scopes)

---

## Minimal Usage

All configuration from environment variables:

```python
from shopify_auth_adapter import get_access_token

# Returns a LiveToken — a str subclass that auto-refreshes every 24 hours.
SHOPIFY_ACCESS_TOKEN = get_access_token()

# Your existing code continues unchanged:
import requests

headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
response = requests.get(
    "https://my-store.myshopify.com/admin/api/2026-07/blogs.json",
    headers=headers,
)
print(response.json())
```

With explicit arguments (alternative to environment variables):

```python
SHOPIFY_ACCESS_TOKEN = get_access_token(
    shop="my-store.myshopify.com",
    client_id="abc123",
    client_secret="super-secret",  # prefer SHOPIFY_CLIENT_SECRET env var instead
)
```

---

## Existing Application Migration

### Before (legacy permanent token — no longer valid for new apps)

```python
# my_app.py

SHOPIFY_ACCESS_TOKEN = "shpat_xxxxxxxxxxxxxxxxxxxxxxxxxx"

def create_blog_article(blog_id, title, body_html):
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }
    payload = {"article": {"title": title, "body_html": body_html}}
    response = requests.post(
        f"https://my-store.myshopify.com/admin/api/2026-07/blogs/{blog_id}/articles.json",
        headers=headers,
        json=payload,
    )
    return response.json()
```

### After — minimal change (one import, one line changed)

```python
# my_app.py

from shopify_auth_adapter import get_access_token   # ← add this import

SHOPIFY_ACCESS_TOKEN = get_access_token()            # ← replace the string

# Everything below is unchanged:
def create_blog_article(blog_id, title, body_html):
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }
    payload = {"article": {"title": title, "body_html": body_html}}
    response = requests.post(
        f"https://my-store.myshopify.com/admin/api/2026-07/blogs/{blog_id}/articles.json",
        headers=headers,
        json=payload,
    )
    return response.json()
```

Set your credentials in environment variables (or a `.env` file) and you are done.
No other code changes are required.

### Important: How LiveToken Keeps Headers Fresh

`SHOPIFY_ACCESS_TOKEN = get_access_token()` stores a `LiveToken` object — a `str`
subclass — rather than a plain string. When the token is used in an HTTP header
dict, both `requests` and `httpx` call `.encode("latin-1")` on the value at request
send time. `LiveToken` intercepts this call and returns the *current valid token's*
bytes — automatically fetching a fresh token if the cached one has expired.

This means the pattern:

```python
# Built once, used repeatedly across the day — works correctly:
headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
```

...is safe as long as `SHOPIFY_ACCESS_TOKEN` is the `LiveToken` object and not a
plain string extracted from it. If you ever do `str(SHOPIFY_ACCESS_TOKEN)` to
extract the raw value, you will get a snapshot that may expire.

### If You Cannot Use LiveToken

For the small number of HTTP libraries that do not call `.encode()` on header
values and instead require a plain `str`, call `get_access_token()` at the point
of building the headers:

```python
# Called fresh before each request — always current:
headers = {"X-Shopify-Access-Token": get_access_token(live=False)}
```

---

## Higher-Level Client (ShopifyClient)

`ShopifyClient` wraps `httpx` and handles authentication, URL construction,
and error handling automatically.

### Basic REST Usage

```python
from shopify_auth_adapter import ShopifyClient

shopify = ShopifyClient()

# List blogs
response = shopify.get("/blogs.json")
blogs = response.json()["blogs"]

# Create a blog
response = shopify.post("/blogs.json", json={"blog": {"title": "Engineering"}})
blog_id = response.json()["blog"]["id"]

# Create an article
response = shopify.post(
    f"/blogs/{blog_id}/articles.json",
    json={
        "article": {
            "title": "Hello from the adapter",
            "body_html": "<p>Automatically authenticated!</p>",
            "published": True,
        }
    },
)

# Update an article
article_id = response.json()["article"]["id"]
shopify.put(
    f"/blogs/{blog_id}/articles/{article_id}.json",
    json={"article": {"title": "Updated title"}},
)

# Delete an article
shopify.delete(f"/blogs/{blog_id}/articles/{article_id}.json")
```

### GraphQL Usage

```python
data = shopify.graphql("""
    query {
      blogs(first: 10) {
        edges {
          node {
            id
            title
          }
        }
      }
    }
""")

for edge in data["blogs"]["edges"]:
    print(edge["node"]["title"])
```

With variables:

```python
data = shopify.graphql(
    """
    query GetBlog($id: ID!) {
      blog(id: $id) { title }
    }
    """,
    variables={"id": "gid://shopify/Blog/123456"},
)
```

---

## Token Lifetime and Automatic Renewal

| Property | Value |
|----------|-------|
| Token lifetime | 86 399 seconds (≈ 24 hours) |
| Proactive refresh buffer | 300 seconds (5 minutes before expiry) |
| Refresh mechanism | Re-POST to `/admin/oauth/access_token` with same credentials |
| Refresh token | None — not used in this flow |
| User interaction required | None |
| Threads / processes | In-memory cache; each process manages its own token |

The cache is **in-memory only**. If your application restarts, it fetches a new
token on the first request. This is by design — persisting tokens to disk would
require encryption and adds unnecessary complexity for a credential that can be
re-obtained instantly with client credentials.

For multi-process deployments (e.g. `gunicorn` with multiple workers), each worker
maintains its own token cache and independently refreshes when needed. This is
correct behaviour — each process makes at most one extra token request per 24 hours,
which is well within Shopify's rate limits.

---

## Security Considerations

### What to keep on the server

| Credential | Keep server-side? | Notes |
|-----------|-------------------|-------|
| `SHOPIFY_CLIENT_SECRET` | **Always** | Must never reach the browser |
| Access token | **Always** | Must never reach the browser |
| `SHOPIFY_CLIENT_ID` | Prefer server-side | Not technically secret but limits attack surface |

### Secrets in source control

- Use environment variables or a secrets manager (AWS Secrets Manager, GCP Secret
  Manager, HashiCorp Vault, etc.).
- Add `.env` to `.gitignore` (already done if you used this template).
- Rotate `SHOPIFY_CLIENT_SECRET` immediately if it is ever accidentally committed.

### Secrets in logs

`shopify_auth_adapter` never logs access tokens or client secrets. All log messages
reference the store domain and scopes only. The `LiveToken.__repr__()` method returns
`LiveToken(<masked>)` so that tokens do not appear in tracebacks or debug logs.

### Secrets in exceptions

All exception messages are carefully written to exclude credential values. The
test suite includes explicit tests that verify this guarantee.

### HTTPS only

All requests to Shopify are made over HTTPS. The library does not provide an option
to disable certificate verification.

### Least privilege

Configure only the scopes your application actually needs. For blog management:
`read_content,write_content`. Do not enable `write_products`, `write_customers`,
or other sensitive scopes unless required.

---

## API Reference

### `get_access_token(...) → LiveToken | str`

```python
from shopify_auth_adapter import get_access_token

SHOPIFY_ACCESS_TOKEN = get_access_token(
    shop="my-store.myshopify.com",   # or SHOPIFY_SHOP env var
    client_id="...",                  # or SHOPIFY_CLIENT_ID env var
    client_secret="...",              # or SHOPIFY_CLIENT_SECRET env var
    api_version="2026-07",            # optional; defaults to current stable
    live=True,                        # default: True (returns LiveToken)
                                      # False: returns a plain str snapshot
)
```

### `class ShopifyClient`

```python
shopify = ShopifyClient(
    shop="my-store.myshopify.com",   # optional if SHOPIFY_SHOP is set
    client_id="...",                  # optional if SHOPIFY_CLIENT_ID is set
    client_secret="...",              # optional if SHOPIFY_CLIENT_SECRET is set
    api_version="2026-07",            # optional
    timeout=httpx.Timeout(30.0),      # optional
)

shopify.get(path, **httpx_kwargs)   → httpx.Response
shopify.post(path, **httpx_kwargs)  → httpx.Response
shopify.put(path, **httpx_kwargs)   → httpx.Response
shopify.patch(path, **httpx_kwargs) → httpx.Response
shopify.delete(path, **httpx_kwargs)→ httpx.Response
shopify.graphql(query, variables)   → dict
```

### `class TokenManager`

```python
manager = TokenManager(config=ShopifyConfig(...))
# or
manager = TokenManager(shop="...", client_id="...", client_secret="...")

manager.get_token()       → str          # current valid token (fetches if needed)
manager.get_live_token()  → LiveToken    # proxy that auto-refreshes
manager.invalidate()      → None         # force cache clear
```

### Exceptions

```
ShopifyAuthAdapterError          (base)
├── ShopifyConfigurationError    – missing env var or argument
├── ShopifyAuthenticationError   – Shopify returned 401 or 403
├── ShopifyNetworkError          – timeout or DNS failure
└── ShopifyAPIError              – unexpected HTTP error from Admin API
    └── ShopifyRateLimitError    – 429; has .retry_after attribute
```

---

## Running the Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run the full test suite
pytest

# With coverage
pytest --cov=shopify_auth_adapter --cov-report=term-missing

# Run a specific test file
pytest tests/test_auth.py -v

# Run a specific test
pytest tests/test_live_token.py::TestLiveTokenAutoRefresh -v
```

All tests mock HTTP calls with `respx`. No real Shopify credentials are required
to run the test suite.

---

## Troubleshooting

### `ShopifyConfigurationError: SHOPIFY_SHOP is not configured`

The `SHOPIFY_SHOP` environment variable is not set. Ensure your `.env` file exists
and is loaded before `get_access_token()` is called:

```python
from dotenv import load_dotenv
load_dotenv()  # Must be called before get_access_token()

from shopify_auth_adapter import get_access_token
SHOPIFY_ACCESS_TOKEN = get_access_token()
```

### `ShopifyAuthenticationError: Shopify rejected the client credentials (HTTP 401)`

- Double-check `SHOPIFY_CLIENT_ID` and `SHOPIFY_CLIENT_SECRET` against the app's
  Settings page in the Partner Dashboard.
- Ensure you are using credentials from a **Dev Dashboard app**, not from a legacy
  Custom App created before 2026.
- Verify that the app is installed on the store named in `SHOPIFY_SHOP`.

### `ShopifyAuthenticationError: Shopify denied access (HTTP 403)`

The app is missing required access scopes. Go to the app's **Configuration** page
in the Partner Dashboard, add the required scopes, save, and reinstall the app on
your store.

### `ShopifyNetworkError: Request to Shopify token endpoint timed out`

- Check that your server can reach `https://{shop}.myshopify.com` on port 443.
- Verify firewall and proxy settings.
- If you are behind a corporate proxy, configure it via the `HTTPS_PROXY`
  environment variable (httpx respects standard proxy env vars).

### `ShopifyRateLimitError (HTTP 429)`

Shopify's rate limits apply to the token endpoint too. This is extremely unlikely
in normal operation — it would require hundreds of token requests per minute.
If you see this, check for a misconfigured loop that calls `get_access_token()`
on every request instead of reusing the cached `LiveToken`.

### Token works at startup but fails after ~24 hours

You are storing a plain `str` extracted from the token rather than using the
`LiveToken` proxy. Replace:

```python
# Wrong — plain str that expires:
token_str = str(get_access_token())
SHOPIFY_ACCESS_TOKEN = token_str
```

With:

```python
# Correct — LiveToken that auto-refreshes:
SHOPIFY_ACCESS_TOKEN = get_access_token()
```

### Headers contain an empty string instead of the token

Some libraries directly access the value stored in a header dict (which is the empty
placeholder inside the `LiveToken`) rather than calling `.encode()`. Switch to
`ShopifyClient` (which always calls `manager.get_token()` and passes a plain `str`)
or call `get_access_token(live=False)` to capture a snapshot:

```python
# Snapshot — valid for up to 24 hours (minus the 5-minute skew buffer):
headers = {"X-Shopify-Access-Token": get_access_token(live=False)}
```

---

## Official Shopify Documentation References

All design decisions in this library are based on the following official Shopify
documentation (current as of August 2026):

1. **Client Credentials Grant**
   https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant

2. **API versioning (current stable: 2026-07)**
   https://shopify.dev/docs/api/usage/versioning

3. **Admin API access scopes**
   https://shopify.dev/docs/api/usage/access-scopes

4. **Creating apps in the Partner Dashboard**
   https://shopify.dev/docs/apps/build/scaffold-app

5. **Shopify Admin REST API — Blogs**
   https://shopify.dev/docs/api/admin-rest/latest/resources/blog

6. **Shopify Admin REST API — Articles**
   https://shopify.dev/docs/api/admin-rest/latest/resources/article

7. **Shopify Admin GraphQL API**
   https://shopify.dev/docs/api/admin-graphql

8. **Deprecation of permanent custom app tokens (January 2026)**
   https://shopify.dev/changelog/deprecating-permanent-access-tokens-for-custom-apps
