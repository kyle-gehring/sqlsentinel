# SQL Sentinel - Logging Schema Documentation

**Version:** 1.0
**Last Updated:** 2025-11-07

---

## Overview

SQL Sentinel uses structured JSON logging for production deployments, with a human-readable text format available for development. This document describes the log schema, configuration, and best practices for log aggregation and analysis.

### Key Features

- **Structured JSON** - Machine-readable logs for aggregation
- **Contextual fields** - Alert name, execution ID, duration, etc.
- **Configurable format** - JSON or text via environment variable
- **Log levels** - DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Consistent schema** - Predictable structure across all log entries
- **Timestamp precision** - ISO 8601 format with microseconds

---

## Configuration

### Environment Variables

| Variable | Description | Values | Default |
|----------|-------------|--------|---------|
| `LOG_LEVEL` | Minimum log level | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |
| `LOG_FORMAT` | Log output format | `json`, `text` | `json` |

### Docker Configuration

**docker-compose.yaml:**

```yaml
services:
  sqlsentinel:
    environment:
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json  # Production
```

**docker-compose.dev.yaml:**

```yaml
services:
  sqlsentinel:
    environment:
      - LOG_LEVEL=DEBUG
      - LOG_FORMAT=text  # Development
```

### Setting Log Level at Runtime

```bash
# Production: JSON logs, INFO level
docker run -e LOG_LEVEL=INFO -e LOG_FORMAT=json sqlsentinel/sqlsentinel:latest

# Development: Text logs, DEBUG level
docker run -e LOG_LEVEL=DEBUG -e LOG_FORMAT=text sqlsentinel/sqlsentinel:latest
```

---

## JSON Log Schema

### Standard Fields

Every JSON log entry includes these standard fields:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `timestamp` | string | ISO 8601 timestamp with microseconds | `"2025-11-07T19:00:00.123456Z"` |
| `level` | string | Log level | `"INFO"` |
| `logger` | string | Logger name (module path) | `"sqlsentinel.executor.alert_executor"` |
| `message` | string | Human-readable message | `"Alert execution completed"` |

### Contextual Fields

Contextual information is included in the `context` object when available:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `alert_name` | string | Name of the alert | `"daily_revenue_check"` |
| `execution_id` | string | Unique execution ID (UUID) | `"550e8400-e29b-41d4-a716-446655440000"` |
| `status` | string | Alert status | `"ALERT"` or `"OK"` |
| `duration_ms` | float | Execution duration in milliseconds | `123.45` |
| `actual_value` | number | Metric value from query | `8500` |
| `threshold` | number | Alert threshold | `10000` |
| `channel` | string | Notification channel | `"email"`, `"slack"`, `"webhook"` |
| `recipients` | array | Notification recipients | `["team@company.com"]` |
| `error` | string | Error message (if applicable) | `"Connection timeout"` |
| `traceback` | string | Stack trace (for errors) | `"Traceback (most recent call last)..."` |

### Example Log Entries

#### Alert Execution Started

```json
{
  "timestamp": "2025-11-07T19:00:00.000000Z",
  "level": "INFO",
  "logger": "sqlsentinel.executor.alert_executor",
  "message": "Starting alert execution",
  "context": {
    "alert_name": "daily_revenue_check",
    "execution_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### Alert Execution Completed

```json
{
  "timestamp": "2025-11-07T19:00:01.234567Z",
  "level": "INFO",
  "logger": "sqlsentinel.executor.alert_executor",
  "message": "Alert execution completed",
  "context": {
    "alert_name": "daily_revenue_check",
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "ALERT",
    "duration_ms": 123.45,
    "actual_value": 8500,
    "threshold": 10000
  }
}
```

#### Notification Sent

```json
{
  "timestamp": "2025-11-07T19:00:01.500000Z",
  "level": "INFO",
  "logger": "sqlsentinel.notifications.email",
  "message": "Email notification sent successfully",
  "context": {
    "alert_name": "daily_revenue_check",
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "channel": "email",
    "recipients": ["team@company.com"],
    "duration_ms": 45.67
  }
}
```

#### Error Log

```json
{
  "timestamp": "2025-11-07T19:00:02.000000Z",
  "level": "ERROR",
  "logger": "sqlsentinel.executor.alert_executor",
  "message": "Alert execution failed",
  "context": {
    "alert_name": "daily_revenue_check",
    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
    "error": "Connection timeout",
    "traceback": "Traceback (most recent call last):\n  File \"alert_executor.py\", line 123, in execute\n    ..."
  }
}
```

#### Scheduler Activity

```json
{
  "timestamp": "2025-11-07T19:00:00.000000Z",
  "level": "INFO",
  "logger": "sqlsentinel.scheduler.scheduler",
  "message": "Scheduled job added",
  "context": {
    "alert_name": "daily_revenue_check",
    "schedule": "0 9 * * *",
    "next_run": "2025-11-08T09:00:00Z"
  }
}
```

---

## Text Log Format

Text logs are human-readable and formatted for terminal viewing.

### Format

```
[TIMESTAMP] [LEVEL] [LOGGER] MESSAGE [CONTEXT]
```

### Examples

**Alert execution:**

```
[2025-11-07 19:00:00,000] [INFO] [sqlsentinel.executor.alert_executor] Starting alert execution alert_name=daily_revenue_check execution_id=550e8400-e29b-41d4-a716-446655440000
[2025-11-07 19:00:01,234] [INFO] [sqlsentinel.executor.alert_executor] Alert execution completed alert_name=daily_revenue_check status=ALERT duration_ms=123.45 actual_value=8500 threshold=10000
```

**Notification sent:**

```
[2025-11-07 19:00:01,500] [INFO] [sqlsentinel.notifications.email] Email notification sent successfully alert_name=daily_revenue_check channel=email recipients=['team@company.com']
```

**Error:**

```
[2025-11-07 19:00:02,000] [ERROR] [sqlsentinel.executor.alert_executor] Alert execution failed alert_name=daily_revenue_check error='Connection timeout'
Traceback (most recent call last):
  File "alert_executor.py", line 123, in execute
    ...
```

---

## Log Levels

### DEBUG

**Purpose:** Detailed diagnostic information
**Use case:** Development and troubleshooting
**Volume:** High

**Examples:**

- Query parameters and SQL text
- Configuration values loaded
- Detailed execution flow
- Cache hits/misses

```json
{
  "timestamp": "2025-11-07T19:00:00.123456Z",
  "level": "DEBUG",
  "logger": "sqlsentinel.database.adapter",
  "message": "Executing query",
  "context": {
    "query": "SELECT CASE WHEN SUM(revenue) < 10000 THEN 'ALERT' ELSE 'OK' END as status FROM orders",
    "parameters": {}
  }
}
```

### INFO

**Purpose:** General informational messages
**Use case:** Production monitoring
**Volume:** Medium

**Examples:**

- Alert executions started/completed
- Notifications sent
- Scheduler activity
- Configuration loaded

```json
{
  "timestamp": "2025-11-07T19:00:00.123456Z",
  "level": "INFO",
  "logger": "sqlsentinel.executor.alert_executor",
  "message": "Alert execution completed",
  "context": {
    "alert_name": "daily_revenue_check",
    "status": "OK"
  }
}
```

### WARNING

**Purpose:** Warning messages for potentially harmful situations
**Use case:** Monitoring for issues
**Volume:** Low

**Examples:**

- Slow query execution
- Retry attempts
- Deprecated configuration
- High memory usage

```json
{
  "timestamp": "2025-11-07T19:00:00.123456Z",
  "level": "WARNING",
  "logger": "sqlsentinel.executor.alert_executor",
  "message": "Alert execution took longer than expected",
  "context": {
    "alert_name": "daily_revenue_check",
    "duration_ms": 30000,
    "threshold_ms": 10000
  }
}
```

### ERROR

**Purpose:** Error events that might allow the application to continue
**Use case:** Critical monitoring
**Volume:** Very Low (ideally)

**Examples:**

- Database connection failures
- Query execution errors
- Notification delivery failures
- Configuration errors

```json
{
  "timestamp": "2025-11-07T19:00:00.123456Z",
  "level": "ERROR",
  "logger": "sqlsentinel.notifications.email",
  "message": "Failed to send email notification",
  "context": {
    "alert_name": "daily_revenue_check",
    "channel": "email",
    "error": "SMTP authentication failed",
    "traceback": "..."
  }
}
```

### CRITICAL

**Purpose:** Critical errors that may cause application failure
**Use case:** Immediate action required
**Volume:** Extremely Low (ideally)

**Examples:**

- State database corruption
- Scheduler crashes
- Unrecoverable errors

```json
{
  "timestamp": "2025-11-07T19:00:00.123456Z",
  "level": "CRITICAL",
  "logger": "sqlsentinel.scheduler.scheduler",
  "message": "Scheduler failed to start",
  "context": {
    "error": "Unable to initialize APScheduler",
    "traceback": "..."
  }
}
```

---

## Log Aggregation

### ELK Stack (Elasticsearch, Logstash, Kibana)

#### Logstash Configuration

**logstash.conf:**

```ruby
input {
  docker {
    host => "unix:///var/run/docker.sock"
    port => 5000
    codec => json
  }
}

filter {
  # Parse timestamp
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }

  # Extract context fields to root level
  if [context] {
    ruby {
      code => "
        event.get('context').each do |key, value|
          event.set(key, value)
        end
      "
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "sqlsentinel-%{+YYYY.MM.dd}"
  }
}
```

#### Kibana Queries

**All alert executions:**

```
logger: "sqlsentinel.executor.alert_executor" AND message: "Alert execution completed"
```

**Failed notifications:**

```
logger: "sqlsentinel.notifications.*" AND level: "ERROR"
```

**Slow executions (>10s):**

```
context.duration_ms > 10000
```

### Loki (Grafana Loki)

#### Docker Compose

```yaml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/config.yaml
    command: -config.file=/etc/loki/config.yaml

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./promtail-config.yaml:/etc/promtail/config.yaml
    command: -config.file=/etc/promtail/config.yaml
```

#### LogQL Queries

**All logs from SQL Sentinel:**

```logql
{container_name="sqlsentinel"}
```

**Alert executions:**

```logql
{container_name="sqlsentinel"} |= "Alert execution completed"
```

**Error logs:**

```logql
{container_name="sqlsentinel"} | json | level="ERROR"
```

**Logs for specific alert:**

```logql
{container_name="sqlsentinel"} | json | alert_name="daily_revenue_check"
```

### CloudWatch Logs

#### Docker Log Driver

```yaml
services:
  sqlsentinel:
    logging:
      driver: awslogs
      options:
        awslogs-region: us-east-1
        awslogs-group: /ecs/sqlsentinel
        awslogs-stream: sqlsentinel
```

#### CloudWatch Insights Queries

**All alert executions:**

```
fields @timestamp, context.alert_name, context.status, context.duration_ms
| filter logger = "sqlsentinel.executor.alert_executor"
| filter message = "Alert execution completed"
| sort @timestamp desc
```

**Error rate over time:**

```
fields @timestamp
| filter level = "ERROR"
| stats count() by bin(5m)
```

**Average execution time by alert:**

```
fields context.alert_name, context.duration_ms
| filter message = "Alert execution completed"
| stats avg(context.duration_ms) by context.alert_name
```

---

## Best Practices

### 1. Use JSON Format in Production

Always use JSON format for production deployments:

```yaml
environment:
  - LOG_FORMAT=json
```

**Benefits:**

- Structured data for aggregation
- Easy to parse and query
- Consistent schema
- Integrates with log aggregators

### 2. Set Appropriate Log Level

**Production:** `INFO` or `WARNING`

```yaml
environment:
  - LOG_LEVEL=INFO
```

**Development:** `DEBUG`

```yaml
environment:
  - LOG_LEVEL=DEBUG
```

**Critical systems:** `WARNING` (reduce noise)

### 3. Include Contextual Fields

Always include relevant context in log messages:

```python
logger.info(
    "Alert execution completed",
    extra={
        "alert_name": alert.name,
        "status": result.status,
        "duration_ms": duration
    }
)
```

### 4. Log at Appropriate Levels

| Level | When to Use |
|-------|-------------|
| DEBUG | Detailed flow, SQL queries, parameters |
| INFO | Normal operations (executions, notifications) |
| WARNING | Potential issues (retries, slow queries) |
| ERROR | Failures that need attention |
| CRITICAL | System-threatening issues |

### 5. Configure Log Rotation

**Docker logging:**

```yaml
services:
  sqlsentinel:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### 6. Monitor Log Volume

Track log volume to avoid storage issues:

```bash
# Check log file sizes
docker logs sqlsentinel 2>&1 | wc -l

# Monitor log growth
docker stats sqlsentinel --format "{{.Container}}: {{.BlockIO}}"
```

---

## Common Queries

### Finding Specific Executions

**By execution ID:**

```bash
docker logs sqlsentinel | jq 'select(.context.execution_id == "550e8400-...")'
```

**By alert name:**

```bash
docker logs sqlsentinel | jq 'select(.context.alert_name == "daily_revenue_check")'
```

### Analyzing Errors

**All errors:**

```bash
docker logs sqlsentinel | jq 'select(.level == "ERROR")'
```

**Errors by logger:**

```bash
docker logs sqlsentinel | jq 'select(.level == "ERROR") | .logger' | sort | uniq -c
```

**Recent errors (last 100 lines):**

```bash
docker logs sqlsentinel --tail 100 | jq 'select(.level == "ERROR")'
```

### Performance Analysis

**Execution times:**

```bash
docker logs sqlsentinel | jq 'select(.message == "Alert execution completed") | {alert: .context.alert_name, duration: .context.duration_ms}'
```

**Slowest executions:**

```bash
docker logs sqlsentinel | jq 'select(.context.duration_ms != null) | {alert: .context.alert_name, duration: .context.duration_ms}' | jq -s 'sort_by(.duration) | reverse | .[0:10]'
```

---

## Troubleshooting

### Logs Not in JSON Format

**Check LOG_FORMAT environment variable:**

```bash
docker exec sqlsentinel printenv LOG_FORMAT
```

**Should return:** `json`

**Fix:**

```yaml
environment:
  - LOG_FORMAT=json
```

### Missing Context Fields

**Verify logger is using structured logging:**

```python
# Correct
logger.info("Message", extra={"alert_name": "test"})

# Incorrect
logger.info(f"Message: {alert_name}")  # No structured context
```

### Log Volume Too High

**Increase log level to reduce volume:**

```yaml
environment:
  - LOG_LEVEL=WARNING  # Only warnings and errors
```

**Configure log rotation:**

```yaml
logging:
  options:
    max-size: "5m"
    max-file: "2"
```

---

## Related Documentation

- [Docker Deployment Guide](../deployment/docker-guide.md) - Container configuration
- [Health Check API](../api/health-checks.md) - Health monitoring
- [Metrics API](../api/metrics.md) - Prometheus metrics

---

**Last Updated:** 2025-11-07
**Version:** 1.0
