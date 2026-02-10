# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email security concerns to the maintainers via the [GitHub Security Advisories](https://github.com/kyle-gehring/sql-sentinel/security/advisories/new) feature
3. Include steps to reproduce and potential impact

## Security Considerations

### Credential Management

- **Never** put database passwords or API keys directly in `alerts.yaml`
- Use environment variables for all secrets:
  ```yaml
  database:
    url: "${DATABASE_URL}" # Set via environment variable
  ```
- Use `.env` files (excluded from Git via `.gitignore`) for local development
- In production, use your platform's secret manager (AWS Secrets Manager, GCP Secret Manager, etc.)

### Database Access

- SQL Sentinel executes user-defined SQL queries against your database
- Use **read-only** database credentials — SQL Sentinel never needs write access to your data
- Create a dedicated database user with minimal permissions (SELECT only on required tables)
- The state database (SQLite by default) is the only database SQL Sentinel writes to

### SQL Injection

- Alert queries are defined by the config file author, not by end users
- SQL Sentinel does not interpolate user input into queries
- Config files should be treated as trusted code — review changes via pull requests

### Network Security

- SMTP credentials are transmitted over TLS (port 587) by default
- Slack and webhook notifications use HTTPS
- Database connections should use TLS in production (`?sslmode=require` for PostgreSQL)

### Docker Security

- The Docker image runs as a non-root user (`sqlsentinel`)
- No unnecessary packages or tools are included (multi-stage build)
- Health checks are built in for container orchestration

## Dependency Security

SQL Sentinel uses automated security scanning:

- **pip-audit** — Checks Python dependencies for known vulnerabilities
- **Bandit** — Static analysis for common Python security issues
- **GitHub Actions** — Runs security scans on every push

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |
