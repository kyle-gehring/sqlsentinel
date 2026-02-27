# SQL Sentinel

[![CI](https://github.com/kyle-gehring/sqlsentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/kyle-gehring/sqlsentinel/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/sqlsentinel.svg)](https://pypi.org/project/sqlsentinel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**SQL-first alerting for data analysts.** Monitor business metrics and data quality using the SQL you already know.

```yaml
# alerts.yaml — that's all you need
database:
  url: "postgresql://user:pass@localhost/mydb"

alerts:
  - name: "Daily Revenue Check"
    query: |
      SELECT
        CASE WHEN SUM(revenue) < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        SUM(revenue) as actual_value,
        10000 as threshold
      FROM orders
      WHERE order_date = CURRENT_DATE - 1
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["team@company.com"]
```

```bash
sqlsentinel validate alerts.yaml   # Check config
sqlsentinel run alerts.yaml --dry-run  # Test without sending notifications
sqlsentinel daemon alerts.yaml     # Run on schedule
```

---

## Installation

### pip (recommended)

```bash
pip install sqlsentinel
```

### Docker

```bash
docker pull kgehring/sqlsentinel:latest
```

### From source

```bash
git clone https://github.com/kyle-gehring/sqlsentinel.git
cd sqlsentinel
pip install .
```

## Quick Start (5 minutes)

### 1. Create a config file

Create `alerts.yaml` with your database connection and alert definitions. Each alert is a SQL query that returns a `status` column with `'ALERT'` or `'OK'`:

```yaml
database:
  url: "sqlite:///mydata.db"  # Or postgresql://, mysql://, bigquery://, etc.

alerts:
  - name: "Daily Revenue Check"
    description: "Alert if yesterday's revenue is below $10,000"
    query: |
      SELECT
        CASE WHEN SUM(revenue) < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        SUM(revenue) as actual_value,
        10000 as threshold
      FROM orders
      WHERE order_date = CURRENT_DATE - 1
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["team@company.com"]
```

### 2. Validate and test

```bash
# Check your config is valid
sqlsentinel validate alerts.yaml

# Run alerts without sending notifications
sqlsentinel run alerts.yaml --dry-run

# Run a specific alert
sqlsentinel run alerts.yaml --alert "Daily Revenue Check" --dry-run
```

### 3. Run in production

```bash
# Start the daemon — runs alerts on their cron schedules
sqlsentinel daemon alerts.yaml
```

Or with Docker:

```bash
docker run -d \
  -v $(pwd)/alerts.yaml:/app/config/alerts.yaml \
  -e SMTP_HOST="smtp.gmail.com" \
  -e SMTP_USER="alerts@company.com" \
  -e SMTP_PASSWORD="your-app-password" \
  kgehring/sqlsentinel:latest
```

## Query Contract

All alert queries must return a `status` column. Everything else is optional context:

| Column | Required | Description |
|--------|----------|-------------|
| `status` | Yes | `'ALERT'` or `'OK'` |
| `actual_value` | No | The metric value |
| `threshold` | No | The threshold that was exceeded |
| *(any other)* | No | Included in notification context |

## Supported Databases

Via SQLAlchemy: **PostgreSQL**, **MySQL/MariaDB**, **SQLite**, **SQL Server**, **Snowflake**, **BigQuery**, **Redshift**, **DuckDB**

## Notification Channels

- **Email** — SMTP with configurable templates
- **Slack** — Webhook integration
- **Webhook** — Generic HTTP POST for any service

## CLI Reference

```bash
sqlsentinel validate <config>                  # Validate configuration
sqlsentinel run <config> [--alert NAME] [--dry-run]  # Run alerts
sqlsentinel daemon <config>                    # Run on schedule
sqlsentinel history [--state-db URL]           # View execution history
sqlsentinel status <config> [--state-db URL]   # Show alert states
sqlsentinel silence <config> --alert NAME      # Silence an alert
sqlsentinel unsilence <config> --alert NAME    # Unsilence an alert
sqlsentinel healthcheck <config>               # Check system health
sqlsentinel metrics                            # Prometheus metrics
sqlsentinel init <config>                      # Initialize state database
```

## AI-First Design

SQL Sentinel works naturally with AI coding assistants like [Claude Code](https://claude.ai/code). Instead of writing YAML by hand, describe what you want:

**You:** "I need an alert that checks if yesterday's revenue is below $10,000. Email me at team@company.com every morning at 9 AM."

**Claude Code will:**
1. Generate the SQL query for your database
2. Create the YAML configuration
3. Validate the alert
4. Test the database connection
5. Set up the schedule

### Common AI Tasks

- "Create an alert for daily revenue dropping below $10k"
- "Show me all my configured alerts"
- "Test the daily_revenue alert without sending notifications"
- "Silence the inventory_low alert for 2 hours"
- "What was the last execution result for my data quality alerts?"
- "Add a Slack notification to my existing revenue alert"

All of these work naturally with Claude Code — no MCP server needed. See [AI Workflows Guide](docs/ai-workflows.md) for more examples.

### Set Up Your AI Assistant

Copy a template file into your project so your AI assistant understands SQL Sentinel:

```bash
# Claude Code
cp docs/ai-setup/CLAUDE.md /path/to/your/project/

# OpenAI Codex
cp docs/ai-setup/AGENTS.md /path/to/your/project/

# Google Gemini
cp docs/ai-setup/GEMINI.md /path/to/your/project/

# GitHub Copilot
cp docs/ai-setup/copilot-instructions.md /path/to/your/project/.github/

# Cursor
cp docs/ai-setup/.cursorrules /path/to/your/project/
```

See [AI Setup Guide](docs/ai-setup/) for details.

## Examples

The [`examples/`](examples/) directory contains ready-to-run configurations:

- [`alerts.yaml`](examples/alerts.yaml) — Basic alerts with SQLite (revenue, error rate, data freshness)
- [`alerts-multi-channel.yaml`](examples/alerts-multi-channel.yaml) — Multi-channel notifications (email + Slack + webhook)
- [`bigquery-alerts.yaml`](examples/bigquery-alerts.yaml) — BigQuery-specific examples
- [`sample_data.db`](examples/sample_data.db) — Sample SQLite database for testing

Try it locally:

```bash
sqlsentinel validate examples/alerts.yaml
sqlsentinel run examples/alerts.yaml --dry-run
```

## Documentation

- [AI Workflows Guide](docs/ai-workflows.md) — Using SQL Sentinel with Claude Code
- [Docker Deployment](docs/deployment/docker-guide.md) — Production Docker setup
- [Health Checks](docs/api/health-checks.md) — Monitoring SQL Sentinel itself
- [Prometheus Metrics](docs/api/metrics.md) — Metrics export reference
- [Multi-Channel Notifications](docs/notifications/multi-channel.md) — Email, Slack, webhook setup
- [Daemon Usage](docs/guides/daemon-usage.md) — Running as a background service
- [BigQuery Setup](docs/guides/bigquery-setup.md) — Google BigQuery configuration
- [FAQ](docs/FAQ.md) — Frequently asked questions

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and PR guidelines.

## License

[MIT](LICENSE)
