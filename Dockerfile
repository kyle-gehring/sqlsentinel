# Multi-stage Dockerfile for SQL Sentinel
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --only main --no-root --no-interaction --no-ansi

# Copy application code
COPY src/ ./src/
COPY README.md ./

# Install the package
RUN poetry install --only-root --no-interaction --no-ansi

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r sqlsentinel && useradd -r -g sqlsentinel sqlsentinel

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/src /app/src

# Set Python path
ENV PYTHONPATH=/app/src:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Create config directory
RUN mkdir -p /config && chown -R sqlsentinel:sqlsentinel /config

# Switch to non-root user
USER sqlsentinel

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import sqlsentinel; print('healthy')" || exit 1

# Default command (will be overridden with actual alert engine)
CMD ["python", "-c", "import sqlsentinel; print(f'SQL Sentinel v{sqlsentinel.__version__}')"]
