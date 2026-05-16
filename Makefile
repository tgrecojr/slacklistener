.PHONY: help setup install install-dev lock run clean test test-unit test-integration test-cov lint format

help:
	@echo "Slack Listener - Available commands:"
	@echo "  make setup            - Run initial setup (create venv, install deps, create config)"
	@echo "  make install          - Install/update runtime dependencies (uv sync --no-dev)"
	@echo "  make install-dev      - Install runtime + dev dependencies (uv sync)"
	@echo "  make lock             - Refresh uv.lock from pyproject.toml"
	@echo "  make run              - Run the application"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo "  make clean            - Clean up generated files"
	@echo "  make lint             - Run code linting"
	@echo "  make format           - Format code with black"

setup:
	@bash setup.sh

install:
	@uv sync --frozen --no-dev

install-dev:
	@uv sync --frozen
	@echo "✓ Development dependencies installed"

lock:
	@uv lock

run:
	@uv run python run.py

test:
	@echo "Running all tests..."
	@uv run pytest

test-unit:
	@echo "Running unit tests..."
	@uv run pytest tests/unit -v

test-integration:
	@echo "Running integration tests..."
	@uv run pytest tests/integration -v

test-cov:
	@echo "Running tests with coverage..."
	@uv run pytest --cov=src --cov-report=html --cov-report=term
	@echo "✓ Coverage report generated in htmlcov/index.html"

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.log" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type f -name "coverage.xml" -delete
	@echo "✓ Cleaned up"

lint:
	@echo "Running linters..."
	@uv run pylint src/ || true

format:
	@echo "Formatting code..."
	@uv run black src/ tests/
	@echo "✓ Code formatted"
