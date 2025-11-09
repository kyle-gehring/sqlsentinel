# Security Validation Guide

**Status:** 📋 Planned for Sprint 4.2
**Last Updated:** 2025-11-07

## Overview

This document outlines the security validation procedures for SQL Sentinel to ensure the application meets security best practices before production deployment.

## Security Tools Required

Add the following to `pyproject.toml` under `[tool.poetry.group.dev.dependencies]`:

```toml
safety = "^3.7.0"      # Dependency vulnerability scanning
pip-audit = "^2.9.0"   # CVE detection
bandit = "^1.8.6"      # Python security linter
```

After adding, rebuild the devcontainer to install these tools.

## Security Validation Checklist

### 1. Dependency Vulnerability Scanning

**Tool:** `safety` and `pip-audit`

```bash
# Run safety check
poetry run safety check --json > security-reports/safety-report.json

# Run pip-audit
poetry run pip-audit --format=json > security-reports/pip-audit-report.json
```

**Success Criteria:**
- ✅ No critical CVEs
- ✅ No high-severity vulnerabilities
- ⚠️  Medium-severity issues documented with mitigation plan

### 2. Code Security Analysis

**Tool:** `bandit`

```bash
# Run bandit security scan
poetry run bandit -r src/ -f json -o security-reports/bandit-report.json

# Run with verbose output
poetry run bandit -r src/ -ll -i
```

**Success Criteria:**
- ✅ No high-severity issues
- ✅ No medium-severity issues in critical paths
- ✅ All findings reviewed and documented

**Key Areas to Review:**
- SQL injection protection (parameterized queries)
- Secret handling (no secrets in logs)
- Input validation
- File operations security

### 3. Docker Security

**Tool:** `docker scan` (Snyk)

```bash
# Build the image
docker build -t sqlsentinel:security-scan .

# Scan the image
docker scan sqlsentinel:security-scan --json > security-reports/docker-scan-report.json

# Alternative: Use trivy for container scanning
trivy image sqlsentinel:security-scan
```

**Success Criteria:**
- ✅ No critical vulnerabilities in base image
- ✅ Non-root user enforced
- ✅ Minimal attack surface
- ✅ No secrets in image layers

### 4. Configuration Security

**Manual Review Checklist:**

- [ ] **YAML Parser Security**
  - Using safe YAML loader (`yaml.safe_load`)
  - No arbitrary code execution risks

- [ ] **SQL Query Validation**
  - All database queries use parameterized statements
  - No string concatenation for SQL
  - Query validation before execution

- [ ] **Secret Management**
  - Secrets loaded from environment variables
  - Secrets not logged or displayed
  - Passwords masked in error messages
  - No secrets in configuration files

- [ ] **File Permissions**
  - Configuration files have appropriate permissions
  - State database properly secured
  - Log files not world-readable

- [ ] **Authentication**
  - SMTP authentication uses TLS
  - Webhook requests can use authentication headers
  - API tokens stored securely

### 5. Input Validation

**Manual Code Review:**

- [ ] **Alert Configuration**
  - Alert names validated (no special characters that could cause issues)
  - Cron schedules validated
  - Email addresses validated
  - URLs validated for webhooks

- [ ] **Database Connections**
  - Connection strings validated
  - Timeouts enforced
  - Connection pooling configured safely

- [ ] **Notification Content**
  - User-provided content sanitized
  - No XSS risks in email/Slack messages
  - Proper encoding of special characters

## Security Best Practices Implemented

### ✅ SQL Injection Protection

All database queries use SQLAlchemy's parameterized queries:

```python
# GOOD - Parameterized query
conn.execute(text("SELECT * FROM users WHERE id = :user_id"), {"user_id": user_id})

# BAD - String concatenation (NOT used in our code)
conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

**Files to verify:**
- `src/sqlsentinel/database/adapter.py`
- `src/sqlsentinel/database/bigquery_adapter.py`

### ✅ Secret Masking in Logs

Sensitive information is masked in logs and error messages:

```python
# Email passwords masked
# Database connection strings masked
# API tokens masked
```

**Files to verify:**
- `src/sqlsentinel/logging/config.py`
- `src/sqlsentinel/notifications/email.py`

### ✅ Environment Variable Security

All secrets loaded from environment variables:

```bash
SMTP_PASSWORD=***
DATABASE_URL=***
SLACK_WEBHOOK_URL=***
```

### ✅ Non-Root Container User

Docker container runs as non-root user:

```dockerfile
# Create non-root user
RUN adduser --disabled-password --gecos '' sqlsentinel

# Switch to non-root user
USER sqlsentinel
```

**File:** `Dockerfile`

## Known Security Considerations

### 1. Database Credential Storage

**Current:** Database credentials are passed via environment variables or connection strings.

**Recommendation:** For production, consider:
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
- HashiCorp Vault

### 2. Alert Query Execution

**Risk:** Users define arbitrary SQL queries that are executed.

**Mitigation:**
- Read-only database users recommended
- Query timeouts enforced
- Resource limits on database connections
- Audit logging of all queries

**Documentation:** Users should be warned to use read-only credentials.

### 3. Notification Webhook Security

**Risk:** Webhook URLs could be used to exfiltrate data.

**Mitigation:**
- HTTPS enforcement recommended
- Webhook authentication supported
- Rate limiting recommended
- Network egress controls in production

### 4. YAML Configuration Parsing

**Risk:** Malicious YAML could exploit parser vulnerabilities.

**Mitigation:**
- Using `yaml.safe_load()` (not `yaml.load()`)
- Configuration validation before use
- File permissions restrict config modification

## Security Incident Response

If a security vulnerability is discovered:

1. **Assess Severity:** Critical, High, Medium, Low
2. **Create Private Issue:** Do not disclose publicly until patched
3. **Develop Fix:** Test thoroughly
4. **Release Patch:** Follow semantic versioning (PATCH for security)
5. **Notify Users:** Security advisory with upgrade instructions
6. **Post-Mortem:** Document lessons learned

## Compliance Considerations

### GDPR (if applicable)

- No PII stored by default
- Alert query results may contain PII (user responsibility)
- Logging can be configured to exclude sensitive data

### SOC 2 (if applicable)

- Audit logging available
- Access controls via environment variables
- Encryption in transit (TLS for SMTP, HTTPS for webhooks)

## Security Audit Schedule

**Recommended Frequency:**

- **Dependency Scans:** Weekly (automated CI/CD)
- **Code Security Scans:** On every commit (CI/CD)
- **Docker Image Scans:** On every build (CI/CD)
- **Manual Security Review:** Quarterly
- **Penetration Testing:** Annually (if enterprise deployment)

## Security Reporting

To report a security vulnerability:

1. **Do NOT** create a public GitHub issue
2. Email: security@sqlsentinel.dev (if available)
3. Or use GitHub Security Advisories (private disclosure)
4. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security.html)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)

---

**Next Steps:**

1. Add security tools to `pyproject.toml`
2. Rebuild devcontainer
3. Run all security scans
4. Address findings
5. Document results in Sprint 4.2 completion report
