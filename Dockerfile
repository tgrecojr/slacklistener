# syntax=docker/dockerfile:1.25@sha256:0adf442eae370b6087e08edc7c50b552d80ddf261576f4ebd6421006b2461f12

# Build stage - resolve and install dependencies with uv.
# Chainguard's -dev image ships uv and gcc, so no extra apt installs are needed.
FROM cgr.dev/chainguard/python:latest-dev@sha256:a38c998396e846c009bcabfc70702f64205b8db1dde71c8c8e5e734213afb237 AS builder

# Default user is nonroot; switch to root so we can write to /app during build.
USER root

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

# Pre-create runtime directories with nonroot ownership so the distroless
# final stage (which has no shell) can receive them via COPY.
RUN mkdir -p /scaffold/config /scaffold/data && \
    chown -R 65532:65532 /scaffold


# Final stage - distroless runtime.
# Chainguard's runtime image is distroless and already runs as uid 65532 (nonroot).
FROM cgr.dev/chainguard/python:latest@sha256:c6edbd621ec53f2c6dc7d0d9f3faf930e19af1a76241c0868b8b5da7cd4c9bdc

# Clear the upstream ENTRYPOINT (/usr/bin/python) so PATH-resolved "python" picks
# up the venv interpreter and activates the venv's site-packages.
ENTRYPOINT []

WORKDIR /app

# Copy the resolved virtualenv from the builder, owned by the runtime nonroot user.
COPY --from=builder --chown=65532:65532 /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --chown=65532:65532 src/ ./src/
COPY --chown=65532:65532 run.py .

# Create config (mount target) and data (RSS state) directories owned by nonroot.
COPY --from=builder --chown=65532:65532 /scaffold/config /app/config
COPY --from=builder --chown=65532:65532 /scaffold/data /app/data

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import sys; sys.exit(0)"]

CMD ["python", "run.py"]
