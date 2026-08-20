.PHONY: help install test lint format typecheck check build clean docker-build docker-test

PYTHON ?= python3

help:
	@echo "Available make targets:"
	@echo "  install      Install package in editable mode with development dependencies"
	@echo "  test         Run unit and integration test suite with coverage"
	@echo "  lint         Run ruff linter checks"
	@echo "  format       Format code with ruff"
	@echo "  typecheck    Run mypy static type checking"
	@echo "  check        Run all quality checks (lint, format check, typecheck, test)"
	@echo "  build        Build sdist and wheel distribution packages"
	@echo "  clean        Clean build, cache, and test artifacts"
	@echo "  docker-build Build Docker test image"
	@echo "  docker-test  Run pytest suite inside Docker container"

install:
	$(PYTHON) -m pip install --upgrade pip build hatchling
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest --cov=shopify_auth_adapter --cov-report=term-missing -v

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

typecheck:
	$(PYTHON) -m mypy shopify_auth_adapter

check: lint format typecheck test

build: clean
	$(PYTHON) -m build

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} +

docker-build:
	docker build -t shopify-auth-adapter:latest .

docker-test: docker-build
	docker run --rm shopify-auth-adapter:latest pytest
