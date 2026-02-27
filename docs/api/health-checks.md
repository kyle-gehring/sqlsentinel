# SQL Sentinel - Health Check API Reference

**Version:** 1.0
**Last Updated:** 2025-11-07

---

## Overview

SQL Sentinel's health check system validates the operational status of all critical components. The health check command provides both human-readable text and machine-readable JSON output for monitoring and alerting.

### Key Features

- **Database connectivity** - Validates state and alert databases
- **Notification channels** - Checks email, Slack, and webhook configuration
- **Latency measurement** - Reports connection latency in milliseconds
- **Multiple output formats** - Text and JSON for different use cases
- **Docker integration** - Used for container health checks

---

## CLI Command

### Syntax

```bash
sqlsentinel healthcheck <config_file> [OPTIONS]
```

### Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `config_file` | Path to alert configuration YAML file | Yes |

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output` | Output format: `text` or `json` | `text` |
| `--timeout` | Health check timeout in seconds | `10` |

### Examples

**Basic usage (text output):**

```bash
sqlsentinel healthcheck /app/config/alerts.yaml
```

**JSON output:**

```bash
sqlsentinel healthcheck /app/config/alerts.yaml --output json
```

**Custom timeout:**

```bash
sqlsentinel healthcheck /app/config/alerts.yaml --timeout 30
```

**Docker usage:**

```bash
docker exec sqlsentinel sqlsentinel healthcheck /app/config/alerts.yaml
```

---

## Output Formats

### Text Format

Human-readable format for terminal viewing and debugging.

**Example output:**

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

**Status symbols:**

- `✓` - Component is healthy
- `✗` - Component is unhealthy
- `⊘` - Component is not configured

### JSON Format

Machine-readable format for monitoring systems and automation.

**Example output:**

```json
{
  "status": "healthy",
  "timestamp": "2025-11-07T19:00:00.000000Z",
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
        "email": {
          "status": "healthy",
          "message": "SMTP connection OK"
        },
        "slack": {
          "status": "healthy",
          "message": "Webhook URL configured"
        },
        "webhook": {
          "status": "not_configured",
          "message": "WEBHOOK_URL not set"
        }
      }
    }
  }
}
```

---

## Health Check Components

### 1. State Database

Validates the SQLite state database used for alert deduplication and execution history.

**Checks:**

- ✅ Database file exists and is readable
- ✅ Database connection can be established
- ✅ Required tables exist (or can be created)
- ✅ Connection latency is measured

**Status values:**

- `healthy` - Database is accessible and operational
- `unhealthy` - Database connection failed or tables are missing
- `degraded` - Database is accessible but slow (>100ms latency)

**Example:**

```json
{
  "state_database": {
    "status": "healthy",
    "latency_ms": 5.09,
    "message": "Database connection OK"
  }
}
```

### 2. Alert Database

Validates the database containing the data to be monitored (PostgreSQL, BigQuery, etc.).

**Checks:**

- ✅ Database connection can be established
- ✅ Connection latency is measured
- ✅ Basic query can be executed

**Status values:**

- `healthy` - Database is accessible
- `unhealthy` - Database connection failed
- `not_configured` - `DATABASE_URL` not set
- `degraded` - Database is accessible but slow (>500ms latency)

**Example:**

```json
{
  "alert_database": {
    "status": "healthy",
    "latency_ms": 12.34,
    "message": "Connected to PostgreSQL"
  }
}
```

**Not configured example:**

```json
{
  "alert_database": {
    "status": "not_configured",
    "message": "DATABASE_URL not set"
  }
}
```

### 3. Notification Channels

Validates configuration for all notification channels.

#### Email (SMTP)

**Checks:**

- ✅ SMTP environment variables are set
- ✅ SMTP host is configured
- ✅ SMTP credentials are present

**Status values:**

- `healthy` - SMTP is configured correctly
- `not_configured` - SMTP environment variables not set
- `unhealthy` - SMTP configuration is invalid

**Example:**

```json
{
  "email": {
    "status": "healthy",
    "message": "SMTP connection OK"
  }
}
```

#### Slack

**Checks:**

- ✅ Slack webhook URL is configured
- ✅ Webhook URL format is valid

**Status values:**

- `healthy` - Slack webhook URL is configured
- `not_configured` - `SLACK_WEBHOOK_URL` not set
- `unhealthy` - Webhook URL format is invalid

**Example:**

```json
{
  "slack": {
    "status": "healthy",
    "message": "Webhook URL configured"
  }
}
```

#### Webhook

**Checks:**

- ✅ Webhook URL is configured
- ✅ Webhook URL format is valid

**Status values:**

- `healthy` - Webhook URL is configured
- `not_configured` - `WEBHOOK_URL` not set
- `unhealthy` - Webhook URL format is invalid

**Example:**

```json
{
  "webhook": {
    "status": "not_configured",
    "message": "WEBHOOK_URL not set"
  }
}
```

---

## Overall Status

The overall health status is determined by aggregating component statuses:

| Overall Status | Condition |
|---------------|-----------|
| `healthy` | All components are healthy or not_configured |
| `degraded` | At least one component is degraded |
| `unhealthy` | At least one component is unhealthy |

**Status hierarchy:** `unhealthy` > `degraded` > `healthy`

---

## Exit Codes

The health check command returns different exit codes for automation:

| Exit Code | Status | Description |
|-----------|--------|-------------|
| `0` | Success | All checks passed (healthy or not_configured) |
| `1` | Warning | Some checks are degraded |
| `2` | Error | One or more checks failed (unhealthy) |

### Usage in Scripts

```bash
#!/bin/bash

if sqlsentinel healthcheck /app/config/alerts.yaml --output json; then
  echo "System is healthy"
  exit 0
else
  echo "System is unhealthy"
  exit 1
fi
```

---

## Docker Integration

### Health Check Directive

SQL Sentinel's Dockerfile includes a health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
  CMD sqlsentinel healthcheck /app/config/alerts.yaml --output json || exit 1
```

**Parameters:**

- `interval` - Run health check every 30 seconds
- `timeout` - Fail if check takes longer than 10 seconds
- `retries` - Mark unhealthy after 3 consecutive failures
- `start_period` - Grace period during container startup

### Docker Compose

```yaml
services:
  sqlsentinel:
    image: kgehring/sqlsentinel:latest
    healthcheck:
      test: ["CMD", "sqlsentinel", "healthcheck", "/app/config/alerts.yaml", "--output", "json"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

### Checking Container Health

```bash
# View health status
docker inspect sqlsentinel --format='{{.State.Health.Status}}'

# View health logs
docker inspect sqlsentinel --format='{{json .State.Health}}' | jq
```

---

## Monitoring Integration

### Prometheus

Use a script to export health status as Prometheus metrics:

```bash
#!/bin/bash
# Export health check as Prometheus metric

HEALTH_OUTPUT=$(sqlsentinel healthcheck /app/config/alerts.yaml --output json)
STATUS=$(echo $HEALTH_OUTPUT | jq -r '.status')

if [ "$STATUS" = "healthy" ]; then
  echo "sqlsentinel_health_status 1"
else
  echo "sqlsentinel_health_status 0"
fi
```

### Alertmanager

Configure alerts on health status:

```yaml
groups:
  - name: sqlsentinel
    rules:
      - alert: SQLSentinelUnhealthy
        expr: sqlsentinel_health_status == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "SQL Sentinel is unhealthy"
          description: "SQL Sentinel has failed health checks for 5 minutes"
```

---

## Troubleshooting

### Common Issues

#### 1. State Database Unhealthy

**Symptoms:**

```json
{
  "state_database": {
    "status": "unhealthy",
    "message": "Database file not found"
  }
}
```

**Solutions:**

- Verify `/data` volume mount exists
- Check file permissions: `chmod 644 /data/state.db`
- Ensure parent directory is writable

#### 2. Alert Database Unhealthy

**Symptoms:**

```json
{
  "alert_database": {
    "status": "unhealthy",
    "message": "Connection refused"
  }
}
```

**Solutions:**

- Verify `DATABASE_URL` is correct
- Check network connectivity to database
- Verify database credentials
- Check firewall rules

#### 3. Email Not Configured

**Symptoms:**

```json
{
  "email": {
    "status": "not_configured",
    "message": "SMTP_HOST not set"
  }
}
```

**Solutions:**

- Set required environment variables:
  - `SMTP_HOST`
  - `SMTP_PORT`
  - `SMTP_USERNAME`
  - `SMTP_PASSWORD`
  - `SMTP_FROM`

#### 4. High Latency (Degraded)

**Symptoms:**

```json
{
  "alert_database": {
    "status": "degraded",
    "latency_ms": 1234.56,
    "message": "High latency detected"
  }
}
```

**Solutions:**

- Check database server load
- Verify network connectivity
- Consider moving to same region/network
- Optimize database indexes

---

## Best Practices

### 1. Regular Health Checks

Run health checks regularly to detect issues early:

```bash
# Cron job - every 5 minutes
*/5 * * * * docker exec sqlsentinel sqlsentinel healthcheck /app/config/alerts.yaml --output json
```

### 2. Alert on Health Status

Configure monitoring alerts based on health check results:

```yaml
# Alertmanager rule
- alert: HealthCheckFailing
  expr: sqlsentinel_health_status == 0
  for: 5m
```

### 3. Pre-Deployment Validation

Always run health checks before deploying configuration changes:

```bash
# Test new configuration
docker run --rm \
  -v $(pwd)/new-config.yaml:/app/config/alerts.yaml \
  -e DATABASE_URL="..." \
  kgehring/sqlsentinel:latest \
  sqlsentinel healthcheck /app/config/alerts.yaml
```

### 4. Include in CI/CD

Add health checks to deployment pipelines:

```yaml
# GitHub Actions
- name: Health Check
  run: |
    docker exec sqlsentinel sqlsentinel healthcheck /app/config/alerts.yaml --output json
    if [ $? -ne 0 ]; then
      echo "Health check failed"
      exit 1
    fi
```

---

## Related Documentation

- [Metrics API Reference](./metrics.md) - Prometheus metrics
- [Docker Deployment Guide](../deployment/docker-guide.md) - Complete deployment guide
- [Troubleshooting Guide](../operations/troubleshooting-docker.md) - Common issues

---

**Last Updated:** 2025-11-07
**Version:** 1.0
