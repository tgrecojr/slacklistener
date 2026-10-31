# syntax=docker/dockerfile:1.28@sha256:bb22d9815c728170f72750f4e5b0d672e06176142e1d602c7e66c050100b7e5b

# Build stage - resolve and install dependencies with uv.
# Chainguard's -dev image ships uv and gcc, so no extra apt installs are needed.
FROM cgr.dev/chainguard/python:latest-dev@sha256:157a562dbc225a2a9039dbd8249cbf704202260ba27bf525f24e47a3a685050f AS builder

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
FROM cgr.dev/chainguard/python:latest@sha256:35d6025b288eb1c40ae631db77ed6cdd26c6f51d898428d8fc9989db7f29e784

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
