# SQL Sentinel - Metrics API Reference

**Version:** 1.0
**Last Updated:** 2025-11-07

---

## Overview

SQL Sentinel collects comprehensive metrics using the Prometheus client library. Metrics are available via CLI command and can be scraped by Prometheus for visualization and alerting.

### Key Features

- **Prometheus-compatible format** - Standard exposition format
- **Alert execution metrics** - Track executions, duration, and status
- **Notification metrics** - Monitor delivery success/failure
- **System metrics** - Uptime, job count, resource usage
- **Built-in labels** - Alert names, channels, and status for filtering
- **No server required** - Metrics available via CLI

---

## CLI Command

### Syntax

```bash
sqlsentinel metrics [OPTIONS]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output` | Output format: `text` or `json` | `text` |

### Examples

**View all metrics (text format):**

```bash
sqlsentinel metrics
```

**JSON output:**

```bash
sqlsentinel metrics --output json
```

**Docker usage:**

```bash
docker exec sqlsentinel sqlsentinel metrics
```

**Filter specific metrics:**

```bash
sqlsentinel metrics | grep sqlsentinel_alerts
```

---

## Metric Categories

### 1. Alert Execution Metrics

Track alert execution counts, duration, and status.

#### `sqlsentinel_alerts_total`

**Type:** Counter
**Description:** Total number of alert executions
**Labels:**
- `alert_name` - Name of the alert
- `status` - Alert status (`ok` or `alert`)

**Example:**

```prometheus
# HELP sqlsentinel_alerts_total Total number of alert executions
# TYPE sqlsentinel_alerts_total counter
sqlsentinel_alerts_total{alert_name="daily_revenue_check",status="ok"} 150.0
sqlsentinel_alerts_total{alert_name="daily_revenue_check",status="alert"} 5.0
sqlsentinel_alerts_total{alert_name="user_signups_check",status="ok"} 200.0
```

**Usage:**

```promql
# Alert execution rate
rate(sqlsentinel_alerts_total[5m])

# Alert execution count by status
sum(sqlsentinel_alerts_total) by (status)

# Alerts with most executions
topk(5, sqlsentinel_alerts_total)
```

#### `sqlsentinel_alert_duration_seconds`

**Type:** Histogram
**Description:** Alert execution duration in seconds
**Labels:**
- `alert_name` - Name of the alert

**Buckets:** `0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0`

**Example:**

```prometheus
# HELP sqlsentinel_alert_duration_seconds Alert execution duration in seconds
# TYPE sqlsentinel_alert_duration_seconds histogram
sqlsentinel_alert_duration_seconds_bucket{alert_name="daily_revenue_check",le="0.1"} 10.0
sqlsentinel_alert_duration_seconds_bucket{alert_name="daily_revenue_check",le="0.5"} 45.0
sqlsentinel_alert_duration_seconds_bucket{alert_name="daily_revenue_check",le="1.0"} 50.0
sqlsentinel_alert_duration_seconds_bucket{alert_name="daily_revenue_check",le="+Inf"} 155.0
sqlsentinel_alert_duration_seconds_sum{alert_name="daily_revenue_check"} 75.5
sqlsentinel_alert_duration_seconds_count{alert_name="daily_revenue_check"} 155.0
```

**Usage:**

```promql
# Average execution time
rate(sqlsentinel_alert_duration_seconds_sum[5m]) / rate(sqlsentinel_alert_duration_seconds_count[5m])

# 95th percentile execution time
histogram_quantile(0.95, rate(sqlsentinel_alert_duration_seconds_bucket[5m]))

# Slow alerts (>5 seconds)
topk(5, rate(sqlsentinel_alert_duration_seconds_sum[5m]) / rate(sqlsentinel_alert_duration_seconds_count[5m]))
```

### 2. Notification Metrics

Track notification delivery success and failure rates.

#### `sqlsentinel_notifications_total`

**Type:** Counter
**Description:** Total number of notifications sent
**Labels:**
- `channel` - Notification channel (`email`, `slack`, `webhook`)
- `status` - Delivery status (`success` or `failure`)

**Example:**

```prometheus
# HELP sqlsentinel_notifications_total Total number of notifications sent
# TYPE sqlsentinel_notifications_total counter
sqlsentinel_notifications_total{channel="email",status="success"} 50.0
sqlsentinel_notifications_total{channel="email",status="failure"} 2.0
sqlsentinel_notifications_total{channel="slack",status="success"} 48.0
sqlsentinel_notifications_total{channel="slack",status="failure"} 0.0
sqlsentinel_notifications_total{channel="webhook",status="success"} 25.0
```

**Usage:**

```promql
# Notification success rate
sum(rate(sqlsentinel_notifications_total{status="success"}[5m])) / sum(rate(sqlsentinel_notifications_total[5m]))

# Failed notifications by channel
sum(sqlsentinel_notifications_total{status="failure"}) by (channel)

# Notification rate by channel
rate(sqlsentinel_notifications_total[5m])
```

#### `sqlsentinel_notification_duration_seconds`

**Type:** Histogram
**Description:** Notification delivery duration in seconds
**Labels:**
- `channel` - Notification channel

**Buckets:** `0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0`

**Example:**

```prometheus
# HELP sqlsentinel_notification_duration_seconds Notification delivery duration in seconds
# TYPE sqlsentinel_notification_duration_seconds histogram
sqlsentinel_notification_duration_seconds_bucket{channel="email",le="0.5"} 30.0
sqlsentinel_notification_duration_seconds_bucket{channel="email",le="1.0"} 45.0
sqlsentinel_notification_duration_seconds_bucket{channel="email",le="+Inf"} 52.0
sqlsentinel_notification_duration_seconds_sum{channel="email"} 25.5
sqlsentinel_notification_duration_seconds_count{channel="email"} 52.0
```

**Usage:**

```promql
# Average notification delivery time
rate(sqlsentinel_notification_duration_seconds_sum[5m]) / rate(sqlsentinel_notification_duration_seconds_count[5m])

# Slow notification channels
topk(3, rate(sqlsentinel_notification_duration_seconds_sum[5m]) / rate(sqlsentinel_notification_duration_seconds_count[5m]))
```

### 3. System Metrics

Track system-level metrics for operational monitoring.

#### `sqlsentinel_scheduler_jobs`

**Type:** Gauge
**Description:** Current number of scheduled jobs

**Example:**

```prometheus
# HELP sqlsentinel_scheduler_jobs Current number of scheduled jobs
# TYPE sqlsentinel_scheduler_jobs gauge
sqlsentinel_scheduler_jobs 5.0
```

**Usage:**

```promql
# Current job count
sqlsentinel_scheduler_jobs

# Alert if no jobs scheduled
sqlsentinel_scheduler_jobs == 0
```

#### `sqlsentinel_uptime_seconds`

**Type:** Counter
**Description:** Application uptime in seconds since start

**Example:**

```prometheus
# HELP sqlsentinel_uptime_seconds Application uptime in seconds
# TYPE sqlsentinel_uptime_seconds counter
sqlsentinel_uptime_seconds 3600.0
```

**Usage:**

```promql
# Current uptime
sqlsentinel_uptime_seconds

# Alert if uptime < 60 seconds (recent restart)
sqlsentinel_uptime_seconds < 60
```

### 4. Python Process Metrics

Standard Python process metrics automatically collected by `prometheus_client`:

#### `process_cpu_seconds_total`

**Type:** Counter
**Description:** Total CPU time consumed

#### `process_virtual_memory_bytes`

**Type:** Gauge
**Description:** Virtual memory size in bytes

#### `process_resident_memory_bytes`

**Type:** Gauge
**Description:** Resident memory size in bytes

#### `process_open_fds`

**Type:** Gauge
**Description:** Number of open file descriptors

#### `python_gc_objects_collected_total`

**Type:** Counter
**Description:** Objects collected during garbage collection
**Labels:** `generation` (0, 1, 2)

#### `python_gc_collections_total`

**Type:** Counter
**Description:** Number of garbage collection runs
**Labels:** `generation` (0, 1, 2)

---

## Output Formats

### Prometheus Format (Text)

Standard Prometheus exposition format for scraping.

**Example:**

```prometheus
# HELP sqlsentinel_alerts_total Total number of alert executions
# TYPE sqlsentinel_alerts_total counter
sqlsentinel_alerts_total{alert_name="daily_revenue_check",status="ok"} 150.0
sqlsentinel_alerts_total{alert_name="daily_revenue_check",status="alert"} 5.0

# HELP sqlsentinel_alert_duration_seconds Alert execution duration in seconds
# TYPE sqlsentinel_alert_duration_seconds histogram
sqlsentinel_alert_duration_seconds_bucket{alert_name="daily_revenue_check",le="0.1"} 10.0
sqlsentinel_alert_duration_seconds_bucket{alert_name="daily_revenue_check",le="0.5"} 45.0
sqlsentinel_alert_duration_seconds_bucket{alert_name="daily_revenue_check",le="+Inf"} 155.0
sqlsentinel_alert_duration_seconds_sum{alert_name="daily_revenue_check"} 75.5
sqlsentinel_alert_duration_seconds_count{alert_name="daily_revenue_check"} 155.0

# HELP sqlsentinel_notifications_total Total number of notifications sent
# TYPE sqlsentinel_notifications_total counter
sqlsentinel_notifications_total{channel="email",status="success"} 50.0
sqlsentinel_notifications_total{channel="email",status="failure"} 2.0

# HELP sqlsentinel_scheduler_jobs Current number of scheduled jobs
# TYPE sqlsentinel_scheduler_jobs gauge
sqlsentinel_scheduler_jobs 5.0

# HELP sqlsentinel_uptime_seconds Application uptime in seconds
# TYPE sqlsentinel_uptime_seconds counter
sqlsentinel_uptime_seconds 3600.0
```

### JSON Format

Machine-readable JSON for programmatic access.

**Example:**

```json
{
  "alerts": {
    "total": {
      "daily_revenue_check": {
        "ok": 150,
        "alert": 5
      }
    },
    "duration": {
      "daily_revenue_check": {
        "sum": 75.5,
        "count": 155,
        "avg": 0.487
      }
    }
  },
  "notifications": {
    "total": {
      "email": {
        "success": 50,
        "failure": 2
      },
      "slack": {
        "success": 48,
        "failure": 0
      }
    }
  },
  "system": {
    "scheduler_jobs": 5,
    "uptime_seconds": 3600
  }
}
```

---

## Prometheus Integration

### Scrape Configuration

Configure Prometheus to scrape SQL Sentinel metrics:

**prometheus.yml:**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'sqlsentinel'
    static_configs:
      - targets: ['sqlsentinel:8080']
    scrape_interval: 30s
    scrape_timeout: 10s
```

### Exporting Metrics

Since SQL Sentinel uses CLI-based metrics (not HTTP endpoint), use a sidecar exporter:

**metrics-exporter.sh:**

```bash
#!/bin/bash
# Export SQL Sentinel metrics to file for node_exporter

METRICS_FILE="/var/lib/node_exporter/textfile_collector/sqlsentinel.prom"

while true; do
  docker exec sqlsentinel sqlsentinel metrics > "${METRICS_FILE}.tmp"
  mv "${METRICS_FILE}.tmp" "${METRICS_FILE}"
  sleep 30
done
```

Then configure Prometheus to scrape from node_exporter with textfile collector.

---

## Alerting Rules

Example Prometheus alerting rules for SQL Sentinel:

**sqlsentinel-alerts.yml:**

```yaml
groups:
  - name: sqlsentinel
    interval: 30s
    rules:
      # Alert on high failure rate
      - alert: SQLSentinelHighFailureRate
        expr: |
          sum(rate(sqlsentinel_notifications_total{status="failure"}[5m])) /
          sum(rate(sqlsentinel_notifications_total[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "SQL Sentinel has high notification failure rate"
          description: "{{ $value | humanizePercentage }} of notifications are failing"

      # Alert on slow execution
      - alert: SQLSentinelSlowExecution
        expr: |
          histogram_quantile(0.95,
            rate(sqlsentinel_alert_duration_seconds_bucket[5m])
          ) > 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "SQL Sentinel alerts are executing slowly"
          description: "95th percentile execution time is {{ $value }}s"

      # Alert if no jobs scheduled
      - alert: SQLSentinelNoJobsScheduled
        expr: sqlsentinel_scheduler_jobs == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "SQL Sentinel has no jobs scheduled"
          description: "Scheduler is running but no alerts are scheduled"

      # Alert on recent restart
      - alert: SQLSentinelRestarted
        expr: sqlsentinel_uptime_seconds < 300
        labels:
          severity: info
        annotations:
          summary: "SQL Sentinel recently restarted"
          description: "Uptime is {{ $value }}s (< 5 minutes)"

      # Alert on notification channel failure
      - alert: SQLSentinelNotificationChannelDown
        expr: |
          sum(increase(sqlsentinel_notifications_total{status="failure"}[15m])) by (channel) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "SQL Sentinel {{ $labels.channel }} channel is failing"
          description: "{{ $value }} failures in the last 15 minutes"
```

---

## Grafana Dashboards

### Key Panels

#### 1. Alert Execution Rate

```promql
sum(rate(sqlsentinel_alerts_total[5m])) by (alert_name)
```

**Panel Type:** Graph
**Visualization:** Time series

#### 2. Alert Success Rate

```promql
sum(rate(sqlsentinel_alerts_total{status="ok"}[5m])) /
sum(rate(sqlsentinel_alerts_total[5m]))
```

**Panel Type:** Stat
**Visualization:** Percentage (0-100%)

#### 3. Average Execution Time

```promql
rate(sqlsentinel_alert_duration_seconds_sum[5m]) /
rate(sqlsentinel_alert_duration_seconds_count[5m])
```

**Panel Type:** Graph
**Visualization:** Time series (seconds)

#### 4. Notification Success Rate by Channel

```promql
sum(rate(sqlsentinel_notifications_total{status="success"}[5m])) by (channel) /
sum(rate(sqlsentinel_notifications_total[5m])) by (channel)
```

**Panel Type:** Bar gauge
**Visualization:** Percentage by channel

#### 5. System Uptime

```promql
sqlsentinel_uptime_seconds / 3600
```

**Panel Type:** Stat
**Visualization:** Hours with 2 decimals

#### 6. Scheduled Jobs

```promql
sqlsentinel_scheduler_jobs
```

**Panel Type:** Stat
**Visualization:** Number

---

## Best Practices

### 1. Label Cardinality

Avoid high-cardinality labels (e.g., execution IDs, timestamps):

**Good:**

```python
alerts_total.labels(alert_name="daily_revenue", status="ok").inc()
```

**Bad:**

```python
# DON'T DO THIS - execution_id creates infinite label combinations
alerts_total.labels(alert_name="daily_revenue", execution_id="uuid-123").inc()
```

### 2. Metric Naming

Follow Prometheus naming conventions:

- **Units suffix:** `_seconds`, `_bytes`, `_total`
- **Base unit:** Use base units (seconds not milliseconds)
- **Namespace prefix:** `sqlsentinel_` for all metrics

### 3. Histogram Buckets

Use appropriate buckets for alert execution time:

```python
# Default buckets for alert duration (in seconds)
buckets = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
```

Adjust based on your alert execution patterns.

### 4. Regular Monitoring

Monitor key metrics regularly:

- **Alert execution rate** - Detect if alerts stop running
- **Notification failure rate** - Detect delivery issues
- **Execution duration** - Detect performance degradation
- **Scheduled jobs** - Detect configuration issues

---

## Common Queries

### Alert Execution

```promql
# Total executions in last hour
increase(sqlsentinel_alerts_total[1h])

# Executions per minute
rate(sqlsentinel_alerts_total[5m]) * 60

# Alerts by status
sum(sqlsentinel_alerts_total) by (status)

# Most active alerts
topk(10, sum(rate(sqlsentinel_alerts_total[1h])) by (alert_name))
```

### Performance

```promql
# Average execution time
avg(rate(sqlsentinel_alert_duration_seconds_sum[5m]) / rate(sqlsentinel_alert_duration_seconds_count[5m]))

# Slowest alerts
topk(5, rate(sqlsentinel_alert_duration_seconds_sum[5m]) / rate(sqlsentinel_alert_duration_seconds_count[5m]))

# 99th percentile execution time
histogram_quantile(0.99, rate(sqlsentinel_alert_duration_seconds_bucket[5m]))
```

### Notifications

```promql
# Notification failure rate
sum(rate(sqlsentinel_notifications_total{status="failure"}[5m])) /
sum(rate(sqlsentinel_notifications_total[5m]))

# Failed notifications by channel
sum(sqlsentinel_notifications_total{status="failure"}) by (channel)

# Notification delivery time by channel
rate(sqlsentinel_notification_duration_seconds_sum[5m]) by (channel) /
rate(sqlsentinel_notification_duration_seconds_count[5m]) by (channel)
```

---

## Troubleshooting

### Metrics Not Available

**Check if metrics command works:**

```bash
docker exec sqlsentinel sqlsentinel metrics
```

**If command fails:**

- Verify container is running
- Check logs for errors: `docker logs sqlsentinel`
- Ensure prometheus-client is installed

### Metrics Not Updating

**Verify alerts are executing:**

```bash
docker exec sqlsentinel sqlsentinel metrics | grep alerts_total
```

**If metrics are static:**

- Check if daemon is running
- Verify alerts are scheduled correctly
- Check execution history

### Missing Labels

**Ensure labels are set correctly:**

```python
# Correct usage
alerts_total.labels(alert_name="my_alert", status="ok").inc()

# Incorrect - missing labels
alerts_total.inc()  # Labels will be empty
```

---

## Related Documentation

- [Health Check API Reference](./health-checks.md) - System health monitoring
- [Docker Deployment Guide](../deployment/docker-guide.md) - Deployment instructions
- [Logging Schema](../operations/logging-schema.md) - Log format documentation

---

**Last Updated:** 2025-11-07
**Version:** 1.0
