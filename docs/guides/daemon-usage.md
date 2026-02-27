# SQL Sentinel Daemon Usage Guide

**Version:** 0.1.0
**Last Updated:** 2025-10-20
**Audience:** Data analysts, DevOps engineers, System administrators

---

## Overview

The SQL Sentinel daemon runs as a background service that automatically executes alerts based on their cron schedules. This guide covers everything you need to know to run, configure, and manage the daemon.

---

## Quick Start

### Local Development

```bash
# 1. Set up environment
export DATABASE_URL="postgresql://user:pass@localhost:5432/mydb"
export SMTP_HOST="smtp.gmail.com"
export SMTP_USERNAME="alerts@company.com"
export SMTP_PASSWORD="your-password"

# 2. Create alerts configuration
cat > alerts.yaml << 'EOF'
alerts:
  - name: "daily_revenue_check"
    description: "Alert when daily revenue falls below threshold"
    enabled: true
    query: |
      SELECT
        CASE WHEN SUM(revenue) < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        SUM(revenue) as actual_value,
        10000 as threshold
      FROM orders
      WHERE date = CURRENT_DATE - 1
    schedule: "0 9 * * *"  # 9 AM daily
    notify:
      - channel: email
        recipients: ["finance@company.com"]
EOF

# 3. Initialize state database
poetry run sqlsentinel init --state-db sqlite:///state.db

# 4. Start daemon
poetry run sqlsentinel daemon alerts.yaml \
  --state-db sqlite:///state.db \
  --reload \
  --log-level INFO
```

### Docker Deployment

```bash
# 1. Create .env file
cat > .env << 'EOF'
DATABASE_URL=postgresql://user:pass@db-host:5432/mydb
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=alerts@company.com
SMTP_PASSWORD=your-password
STATE_DB_URL=sqlite:////app/state/state.db
TIMEZONE=UTC
LOG_LEVEL=INFO
EOF

# 2. Run container
docker run -d \
  --name sqlsentinel \
  --restart unless-stopped \
  -v $(pwd)/alerts.yaml:/app/config/alerts.yaml:ro \
  -v sqlsentinel-state:/app/state \
  --env-file .env \
  kgehring/sqlsentinel:latest

# 3. View logs
docker logs -f sqlsentinel

# 4. Stop daemon
docker stop sqlsentinel
```

---

## Command Reference

### Daemon Command

```bash
sqlsentinel daemon CONFIG_FILE [OPTIONS]
```

#### Required Arguments

- `CONFIG_FILE` - Path to YAML configuration file containing alerts

#### Optional Arguments

| Flag | Description | Default |
|------|-------------|---------|
| `--state-db TEXT` | State database URL | `sqlite:///sqlsentinel.db` |
| `--database-url TEXT` | Database URL for alert queries | From `DATABASE_URL` env var |
| `--reload` | Watch config file for changes | Disabled |
| `--log-level TEXT` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `--timezone TEXT` | Timezone for scheduling | `UTC` |

#### Examples

**Basic usage:**
```bash
sqlsentinel daemon /config/alerts.yaml
```

**With all options:**
```bash
sqlsentinel daemon /config/alerts.yaml \
  --state-db postgresql://user:pass@localhost:5432/state \
  --database-url postgresql://user:pass@localhost:5432/analytics \
  --reload \
  --log-level DEBUG \
  --timezone "America/New_York"
```

**Using environment variables:**
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/analytics"
export STATE_DB_URL="sqlite:///state.db"
export TIMEZONE="UTC"

sqlsentinel daemon alerts.yaml --reload
```

---

## Configuration

### Alert Configuration File

The daemon watches a YAML file containing alert definitions:

```yaml
alerts:
  - name: "unique_alert_name"
    description: "Human-readable description"
    enabled: true              # Set to false to disable
    query: |
      SELECT
        CASE WHEN condition THEN 'ALERT' ELSE 'OK' END as status,
        metric_value as actual_value,
        threshold_value as threshold
      FROM your_table
    schedule: "0 9 * * *"      # Cron expression
    notify:
      - channel: email
        recipients: ["team@company.com"]
      - channel: slack
        webhook_url: "${SLACK_WEBHOOK_URL}"
```

### Schedule Syntax

SQL Sentinel uses standard cron syntax:

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday = 0)
│ │ │ │ │
* * * * *
```

**Common Patterns:**

| Pattern | Meaning | Example Use Case |
|---------|---------|------------------|
| `0 9 * * *` | Daily at 9 AM | Daily revenue check |
| `*/15 * * * *` | Every 15 minutes | High-frequency monitoring |
| `0 */6 * * *` | Every 6 hours | Periodic health checks |
| `0 0 * * 0` | Weekly on Sunday | Weekly summary |
| `0 0 1 * *` | Monthly on 1st | Monthly reports |
| `0 9 * * 1-5` | Weekdays at 9 AM | Business days only |
| `0 0,12 * * *` | Twice daily (midnight & noon) | Bi-daily checks |

**Testing Schedules:**

Use [crontab.guru](https://crontab.guru/) to validate and test cron expressions.

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `DATABASE_URL` | Database connection for alert queries | Yes* | `postgresql://user:pass@host/db` |
| `STATE_DB_URL` | State database connection | No | `sqlite:///state.db` |
| `TIMEZONE` | Timezone for scheduling | No | `America/New_York` |
| `LOG_LEVEL` | Logging verbosity | No | `INFO` |
| `SMTP_HOST` | Email server (for email notifications) | If using email | `smtp.gmail.com` |
| `SMTP_PORT` | Email server port | No | `587` |
| `SMTP_USERNAME` | Email authentication username | If using email | `alerts@company.com` |
| `SMTP_PASSWORD` | Email authentication password | If using email | `secret` |
| `SMTP_FROM_EMAIL` | From address for emails | If using email | `sqlsentinel@company.com` |
| `SMTP_USE_TLS` | Enable TLS for email | No | `true` |
| `SLACK_WEBHOOK_URL` | Slack webhook (for Slack notifications) | If using Slack | `https://hooks.slack.com/...` |

\* Required unless passed via `--database-url` CLI flag

---

## Running the Daemon

### Foreground Mode

Run in foreground to see logs in real-time:

```bash
sqlsentinel daemon alerts.yaml --log-level INFO
```

Press `Ctrl+C` to stop gracefully.

### Background Mode (systemd)

**Create systemd service file:** `/etc/systemd/system/sqlsentinel.service`

```ini
[Unit]
Description=SQL Sentinel Alert Daemon
After=network.target postgresql.service

[Service]
Type=simple
User=sqlsentinel
Group=sqlsentinel
WorkingDirectory=/opt/sqlsentinel
Environment="DATABASE_URL=postgresql://user:pass@localhost/analytics"
Environment="STATE_DB_URL=sqlite:////var/lib/sqlsentinel/state.db"
Environment="SMTP_HOST=smtp.company.com"
Environment="SMTP_USERNAME=alerts@company.com"
EnvironmentFile=/etc/sqlsentinel/secrets.env
ExecStart=/usr/local/bin/sqlsentinel daemon \
  /etc/sqlsentinel/alerts.yaml \
  --state-db ${STATE_DB_URL} \
  --reload \
  --log-level INFO
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Manage service:**

```bash
# Enable and start
sudo systemctl enable sqlsentinel
sudo systemctl start sqlsentinel

# View status
sudo systemctl status sqlsentinel

# View logs
sudo journalctl -u sqlsentinel -f

# Restart
sudo systemctl restart sqlsentinel

# Stop
sudo systemctl stop sqlsentinel
```

### Background Mode (Docker)

See Docker Deployment in Quick Start section above.

**Docker Compose:**

```yaml
version: '3.8'

services:
  sqlsentinel:
    image: sqlsentinel:latest
    container_name: sqlsentinel
    restart: unless-stopped
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - STATE_DB_URL=sqlite:////app/state/state.db
      - TIMEZONE=UTC
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_USERNAME=${SMTP_USERNAME}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
    volumes:
      - ./alerts.yaml:/app/config/alerts.yaml:ro
      - sqlsentinel-state:/app/state
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  sqlsentinel-state:
```

```bash
docker-compose up -d
docker-compose logs -f sqlsentinel
```

---

## Configuration Hot Reload

The daemon supports automatic configuration reloading when the config file changes.

### Enable Auto-Reload

```bash
sqlsentinel daemon alerts.yaml --reload
```

### How It Works

1. Watchdog monitors the config file
2. When file is modified, reload is triggered (after 2-second debounce)
3. New configuration is validated
4. Jobs are updated:
   - Removed alerts → jobs deleted
   - New alerts → jobs added
   - Changed alerts → jobs updated
5. Scheduler continues running (no restart needed)

### Making Changes

```bash
# 1. Edit config file
vim alerts.yaml

# 2. Save changes

# 3. Check logs for reload confirmation
# You should see:
#   "Configuration file changed, reloading..."
#   "Configuration reloaded. Active jobs: N"
```

### Rollback on Error

If the new configuration is invalid:
- Error is logged
- Old configuration remains active
- Daemon continues running

```
ERROR - Failed to reload configuration: Invalid cron schedule: 0 25 * * *
INFO - Continuing with existing configuration
```

---

## Monitoring

### Log Output

The daemon produces structured logs:

```
2025-10-20 09:00:00 - sqlsentinel.cli - INFO - Starting SQL Sentinel daemon...
2025-10-20 09:00:00 - sqlsentinel.cli - INFO - Configuration file: /config/alerts.yaml
2025-10-20 09:00:00 - sqlsentinel.cli - INFO - State database: sqlite:///state.db
2025-10-20 09:00:00 - sqlsentinel.cli - INFO - Alert database: postgresql://user@host/db
2025-10-20 09:00:00 - sqlsentinel.cli - INFO - Timezone: UTC
2025-10-20 09:00:00 - sqlsentinel.cli - INFO - Config reload: enabled
2025-10-20 09:00:00 - sqlsentinel.scheduler - INFO - Scheduler started successfully
2025-10-20 09:00:00 - sqlsentinel.scheduler - INFO - Scheduled 3 jobs:
2025-10-20 09:00:00 - sqlsentinel.scheduler - INFO -   - daily_revenue: next run at 2025-10-21 09:00:00
2025-10-20 09:00:00 - sqlsentinel.scheduler - INFO -   - api_errors: next run at 2025-10-20 09:15:00
2025-10-20 09:00:00 - sqlsentinel.scheduler - INFO -   - data_freshness: next run at 2025-10-20 10:00:00
2025-10-20 09:00:00 - sqlsentinel.cli - INFO - SQL Sentinel daemon running. Press Ctrl+C to stop.

# When alert executes:
2025-10-20 09:15:00 - sqlsentinel.scheduler - INFO - Executing scheduled alert: api_errors
2025-10-20 09:15:01 - sqlsentinel.scheduler - INFO - Alert 'api_errors' executed successfully: status=success, duration=1234.56ms
```

### Log Levels

| Level | When to Use | What You'll See |
|-------|-------------|-----------------|
| `DEBUG` | Development, troubleshooting | All messages including internal details |
| `INFO` | Production (recommended) | Startup, job executions, config changes |
| `WARNING` | Production (quiet) | Only warnings and errors |
| `ERROR` | Production (silent unless errors) | Only errors |

**Change log level:**

```bash
# Via CLI flag
sqlsentinel daemon alerts.yaml --log-level DEBUG

# Via environment variable
export LOG_LEVEL=DEBUG
sqlsentinel daemon alerts.yaml
```

### Viewing Execution History

```bash
# Show last 10 executions
sqlsentinel history alerts.yaml --limit 10

# Show executions for specific alert
sqlsentinel history alerts.yaml --alert daily_revenue

# Show last 50 executions
sqlsentinel history alerts.yaml --limit 50
```

**Example output:**
```
Execution History
================================================================================
Timestamp            Alert Name              Status    Result  Duration
--------------------------------------------------------------------------------
2025-10-20 09:15:01  api_errors             success   OK      1.23s
2025-10-20 09:00:03  daily_revenue          success   ALERT   2.45s
2025-10-19 09:00:02  daily_revenue          success   OK      2.31s
```

### Health Monitoring

**Check daemon is running:**

```bash
# systemd
systemctl is-active sqlsentinel

# Docker
docker ps | grep sqlsentinel

# Process
pgrep -f "sqlsentinel daemon"
```

**Check logs for errors:**

```bash
# systemd
journalctl -u sqlsentinel --since "1 hour ago" | grep ERROR

# Docker
docker logs sqlsentinel --since 1h | grep ERROR
```

---

## Graceful Shutdown

The daemon handles shutdown signals properly to avoid data corruption.

### Shutdown Process

1. Receive signal (SIGTERM or SIGINT)
2. Stop accepting new job triggers
3. Wait for currently executing jobs to complete (up to timeout)
4. Stop config file watcher
5. Close database connections
6. Exit with code 0

### Initiating Shutdown

**Foreground mode:**
```bash
Ctrl+C
```

**systemd:**
```bash
sudo systemctl stop sqlsentinel
```

**Docker:**
```bash
docker stop sqlsentinel  # Sends SIGTERM, waits 10s, then SIGKILL
```

**Manual signal:**
```bash
kill -TERM $(pgrep -f "sqlsentinel daemon")
```

### Shutdown Logs

```
INFO - Received SIGTERM signal, initiating graceful shutdown...
INFO - Shutting down scheduler...
INFO - Scheduler stopped
INFO - Stopping config watcher...
INFO - Config file watcher stopped
INFO - SQL Sentinel daemon stopped
```

---

## Production Deployment Patterns

### Pattern 1: Single Container (Small Scale)

**Best for:** < 100 alerts, single database

```
Docker Container (sqlsentinel:latest)
├── Daemon process
├── Alert configs (mounted volume)
├── State database (persistent volume)
└── Logs (stdout → Docker logs)
```

**Pros:**
- Simple deployment
- Easy to manage
- Low resource usage

**Cons:**
- Single point of failure
- Limited scalability

### Pattern 2: Kubernetes Deployment (Medium Scale)

**Best for:** 100-1000 alerts, high availability

```
Kubernetes Cluster
├── Deployment (replicas: 1)
│   └── Pod (sqlsentinel container)
├── PersistentVolumeClaim (state database)
├── ConfigMap (alerts.yaml)
└── Secret (credentials)
```

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sqlsentinel
spec:
  replicas: 1  # Single replica (no distributed locking yet)
  selector:
    matchLabels:
      app: sqlsentinel
  template:
    metadata:
      labels:
        app: sqlsentinel
    spec:
      containers:
      - name: sqlsentinel
        image: sqlsentinel:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: sqlsentinel-secrets
              key: database-url
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: state
          mountPath: /app/state
      volumes:
      - name: config
        configMap:
          name: sqlsentinel-config
      - name: state
        persistentVolumeClaim:
          claimName: sqlsentinel-state
```

### Pattern 3: Multi-Instance (Future - Phase 2)

**Best for:** > 1000 alerts, distributed execution

```
Load Balancer
├── Instance 1 (leader)
├── Instance 2 (standby)
└── Instance 3 (standby)
     ↓
Shared Job Store (PostgreSQL/Redis)
```

**Note:** Requires Phase 2 implementation (persistent job store + leader election)

---

## Timezone Management

### Setting Timezone

**Global (all alerts):**
```bash
sqlsentinel daemon alerts.yaml --timezone "America/New_York"
```

**Environment variable:**
```bash
export TIMEZONE="Europe/London"
sqlsentinel daemon alerts.yaml
```

**Docker:**
```bash
docker run -d \
  -e TIMEZONE="Asia/Tokyo" \
  kgehring/sqlsentinel:latest
```

### Common Timezones

| Timezone | UTC Offset | Example City |
|----------|------------|--------------|
| `UTC` | +0:00 | (Universal) |
| `America/New_York` | -5:00/-4:00 | New York (EST/EDT) |
| `America/Chicago` | -6:00/-5:00 | Chicago (CST/CDT) |
| `America/Los_Angeles` | -8:00/-7:00 | Los Angeles (PST/PDT) |
| `Europe/London` | +0:00/+1:00 | London (GMT/BST) |
| `Europe/Paris` | +1:00/+2:00 | Paris (CET/CEST) |
| `Asia/Tokyo` | +9:00 | Tokyo (JST) |
| `Australia/Sydney` | +10:00/+11:00 | Sydney (AEST/AEDT) |

### Daylight Saving Time

APScheduler handles DST transitions automatically:

**Spring Forward (e.g., 2 AM → 3 AM):**
- `schedule: "0 2 * * *"` will skip on the transition day
- `schedule: "0 3 * * *"` will execute normally

**Fall Back (e.g., 2 AM → 1 AM, repeats):**
- `schedule: "0 2 * * *"` will execute once (not twice)

**Recommendation:** Use UTC for production to avoid DST complexity.

---

## Best Practices

### 1. Configuration Management

✅ **DO:**
- Version control your `alerts.yaml` file
- Use environment variables for credentials
- Enable `--reload` in production for hot updates
- Keep alert names unique and descriptive

❌ **DON'T:**
- Hardcode passwords in config files
- Use overly short alert names
- Disable alerts by deleting them (set `enabled: false` instead)

### 2. Scheduling

✅ **DO:**
- Use UTC timezone in production
- Stagger alert schedules to avoid resource spikes
- Set realistic query timeouts
- Test cron expressions before deploying

❌ **DON'T:**
- Schedule all alerts at the same time (e.g., all at midnight)
- Use overly frequent schedules (< 1 minute)
- Forget to account for query execution time

### 3. Monitoring

✅ **DO:**
- Monitor daemon logs for errors
- Set up alerting on daemon failures (meta-monitoring)
- Review execution history regularly
- Track alert execution duration trends

❌ **DON'T:**
- Rely solely on email notifications
- Ignore WARNING level logs
- Run without log aggregation in production

### 4. Resource Management

✅ **DO:**
- Set database connection limits
- Monitor memory usage
- Use connection pooling
- Implement query timeouts

❌ **DON'T:**
- Run unbounded queries
- Ignore memory growth
- Skip load testing before production

### 5. Security

✅ **DO:**
- Use read-only database credentials where possible
- Rotate credentials regularly
- Use secrets management (not .env files in prod)
- Encrypt state database if it contains sensitive data

❌ **DON'T:**
- Commit credentials to version control
- Grant excessive database permissions
- Expose daemon ports publicly
- Run as root user

---

## Troubleshooting

For detailed troubleshooting steps, see [Troubleshooting Guide](troubleshooting-scheduler.md).

**Quick Checks:**

| Issue | Quick Fix |
|-------|-----------|
| Daemon won't start | Check `DATABASE_URL` is set |
| Jobs not executing | Verify alert has `enabled: true` |
| Config reload not working | Ensure `--reload` flag is set |
| Notifications not sent | Check email/Slack credentials |
| High memory usage | Review query result set sizes |

---

## FAQ

**Q: Can I run multiple instances of the daemon?**
A: Not yet. Phase 1 supports single-instance only. Phase 2 will add multi-instance support with Redis/PostgreSQL job store.

**Q: What happens if the daemon crashes?**
A: With `restart: unless-stopped` (Docker) or `Restart=always` (systemd), it will restart automatically. Use persistent state database to avoid losing execution history.

**Q: Can I trigger alerts manually while the daemon is running?**
A: Yes! Use `sqlsentinel run alerts.yaml --alert ALERT_NAME` in a separate terminal/container.

**Q: How do I test a schedule without waiting?**
A: Temporarily change the schedule to `* * * * *` (every minute), then reload config with `--reload` enabled.

**Q: Can I schedule alerts in different timezones?**
A: Not per-alert. The timezone setting is global. Use UTC and adjust your cron expressions accordingly.

**Q: What happens if an alert takes longer than its schedule interval?**
A: APScheduler will skip the next execution (with `max_instances=1`). Check logs for warnings.

---

## Next Steps

- **Advanced Configuration:** [Configuration Reference](configuration-reference.md)
- **Alert Development:** [Writing Effective Alerts](writing-alerts.md)
- **Troubleshooting:** [Troubleshooting Guide](troubleshooting-scheduler.md)
- **Architecture:** [Scheduler Architecture](../architecture/scheduler.md)

---

**Need Help?**

- GitHub Issues: https://github.com/kyle-gehring/sqlsentinel/issues
- Documentation: https://docs.sqlsentinel.io
