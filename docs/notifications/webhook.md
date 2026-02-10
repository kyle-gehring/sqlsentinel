# Webhook Notifications

SQL Sentinel supports sending alerts to any webhook-compatible service via HTTP/HTTPS requests. This flexible integration allows you to connect with PagerDuty, Opsgenie, Microsoft Teams, Discord, custom APIs, and hundreds of other services.

## Features

- Support for GET, POST, PUT, and PATCH HTTP methods
- Custom headers for authentication and content negotiation
- Flexible JSON payload with alert data
- Configurable timeouts and retries
- SSL certificate verification control
- Environment variable support for sensitive data
- Response status validation

## Basic Configuration

### Minimal Configuration

```yaml
alerts:
  - name: "database_failure"
    query: |
      SELECT 'ALERT' as status FROM health_check WHERE status = 'down'
    schedule: "*/5 * * * *"
    notify:
      - channel: webhook
        url: "https://api.example.com/alerts"
```

### With Authentication

```yaml
notify:
  - channel: webhook
    url: "${WEBHOOK_URL}"
    method: "POST"
    headers:
      Authorization: "Bearer ${WEBHOOK_TOKEN}"
      Content-Type: "application/json"
```

## Configuration Options

### All Available Options

```yaml
notify:
  - channel: webhook
    # Required
    url: "https://api.example.com/alerts"

    # Optional - defaults to POST
    method: "POST" # GET, POST, PUT, or PATCH

    # Optional - custom headers
    headers:
      Authorization: "Bearer YOUR_TOKEN"
      Content-Type: "application/json"
      X-Custom-Header: "value"
```

## Payload Format

SQL Sentinel sends the following JSON payload to your webhook:

```json
{
  "alert_name": "high_error_rate",
  "description": "Alert when error rate exceeds 5%",
  "status": "ALERT",
  "actual_value": 7.5,
  "threshold": 5.0,
  "timestamp": "2024-01-15T14:30:00Z",
  "context": {
    "total_requests": 1000,
    "error_count": 75
  }
}
```

### Payload Fields

| Field          | Type          | Description                                          |
| -------------- | ------------- | ---------------------------------------------------- |
| `alert_name`   | string        | Name of the alert                                    |
| `description`  | string        | Alert description (if provided)                      |
| `status`       | string        | Current status: "ALERT" or "OK"                      |
| `actual_value` | number/string | The metric value that triggered the alert (optional) |
| `threshold`    | number/string | The threshold that was exceeded (optional)           |
| `timestamp`    | string        | ISO 8601 timestamp when alert was triggered          |
| `context`      | object        | Additional fields from your SQL query (optional)     |

## Popular Service Integrations

### PagerDuty

```yaml
notify:
  - channel: webhook
    url: "https://events.pagerduty.com/v2/enqueue"
    method: "POST"
    headers:
      Authorization: "Token token=${PAGERDUTY_TOKEN}"
      Content-Type: "application/json"
      From: "alerts@example.com"
```

**Note**: For full PagerDuty integration, you may need to transform the payload. Consider using a middleware service or PagerDuty's native webhook receiver.

### Opsgenie

```yaml
notify:
  - channel: webhook
    url: "https://api.opsgenie.com/v2/alerts"
    method: "POST"
    headers:
      Authorization: "GenieKey ${OPSGENIE_API_KEY}"
      Content-Type: "application/json"
```

### Microsoft Teams

```yaml
notify:
  - channel: webhook
    url: "${TEAMS_WEBHOOK_URL}"
    method: "POST"
    headers:
      Content-Type: "application/json"
```

### Discord

```yaml
notify:
  - channel: webhook
    url: "${DISCORD_WEBHOOK_URL}"
    method: "POST"
    headers:
      Content-Type: "application/json"
```

### Custom API

```yaml
notify:
  - channel: webhook
    url: "https://your-api.company.com/alerts"
    method: "POST"
    headers:
      Authorization: "Bearer ${API_TOKEN}"
      X-API-Version: "2024-01"
      Content-Type: "application/json"
```

## Authentication Patterns

### Bearer Token

```yaml
headers:
  Authorization: "Bearer ${API_TOKEN}"
```

### API Key Header

```yaml
headers:
  X-API-Key: "${API_KEY}"
```

### Basic Authentication

```yaml
headers:
  Authorization: "Basic ${BASE64_CREDENTIALS}"
```

Generate base64 credentials:

```bash
echo -n "username:password" | base64
```

### Token in URL

```yaml
url: "https://api.example.com/alerts?token=${API_TOKEN}"
```

## Error Handling

### Retry Logic

SQL Sentinel automatically retries failed webhook requests:

- **Default Attempts**: 3
- **Backoff**: Exponential (1s, 2s, 4s)
- **Timeout**: 10 seconds per request

### Success Criteria

A webhook call is considered successful if:

- HTTP status code is 2xx (200-299)
- Response received within timeout

### Failure Handling

If a webhook fails after all retries:

1. Error is logged with details (status code, response body)
2. Failure is recorded in state database
3. Alert execution continues (doesn't block other notifications)

## Testing

### Test with curl

Before configuring your webhook in SQL Sentinel, test it with curl:

```bash
curl -X POST "https://api.example.com/alerts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_name": "test_alert",
    "status": "ALERT",
    "actual_value": 100,
    "threshold": 50
  }'
```

### Test with SQL Sentinel

```bash
# Validate configuration
sqlsentinel validate alerts.yaml

# Dry run (doesn't send webhook)
sqlsentinel run alerts.yaml --alert my_alert --dry-run

# Send actual webhook
sqlsentinel run alerts.yaml --alert my_alert
```

## Troubleshooting

### Common Issues

#### 1. Connection Timeout

**Symptoms**: "Request timeout" errors

**Solutions**:

- Verify the webhook URL is accessible from your network
- Check firewall rules
- Ensure the service is running
- Test with curl from the same machine

#### 2. Authentication Failures

**Symptoms**: HTTP 401 or 403 errors

**Solutions**:

- Verify API token/key is correct
- Check token hasn't expired
- Ensure correct header format (Bearer, Basic, etc.)
- Test authentication with curl

```bash
# Test authentication
curl -v -X POST "https://api.example.com/alerts" \
  -H "Authorization: Bearer ${API_TOKEN}"
```

#### 3. Invalid Payload

**Symptoms**: HTTP 400 errors

**Solutions**:

- Check the service's expected payload format
- Verify Content-Type header is correct
- Review service API documentation
- Consider using a request inspector (webhook.site)

#### 4. SSL Certificate Errors

**Symptoms**: "SSL certificate verification failed"

**Solutions**:

- Ensure target service has valid SSL certificate
- Update CA certificates on your system
- For development/testing only: Note that SQL Sentinel validates SSL by default for security

#### 5. Environment Variables Not Resolved

**Symptoms**: Literal `${VARIABLE}` in requests

**Solutions**:

```bash
# Verify variable is set
echo $WEBHOOK_URL

# Set variable
export WEBHOOK_URL="https://api.example.com/alerts"

# Or use .env file
echo 'WEBHOOK_URL=https://api.example.com/alerts' >> .env
```

### Debug Tips

1. **Use webhook.site for testing**

   ```yaml
   url: "https://webhook.site/your-unique-url"
   ```

   Visit webhook.site to see the exact payload being sent

2. **Enable verbose logging**

   ```bash
   LOG_LEVEL=DEBUG sqlsentinel run alerts.yaml
   ```

3. **Check SQL Sentinel logs**
   Look for webhook-related errors with response bodies

4. **Verify with curl**
   Replicate the exact request SQL Sentinel would make

## Best Practices

### 1. Use Environment Variables for Secrets

```yaml
# ❌ Bad - secrets in config file
url: "https://api.example.com/alerts?token=secret123"

# ✅ Good - use environment variables
url: "https://api.example.com/alerts?token=${API_TOKEN}"
```

### 2. Implement Webhook Verification

On your webhook receiver:

- Validate the source of requests
- Use HTTPS endpoints
- Implement authentication
- Rate limit requests

### 3. Handle Both ALERT and OK Status

Your webhook receiver should handle both states:

```javascript
// Example webhook receiver
app.post("/alerts", (req, res) => {
  const { alert_name, status, actual_value, threshold } = req.body;

  if (status === "ALERT") {
    // Create incident
    createIncident(alert_name, actual_value, threshold);
  } else if (status === "OK") {
    // Resolve incident
    resolveIncident(alert_name);
  }

  res.status(200).json({ success: true });
});
```

### 4. Monitor Webhook Health

- Track webhook success/failure rates
- Set up alerts for webhook failures
- Monitor response times

### 5. Use Appropriate HTTP Methods

```yaml
# POST for creating new resources
method: "POST"

# PUT for updating existing resources
method: "PUT"

# PATCH for partial updates
method: "PATCH"
```

## Security Considerations

1. **Use HTTPS**

   - Always use HTTPS endpoints
   - Avoid HTTP for production workloads

2. **Secure Credentials**

   - Never commit API keys/tokens to version control
   - Use environment variables or secrets management
   - Rotate credentials regularly

3. **Validate SSL Certificates**

   - SQL Sentinel validates SSL certificates by default
   - Don't disable verification in production

4. **Rate Limiting**

   - Be aware of your webhook service's rate limits
   - Implement appropriate alert thresholds to avoid spam

5. **Sensitive Data**
   - Avoid including PII or sensitive data in webhook payloads
   - Use alerting for detection, not data transmission
   - Consider using IDs/references instead of full data

## Advanced Patterns

### Multiple Webhooks for Escalation

```yaml
notify:
  # Primary webhook
  - channel: webhook
    url: "${PRIMARY_WEBHOOK}"
    method: "POST"

  # Escalation webhook (e.g., PagerDuty)
  - channel: webhook
    url: "${ESCALATION_WEBHOOK}"
    method: "POST"
    headers:
      X-Priority: "high"
```

### Webhook with Multiple Headers

```yaml
notify:
  - channel: webhook
    url: "https://api.example.com/alerts"
    method: "POST"
    headers:
      Authorization: "Bearer ${API_TOKEN}"
      Content-Type: "application/json"
      X-Environment: "production"
      X-Service: "sqlsentinel"
      X-Alert-Priority: "high"
```

### Conditional Webhooks

Use separate alerts for different severity levels:

```yaml
# High severity
- name: "critical_error"
  query: |
    SELECT 'ALERT' as status WHERE error_count > 100
  notify:
    - channel: webhook
      url: "${CRITICAL_WEBHOOK}"

# Low severity
- name: "warning_error"
  query: |
    SELECT 'ALERT' as status WHERE error_count > 10
  notify:
    - channel: webhook
      url: "${WARNING_WEBHOOK}"
```

## Example Configurations

See [examples/alerts-multi-channel.yaml](../../examples/alerts-multi-channel.yaml) for complete working examples.

## Related Documentation

- [Email Notifications](email.md)
- [Slack Notifications](slack.md)
- [Multi-Channel Alerts](multi-channel.md)
