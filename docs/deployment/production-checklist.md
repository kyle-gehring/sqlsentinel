# SQL Sentinel - Production Deployment Checklist

**Version:** 1.0
**Last Updated:** 2025-11-07

---

## Pre-Deployment

### Alert Configuration

- [ ] All alert queries tested and validated
- [ ] Cron schedules reviewed and verified
- [ ] Alert thresholds appropriate for business needs
- [ ] Notification channels configured correctly
- [ ] Alert descriptions clear and actionable
- [ ] Dry-run mode tested for all alerts
- [ ] Query performance acceptable (<30s execution time)

### Database Configuration

- [ ] Database connection strings tested
- [ ] Database credentials secured (not in YAML files)
- [ ] Network connectivity verified
- [ ] Database permissions verified (SELECT access)
- [ ] Connection pooling configured if needed
- [ ] BigQuery service account configured (if using BigQuery)
- [ ] State database path configured and writable

### Notification Configuration

#### Email (if using)

- [ ] SMTP host and port configured
- [ ] SMTP credentials tested
- [ ] TLS/SSL enabled
- [ ] From address configured
- [ ] Test email sent successfully
- [ ] Email delivery confirmed

#### Slack (if using)

- [ ] Webhook URL configured
- [ ] Test notification sent
- [ ] Message format validated
- [ ] Channel permissions verified

#### Webhook (if using)

- [ ] Webhook URL configured
- [ ] Custom headers configured (if needed)
- [ ] Test webhook delivered
- [ ] Response validation working

### Environment Configuration

- [ ] `.env` file created from `.env.example`
- [ ] All required environment variables set
- [ ] Secrets stored securely (not in git)
- [ ] LOG_LEVEL set appropriately (INFO or WARNING)
- [ ] LOG_FORMAT set to `json` for production
- [ ] Timezone configured correctly
- [ ] Environment variables validated

---

## Security

### Container Security

- [ ] Running as non-root user (default: sqlsentinel:sqlsentinel)
- [ ] Read-only mounts for configuration files
- [ ] Secrets managed via environment variables or secrets manager
- [ ] Container base image up to date
- [ ] No unnecessary ports exposed
- [ ] Docker socket not mounted (security risk)

### Database Security

- [ ] Using read-only database credentials
- [ ] Database credentials in environment variables only
- [ ] Connection uses TLS/SSL encryption (if supported)
- [ ] Database firewall rules configured
- [ ] Minimal database permissions granted
- [ ] Connection strings not logged

### File Permissions

- [ ] Config directory readable by container user
- [ ] Data directory writable by container user
- [ ] State database file permissions set correctly (644)
- [ ] No sensitive data in volume mounts
- [ ] Log files rotated and secured

### Network Security

- [ ] Container on isolated network (if using docker-compose)
- [ ] Only necessary ports exposed
- [ ] Firewall rules configured
- [ ] SMTP connection uses TLS
- [ ] Database connection encrypted

---

## Docker Configuration

### Image

- [ ] Using specific version tag (not `latest`)
- [ ] Image pulled from trusted registry
- [ ] Image size acceptable (<500MB)
- [ ] Image scanned for vulnerabilities

### Volume Mounts

- [ ] `/app/config` mounted (read-only)
- [ ] `/data` mounted for persistence
- [ ] `/app/logs` mounted (optional)
- [ ] Volume permissions correct (1000:1000)
- [ ] Backup strategy for `/data` volume

### Health Checks

- [ ] Health check configured in docker-compose
- [ ] Health check interval appropriate (30s)
- [ ] Health check timeout reasonable (10s)
- [ ] Start period configured (10s)
- [ ] Health check command validated

### Resource Limits

- [ ] Memory limit set (recommend: 512MB)
- [ ] CPU limit set (recommend: 1 CPU)
- [ ] Disk space allocated for volumes
- [ ] Resource monitoring configured

### Restart Policy

- [ ] Restart policy set (recommend: `unless-stopped`)
- [ ] Restart verified after container crash
- [ ] Restart verified after host reboot

---

## Monitoring

### Health Monitoring

- [ ] Health check endpoint tested
- [ ] Health status visible in monitoring
- [ ] Alerts configured for health failures
- [ ] Health check runs every 30s
- [ ] Health check failures investigated

### Metrics Collection

- [ ] Metrics command tested
- [ ] Prometheus scraping configured (optional)
- [ ] Key metrics dashboarded
- [ ] Alert on high failure rate
- [ ] Alert on slow execution times

### Logging

- [ ] JSON logging enabled
- [ ] Log level appropriate (INFO or WARNING)
- [ ] Log aggregation configured (ELK, Loki, CloudWatch)
- [ ] Log rotation configured
- [ ] Logs searchable and queryable
- [ ] Error logs monitored

### Alerting

- [ ] Alerts configured for container failures
- [ ] Alerts configured for high error rate
- [ ] Alerts configured for notification failures
- [ ] Alerts configured for slow execution
- [ ] Alert routing configured (PagerDuty, etc.)

---

## Operations

### Documentation

- [ ] Deployment procedure documented
- [ ] Configuration guide written
- [ ] Troubleshooting runbook created
- [ ] Team trained on SQL Sentinel
- [ ] On-call procedures defined
- [ ] Escalation path documented

### Backup & Recovery

- [ ] State database backed up regularly
- [ ] Backup restoration tested
- [ ] Configuration files in version control
- [ ] Disaster recovery plan documented
- [ ] Recovery time objective (RTO) defined
- [ ] Recovery point objective (RPO) defined

### Change Management

- [ ] Change approval process defined
- [ ] Testing procedure for config changes
- [ ] Rollback procedure documented
- [ ] Configuration hot-reload tested
- [ ] Deployment windows defined

### Capacity Planning

- [ ] Alert execution frequency estimated
- [ ] Database query performance measured
- [ ] Notification volume estimated
- [ ] Storage growth estimated
- [ ] Resource scaling plan defined

---

## Testing

### Pre-Deployment Testing

- [ ] All alerts tested with `--dry-run`
- [ ] Manual execution tested: `sqlsentinel run`
- [ ] Health check passes
- [ ] Metrics collection working
- [ ] Notifications delivered successfully
- [ ] State management working (deduplication)
- [ ] Execution history recorded

### Integration Testing

- [ ] Database connectivity verified
- [ ] Scheduler executing on schedule
- [ ] Notifications sent on alert trigger
- [ ] State deduplication working
- [ ] Error handling tested
- [ ] Graceful shutdown tested

### Performance Testing

- [ ] Query execution time acceptable
- [ ] Notification delivery time acceptable
- [ ] Container startup time <10s
- [ ] Memory usage acceptable (<512MB)
- [ ] CPU usage acceptable
- [ ] No memory leaks observed

### Failure Testing

- [ ] Database connection failure handled
- [ ] SMTP connection failure handled
- [ ] Invalid query handled
- [ ] Container restart recovery tested
- [ ] State database corruption recovery tested

---

## Post-Deployment

### Immediate Validation

- [ ] Container started successfully
- [ ] Health check passing
- [ ] All alerts scheduled
- [ ] First execution successful
- [ ] Notifications delivered
- [ ] No errors in logs

### First 24 Hours

- [ ] All scheduled alerts executed
- [ ] No execution failures
- [ ] No notification failures
- [ ] Performance acceptable
- [ ] Resource usage normal
- [ ] No restarts or crashes

### First Week

- [ ] Alert accuracy validated
- [ ] False positive rate acceptable
- [ ] Notification fatigue avoided
- [ ] Performance stable
- [ ] Resource usage stable
- [ ] Team feedback collected

### Ongoing

- [ ] Weekly log review scheduled
- [ ] Monthly metric review scheduled
- [ ] Quarterly alert review scheduled
- [ ] Regular security updates applied
- [ ] Configuration changes tracked
- [ ] Performance trends monitored

---

## Rollback Plan

### Rollback Triggers

- [ ] High error rate (>10% failures)
- [ ] Critical functionality broken
- [ ] Security vulnerability discovered
- [ ] Performance degradation
- [ ] Data corruption detected

### Rollback Procedure

1. [ ] Stop new container
2. [ ] Restore previous configuration
3. [ ] Start previous container version
4. [ ] Verify health check passes
5. [ ] Verify alerts executing
6. [ ] Monitor for 1 hour
7. [ ] Document rollback reason
8. [ ] Plan remediation

---

## Compliance & Governance

### Data Privacy

- [ ] No PII in alert queries (or masked)
- [ ] Data retention policy defined
- [ ] GDPR compliance verified (if applicable)
- [ ] Data access logged
- [ ] Data encryption in transit
- [ ] Data encryption at rest (if required)

### Audit Requirements

- [ ] All configuration changes tracked
- [ ] Execution history retained
- [ ] Access logs maintained
- [ ] Change approvals documented
- [ ] Compliance reports available

### Security Compliance

- [ ] Security scan passed
- [ ] Vulnerability assessment completed
- [ ] Penetration test results reviewed
- [ ] Security patches applied
- [ ] Compliance requirements met

---

## Validation Commands

### Pre-Deployment Validation

```bash
# Test container startup
./scripts/docker-test.sh

# Validate health check
./scripts/validate-health.sh

# Test alert execution
docker exec sqlsentinel sqlsentinel run /app/config/alerts.yaml --dry-run

# View metrics
docker exec sqlsentinel sqlsentinel metrics
```

### Post-Deployment Validation

```bash
# Check container status
docker ps | grep sqlsentinel

# View health status
docker inspect sqlsentinel --format='{{.State.Health.Status}}'

# Check logs
docker logs sqlsentinel --tail 50

# Verify scheduled jobs
docker exec sqlsentinel sqlsentinel metrics | grep scheduler_jobs

# View execution history
docker exec sqlsentinel sqlsentinel history /app/config/alerts.yaml --limit 10
```

---

## Contact & Support

### Internal Contacts

- [ ] Primary on-call: _______________
- [ ] Secondary on-call: _______________
- [ ] Manager: _______________
- [ ] Database admin: _______________

### External Resources

- [ ] SQL Sentinel Documentation: https://docs.sqlsentinel.com
- [ ] GitHub Issues: https://github.com/yourorg/sqlsentinel/issues
- [ ] Support Email: support@sqlsentinel.com
- [ ] Community Slack: #sqlsentinel

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| **Deployer** | | | |
| **Reviewer** | | | |
| **Manager** | | | |
| **Security** | | | |

---

**Notes:**

---

**Last Updated:** 2025-11-07
**Version:** 1.0
