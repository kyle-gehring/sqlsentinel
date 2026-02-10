# SQL Sentinel — Copilot Instructions

This project uses [SQL Sentinel](https://github.com/kyle-gehring/sqlsentinel) for SQL-based alerting.

## Alert Config Structure

```yaml
database:
  url: "postgresql://user:pass@host/db"

alerts:
  - name: "alert_name"
    description: "Human-readable description"
    query: |
      SELECT
        CASE WHEN <condition> THEN 'ALERT' ELSE 'OK' END as status,
        <metric> as actual_value,
        <limit> as threshold
      FROM <table>
      WHERE <filters>
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["team@company.com"]
      - channel: slack
        webhook: "${SLACK_WEBHOOK_URL}"
      - channel: webhook
        url: "https://example.com/hook"
```

## Query Contract

Every alert query MUST return a `status` column with value `'ALERT'` or `'OK'`. Optional: `actual_value`, `threshold`, plus any context columns.

## CLI Commands

```bash
sqlsentinel validate <config>                        # Validate YAML config
sqlsentinel run <config> [--alert NAME] [--dry-run]  # Run alerts
sqlsentinel daemon <config>                          # Run on cron schedule
sqlsentinel history [--state-db URL]                 # Execution history
sqlsentinel status <config>                          # Alert states
sqlsentinel silence <config> --alert NAME [--duration HOURS]
sqlsentinel unsilence <config> --alert NAME
sqlsentinel healthcheck <config>                     # System health
sqlsentinel metrics                                  # Prometheus metrics
sqlsentinel init <config>                            # Init state database
```

## Supported Databases

PostgreSQL, MySQL/MariaDB, SQLite, SQL Server, Snowflake, BigQuery, Redshift, DuckDB (via SQLAlchemy).

## Notification Channels

- email: SMTP env vars (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM)
- slack: webhook URL
- webhook: generic HTTP POST
