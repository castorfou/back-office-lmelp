# Multi-stage build for Back-Office LMELP Backend
# Stage 1: Build dependencies with uv
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

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

# Install curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ /app/src/

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
CMD ["python", "-m", "back_office_lmelp.app"]
