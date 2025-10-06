# SQL Sentinel Examples

This directory contains example configurations and sample data to help you get started with SQL Sentinel.

## Quick Start

### 1. Initialize the sample database

```bash
# Create sample data database
sqlite3 examples/sample_data.db < examples/sample_data.sql
```

### 2. Initialize SQL Sentinel state database

```bash
# Initialize SQL Sentinel internal tables (for state and history tracking)
python -m sqlsentinel.cli init --state-db sqlite:///examples/sqlsentinel.db
```

### 3. Validate your configuration

```bash
# Check that the configuration file is valid
python -m sqlsentinel.cli validate examples/alerts.yaml
```

### 4. Run alerts manually

```bash
# Run all alerts
python -m sqlsentinel.cli run examples/alerts.yaml --state-db sqlite:///examples/sqlsentinel.db

# Run a specific alert
python -m sqlsentinel.cli run examples/alerts.yaml --alert daily_revenue_check --state-db sqlite:///examples/sqlsentinel.db

# Dry run (no notifications, no state updates)
python -m sqlsentinel.cli run examples/alerts.yaml --dry-run --state-db sqlite:///examples/sqlsentinel.db
```

### 5. View execution history

```bash
# Show last 10 executions
python -m sqlsentinel.cli history examples/alerts.yaml --state-db sqlite:///examples/sqlsentinel.db

# Show history for specific alert
python -m sqlsentinel.cli history examples/alerts.yaml --alert daily_revenue_check --state-db sqlite:///examples/sqlsentinel.db

# Show last 20 executions
python -m sqlsentinel.cli history examples/alerts.yaml --limit 20 --state-db sqlite:///examples/sqlsentinel.db
```

## Example Alerts

### 1. Daily Revenue Check
- **Purpose**: Alert when yesterday's revenue falls below $10,000
- **Expected Result**: OK (sample data has $11,096.50)
- **Schedule**: Daily at 9 AM

### 2. High Error Rate
- **Purpose**: Alert when API error rate exceeds 5% in the last hour
- **Expected Result**: ALERT (sample data has 10% error rate)
- **Schedule**: Every 15 minutes

### 3. Data Freshness Check
- **Purpose**: Alert when data pipeline hasn't updated in 24 hours
- **Expected Result**: OK (sample data updated 30 minutes ago)
- **Schedule**: Every 6 hours

## Configuration Overview

The `alerts.yaml` file demonstrates:

- ✓ Multiple alert definitions
- ✓ SQL queries with CASE statements for alert logic
- ✓ Optional fields: `actual_value`, `threshold`, and context columns
- ✓ Email notification configuration
- ✓ Cron schedule expressions (for future scheduling feature)
- ✓ Enabled/disabled alerts

## Next Steps

1. **Modify the queries**: Edit `alerts.yaml` to experiment with different thresholds
2. **Add your own data**: Create your own tables in `sample_data.db`
3. **Test notifications**: Configure SMTP settings to test email alerts (see below)
4. **Connect to real databases**: Change `database.url` to connect to PostgreSQL, MySQL, etc.

## Email Notification Setup

To actually send email notifications, set these environment variables:

```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_USE_TLS=true
export SMTP_FROM_ADDRESS=alerts@example.com
```

Then run without `--dry-run`:

```bash
python -m sqlsentinel.cli run examples/alerts.yaml --state-db sqlite:///examples/sqlsentinel.db
```

## Troubleshooting

### "No such table" errors
- Make sure you ran: `sqlite3 examples/sample_data.db < examples/sample_data.sql`

### "Configuration validation failed"
- Check your YAML syntax
- Ensure all required fields are present
- Run: `python -m sqlsentinel.cli validate examples/alerts.yaml`

### "SMTP host not configured"
- Set the SMTP environment variables (see above)
- Or use `--dry-run` to test without sending emails

## File Structure

```
examples/
├── README.md              # This file
├── alerts.yaml            # Example alert configuration
├── sample_data.sql        # SQL to create sample database
├── sample_data.db         # SQLite database (created by you)
└── sqlsentinel.db         # State database (created by init command)
```
