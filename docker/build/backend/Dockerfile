# Multi-stage build for Back-Office LMELP Backend
# Stage 1: Build dependencies with uv
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install build tools needed for packages requiring C compilation (e.g. scikit-surprise)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files and source code needed for package build
COPY pyproject.toml uv.lock ./
COPY README.md ./
COPY src/ ./src/

# Install dependencies (requires src/ for editable install)
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.11-slim

# Install curl for healthcheck, gosu to drop root privileges at runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gosu && \
    rm -rf /var/lib/apt/lists/*

# Non-root user (default UID/GID, overridable at runtime via PUID/PGID
# in entrypoint.sh — see issue #258). These ARGs only set the baked-in
# default; the actual UID/GID used at container startup can differ.
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd -g "$APP_GID" appuser \
    && useradd -u "$APP_UID" -g appuser -m -d /home/appuser -s /bin/bash appuser

ENV HOME=/home/appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ /app/src/

# Copy build info and changelog for version display (Issue #205)
COPY build_info.json changelog.json /app/

# Copy scripts directory (needed for migration_runner imports)
COPY scripts/ /app/scripts/

# Copy entrypoint (drops root privileges to appuser after remapping
# PUID/PGID and chowning the bind-mounted cache volume — Issue #258)
COPY docker/build/backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Make /app owned by appuser: the app writes a runtime file there
# (.dev-ports.json, port discovery) and appuser's baked-in UID/GID at
# build time won't generally match the PUID/PGID it gets remapped to at
# runtime, so a plain chown here is fine (unlike /cache, whose ownership
# is only known at container startup — handled in entrypoint.sh instead).
# This also fixes /app/src being unreadable when the host running
# `docker build` has restrictive source file permissions (COPY preserves
# them, which can be as strict as 700) — Issue #258.
RUN chown -R appuser:appuser /app

# Set Python path
ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

# Environment variables with defaults
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV ENVIRONMENT=production
ENV MONGODB_URL=mongodb://mongo:27017/masque_et_la_plume

# Expose port
EXPOSE ${API_PORT}

# Healthcheck (Issue #115: Use dedicated /health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${API_PORT}/health || exit 1

# Run the application (Issue #115: Use main() to configure access_log=False)
# Container starts as root; entrypoint.sh remaps to non-root "appuser"
# (PUID/PGID) before running this command (Issue #258)
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "back_office_lmelp.app"]
