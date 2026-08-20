# Security Policy

## Supported Versions

Only the latest stable release of `shopify_auth_adapter` receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability within `shopify_auth_adapter`, please **DO NOT** open a public GitHub issue.

Instead, please report vulnerabilities privately:

1. **Email**: Send details to **ahmad.hassan@example.com** or use GitHub Private Vulnerability Reporting on our repository.
2. **Details**: Include a description of the issue, steps to reproduce, affected versions, and any suggested mitigations.
3. **Response Time**: You will receive an acknowledgment within 24 hours and regular status updates until resolution.

---

## Security Guarantees in `shopify_auth_adapter`

1. **Token Masking**: `LiveToken` and `CachedToken` `__repr__` and `__str__` outputs mask access tokens and client secrets to prevent unintentional leakage in log files or exception tracebacks.
2. **In-Memory Cache**: Access tokens are held exclusively in memory; no tokens are serialized or persisted to disk.
3. **HTTPS Enforcement**: All communication with Shopify Admin API token endpoints is strictly forced over TLS/HTTPS.
