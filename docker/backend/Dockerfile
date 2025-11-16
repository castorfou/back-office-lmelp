# Multi-stage build for Back-Office LMELP Backend
# Stage 1: Build dependencies with uv
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
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

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${API_PORT}/ || exit 1

# Run the application
CMD uvicorn back_office_lmelp.app:app --host ${API_HOST} --port ${API_PORT}
