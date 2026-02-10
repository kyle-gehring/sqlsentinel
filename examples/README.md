# SQL Sentinel Examples

This directory contains example configurations and sample data for getting started with SQL Sentinel.

## Quick Start

```bash
# Validate the example config
sqlsentinel validate examples/alerts.yaml

# Run all alerts in dry-run mode (no notifications sent)
sqlsentinel run examples/alerts.yaml --dry-run

# Run a specific alert
sqlsentinel run examples/alerts.yaml --alert daily_revenue_check --dry-run
```

## Example Configurations

### alerts.yaml — Basic Alerts (SQLite)

Three alerts using the included `sample_data.db`:

| Alert | Purpose | Expected Result | Schedule |
|-------|---------|----------------|----------|
| `daily_revenue_check` | Revenue below $10,000 | OK ($11,096.50) | Daily at 9 AM |
| `high_error_rate` | API error rate > 5% | ALERT (10%) | Every 15 min |
| `data_freshness_check` | Data not updated in 24h | OK (recent) | Every 6 hours |

### alerts-multi-channel.yaml — Multi-Channel Notifications

Demonstrates sending alerts to multiple channels simultaneously (email + Slack + webhook). Requires environment variables for webhook URLs.

### bigquery-alerts.yaml — BigQuery

BigQuery-specific alert examples. Requires Google Cloud credentials and a BigQuery dataset. See [BigQuery Setup Guide](../docs/guides/bigquery-setup.md).

## Sample Data

- **sample_data.db** — SQLite database with `orders`, `api_logs`, and `data_pipeline` tables
- **sample_data.sql** — SQL script to recreate the sample database

To rebuild the sample database:

```bash
sqlite3 examples/sample_data.db < examples/sample_data.sql
```

## Customizing

1. Copy `alerts.yaml` to your project
2. Change `database.url` to your database connection string
3. Edit the SQL queries to match your schema
4. Configure notification channels
5. Validate with `sqlsentinel validate your-config.yaml`

## File Structure

```
examples/
├── README.md                  # This file
├── alerts.yaml                # Basic SQLite example (3 alerts)
├── alerts-multi-channel.yaml  # Multi-channel notifications
├── bigquery-alerts.yaml       # BigQuery-specific examples
├── sample_data.sql            # SQL to create sample tables
└── sample_data.db             # Pre-built SQLite sample database
```
