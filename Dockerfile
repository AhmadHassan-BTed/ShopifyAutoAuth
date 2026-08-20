# Multi-stage production-hardened Dockerfile for shopify_auth_adapter

FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS dev

# Copy package metadata and code
COPY pyproject.toml README.md ./
COPY shopify_auth_adapter ./shopify_auth_adapter
COPY tests ./tests

# Install dev dependencies
RUN pip install --upgrade pip build hatchling && \
    pip install -e ".[dev]"

# Non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["pytest", "-v"]
