# Troubleshooting SQL Sentinel Scheduler

**Version:** 0.1.0
**Last Updated:** 2025-10-20
**Target Audience:** System administrators, DevOps engineers, Data analysts

---

## Overview

This guide provides step-by-step troubleshooting for common issues with the SQL Sentinel scheduler daemon. Issues are organized by category with symptoms, causes, and solutions.

---

## Quick Diagnostic Checklist

Before diving into specific issues, run through this checklist:

```bash
# 1. Check daemon is running
systemctl status sqlsentinel  # systemd
docker ps | grep sqlsentinel   # Docker
pgrep -f "sqlsentinel daemon"  # Process check

# 2. Check recent logs
journalctl -u sqlsentinel --since "10 minutes ago"  # systemd
docker logs --tail 100 sqlsentinel                   # Docker

# 3. Verify configuration
sqlsentinel validate /path/to/alerts.yaml

# 4. Check database connectivity
sqlsentinel run /path/to/alerts.yaml --alert test_alert --dry-run

# 5. Check state database
sqlite3 /path/to/state.db "SELECT * FROM alert_state LIMIT 5;"

# 6. List scheduled jobs (if daemon running)
# Look for "Scheduled N jobs" in startup logs
```

---

## Daemon Won't Start

### Symptom

```
ERROR - Failed to initialize scheduler: ...
(daemon exits immediately)
```

### Common Causes & Solutions

#### 1. Missing DATABASE_URL

**Error:**
```
✗ No database URL provided. Set DATABASE_URL environment variable or pass --database-url
```

**Solution:**
```bash
# Option A: Environment variable
export DATABASE_URL="postgresql://user:pass@host:5432/db"
sqlsentinel daemon alerts.yaml

# Option B: CLI flag
sqlsentinel daemon alerts.yaml \
  --database-url "postgresql://user:pass@host:5432/db"

# Option C: Docker
docker run -d \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  sqlsentinel/sqlsentinel:latest
```

#### 2. Invalid Configuration File

**Error:**
```
ERROR - Configuration file not found: /path/to/alerts.yaml
```

**Solution:**
```bash
# Verify file exists
ls -la /path/to/alerts.yaml

# Check file permissions
chmod 644 /path/to/alerts.yaml

# Verify YAML syntax
sqlsentinel validate /path/to/alerts.yaml

# Docker: Verify mount
docker run --rm \
  -v $(pwd)/alerts.yaml:/app/config/alerts.yaml \
  sqlsentinel/sqlsentinel:latest \
  ls -la /app/config/
```

#### 3. State Database Connection Issues

**Error:**
```
ERROR - Failed to create state database engine: ...
```

**Solution:**
```bash
# SQLite: Check directory permissions
mkdir -p /path/to/state
chmod 755 /path/to/state

# SQLite: Check file permissions
touch /path/to/state/state.db
chmod 644 /path/to/state/state.db

# PostgreSQL: Test connection
psql "postgresql://user:pass@host:5432/statedb" -c "SELECT 1;"

# Initialize schema
sqlsentinel init --state-db "sqlite:///path/to/state.db"
```

#### 4. Port Already in Use (Future: If HTTP API enabled)

**Error:**
```
ERROR - Address already in use: 0.0.0.0:8080
```

**Solution:**
```bash
# Find process using port
lsof -i :8080
netstat -tunlp | grep 8080

# Kill offending process
kill -9 PID

# Or change port (when API is added)
sqlsentinel daemon alerts.yaml --port 8081
```

---

## Daemon Starts But Jobs Don't Execute

### Symptom

```
INFO - Scheduler started successfully
INFO - Scheduled 0 jobs:
(no job executions in logs)
```

### Common Causes & Solutions

#### 1. All Alerts Disabled

**Cause:** All alerts have `enabled: false`

**Diagnosis:**
```yaml
# Check alerts.yaml
alerts:
  - name: "my_alert"
    enabled: false  # ← Problem!
    ...
```

**Solution:**
```yaml
# Set enabled: true
alerts:
  - name: "my_alert"
    enabled: true  # ✓
    ...
```

#### 2. Invalid Cron Expression

**Cause:** Schedule doesn't match cron syntax

**Diagnosis:**
```
ERROR - Failed to add job for alert 'my_alert': Invalid cron expression
```

**Solution:**
```yaml
# Before (invalid)
schedule: "0 25 * * *"  # Hour 25 doesn't exist!

# After (valid)
schedule: "0 9 * * *"   # 9 AM daily

# Test at https://crontab.guru/
```

**Valid cron ranges:**
- Minutes: 0-59
- Hours: 0-23
- Day of month: 1-31
- Month: 1-12
- Day of week: 0-6 (0 = Sunday)

#### 3. Jobs Scheduled in Future

**Cause:** Schedule hasn't triggered yet

**Diagnosis:**
```
INFO - Scheduled 3 jobs:
INFO -   - daily_report: next run at 2025-10-21 09:00:00
(current time is 2025-10-20 14:00:00)
```

**Solution:**
```bash
# Option A: Wait for scheduled time

# Option B: Temporarily change to frequent schedule for testing
# alerts.yaml:
schedule: "* * * * *"  # Every minute (for testing only!)

# Option C: Trigger manually (doesn't affect schedule)
sqlsentinel run alerts.yaml --alert daily_report
```

#### 4. Scheduler Not Actually Running

**Diagnosis:**
```bash
# Check process
ps aux | grep "sqlsentinel daemon"

# Check logs for startup confirmation
journalctl -u sqlsentinel | grep "Scheduler started"
```

**Solution:**
```bash
# Restart daemon
systemctl restart sqlsentinel  # systemd
docker restart sqlsentinel      # Docker
```

---

## Jobs Execute But Fail

### Symptom

```
INFO - Executing scheduled alert: my_alert
ERROR - Error executing alert 'my_alert': ...
```

### Common Causes & Solutions

#### 1. Database Connection Failures

**Error:**
```
ERROR - could not connect to server: Connection refused
ERROR - password authentication failed for user "..."
```

**Solution:**
```bash
# Test database connection manually
psql "postgresql://user:pass@host:5432/db" -c "SELECT 1;"

# Check firewall
telnet db-host 5432

# Verify credentials
echo $DATABASE_URL

# Check database logs for auth failures
# PostgreSQL: /var/log/postgresql/postgresql-*.log
# MySQL: /var/log/mysql/error.log

# Fix credentials
export DATABASE_URL="postgresql://correct_user:correct_pass@host:5432/db"
systemctl restart sqlsentinel
```

#### 2. Query Syntax Errors

**Error:**
```
ERROR - syntax error at or near "SELEC"
ERROR - column "status" does not exist
```

**Solution:**
```bash
# Test query manually
sqlsentinel run alerts.yaml --alert my_alert --dry-run

# Run query in database client
psql -U user -d db -c "
SELECT
  CASE WHEN COUNT(*) > 0 THEN 'ALERT' ELSE 'OK' END as status
FROM my_table;
"

# Common issues:
# - Typos in SQL keywords
# - Missing 'status' column in SELECT
# - Wrong table/column names
# - Incompatible SQL dialect (e.g., using PostgreSQL syntax on MySQL)
```

#### 3. Missing Required Columns

**Error:**
```
ERROR - Query result must contain 'status' column
```

**Solution:**
```yaml
# Before (missing required column)
query: |
  SELECT COUNT(*) as count
  FROM orders
  WHERE date = CURRENT_DATE

# After (includes required 'status' column)
query: |
  SELECT
    CASE WHEN COUNT(*) < 10 THEN 'ALERT' ELSE 'OK' END as status,
    COUNT(*) as actual_value,
    10 as threshold
  FROM orders
  WHERE date = CURRENT_DATE
```

**Required:** `status` column with values 'ALERT' or 'OK'
**Optional:** `actual_value`, `threshold`, custom context columns

#### 4. Query Timeout

**Error:**
```
ERROR - query execution timeout after 30 seconds
```

**Solution:**
```sql
-- Optimize query
-- Before (slow - full table scan)
SELECT
  CASE WHEN AVG(price) > 1000 THEN 'ALERT' ELSE 'OK' END as status
FROM orders;

-- After (fast - indexed date filter)
SELECT
  CASE WHEN AVG(price) > 1000 THEN 'ALERT' ELSE 'OK' END as status
FROM orders
WHERE date >= CURRENT_DATE - 7;  -- Only last 7 days

-- Add index
CREATE INDEX idx_orders_date ON orders(date);
```

#### 5. Notification Failures

**Error:**
```
ERROR - Failed to send email notification: ...
ERROR - Slack webhook returned 404
```

**Solution:**
```bash
# Email: Test SMTP settings
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('user@gmail.com', 'password')
print('SMTP OK')
server.quit()
"

# Slack: Test webhook
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test from SQL Sentinel"}' \
  https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Check environment variables
env | grep SMTP
env | grep SLACK

# Note: Notification failures don't fail the alert
# The alert still executes and records history
```

---

## Configuration Reload Issues

### Symptom

Config file changes but daemon doesn't reload

### Common Causes & Solutions

#### 1. Reload Not Enabled

**Diagnosis:**
```
# Logs show:
INFO - Config reload: disabled
```

**Solution:**
```bash
# Start daemon with --reload flag
sqlsentinel daemon alerts.yaml --reload

# Docker
docker run -d \
  sqlsentinel/sqlsentinel:latest \
  daemon /app/config/alerts.yaml --reload
```

#### 2. File Watcher Not Working

**Diagnosis:**
```
# Edit config file
vim alerts.yaml

# Check logs - should see:
# "Configuration file changed, reloading..."
# But see nothing
```

**Solution:**
```bash
# Check inotify limits (Linux)
cat /proc/sys/fs/inotify/max_user_watches
# Should be > 8192

# Increase if needed
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Docker: File watcher may not work with bind mounts on some systems
# Workaround: Restart container manually after config changes
docker restart sqlsentinel
```

#### 3. Configuration Validation Errors

**Diagnosis:**
```
ERROR - Failed to reload configuration: Invalid cron schedule: 0 25 * * *
INFO - Continuing with existing configuration
```

**Solution:**
```bash
# Validate config before saving
sqlsentinel validate alerts.yaml

# Fix errors
vim alerts.yaml

# Save and watcher will retry
```

#### 4. Debounce Preventing Reload

**Diagnosis:**
```
DEBUG - Ignoring config change (debounced): 0.5s since last reload
```

**Solution:**
```
# This is normal! Debouncing prevents rapid reloads
# Default: 2 seconds between reloads
# Wait 2 seconds, then change will be picked up
```

---

## High Memory Usage

### Symptom

```bash
docker stats sqlsentinel
# CONTAINER   CPU %   MEM USAGE / LIMIT     MEM %
# sqlsentinel 5.2%    2.5GiB / 4GiB        62.5%  # High!
```

### Common Causes & Solutions

#### 1. Large Query Result Sets

**Cause:** Query returns millions of rows

**Diagnosis:**
```sql
-- Check query result size
EXPLAIN ANALYZE
SELECT * FROM huge_table;  -- Returns 10M rows!
```

**Solution:**
```sql
-- Limit result set
SELECT
  CASE WHEN SUM(revenue) < 10000 THEN 'ALERT' ELSE 'OK' END as status,
  SUM(revenue) as actual_value
FROM orders
WHERE date = CURRENT_DATE - 1;  -- Only yesterday's data

-- NOT this:
SELECT * FROM orders;  -- Entire table!
```

#### 2. Memory Leaks (APScheduler Jobs)

**Cause:** Jobs not cleaning up properly

**Diagnosis:**
```bash
# Monitor memory over time
while true; do
  docker stats --no-stream sqlsentinel | grep sqlsentinel
  sleep 300  # Every 5 minutes
done
```

**Solution:**
```bash
# Restart daemon daily (workaround)
# systemd timer or cron:
0 3 * * * systemctl restart sqlsentinel

# Or set memory limits
docker run -d \
  --memory=1g \
  --memory-reservation=512m \
  sqlsentinel/sqlsentinel:latest
```

#### 3. Large Execution History

**Cause:** History table growing unbounded

**Diagnosis:**
```sql
-- Check history size
sqlite3 state.db "
SELECT COUNT(*) FROM execution_history;
"
# Returns 100,000+ rows
```

**Solution:**
```sql
-- Clean old history (> 90 days)
sqlite3 state.db "
DELETE FROM execution_history
WHERE timestamp < datetime('now', '-90 days');
"

# Add to cron
0 2 * * 0 sqlite3 /path/to/state.db "DELETE FROM execution_history WHERE timestamp < datetime('now', '-90 days');"
```

---

## Clock Skew / Timezone Issues

### Symptom

Jobs execute at wrong times

### Common Causes & Solutions

#### 1. Container Clock Drift

**Diagnosis:**
```bash
# Check container time
docker exec sqlsentinel date
# Thu Oct 20 14:30:00 UTC 2025

# Check host time
date
# Thu Oct 20 07:30:00 PDT 2025

# 7 hour difference - timezone issue!
```

**Solution:**
```bash
# Set timezone
docker run -d \
  -e TIMEZONE="America/Los_Angeles" \
  sqlsentinel/sqlsentinel:latest

# Or use UTC everywhere (recommended)
export TIMEZONE="UTC"
```

#### 2. Daylight Saving Time Confusion

**Diagnosis:**
```
# Job scheduled for 2:00 AM during DST transition
# Either skips or executes at wrong time
```

**Solution:**
```bash
# Use UTC to avoid DST issues
sqlsentinel daemon alerts.yaml --timezone UTC

# Adjust schedules in query logic instead:
SELECT
  CASE WHEN ...  THEN 'ALERT' ELSE 'OK' END as status
FROM orders
WHERE date = CURRENT_DATE - 1
  AND EXTRACT(HOUR FROM timestamp AT TIME ZONE 'America/New_York') = 9
```

---

## Jobs Skipped / Missed

### Symptom

```
WARNING - Execution of job "my_alert" skipped: maximum number of running instances reached (1)
```

### Common Causes & Solutions

#### 1. Long-Running Queries

**Cause:** Query takes longer than schedule interval

**Diagnosis:**
```bash
# Check execution duration in history
sqlsentinel history alerts.yaml --alert my_alert

# Example output:
# my_alert  2025-10-20 09:15:00  success  OK  Duration: 15m 30s
# my_alert  2025-10-20 09:30:00  SKIPPED (previous still running)
```

**Solution:**
```sql
-- Optimize query
-- Add indexes
CREATE INDEX idx_orders_date ON orders(date);

-- Reduce data scanned
WHERE date >= CURRENT_DATE - 1  -- Not entire table

-- Or increase schedule interval
# Before: */15 * * * *  (every 15 minutes)
# After:  0 * * * *     (hourly)
```

#### 2. System Resource Constraints

**Diagnosis:**
```bash
# Check system load
uptime
# load average: 15.0, 12.0, 10.0  # High!

# Check database load
# PostgreSQL
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

**Solution:**
```bash
# Add more resources
# - Increase container memory
# - Upgrade database instance
# - Reduce concurrent alerts

# Stagger schedules
# Before (all at midnight):
# - alert1: 0 0 * * *
# - alert2: 0 0 * * *
# - alert3: 0 0 * * *

# After (staggered):
# - alert1: 0 0 * * *
# - alert2: 5 0 * * *
# - alert3: 10 0 * * *
```

---

## Logging Issues

### Problem: No Logs Appearing

**Diagnosis:**
```bash
# systemd - no output
journalctl -u sqlsentinel
# (empty)

# Docker - no output
docker logs sqlsentinel
# (empty)
```

**Solution:**
```bash
# Check log level
sqlsentinel daemon alerts.yaml --log-level DEBUG

# systemd: Check StandardOutput
cat /etc/systemd/system/sqlsentinel.service
# Should have: StandardOutput=journal

# Docker: Check logging driver
docker inspect sqlsentinel | grep LogConfig

# Verify daemon is actually running
ps aux | grep sqlsentinel
```

### Problem: Too Many Logs

**Solution:**
```bash
# Reduce log level
sqlsentinel daemon alerts.yaml --log-level WARNING

# Rotate logs
# systemd (automatic with journald)
journalctl --vacuum-time=7d

# Docker: Configure log rotation
docker run -d \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  sqlsentinel/sqlsentinel:latest
```

---

## Permission Denied Errors

### Symptom

```
ERROR - PermissionError: [Errno 13] Permission denied: '/app/state/state.db'
```

### Common Causes & Solutions

#### 1. Volume Mount Permissions (Docker)

**Solution:**
```bash
# Check directory ownership
ls -la /path/to/state/
# drwxr-xr-x root root  # ← Problem: owned by root

# Fix ownership
sudo chown -R 1000:1000 /path/to/state/  # Match container user ID

# Or create with correct permissions
mkdir -p state
chmod 777 state  # Permissive (for testing only)

# Production: Use named volumes
docker volume create sqlsentinel-state
docker run -d \
  -v sqlsentinel-state:/app/state \
  sqlsentinel/sqlsentinel:latest
```

#### 2. Read-Only Filesystem

**Solution:**
```bash
# Don't mount state directory as read-only!
# Before (wrong):
docker run -d \
  -v state:/app/state:ro  # ← Read-only!

# After (correct):
docker run -d \
  -v state:/app/state  # ✓ Read-write
```

---

## Database Locking Issues (SQLite)

### Symptom

```
ERROR - database is locked
```

### Common Causes & Solutions

#### 1. Multiple Processes Accessing SQLite

**Cause:** Two daemons writing to same SQLite file

**Solution:**
```bash
# Don't run multiple instances with SQLite state DB
# Use PostgreSQL for multi-instance deployments

# Or ensure only one daemon instance
systemctl status sqlsentinel
docker ps | grep sqlsentinel
# Should show only ONE instance
```

#### 2. Network Filesystem (NFS) with SQLite

**Cause:** SQLite doesn't work well over NFS

**Solution:**
```bash
# Don't use NFS for SQLite
# Move to local disk:
mv /nfs/state/state.db /var/lib/sqlsentinel/state.db

# Or use PostgreSQL instead
--state-db postgresql://user:pass@host:5432/statedb
```

---

## Getting More Help

### Enabling Debug Logging

```bash
sqlsentinel daemon alerts.yaml \
  --log-level DEBUG \
  2>&1 | tee debug.log
```

### Collecting Diagnostic Information

```bash
#!/bin/bash
# save-diagnostics.sh

echo "=== System Info ==="
uname -a
date

echo "=== Daemon Status ==="
systemctl status sqlsentinel 2>&1 || docker ps | grep sqlsentinel

echo "=== Recent Logs ==="
journalctl -u sqlsentinel --since "1 hour ago" 2>&1 || docker logs --tail 100 sqlsentinel

echo "=== Config Validation ==="
sqlsentinel validate /path/to/alerts.yaml

echo "=== Database Connectivity ==="
echo "SELECT 1;" | psql "$DATABASE_URL" 2>&1 || echo "DB test failed"

echo "=== State Database ==="
sqlite3 /path/to/state.db "SELECT COUNT(*) FROM alert_state;" 2>&1 || echo "State DB check failed"

echo "=== Disk Space ==="
df -h /path/to/state

echo "=== Memory Usage ==="
free -h

echo "=== Process Info ==="
ps aux | grep sqlsentinel
```

### Reporting Issues

When reporting issues, include:

1. SQL Sentinel version: `sqlsentinel --version`
2. Deployment method: Docker, systemd, etc.
3. Operating system: `uname -a`
4. Python version: `python --version`
5. Complete error logs (with `--log-level DEBUG`)
6. Sanitized configuration file (remove credentials)
7. Steps to reproduce

**GitHub Issues:** https://github.com/sqlsentinel/sqlsentinel/issues

---

## Preventive Measures

### Health Checks

```bash
# Script: check-sqlsentinel-health.sh
#!/bin/bash

# Check daemon is running
if ! pgrep -f "sqlsentinel daemon" > /dev/null; then
    echo "CRITICAL: Daemon not running"
    exit 2
fi

# Check recent executions
LAST_EXEC=$(sqlite3 /path/to/state.db \
    "SELECT MAX(timestamp) FROM execution_history;")

if [[ -z "$LAST_EXEC" ]]; then
    echo "WARNING: No execution history"
    exit 1
fi

# Check age of last execution (should be < 1 hour for frequent alerts)
# ... add time comparison logic ...

echo "OK: Daemon healthy"
exit 0
```

### Monitoring Dashboard

Consider integrating with:
- **Prometheus** - Metrics (future enhancement)
- **Grafana** - Visualization
- **Alertmanager** - Meta-monitoring (alerts on alerting system!)
- **ELK Stack** - Log aggregation

---

## Additional Resources

- [Daemon Usage Guide](daemon-usage.md)
- [Scheduler Architecture](../architecture/scheduler.md)
- [Configuration Reference](configuration-reference.md)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)

---

**Still stuck?** Open an issue with full diagnostics: https://github.com/sqlsentinel/sqlsentinel/issues
