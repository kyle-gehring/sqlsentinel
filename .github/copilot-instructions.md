# SQL Sentinel — Copilot Instructions

## What is SQL Sentinel?

SQL Sentinel is a SQL-first alerting system. Users define alerts as SQL queries in YAML config files. The system runs queries on a schedule and sends notifications when the query returns `'ALERT'` status.

## Alert Config Structure

```yaml
database:
  url: "postgresql://user:pass@host/db"  # SQLAlchemy connection string

alerts:
  - name: "alert_name"
    description: "Human-readable description"
    enabled: true
    query: |
      SELECT
        CASE WHEN <condition> THEN 'ALERT' ELSE 'OK' END as status,
        <metric> as actual_value,
        <limit> as threshold
      FROM <table>
      WHERE <filters>
    schedule: "0 9 * * *"  # Cron expression
    notify:
      - channel: email
        recipients: ["team@company.com"]
      - channel: slack
        webhook: "${SLACK_WEBHOOK_URL}"
      - channel: webhook
        url: "https://example.com/hook"
```

## Query Contract

Every alert query MUST return a `status` column with value `'ALERT'` or `'OK'`. Optional columns: `actual_value`, `threshold`, plus any additional context columns.

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

SQLAlchemy-based: PostgreSQL, MySQL/MariaDB, SQLite, SQL Server, Snowflake, BigQuery, Redshift, DuckDB.

## Notification Channels

- **email**: Requires SMTP env vars (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM)
- **slack**: Requires webhook URL
- **webhook**: Generic HTTP POST to any URL

## Development

All commands require `poetry run` prefix. Tests: `poetry run pytest`. Format: `poetry run black src/ tests/`. Lint: `poetry run ruff check src/ tests/`. Type check: `poetry run mypy src/`.
