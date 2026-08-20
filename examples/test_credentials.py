#!/usr/bin/env python3
"""
ShopifyAutoAuth Credentials Tester
==================================
Run this script to verify your Shopify Dev Dashboard OAuth 2.0 credentials
and API connectivity.

Usage:
    python3 examples/test_credentials.py

Environment Variables (optional if using .env file):
    SHOPIFY_SHOP=your-store.myshopify.com
    SHOPIFY_CLIENT_ID=your_client_id
    SHOPIFY_CLIENT_SECRET=your_client_secret
"""

import sys
from pathlib import Path

# Add src to sys.path for local repository testing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from shopify_auth_adapter import (
    ShopifyAPIError,
    ShopifyAuthenticationError,
    ShopifyClient,
    ShopifyConfigurationError,
    get_access_token,
)


def run_credential_test() -> None:
    print("=" * 60)
    print("   ShopifyAutoAuth — Credentials & Connection Tester")
    print("=" * 60)

    try:
        print("\n[1/2] Testing OAuth 2.0 Client Credentials Token Fetch...")
        token = get_access_token()
        print("      Status : SUCCESS")
        print(f"      Token  : {token!r}")
        print(f"      Length : {len(str(token))} characters")

        print("\n[2/2] Testing Admin API Connectivity (GET /shop.json)...")
        client = ShopifyClient()
        response = client.get("/shop.json")

        if response.status_code == 200:
            shop_info = response.json().get("shop", {})
            print("      Status : SUCCESS (HTTP 200 OK)")
            print(f"      Name   : {shop_info.get('name')}")
            print(f"      Email  : {shop_info.get('email')}")
            print(f"      Domain : {shop_info.get('domain')}")
            print("\n" + "=" * 60)
            print("   SUCCESS: All credentials and API connections verified!")
            print("=" * 60)
        else:
            print(f"      Status : FAILED (HTTP {response.status_code})")
            print(f"      Details: {response.text[:200]}")
            sys.exit(1)

    except ShopifyConfigurationError as e:
        print("\n[CONFIGURATION ERROR]")
        print(f"  -> {e}")
        print("\nHow to fix:")
        print("  Provide your credentials in a .env file or environment variables:")
        print("    SHOPIFY_SHOP=your-store.myshopify.com")
        print("    SHOPIFY_CLIENT_ID=your_client_id")
        print("    SHOPIFY_CLIENT_SECRET=your_client_secret")
        sys.exit(1)

    except ShopifyAuthenticationError as e:
        print("\n[AUTHENTICATION ERROR]")
        print(f"  -> {e}")
        print("\nHow to fix:")
        print(
            "  Double-check your SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET in Dev Dashboard."
        )
        sys.exit(1)

    except ShopifyAPIError as e:
        print("\n[API ERROR]")
        print(f"  -> {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\n[UNEXPECTED ERROR]: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_credential_test()
