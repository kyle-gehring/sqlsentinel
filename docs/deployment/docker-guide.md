# SQL Sentinel - Docker Deployment Guide

**Version:** 1.0
**Last Updated:** 2025-11-07
**Status:** Production Ready

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Scenarios](#deployment-scenarios)
- [Configuration](#configuration)
- [Health Monitoring](#health-monitoring)
- [Metrics Collection](#metrics-collection)
- [Troubleshooting](#troubleshooting)
- [Production Checklist](#production-checklist)

---

## Overview

SQL Sentinel provides production-ready Docker images and deployment templates for running the alerting system in containerized environments. This guide covers all deployment scenarios from local development to production.

### Key Features

- **Multi-stage builds** for optimized image size (<500MB)
- **Health checks** for container orchestration
- **Prometheus metrics** for monitoring
- **Structured JSON logging** for aggregation
- **Non-root execution** for security
- **Graceful shutdown** for reliability

---

## Prerequisites

### Required

- **Docker:** 20.10+ (for multi-stage builds and health checks)
- **Docker Compose:** 2.0+ (for orchestration)
- **Database:** PostgreSQL, MySQL, BigQuery, or SQLite
- **Alert configuration:** YAML file with alert definitions

### Optional

- **Prometheus:** For metrics collection
- **Grafana:** For visualization dashboards
- **Log aggregation:** ELK stack, Loki, or CloudWatch

---

## Quick Start

### 1. Pull the Docker Image

```bash
docker pull kgehring/sqlsentinel:latest
```

### 2. Create Alert Configuration

Create `alerts.yaml`:

```yaml
alerts:
  - name: "daily_revenue_check"
    description: "Alert when daily revenue is below threshold"
    query: |
      SELECT
        CASE WHEN SUM(revenue) < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        SUM(revenue) as actual_value,
        10000 as threshold
      FROM orders
      WHERE date = CURRENT_DATE - 1
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["team@company.com"]
```

### 3. Run the Container

```bash
docker run -d \
  --name sqlsentinel \
  -v $(pwd)/alerts.yaml:/app/config/alerts.yaml \
  -e DATABASE_URL="postgresql://user:pass@host/db" \
  -e SMTP_HOST="smtp.gmail.com" \
  -e SMTP_PORT="587" \
  -e SMTP_USERNAME="your-email@gmail.com" \
  -e SMTP_PASSWORD="your-app-password" \
  -e SMTP_FROM="alerts@company.com" \
  kgehring/sqlsentinel:latest
```

### 4. Verify Health

```bash
docker exec sqlsentinel sqlsentinel healthcheck /app/config/alerts.yaml
```

---

## Deployment Scenarios

SQL Sentinel provides multiple docker-compose templates for different use cases.

### Production Deployment

**File:** `docker-compose.yaml`

```yaml
version: '3.8'

services:
  sqlsentinel:
    image: kgehring/sqlsentinel:latest
    container_name: sqlsentinel
    restart: unless-stopped

    environment:
      - DATABASE_URL=${DATABASE_URL}
      - STATE_DATABASE=/data/state.db
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT}
      - SMTP_USERNAME=${SMTP_USERNAME}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - SMTP_FROM=${SMTP_FROM}

    volumes:
      - ./config:/app/config:ro
      - ./data:/data
      - ./logs:/app/logs

    healthcheck:
      test: ["CMD", "sqlsentinel", "healthcheck", "/app/config/alerts.yaml", "--output", "json"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

    command: ["daemon", "/app/config/alerts.yaml", "--reload"]
```

**Deploy:**

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f
```

### Development Deployment

**File:** `docker-compose.dev.yaml`

```yaml
version: '3.8'

services:
  sqlsentinel:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: sqlsentinel-dev

    environment:
      - DATABASE_URL=${DATABASE_URL}
      - STATE_DATABASE=/data/state.db
      - LOG_LEVEL=DEBUG
      - LOG_FORMAT=text  # Human-readable for development
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT}
      - SMTP_USERNAME=${SMTP_USERNAME}
      - SMTP_PASSWORD=${SMTP_PASSWORD}

    volumes:
      - ./config:/app/config:ro
      - ./data:/data
      - ./src:/app/src  # Mount source for hot reload

    command: ["daemon", "/app/config/alerts.yaml", "--reload", "--log-level", "DEBUG"]
```

**Deploy:**

```bash
docker-compose -f docker-compose.dev.yaml up
```

### Testing Deployment

**File:** `docker-compose.test.yaml`

Includes a PostgreSQL database for testing:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: sqlsentinel-postgres
    environment:
      - POSTGRES_USER=sqlsentinel
      - POSTGRES_PASSWORD=sqlsentinel
      - POSTGRES_DB=test_db
    ports:
      - "5432:5432"
    volumes:
      - ./test-data:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sqlsentinel"]
      interval: 5s
      timeout: 5s
      retries: 5

  sqlsentinel:
    image: kgehring/sqlsentinel:latest
    container_name: sqlsentinel-test
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://sqlsentinel:sqlsentinel@postgres:5432/test_db
      - STATE_DATABASE=/data/state.db
      - LOG_LEVEL=DEBUG
    volumes:
      - ./examples/alerts:/app/config:ro
      - ./test-data:/data
    command: ["daemon", "/app/config/revenue_check.yaml"]
```

**Deploy:**

```bash
docker-compose -f docker-compose.test.yaml up
```

### Monitoring Deployment

**File:** `docker-compose.monitoring.yaml`

Adds Prometheus and Grafana for observability:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana-dashboards:/etc/grafana/provisioning/dashboards:ro
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:
```

**Deploy:**

```bash
# Deploy with monitoring
docker-compose -f docker-compose.yaml -f docker-compose.monitoring.yaml up -d

# Access Grafana
open http://localhost:3000  # admin/admin

# Access Prometheus
open http://localhost:9090
```

---

## Configuration

### Environment Variables

#### Database Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | Alert database connection string | No | None |
| `STATE_DATABASE` | State database path (SQLite) | Yes | `/data/state.db` |

**Example DATABASE_URL formats:**

```bash
# PostgreSQL
DATABASE_URL="postgresql://user:pass@host:5432/database"

# MySQL
DATABASE_URL="mysql://user:pass@host:3306/database"

# BigQuery
DATABASE_URL="bigquery://project-id/dataset"
GOOGLE_APPLICATION_CREDENTIALS="/app/credentials/service-account.json"

# SQLite
DATABASE_URL="sqlite:///path/to/database.db"
```

#### Email Configuration

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SMTP_HOST` | SMTP server hostname | Yes (for email) | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | Yes (for email) | `587` |
| `SMTP_USERNAME` | SMTP username | Yes (for email) | `alerts@company.com` |
| `SMTP_PASSWORD` | SMTP password | Yes (for email) | `app-password` |
| `SMTP_FROM` | From email address | Yes (for email) | `alerts@company.com` |
| `SMTP_USE_TLS` | Use TLS encryption | No | `true` |

#### Slack Configuration

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SLACK_WEBHOOK_URL` | Slack webhook URL | Yes (for Slack) | `https://hooks.slack.com/...` |

#### Webhook Configuration

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `WEBHOOK_URL` | Generic webhook URL | Yes (for webhook) | `https://api.example.com/alerts` |
| `WEBHOOK_HEADERS` | Custom headers (JSON) | No | `{"Authorization": "Bearer token"}` |

#### Logging Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LOG_LEVEL` | Log level | No | `INFO` |
| `LOG_FORMAT` | Log format (json/text) | No | `json` |

**Log Levels:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### Volume Mounts

| Path | Description | Read-Only | Required |
|------|-------------|-----------|----------|
| `/app/config` | Alert configuration files | Yes | Yes |
| `/data` | State database and persistent data | No | Yes |
| `/app/logs` | Log files (if file logging enabled) | No | No |
| `/app/credentials` | Service account keys (BigQuery, etc.) | Yes | No |

### Health Check Configuration

The health check validates:
- ✅ State database connectivity
- ✅ Alert database connectivity (if configured)
- ✅ Notification channels (email, Slack, webhook)

**Docker health check:**

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
  CMD sqlsentinel healthcheck /app/config/alerts.yaml --output json || exit 1
```

---

## Health Monitoring

### Checking Container Health

**Via Docker:**

```bash
# Check health status
docker inspect sqlsentinel --format='{{.State.Health.Status}}'

# View health check logs
docker inspect sqlsentinel --format='{{range .State.Health.Log}}{{.Output}}{{end}}'
```

**Via CLI:**

```bash
# Text output
docker exec sqlsentinel sqlsentinel healthcheck /app/config/alerts.yaml

# JSON output
docker exec sqlsentinel sqlsentinel healthcheck /app/config/alerts.yaml --output json
```

**Using validation script:**

```bash
./scripts/validate-health.sh
```

### Health Check Output

**Text format:**

```
============================================================
SQL Sentinel Health Check
============================================================

✓ State Database
  Status: healthy
  Latency: 5.09ms
  Message: Database connection OK

✓ Alert Database
  Status: healthy
  Latency: 12.34ms
  Message: Connected to PostgreSQL

✓ Notifications
  Status: healthy
  Channels:
    ✓ email: healthy
    ✓ slack: healthy
    ⊘ webhook: not_configured

============================================================
Overall Status: HEALTHY
============================================================
```

**JSON format:**

```json
{
  "status": "healthy",
  "timestamp": "2025-11-07T19:00:00Z",
  "checks": {
    "state_database": {
      "status": "healthy",
      "latency_ms": 5.09,
      "message": "Database connection OK"
    },
    "alert_database": {
      "status": "healthy",
      "latency_ms": 12.34,
      "message": "Connected to PostgreSQL"
    },
    "notifications": {
      "status": "healthy",
      "channels": {
        "email": {"status": "healthy"},
        "slack": {"status": "healthy"},
        "webhook": {"status": "not_configured"}
      }
    }
  }
}
```

---

## Metrics Collection

SQL Sentinel exposes Prometheus-compatible metrics for monitoring.

### Viewing Metrics

**Via CLI:**

```bash
# View all metrics
docker exec sqlsentinel sqlsentinel metrics

# JSON output
docker exec sqlsentinel sqlsentinel metrics --output json
```

### Available Metrics

See [docs/api/metrics.md](../api/metrics.md) for complete metrics reference.

**Key metrics:**

- `sqlsentinel_alerts_total` - Total alert executions
- `sqlsentinel_alert_duration_seconds` - Alert execution duration
- `sqlsentinel_notifications_total` - Total notifications sent
- `sqlsentinel_scheduler_jobs` - Current scheduled jobs
- `sqlsentinel_uptime_seconds` - Application uptime

### Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'sqlsentinel'
    static_configs:
      - targets: ['sqlsentinel:8080']
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**

```bash
docker logs sqlsentinel
```

**Common issues:**

1. **Missing configuration file**
   ```
   Error: Configuration file not found: /app/config/alerts.yaml
   ```
   **Solution:** Verify volume mount and file path

2. **Database connection failed**
   ```
   Error: Could not connect to database
   ```
   **Solution:** Check `DATABASE_URL` and network connectivity

3. **Permission denied**
   ```
   Error: Permission denied: /data/state.db
   ```
   **Solution:** Fix volume permissions:
   ```bash
   sudo chown -R 1000:1000 ./data
   ```

### Health Check Failing

**Debug health check:**

```bash
docker exec -it sqlsentinel sqlsentinel healthcheck /app/config/alerts.yaml
```

**Check component status:**

- State database: Verify `/data/state.db` is writable
- Alert database: Test `DATABASE_URL` manually
- Notifications: Check SMTP/Slack credentials

### Alerts Not Executing

**Check scheduler status:**

```bash
docker exec sqlsentinel sqlsentinel metrics | grep scheduler
```

**View daemon logs:**

```bash
docker logs sqlsentinel -f --tail 100
```

**Verify cron schedule:**

```bash
# Test alert manually
docker exec sqlsentinel sqlsentinel run /app/config/alerts.yaml --alert daily_revenue_check
```

### High Memory Usage

**Check container stats:**

```bash
docker stats sqlsentinel
```

**Adjust resource limits:**

```yaml
services:
  sqlsentinel:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

---

## Production Checklist

### Pre-Deployment

- [ ] Review alert configurations
- [ ] Test alerts manually with `--dry-run`
- [ ] Configure database connections
- [ ] Set up notification channels
- [ ] Create `.env` file with secrets
- [ ] Review and adjust health check settings
- [ ] Set up volume mounts for persistence
- [ ] Configure resource limits

### Security

- [ ] Use non-root user (default: sqlsentinel)
- [ ] Store secrets in environment variables (not in YAML)
- [ ] Use read-only volume mounts for config
- [ ] Enable TLS for SMTP connections
- [ ] Restrict network access
- [ ] Regularly update Docker images
- [ ] Review file permissions on volumes

### Monitoring

- [ ] Configure health checks
- [ ] Set up metrics collection (Prometheus)
- [ ] Configure log aggregation
- [ ] Set up alerting on system health
- [ ] Create dashboards (Grafana)
- [ ] Monitor disk usage
- [ ] Monitor memory usage

### Operations

- [ ] Document deployment procedure
- [ ] Set up backup for state database
- [ ] Configure log rotation
- [ ] Test disaster recovery
- [ ] Create runbook for common issues
- [ ] Set up monitoring alerts
- [ ] Schedule regular health checks

### Post-Deployment

- [ ] Verify all alerts execute successfully
- [ ] Confirm notifications are delivered
- [ ] Check health status
- [ ] Review metrics
- [ ] Monitor logs for errors
- [ ] Document any issues encountered
- [ ] Update team documentation

---

## Operational Scripts

SQL Sentinel provides helper scripts for common operations:

### Build Script

```bash
./scripts/docker-build.sh
```

Builds and tags Docker images with metadata.

### Test Script

```bash
./scripts/docker-test.sh
```

Runs comprehensive container tests.

### Health Validation Script

```bash
./scripts/validate-health.sh
```

Validates health of running deployment.

---

## Additional Resources

- [Health Check API Reference](../api/health-checks.md)
- [Metrics Reference](../api/metrics.md)
- [Logging Schema](../operations/logging-schema.md)
- [Troubleshooting Guide](../operations/troubleshooting-docker.md)
- [Production Checklist](./production-checklist.md)

---

**Last Updated:** 2025-11-07
**Version:** 1.0
**Status:** Production Ready
