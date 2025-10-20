# SQL Sentinel - Production Docker Image
# Multi-stage build for minimal image size and security

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.7.1 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (without dev dependencies)
RUN poetry install --no-root --only main && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY src/ ./src/
COPY README.md LICENSE ./

# Install the package
RUN poetry install --only-root

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN groupadd -r sqlsentinel && useradd -r -g sqlsentinel sqlsentinel

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder --chown=sqlsentinel:sqlsentinel /app/src /app/src
COPY --from=builder --chown=sqlsentinel:sqlsentinel /app/README.md /app/LICENSE /app/

# Create directories for state and configuration
RUN mkdir -p /app/state /app/config /app/logs && \
    chown -R sqlsentinel:sqlsentinel /app/state /app/config /app/logs

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    STATE_DB_PATH=/app/state/state.db

# Switch to non-root user
USER sqlsentinel

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default entrypoint: SQL Sentinel CLI
ENTRYPOINT ["python", "-m", "sqlsentinel.cli"]
CMD ["--help"]

# Labels for metadata
LABEL org.opencontainers.image.title="SQL Sentinel" \
      org.opencontainers.image.description="SQL-first alerting system for data analysts" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.vendor="SQL Sentinel Contributors" \
      org.opencontainers.image.licenses="MIT"
