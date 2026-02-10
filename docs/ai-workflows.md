# AI Workflows Guide

SQL Sentinel is designed to work naturally with AI coding assistants like [Claude Code](https://claude.ai/code). This guide shows common patterns for using AI to create, manage, and troubleshoot alerts.

## Getting Started

Point Claude Code at your project directory containing `alerts.yaml` and your database. Then just describe what you need in plain English.

## Creating Alerts

### From a business requirement

**You:** "I need to monitor daily revenue. Alert if it drops below $10,000. Check every morning at 9 AM and email the finance team at finance@company.com."

Claude Code will:
1. Write the SQL query for your database dialect
2. Add the alert to your `alerts.yaml`
3. Run `sqlsentinel validate` to verify it works
4. Test with `sqlsentinel run --dry-run` to show what would happen

### Data quality checks

**You:** "Create an alert that checks if more than 5% of customer email addresses are NULL in the last 24 hours of signups."

```yaml
# Claude Code generates:
alerts:
  - name: "email_completeness"
    description: "Alert if >5% of new customer emails are NULL"
    query: |
      SELECT
        CASE WHEN
          (SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END)::FLOAT / COUNT(*)) * 100 > 5
        THEN 'ALERT' ELSE 'OK' END as status,
        ROUND((SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END)::FLOAT / COUNT(*)) * 100, 2) as actual_value,
        5 as threshold,
        COUNT(*) as total_signups
      FROM customers
      WHERE created_at >= CURRENT_DATE - 1
    schedule: "0 7 * * *"
    notify:
      - channel: email
        recipients: ["data-quality@company.com"]
```

### Pipeline monitoring

**You:** "Alert me if the ETL pipeline hasn't loaded data in the last 2 hours."

**You:** "Add a Slack notification to the pipeline alert too."

Claude Code iterates on the config, adding channels and refining queries based on your feedback.

## Managing Alerts

### Viewing status

- "Show me all my configured alerts"
- "What's the current state of the daily_revenue alert?"
- "Show me the execution history for the last 24 hours"

Claude Code runs the appropriate CLI commands:
```bash
sqlsentinel validate alerts.yaml     # List all alerts
sqlsentinel status alerts.yaml       # Current states
sqlsentinel history --state-db sqlite:///sqlsentinel.db  # History
```

### Silencing and unsilencing

- "Silence the inventory_low alert for 2 hours — we're doing a planned restock"
- "Unsilence all alerts, maintenance is over"

```bash
sqlsentinel silence alerts.yaml --alert "inventory_low" --duration 2
sqlsentinel unsilence alerts.yaml --alert "inventory_low"
```

### Modifying alerts

- "Change the revenue threshold from $10,000 to $12,000"
- "Add a webhook notification to the error_rate alert"
- "Disable the data_freshness alert temporarily"

Claude Code edits `alerts.yaml` directly and validates the changes.

## Troubleshooting

### Alert not firing

**You:** "The daily_revenue alert should be firing but it's showing OK. Can you check why?"

Claude Code will:
1. Read the alert query from your config
2. Run it against your database with `--dry-run`
3. Inspect the raw results
4. Identify the issue (wrong date filter, threshold too low, etc.)

### Database connection issues

**You:** "I'm getting connection errors when running my alerts."

Claude Code will:
1. Check your database URL format
2. Run `sqlsentinel validate` to surface connection errors
3. Suggest fixes (missing driver, wrong credentials, network issues)

### Notification problems

**You:** "Alerts are running but I'm not getting emails."

Claude Code will:
1. Check your SMTP environment variables
2. Run an alert without `--dry-run` and inspect the output
3. Verify notification channel configuration

## Advanced Patterns

### Multiple environments

**You:** "Set up the same alerts for staging and production databases."

Claude Code creates separate config files with different `database.url` values and shared alert definitions.

### Composite alerts

**You:** "Alert if revenue is low AND order count is also low — I only want to know if both conditions are true."

```yaml
query: |
  SELECT
    CASE WHEN SUM(revenue) < 10000 AND COUNT(*) < 50
    THEN 'ALERT' ELSE 'OK' END as status,
    SUM(revenue) as revenue,
    COUNT(*) as order_count
  FROM orders
  WHERE order_date = CURRENT_DATE - 1
```

### Time-window comparisons

**You:** "Alert if today's revenue is 30% below the same day last week."

Claude Code writes the SQL with week-over-week comparison logic appropriate for your database dialect.

## Tips

- **Be specific about your database.** Mention PostgreSQL, BigQuery, MySQL, etc. so the generated SQL uses the right dialect.
- **Describe thresholds in business terms.** "Alert if revenue drops below $10k" is clearer than "add a CASE WHEN for revenue."
- **Ask for dry runs first.** Always test with `--dry-run` before enabling notifications.
- **Iterate naturally.** Start with a basic alert and refine: "also add the order count to the notification" or "change the schedule to every 30 minutes."
