# GEMINI.md

This file provides guidance to Gemini Code Assist when working in this repository.

## What is SQL Sentinel?

SQL Sentinel is a SQL-first alerting system. Users define alerts as SQL queries in YAML config files. The system runs those queries on a schedule and sends notifications (email, Slack, webhook) when the query returns `'ALERT'` status.

## Helping Users with SQL Sentinel

When a user asks you to create, modify, or troubleshoot alerts, follow these patterns.

### Alert Config Structure

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

### Query Contract

Every alert query MUST return a `status` column with value `'ALERT'` or `'OK'`. Optional columns: `actual_value`, `threshold`, plus any additional context columns.

### CLI Commands

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

### Workflow When Creating Alerts

1. Ask the user what metric/condition they want to monitor
2. Ask which database dialect (PostgreSQL, MySQL, BigQuery, SQLite, etc.)
3. Write the SQL query using the correct dialect
4. Add the alert to their YAML config
5. Run `sqlsentinel validate <config>` to verify
6. Run `sqlsentinel run <config> --alert "name" --dry-run` to test
7. Confirm results look correct before enabling notifications

### Supported Databases

SQLAlchemy-based: PostgreSQL, MySQL/MariaDB, SQLite, SQL Server, Snowflake, BigQuery, Redshift, DuckDB.

### Notification Channels

- **email**: Requires SMTP env vars (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`)
- **slack**: Requires `webhook` URL
- **webhook**: Generic HTTP POST to any `url`

---

## Development

Instructions for contributing to SQL Sentinel itself.

### Running Commands

**All commands require `poetry run` prefix** — dependencies are in a Poetry virtualenv.

```bash
poetry run pytest                        # Run tests (529 passing, 92.9% coverage)
poetry run black src/ tests/             # Format
poetry run ruff check src/ tests/        # Lint
poetry run mypy src/                     # Type check
poetry run sqlsentinel --help            # Run CLI
```

### Key Conventions

- Python 3.11+, strict mypy, Black (100 char), Ruff
- Tests in `tests/` mirroring `src/` structure
- Config validation via Pydantic v2
- All database access via SQLAlchemy
- 80% minimum test coverage enforced
