# Slack Notifications

SQL Sentinel supports sending alerts to Slack channels via incoming webhooks. Slack notifications provide rich, formatted messages with color-coded alerts and structured information.

## Features

- Rich message formatting using Slack Block Kit
- Color-coded alerts (red for ALERT, green for OK)
- Structured display of alert details
- Optional channel and username overrides
- Automatic retry logic with exponential backoff
- Environment variable support for webhook URLs

## Setup

### 1. Create a Slack Incoming Webhook

1. Go to your Slack workspace
2. Navigate to https://api.slack.com/apps
3. Click "Create New App" → "From scratch"
4. Name your app (e.g., "SQL Sentinel") and select your workspace
5. Navigate to "Incoming Webhooks" in the left sidebar
6. Toggle "Activate Incoming Webhooks" to **On**
7. Click "Add New Webhook to Workspace"
8. Select the channel where alerts should be posted
9. Click "Allow"
10. Copy the webhook URL (format: `https://hooks.slack.com/services/...`)

### 2. Configure Environment Variable

Set the `SLACK_WEBHOOK_URL` environment variable:

```bash
# In .env file
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Or as environment variable
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### 3. Update Alert Configuration

Add Slack notifications to your alerts:

```yaml
alerts:
  - name: "high_error_rate"
    description: "Alert when error rate exceeds 5%"
    query: |
      SELECT
        CASE WHEN error_rate > 5 THEN 'ALERT' ELSE 'OK' END as status,
        error_rate as actual_value,
        5 as threshold
      FROM error_metrics
    schedule: "*/15 * * * *"
    notify:
      - channel: slack
        webhook_url: "${SLACK_WEBHOOK_URL}"
```

## Configuration Options

### Basic Configuration

```yaml
notify:
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
```

### With Channel Override

Post to a different channel than the webhook default:

```yaml
notify:
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#critical-alerts"
```

### With Username Override

Customize the bot username:

```yaml
notify:
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#alerts"
    username: "SQL Sentinel Production"
```

### Multiple Slack Channels

Send the same alert to multiple Slack channels:

```yaml
notify:
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_PRIMARY}"
    channel: "#team-alerts"

  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_ONCALL}"
    channel: "#oncall-critical"
```

## Message Format

Slack notifications include:

- **Header**: Alert name with color-coded icon (🔴 for ALERT, 🟢 for OK)
- **Status**: Current alert status with color formatting
- **Metric Details**: Actual value vs threshold (when available)
- **Context**: Additional fields from your query
- **Metadata**: Timestamp and execution information

Example ALERT message:

```
🔴 High Error Rate
Status: ALERT

Actual Value: 7.5
Threshold: 5.0

Additional Context:
  • total_requests: 1000
  • error_count: 75

Triggered at: 2024-01-15 14:30:00 UTC
```

Example OK message:

```
🟢 High Error Rate
Status: OK

Actual Value: 2.3
Threshold: 5.0

Triggered at: 2024-01-15 14:45:00 UTC
```

## Error Handling

SQL Sentinel implements robust error handling for Slack notifications:

- **Retry Logic**: 3 attempts with exponential backoff (1s, 2s, 4s)
- **Timeout**: 10-second timeout per request
- **Error Logging**: Detailed error messages for troubleshooting
- **Failure Tracking**: Notification failures recorded in state database

If a Slack notification fails after all retries:
1. The error is logged
2. The failure is recorded in the state database
3. The alert execution continues (doesn't block other notifications)

## Troubleshooting

### Common Issues

#### 1. "Invalid Slack webhook URL" Error

**Cause**: Webhook URL doesn't match the expected format

**Solution**: Ensure your webhook URL starts with `https://hooks.slack.com/services/`

```yaml
# ❌ Incorrect
webhook_url: "https://api.slack.com/..."

# ✅ Correct
webhook_url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
```

#### 2. "Channel not found" Error

**Cause**: Specified channel doesn't exist or bot doesn't have access

**Solution**:
- Verify the channel exists in your workspace
- Ensure the channel name includes the `#` prefix
- Check that the Slack app has permission to post to that channel

```yaml
# ❌ Incorrect
channel: "alerts"

# ✅ Correct
channel: "#alerts"
```

#### 3. Messages Not Appearing

**Cause**: Multiple possible issues

**Solution**:
1. Verify the webhook URL is correct
2. Check that the Slack app isn't disabled
3. Look for error messages in SQL Sentinel logs
4. Test the webhook with curl:

```bash
curl -X POST "${SLACK_WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message from SQL Sentinel"}'
```

#### 4. Environment Variable Not Resolved

**Cause**: `${SLACK_WEBHOOK_URL}` not being replaced with actual value

**Solution**:
- Ensure the environment variable is set before running SQL Sentinel
- Use `.env` file or export the variable in your shell
- For Docker, pass the variable via `-e` flag or docker-compose

```bash
# Check if variable is set
echo $SLACK_WEBHOOK_URL

# Set for current session
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Or use .env file
echo 'SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...' >> .env
```

## Best Practices

### 1. Use Different Channels for Different Severities

```yaml
# Critical alerts
notify:
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#critical-alerts"

# vs. Warning alerts
notify:
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#warnings"
```

### 2. Combine with Email for Critical Alerts

```yaml
notify:
  # Immediate Slack notification
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#oncall"

  # Email for record-keeping
  - channel: email
    recipients: ["team@company.com"]
```

### 3. Use Descriptive Usernames for Multiple Environments

```yaml
# Production
notify:
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    username: "SQL Sentinel [PROD]"

# Staging
notify:
  - channel: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
    username: "SQL Sentinel [STAGING]"
```

### 4. Avoid Notification Spam

- Use appropriate thresholds
- Leverage state tracking to prevent duplicate alerts
- Use the `silence` command during maintenance windows:

```bash
sqlsentinel silence alerts.yaml --alert high_error_rate --duration 2
```

## Testing

Test your Slack integration:

```bash
# Validate configuration
sqlsentinel validate alerts.yaml

# Dry run (doesn't send notifications)
sqlsentinel run alerts.yaml --alert high_error_rate --dry-run

# Send actual notification
sqlsentinel run alerts.yaml --alert high_error_rate
```

## Security Considerations

1. **Webhook URL Protection**
   - Never commit webhook URLs to version control
   - Use environment variables or secrets management
   - Rotate webhooks periodically

2. **Channel Permissions**
   - Create dedicated channels for alerts
   - Limit who can read sensitive alert channels
   - Use private channels for critical alerts

3. **Message Content**
   - Avoid including sensitive data in alert queries
   - Be mindful of compliance requirements (GDPR, HIPAA, etc.)
   - Consider using generic messages with links to secure dashboards

## Rate Limits

Slack incoming webhooks have rate limits:
- **Limit**: ~1 message per second per webhook
- **Recommendation**: If you have high-frequency alerts, consider batching or using different webhooks

SQL Sentinel handles rate limiting gracefully with retry logic.

## Example Configurations

See [examples/alerts-multi-channel.yaml](../../examples/alerts-multi-channel.yaml) for complete working examples.

## Related Documentation

- [Email Notifications](email.md)
- [Webhook Notifications](webhook.md)
- [Multi-Channel Alerts](multi-channel.md)
- [Slack Block Kit Documentation](https://api.slack.com/block-kit)
