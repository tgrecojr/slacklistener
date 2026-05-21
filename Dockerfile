# syntax=docker/dockerfile:1.24@sha256:87999aa3d42bdc6bea60565083ee17e86d1f3339802f543c0d03998580f9cb89

# Build stage - resolve and install dependencies with uv
FROM python:3.14-slim@sha256:a7185a8e40af01bf891414a4df16ef10fc6000cee460a404a13da9029fe41604 AS builder

# Pull the uv binary from the official distroless image
COPY --from=ghcr.io/astral-sh/uv:0.11@sha256:e590846f4776907b254ac0f44b5b380347af5d90d668138ca7938d1b0c2f98d3 /uv /uvx /usr/local/bin/

# Install build toolchain for any deps that ship sdists requiring C extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# uv settings: install into /app/.venv, copy (not symlink) for portability between stages
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# Install only production deps first (no project), cached by lockfile contents
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project


# Final stage - runtime only
FROM python:3.14-slim@sha256:a7185a8e40af01bf891414a4df16ef10fc6000cee460a404a13da9029fe41604

WORKDIR /app

# Copy the resolved virtualenv from the builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY run.py .

# Create config directory (config.yaml should be mounted as volume)
RUN mkdir -p config

# Run as non-root user
RUN useradd -m -u 1000 slackbot && \
    chown -R slackbot:slackbot /app
USER slackbot

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "run.py"]
