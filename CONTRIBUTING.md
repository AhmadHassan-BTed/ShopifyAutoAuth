# Contributing to shopify_auth_adapter

Thank you for your interest in contributing to `shopify_auth_adapter`! We welcome contributions from developers of all skill levels.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to the project maintainers.

---

## How Can I Contribute?

### 1. Reporting Bugs
Before submitting a bug report:
- Check existing [GitHub Issues](https://github.com/AhmadHassan-BTed/ShopifyAutoAuth/issues) to avoid duplicates.
- Ensure your issue includes clear steps to reproduce, Python version, library version, and expected vs actual behavior.

### 2. Suggesting Enhancements
Feature requests are welcome! Please open an issue outlining:
- The problem your request solves.
- Proposed solution or API design.
- Alternative approaches considered.

### 3. Pull Requests
1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/ShopifyAutoAuth.git
   cd ShopifyAutoAuth
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```
4. Set up your development environment:
   ```bash
   make install
   ```
5. Implement your changes following our code quality standards.
6. Run tests, linter, and type checker:
   ```bash
   make check
   ```
7. Commit your changes using conventional commit messages (e.g. `feat: add async token provider`).
8. Push to your fork and submit a Pull Request.

---

## Development Standards

- **Code Style**: We enforce `ruff` formatting and linting. Run `make format` and `make lint`.
- **Type Annotations**: All code must pass strict `mypy` type checking (`make typecheck`).
- **Test Coverage**: All new functionality must include unit tests using `pytest` (`make test`).
- **Security**: Never log sensitive credentials, client secrets, or full access token strings.

---

## Questions?

Feel free to start a discussion in [GitHub Discussions](https://github.com/AhmadHassan-BTed/ShopifyAutoAuth/discussions) or consult [SUPPORT.md](SUPPORT.md).
