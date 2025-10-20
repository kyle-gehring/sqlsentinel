# Multi-Channel Notifications

SQL Sentinel allows you to send alerts to multiple notification channels simultaneously. This ensures critical alerts reach the right people through their preferred communication methods.

## Overview

Send a single alert to any combination of:

- **Email** - for record-keeping and detailed information
- **Slack** - for real-time team visibility
- **Webhook** - for integration with incident management systems

## Basic Multi-Channel Configuration

```yaml
alerts:
  - name: "critical_system_failure"
    description: "Critical system failure detected"
    query: |
      SELECT 'ALERT' as status
      WHERE system_status = 'down'
    schedule: "*/5 * * * *"
    notify:
      # Send to email
      - channel: email
        recipients: ["sqlsentinel@kylegehring.com"]
        subject: "CRITICAL: System Failure"

      # AND send to Slack
      - channel: slack
        webhook_url: "${SLACK_WEBHOOK_URL}"
        channel: "#critical-alerts"

      # AND trigger webhook (PagerDuty, Opsgenie, etc.)
      - channel: webhook
        url: "${PAGERDUTY_WEBHOOK}"
        method: "POST"
```

## Common Patterns

### Pattern 1: Email + Slack (Standard Alerting)

Best for: Regular operational alerts where you want both documentation and visibility

```yaml
notify:
  - channel: email
    recipients: ["team@company.com"]
    subject: "Alert: {alert_name}"

  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
```

**Benefits:**

- Email provides searchable history
- Slack ensures immediate visibility
- Team can discuss in Slack thread

### Pattern 2: Slack + Webhook (Incident Management)

Best for: Critical alerts that require immediate response and incident tracking

```yaml
notify:
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#incidents"

  - channel: webhook
    url: "${PAGERDUTY_WEBHOOK}"
    headers:
      Authorization: "Token token=${PAGERDUTY_TOKEN}"
```

**Benefits:**

- Slack for team awareness
- Webhook creates incident in PagerDuty/Opsgenie
- On-call engineer gets paged automatically

### Pattern 3: Email + Slack + Webhook (Maximum Visibility)

Best for: Business-critical systems where failure has severe impact

```yaml
notify:
  - channel: email
    recipients:
      - "executives@company.com"
      - "operations@company.com"
    subject: "URGENT: {alert_name}"

  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#executive-alerts"

  - channel: webhook
    url: "${PAGERDUTY_WEBHOOK}"
    method: "POST"
```

**Benefits:**

- Email reaches executives and creates audit trail
- Slack provides real-time visibility
- Webhook triggers incident response process

### Pattern 4: Tiered Notifications

Use different channels based on alert severity:

```yaml
# Critical alert - all channels
- name: "payment_system_down"
  query: |
    SELECT 'ALERT' as status WHERE payment_status = 'down'
  notify:
    - channel: email
      recipients: ["oncall@company.com"]
    - channel: slack
      webhook_url: "${SLACK_WEBHOOK_URL}"
      channel: "#critical"
    - channel: webhook
      url: "${PAGERDUTY_WEBHOOK}"

# Warning alert - Slack only
- name: "payment_latency_high"
  query: |
    SELECT 'ALERT' as status WHERE latency_p99 > 1000
  notify:
    - channel: slack
      webhook_url: "${SLACK_WEBHOOK_URL}"
      channel: "#warnings"
```

## Real-World Examples

### Example 1: E-commerce Transaction Monitoring

```yaml
- name: "failed_transactions"
  description: "Monitor failed payment transactions"
  query: |
    SELECT
      CASE WHEN failed_count > 10 THEN 'ALERT' ELSE 'OK' END as status,
      failed_count as actual_value,
      10 as threshold,
      total_transactions,
      failure_rate
    FROM transaction_health
  schedule: "*/5 * * * *"
  notify:
    # Email for finance team
    - channel: email
      recipients:
        - "finance@company.com"
        - "payments-team@company.com"
      subject: "Payment Alert: {actual_value} failed transactions"

    # Slack for engineering team
    - channel: slack
      webhook_url: "${SLACK_WEBHOOK_URL}"
      channel: "#payments-alerts"
      username: "Payment Monitor"

    # PagerDuty for on-call engineer
    - channel: webhook
      url: "${PAGERDUTY_WEBHOOK}"
      headers:
        Authorization: "Token token=${PAGERDUTY_TOKEN}"
        From: "sqlsentinel@kylegehring.com"
```

### Example 2: Data Quality Monitoring

```yaml
- name: "data_quality_degradation"
  description: "Alert when data quality metrics fail"
  query: |
    SELECT
      CASE WHEN null_percentage > 5 THEN 'ALERT' ELSE 'OK' END as status,
      null_percentage as actual_value,
      5 as threshold,
      affected_rows
    FROM data_quality_checks
  schedule: "0 */2 * * *"
  notify:
    # Email for data team with details
    - channel: email
      recipients:
        - "data-eng@company.com"
        - "analytics@company.com"
      subject: "Data Quality Alert: {actual_value}% null values detected"

    # Slack for immediate awareness
    - channel: slack
      webhook_url: "${SLACK_WEBHOOK_URL}"
      channel: "#data-quality"
      username: "Data Quality Monitor"
```

### Example 3: Infrastructure Monitoring

```yaml
- name: "database_connection_failure"
  description: "Alert when database connections fail"
  query: |
    SELECT
      CASE WHEN failed_connections > 5 THEN 'ALERT' ELSE 'OK' END as status,
      failed_connections as actual_value,
      5 as threshold,
      active_connections
    FROM connection_pool_metrics
  schedule: "*/2 * * * *"
  notify:
    # Slack for platform team
    - channel: slack
      webhook_url: "${SLACK_WEBHOOK_URL}"
      channel: "#platform-alerts"

    # Opsgenie for incident management
    - channel: webhook
      url: "https://api.opsgenie.com/v2/alerts"
      method: "POST"
      headers:
        Authorization: "GenieKey ${OPSGENIE_API_KEY}"

    # Email for SRE team
    - channel: email
      recipients: ["sre@company.com"]
      subject: "Database Connection Alert"
```

## Best Practices

### 1. Match Urgency to Channels

| Urgency  | Recommended Channels                |
| -------- | ----------------------------------- |
| Critical | Email + Slack + Webhook (PagerDuty) |
| High     | Slack + Email                       |
| Medium   | Slack only                          |
| Low      | Email only                          |

### 2. Avoid Notification Fatigue

```yaml
# ❌ Bad - too many channels for minor issue
- name: "minor_warning"
  query: SELECT 'ALERT' as status WHERE metric > 90
  notify:
    - channel: email
      recipients: ["everyone@company.com"]
    - channel: slack
      webhook_url: "${SLACK_WEBHOOK_URL}"
      channel: "#general"
    - channel: webhook
      url: "${PAGERDUTY_WEBHOOK}"

# ✅ Good - appropriate for severity
- name: "minor_warning"
  query: SELECT 'ALERT' as status WHERE metric > 90
  notify:
    - channel: slack
      webhook_url: "${SLACK_WEBHOOK_URL}"
      channel: "#monitoring"
```

### 3. Use Targeted Recipients

```yaml
# Specific teams for specific issues
notify:
  # Engineering team via Slack
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#engineering"

  # Business team via email
  - channel: email
    recipients: ["business-ops@company.com"]

  # On-call engineer via PagerDuty
  - channel: webhook
    url: "${PAGERDUTY_WEBHOOK}"
```

### 4. Consider Time Zones

For global teams, use multiple channels to ensure coverage:

```yaml
notify:
  # Slack for active hours visibility
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"

  # Email for async communication
  - channel: email
    recipients:
      - "us-team@company.com"
      - "eu-team@company.com"
      - "apac-team@company.com"
```

### 5. Document Your Notification Strategy

Create a runbook documenting:

- Which alerts go to which channels
- Expected response times per channel
- Escalation procedures
- On-call rotation schedule

## Notification Lifecycle

Understanding how multi-channel notifications work:

1. **Alert Executes**: SQL query runs and returns status
2. **State Check**: SQL Sentinel checks if this is a new alert (prevents duplicates)
3. **Parallel Notification**: All configured channels receive notification simultaneously
4. **Retry Logic**: Each channel independently retries on failure
5. **Failure Handling**: Failed channels don't block successful ones
6. **State Update**: Alert state updated regardless of notification success

```
┌─────────────┐
│ Alert Query │
└──────┬──────┘
       │
       ▼
┌──────────────┐
│ State Check  │◄─────── Prevents duplicate alerts
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Notify     │
│  (Parallel)  │
└──┬───┬───┬───┘
   │   │   │
   ▼   ▼   ▼
┌─────┐ ┌─────┐ ┌────────┐
│Email│ │Slack│ │Webhook │
└─────┘ └─────┘ └────────┘
```

## Debugging Multi-Channel Alerts

### Check Which Notifications Succeeded

```bash
# View execution history
sqlsentinel history alerts.yaml --alert critical_failure --limit 5
```

### Dry Run Testing

Test configuration without sending actual notifications:

```bash
# Test all channels without sending
sqlsentinel run alerts.yaml --alert critical_failure --dry-run
```

### Test Individual Channels

Create separate alerts to test each channel:

```yaml
# Test email only
- name: "test_email"
  query: SELECT 'ALERT' as status
  enabled: false
  notify:
    - channel: email
      recipients: ["sqlsentinel@kylegehring.com"]

# Test Slack only
- name: "test_slack"
  query: SELECT 'ALERT' as status
  enabled: false
  notify:
    - channel: slack
      webhook_url: "${SLACK_WEBHOOK_URL}"
```

Run with:

```bash
sqlsentinel run alerts.yaml --alert test_email
sqlsentinel run alerts.yaml --alert test_slack
```

## Cost Considerations

### Email

- Usually free or very low cost
- No rate limits for most SMTP providers
- Good for high-frequency alerts

### Slack

- Free for webhook usage
- Rate limit: ~1 message/second
- Consider batching high-frequency alerts

### Webhooks

- Cost depends on destination service
- PagerDuty/Opsgenie: Check your plan limits
- API services: May have rate limits or costs per request

## Security Best Practices

1. **Use Environment Variables**

   ```yaml
   # ❌ Bad
   webhook_url: "https://hooks.slack.com/services/T123/B456/SECRET"

   # ✅ Good
   webhook_url: "${SLACK_WEBHOOK_URL}"
   ```

2. **Separate Credentials by Environment**

   ```bash
   # Production
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/PROD/..."

   # Staging
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/STAGING/..."
   ```

3. **Use Different Channels for Different Environments**

   ```yaml
   # Production alerts → #prod-alerts
   # Staging alerts → #staging-alerts
   ```

4. **Secure Email Recipients**
   - Use distribution lists instead of individual emails
   - Review recipient lists regularly
   - Use role-based emails (oncall@, sre@, etc.)

## Example Complete Configuration

See [examples/alerts-multi-channel.yaml](../../examples/alerts-multi-channel.yaml) for a comprehensive multi-channel setup.

## Related Documentation

- [Email Notifications](email.md)
- [Slack Notifications](slack.md)
- [Webhook Notifications](webhook.md)
- [State Management & Deduplication](../state-management.md)
