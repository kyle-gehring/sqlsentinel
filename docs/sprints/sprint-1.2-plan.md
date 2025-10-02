# Sprint 1.2: Configuration Management & Database Connectivity

**Duration:** Days 4-7
**Sprint Goal:** Implement YAML configuration parsing and database connectivity layer
**Status:** Not Started

## Objectives

Build the configuration management system to parse YAML alert definitions and establish database connectivity using SQLAlchemy adapters. This sprint focuses on reading and validating alert configurations and connecting to data sources.

## Success Criteria

- [ ] Successfully parse YAML configuration files into AlertConfig models
- [ ] Validate all configuration files with clear error messages
- [ ] Database connections established for PostgreSQL (initial target)
- [ ] Environment variable substitution working in configurations
- [ ] All tests pass with >80% code coverage
- [ ] Code passes all linting checks (black, mypy, ruff)

## Work Items

### 1. YAML Configuration Parser
- [ ] Create `ConfigLoader` class to read YAML files
- [ ] Implement YAML to Pydantic model conversion
- [ ] Add support for multiple alert definitions in single file
- [ ] Support for environment variable substitution (e.g., `${DATABASE_URL}`)
- [ ] Validate cron schedules using croniter
- [ ] Error handling for malformed YAML
- [ ] Support for loading from file paths or directories
- [ ] Configuration validation with detailed error messages

### 2. Configuration Validation
- [ ] Create `ConfigValidator` class
- [ ] Validate required fields are present
- [ ] Check for duplicate alert names
- [ ] Validate notification channel configurations
- [ ] Ensure query strings are non-empty
- [ ] Validate schedule expressions
- [ ] Create helpful error messages for common mistakes
- [ ] Add warnings for potential issues (e.g., very frequent schedules)

### 3. Database Connection Management
- [ ] Create `DatabaseAdapter` class using SQLAlchemy Engine
- [ ] Support connection string/URL parsing for multiple databases
- [ ] Connection pooling configuration (SQLAlchemy's built-in pool)
- [ ] Connection health checks (`SELECT 1` queries)
- [ ] Proper connection cleanup and disposal
- [ ] Environment variable support for credentials
- [ ] Connection timeout handling
- [ ] Retry logic for transient failures
- [ ] Factory method to create engine from connection string

### 4. Query Execution Engine (Basic)
- [ ] Create `QueryExecutor` class
- [ ] Execute SQL queries against database
- [ ] Parse result sets into `QueryResult` models
- [ ] Validate result set schema (status column required)
- [ ] Query timeout enforcement
- [ ] Error handling for SQL errors
- [ ] Result set size limits
- [ ] Extract context fields from query results

### 5. Testing Framework
- [ ] Unit tests for ConfigLoader
- [ ] Unit tests for ConfigValidator
- [ ] Unit tests for DatabaseAdapter
- [ ] Mock database tests for QueryExecutor
- [ ] Integration tests with SQLite (no external dependencies)
- [ ] Test fixtures for sample YAML configurations
- [ ] Test error conditions and edge cases
- [ ] Achieve >80% code coverage

### 6. Example Configurations
- [ ] Create example YAML configuration files
- [ ] Document configuration format in comments
- [ ] Create templates for common use cases
- [ ] Add example alerts for different scenarios
- [ ] Create troubleshooting guide for common issues

## Technical Decisions

### YAML Parser
- **Library**: PyYAML (already in dependencies)
- **Validation**: Pydantic models for type safety
- **Environment Variables**: Custom resolver for `${VAR}` syntax

### Database Connectivity
- **Abstraction Layer**: SQLAlchemy 2.0+ Core (not ORM)
- **Multi-Database Support**: SQLAlchemy handles dialect differences automatically
- **Initial Testing**: SQLite (no external dependencies) and PostgreSQL
- **Connection Pooling**: SQLAlchemy's built-in QueuePool
- **Async Support**: Deferred to future sprint
- **Driver Detection**: SQLAlchemy auto-selects appropriate driver based on connection URL

### Error Handling
- **Configuration Errors**: Raise `ConfigurationError` with details
- **Database Errors**: Raise `ExecutionError` with context
- **Validation Errors**: Raise `ValidationError` with field-level details

## Dependencies

**New:**
- psycopg2-binary (PostgreSQL driver - optional)

**Existing:**
- pyyaml>=6.0
- sqlalchemy>=2.0 (includes SQLite support built-in)
- pydantic>=2.0
- croniter>=2.0

**Note:** SQLAlchemy supports multiple databases out of the box. Additional drivers can be installed as needed:
- PostgreSQL: `psycopg2-binary` or `psycopg`
- MySQL: `mysqlclient` or `pymysql`
- SQL Server: `pyodbc` or `pymssql`
- SQLite: Built into Python (no extra driver needed)

## File Structure

```
src/sqlsentinel/
├── config/
│   ├── __init__.py
│   ├── loader.py          # ConfigLoader class
│   └── validator.py       # ConfigValidator class
├── database/
│   ├── __init__.py
│   └── adapter.py         # DatabaseAdapter using SQLAlchemy
├── executor/
│   ├── __init__.py
│   └── query.py           # QueryExecutor class
└── models/                # (existing)

tests/
├── config/
│   ├── __init__.py
│   ├── test_loader.py
│   └── test_validator.py
├── database/
│   ├── __init__.py
│   └── test_adapter.py    # Tests with SQLite and mocks
├── executor/
│   ├── __init__.py
│   └── test_query.py
└── fixtures/
    ├── valid_config.yaml
    ├── invalid_config.yaml
    └── multi_alert_config.yaml
```

## Example Configuration Format

```yaml
# alerts.yaml
database:
  url: "${DATABASE_URL}"  # PostgreSQL connection string
  pool_size: 5
  timeout: 30

alerts:
  - name: "daily_revenue_check"
    description: "Alert when daily revenue is below threshold"
    query: |
      SELECT
        CASE WHEN SUM(revenue) < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        SUM(revenue) as actual_value,
        10000 as threshold,
        COUNT(*) as order_count
      FROM orders
      WHERE date = CURRENT_DATE - 1
    schedule: "0 9 * * *"
    enabled: true
    notify:
      - channel: email
        config:
          recipients: ["team@company.com"]
          subject: "Revenue Alert: {alert_name}"

  - name: "data_quality_check"
    description: "Check for null values in customer data"
    query: |
      SELECT
        CASE WHEN null_pct > 5 THEN 'ALERT' ELSE 'OK' END as status,
        null_pct as actual_value,
        5 as threshold
      FROM (
        SELECT (COUNT(*) FILTER (WHERE email IS NULL) * 100.0 / COUNT(*)) as null_pct
        FROM customers
        WHERE created_at > CURRENT_DATE - 1
      ) q
    schedule: "0 6 * * *"
    enabled: true
    notify:
      - channel: slack
        config:
          webhook_url: "${SLACK_WEBHOOK_URL}"
          channel: "#data-quality"
```

## Risks & Mitigations

| Risk                           | Impact | Mitigation                                              |
|--------------------------------|--------|---------------------------------------------------------|
| Complex YAML parsing edge cases| Medium | Comprehensive test suite with edge cases                |
| Database connection failures   | High   | Retry logic, health checks, clear error messages        |
| SQL injection vulnerabilities  | High   | Use parameterized queries, document safe practices      |
| Environment variable security  | Medium | Document secure storage practices, support secret mgmt  |

## Deliverables

1. YAML configuration loader with validation
2. SQLAlchemy-based database adapter supporting multiple databases
3. Query executor that converts SQL results to QueryResult models
4. Comprehensive test suite (>80% coverage) using SQLite
5. Example configuration files for different database types
6. Configuration documentation with connection string examples

## Definition of Done

- [ ] All work items completed
- [ ] All tests passing
- [ ] Code coverage >80%
- [ ] All linting checks pass (black, mypy, ruff)
- [ ] Can successfully parse example YAML files
- [ ] Can connect to databases via SQLAlchemy (tested with SQLite)
- [ ] Can execute queries and parse results
- [ ] Documentation updated with configuration guide
- [ ] Code review completed
- [ ] Sprint retrospective completed

## Notes

- SQLAlchemy provides database abstraction - no need for database-specific adapters
- Use SQLite for testing (no external dependencies)
- Connection string format follows SQLAlchemy standards (e.g., `postgresql://`, `mysql://`, `sqlite://`)
- Keep configuration format simple and intuitive for SQL analysts
- Prioritize clear error messages for configuration issues
- Environment variable support is critical for credential management
- Consider adding schema validation for query results in future

## Connection String Examples

```python
# PostgreSQL
"postgresql://user:password@localhost/dbname"
"postgresql+psycopg2://user:password@localhost/dbname"

# MySQL
"mysql://user:password@localhost/dbname"
"mysql+pymysql://user:password@localhost/dbname"

# SQLite
"sqlite:///path/to/database.db"
"sqlite:///:memory:"  # In-memory for testing

# SQL Server
"mssql+pyodbc://user:password@localhost/dbname?driver=ODBC+Driver+17+for+SQL+Server"

# Snowflake (future)
"snowflake://user:password@account/database/schema?warehouse=warehouse_name"
```
