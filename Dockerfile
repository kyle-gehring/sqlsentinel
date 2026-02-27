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
RUN poetry install --no-root --only main --all-extras && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY src/ ./src/
COPY README.md LICENSE ./

# Install the package itself (pip avoids poetry --only-root syncing away extras)
RUN .venv/bin/pip install --no-deps .

# Verify optional extras are present so the build fails fast if they were stripped
RUN .venv/bin/python -c "import google.auth, psycopg2, pymysql, duckdb, pymssql; print('extras ok')"

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
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
    STATE_DB_PATH=/app/state/state.db \
    STATE_DB_URL=sqlite:////app/state/state.db \
    CONFIG_PATH=/app/config/alerts.yaml

# Switch to non-root user
USER sqlsentinel

# Expose health/metrics HTTP port
EXPOSE 8080

# Health check via HTTP endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default entrypoint: SQL Sentinel CLI
ENTRYPOINT ["python", "-m", "sqlsentinel.cli"]
# Default command: Run daemon with config reload enabled
CMD ["daemon", "/app/config/alerts.yaml", "--reload", "--log-level", "INFO"]

# Labels for metadata
ARG VERSION=dev
LABEL org.opencontainers.image.title="SQL Sentinel" \
      org.opencontainers.image.description="SQL-first alerting system for data analysts" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.vendor="SQL Sentinel Contributors" \
      org.opencontainers.image.licenses="MIT"
