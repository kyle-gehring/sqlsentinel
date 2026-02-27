# Frequently Asked Questions

## General

### What is SQL Sentinel?

SQL Sentinel is a lightweight alerting system that lets you monitor business metrics and data quality using SQL queries. You define alerts in YAML, write the logic in SQL, and SQL Sentinel handles scheduling, execution, and notifications.

### Why SQL Sentinel instead of Datadog/PagerDuty/Grafana?

SQL Sentinel is for teams that:
- Already have SQL skills and don't want to learn a new query language
- Need cost-effective monitoring (no per-host or per-metric pricing)
- Want configuration-as-code that lives in Git
- Don't need a full observability platform — just SQL-based alerting

### Is there a Web UI?

Not currently. SQL Sentinel is CLI-first and designed to work with AI coding assistants. A web UI may be added in a future version.

### What's the query contract?

Every alert query must return a `status` column with the value `'ALERT'` or `'OK'`. Optionally include `actual_value`, `threshold`, and any other columns for notification context.

## Databases

### What databases are supported?

Any database with a SQLAlchemy-compatible driver: PostgreSQL, MySQL/MariaDB, SQLite, SQL Server, Snowflake, BigQuery, Redshift, and DuckDB.

### How do I connect to BigQuery?

See the [BigQuery Setup Guide](guides/bigquery-setup.md). You'll need a service account with BigQuery read access and the `google-cloud-bigquery` driver (included with SQL Sentinel).

### Can I monitor multiple databases in one config?

Currently each config file connects to one database. Use separate config files for different databases and run multiple daemon instances.

## Notifications

### How do I configure email notifications?

Set these environment variables:

```bash
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_FROM="alerts@company.com"
```

Then add email notifications to your alerts:

```yaml
notify:
  - channel: email
    recipients: ["team@company.com"]
```

### How do I set up Slack notifications?

Create a Slack incoming webhook, then add it to your alert config:

```yaml
notify:
  - channel: slack
    webhook: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

See [Slack Notifications](notifications/slack.md) for details.

### Can I send to multiple channels at once?

Yes. Add multiple entries to the `notify` list:

```yaml
notify:
  - channel: email
    recipients: ["team@company.com"]
  - channel: slack
    webhook: "${SLACK_WEBHOOK_URL}"
  - channel: webhook
    url: "https://your-service.com/alerts"
```

## Operations

### How does state management work?

SQL Sentinel uses a local SQLite database (by default `sqlsentinel.db`) to track alert execution history, current state, and silencing. This prevents duplicate notifications — if an alert is already in `ALERT` state, subsequent runs won't re-notify unless the state changes.

### How do I silence an alert during maintenance?

```bash
sqlsentinel silence alerts.yaml --alert "alert_name" --duration 2  # 2 hours
sqlsentinel unsilence alerts.yaml --alert "alert_name"  # Re-enable
```

### How do I run SQL Sentinel in production?

Use the daemon mode with Docker:

```bash
docker run -d \
  -v $(pwd)/alerts.yaml:/app/config/alerts.yaml \
  -e DATABASE_URL="postgresql://..." \
  kgehring/sqlsentinel:latest
```

See [Docker Deployment](deployment/docker-guide.md) and [Production Checklist](deployment/production-checklist.md).

### How do I monitor SQL Sentinel itself?

Use the built-in health check and Prometheus metrics:

```bash
sqlsentinel healthcheck alerts.yaml
sqlsentinel metrics
```

See [Health Checks](api/health-checks.md) and [Metrics](api/metrics.md).
