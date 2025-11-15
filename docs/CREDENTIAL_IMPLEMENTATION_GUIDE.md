# SQL Sentinel Credential Management - Complete Implementation Guide

**Purpose**: This document provides a complete, LLM-optimized guide for implementing credential management in SQL Sentinel. It synthesizes all research findings, provides concrete implementation steps, and includes all necessary code patterns.

---

## Table of Contents

1. [Implementation TODO List](#implementation-todo-list)
2. [Problem Statement](#problem-statement)
3. [Recommended Solution](#recommended-solution)
4. [Architecture Overview](#architecture-overview)
5. [Core Implementation](#core-implementation)
6. [Integration Points](#integration-points)
7. [Configuration Examples](#configuration-examples)
8. [Testing Strategy](#testing-strategy)
9. [Documentation Requirements](#documentation-requirements)
10. [Security Considerations](#security-considerations)

---

## Implementation TODO List

### Phase 1: Core Implementation (Required)

- [ ] **Task 1**: Create `src/sqlsentinel/credentials/` directory and `__init__.py`
- [ ] **Task 2**: Implement `CredentialResolver` class in `src/sqlsentinel/credentials/resolver.py`
- [ ] **Task 3**: Add environment variable resolution (`${VAR_NAME}` syntax)
- [ ] **Task 4**: Add connections.yml file support (`@connection:name` syntax)
- [ ] **Task 5**: Implement connection string builders (PostgreSQL, BigQuery, MySQL, Snowflake)
- [ ] **Task 6**: Integrate CredentialResolver into `ConfigLoader` class
- [ ] **Task 7**: Add credential validation with helpful error messages

### Phase 2: Testing & Validation

- [ ] **Task 8**: Create `tests/test_credentials/test_resolver.py` with unit tests
- [ ] **Task 9**: Test all resolution methods (env vars, connections.yml, literals)
- [ ] **Task 10**: Test error cases and error messages
- [ ] **Task 11**: Add integration tests with ConfigLoader
- [ ] **Task 12**: Add CLI flag `--validate-credentials` to test connections

### Phase 3: Documentation & Examples

- [ ] **Task 13**: Create `examples/connections.yml.example` template
- [ ] **Task 14**: Update `.gitignore` to exclude credential files
- [ ] **Task 15**: Update example alert files to use `${DATABASE_URL}` pattern
- [ ] **Task 16**: Create `docs/CREDENTIAL_GUIDE.md` for analysts
- [ ] **Task 17**: Add troubleshooting guide with common issues

---

## Problem Statement

### Current State

**What exists today**:
- SQL Sentinel requires database connection strings in `alerts.yaml`
- Connection strings can contain credentials directly or use environment variables
- No standard pattern for managing multiple databases
- No credential resolution layer

**Example current usage**:
```yaml
database:
  url: "postgresql://user:password@host:5432/db"  # Credentials in YAML - BAD
```

**Problems**:
1. ❌ Credentials stored in version-controlled YAML files (security risk)
2. ❌ No standard pattern for using environment variables
3. ❌ Difficult to manage multiple database connections
4. ❌ Not analyst-friendly (requires DevOps knowledge)
5. ❌ No validation until runtime (late failure)

### User Requirement

> "I don't think it's reasonable to expect analysts to manage credentials with each alert."

**User needs**:
- Simple, analyst-friendly credential management
- No credentials in git-tracked files
- Easy to use in development and production
- Support for multiple databases
- Industry-standard patterns (like dbt)

---

## Recommended Solution

### Industry Standard: Hybrid Credential Management

Based on analysis of dbt, Airflow, Great Expectations, and Metabase, the recommended approach is a **hybrid system** supporting three credential resolution methods:

#### Method 1: Environment Variables (Primary - 80% of use cases)

**Usage**:
```yaml
database:
  url: "${DATABASE_URL}"
```

**Setup**:
```bash
export DATABASE_URL="postgresql://user:pass@host:5432/db"
sqlsentinel run alerts.yaml
```

**Why**: Simplest, works everywhere (Docker, K8s, Lambda), no extra files needed.

#### Method 2: Connection References (Multiple databases)

**Usage**:
```yaml
database:
  url: "@prod"  # References 'prod' connection
```

**Setup** (`connections.yml` - gitignored):
```yaml
connections:
  prod:
    type: postgresql
    host: ${DB_HOST}
    user: ${DB_USER}
    password: ${DB_PASSWORD}
    database: prod_db

  analytics:
    type: bigquery
    project_id: my-project
    credentials_path: ${GOOGLE_APPLICATION_CREDENTIALS}
```

**Why**: Organized, reusable, supports complex multi-database scenarios.

#### Method 3: Literal Strings (Backward compatible)

**Usage**:
```yaml
database:
  url: "sqlite:///local.db"  # Direct connection string
```

**Why**: Backward compatibility, simple local development.

### Key Benefits

✅ **Standard pattern**: Similar to dbt (data analysts already know this)
✅ **Git-safe**: No credentials in version control
✅ **Production-ready**: Works in all deployment environments
✅ **Backward compatible**: Existing configs still work
✅ **Minimal code**: ~200 lines of implementation code
✅ **Extensible**: Easy to add cloud secret manager support later

---

## Architecture Overview

### Components

```
┌─────────────────────────────────────────────────────┐
│                   alerts.yaml                       │
│  database:                                          │
│    url: "${DATABASE_URL}" or "@prod" or "sqlite://│
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              ConfigLoader.load()                    │
│  - Loads and parses YAML                           │
│  - Calls CredentialResolver.resolve()              │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│           CredentialResolver.resolve()              │
│  - Detects credential type from syntax             │
│  - ${VAR} → Environment variable                   │
│  - @name → connections.yml lookup                  │
│  - scheme:// → Literal connection string           │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│        Resolved Connection String                   │
│  "postgresql://user:pass@host:5432/db"             │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│         AdapterFactory.create_adapter()             │
│  - Creates appropriate database adapter            │
└─────────────────────────────────────────────────────┘
```

### Resolution Priority

1. **Connection reference** (`@name`) → Load from `connections.yml`
2. **Environment variable** (`${VAR}`) → Load from `os.environ`
3. **Literal string** (`scheme://...`) → Use as-is
4. **Error** → Raise helpful error message

### File Structure

```
src/sqlsentinel/
├── credentials/
│   ├── __init__.py
│   └── resolver.py          # NEW: CredentialResolver class
├── config/
│   └── loader.py             # MODIFIED: Add credential resolution
├── database/
│   ├── adapter.py           # UNCHANGED
│   ├── bigquery_adapter.py  # UNCHANGED
│   └── factory.py           # UNCHANGED
└── cli.py                   # MODIFIED: Add --validate-credentials flag

examples/
├── alerts.yaml              # MODIFIED: Use ${DATABASE_URL}
├── bigquery-alerts.yaml     # MODIFIED: Use ${DATABASE_URL}
└── connections.yml.example  # NEW: Template for connections

tests/
└── test_credentials/
    ├── __init__.py
    ├── test_resolver.py     # NEW: Unit tests
    └── test_integration.py  # NEW: Integration tests

docs/
└── CREDENTIAL_GUIDE.md      # NEW: Analyst documentation
```

---

## Core Implementation

### 1. CredentialResolver Class

**File**: `src/sqlsentinel/credentials/resolver.py`

```python
"""Credential resolution for SQL Sentinel."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import yaml

from ..models.errors import ConfigurationError, ExecutionError


class CredentialResolver:
    """
    Resolves database credentials from multiple sources.

    Supports three resolution methods:
    1. Environment variables: ${VAR_NAME}
    2. Connection references: @connection:name or @name
    3. Literal connection strings: postgresql://...

    Examples:
        >>> resolver = CredentialResolver()
        >>> resolver.resolve("${DATABASE_URL}")
        'postgresql://user:pass@host/db'

        >>> resolver.resolve("@prod")
        'postgresql://prod-host:5432/prod_db'

        >>> resolver.resolve("sqlite:///local.db")
        'sqlite:///local.db'
    """

    # Supported database types for connections.yml
    SUPPORTED_TYPES = [
        'postgresql', 'postgres',
        'mysql', 'mariadb',
        'bigquery',
        'snowflake',
        'sqlite',
        'mssql', 'sqlserver',
    ]

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        connections_file: Optional[Path] = None,
    ):
        """
        Initialize credential resolver.

        Args:
            config_dir: Directory to search for connections.yml (default: cwd)
            connections_file: Explicit path to connections.yml (overrides config_dir)
        """
        self.config_dir = config_dir or Path.cwd()

        if connections_file:
            self._connections_file = Path(connections_file)
        else:
            self._connections_file = self.config_dir / "connections.yml"

        # Cache for loaded connections
        self._connections_cache: Optional[Dict[str, Any]] = None

    def resolve(self, reference: str) -> str:
        """
        Resolve a credential reference to a connection string.

        Args:
            reference: Credential reference in one of these formats:
                - ${VAR_NAME} - Environment variable
                - @connection:name or @name - Connection reference
                - scheme://... - Literal connection string

        Returns:
            Resolved connection string

        Raises:
            ConfigurationError: If reference format is invalid
            ExecutionError: If credential cannot be resolved
        """
        if not reference or not reference.strip():
            raise ConfigurationError("Database URL cannot be empty")

        reference = reference.strip()

        # Method 1: Connection reference (@name)
        if reference.startswith("@"):
            return self._resolve_connection_reference(reference)

        # Method 2: Environment variable (${VAR_NAME})
        if reference.startswith("${") and reference.endswith("}"):
            return self._resolve_env_variable(reference)

        # Method 3: Literal connection string
        if self._is_connection_string(reference):
            return reference

        # Invalid format
        raise ConfigurationError(
            f"Invalid database URL format: {reference}\n"
            f"Supported formats:\n"
            f"  - Environment variable: ${{DATABASE_URL}}\n"
            f"  - Connection reference: @prod or @connection:prod\n"
            f"  - Connection string: postgresql://user:pass@host/db"
        )

    def _resolve_env_variable(self, reference: str) -> str:
        """
        Resolve environment variable reference.

        Args:
            reference: Format ${VAR_NAME}

        Returns:
            Value of environment variable

        Raises:
            ExecutionError: If environment variable not found
        """
        # Extract variable name (remove ${ and })
        var_name = reference[2:-1].strip()

        if not var_name:
            raise ConfigurationError("Empty environment variable name: ${}")

        # Try to get from environment
        value = os.environ.get(var_name)

        if value is None:
            raise ExecutionError(
                f"Environment variable not found: {var_name}\n"
                f"Set it with: export {var_name}=\"your-connection-string\""
            )

        if not value.strip():
            raise ExecutionError(
                f"Environment variable is empty: {var_name}"
            )

        return value.strip()

    def _resolve_connection_reference(self, reference: str) -> str:
        """
        Resolve connection reference from connections.yml.

        Args:
            reference: Format @name or @connection:name

        Returns:
            Built connection string from connections.yml

        Raises:
            ExecutionError: If connection not found or file missing
        """
        # Extract connection name
        # @prod or @connection:prod → "prod"
        conn_name = reference.lstrip("@")
        if ":" in conn_name:
            conn_name = conn_name.split(":", 1)[1]

        conn_name = conn_name.strip()

        if not conn_name:
            raise ConfigurationError(
                f"Empty connection name in reference: {reference}"
            )

        # Load connections.yml if not already loaded
        if self._connections_cache is None:
            self._load_connections_file()

        # Look up connection
        if conn_name not in self._connections_cache:
            available = ", ".join(self._connections_cache.keys())
            raise ExecutionError(
                f"Connection '{conn_name}' not found in connections.yml\n"
                f"Available connections: {available}\n"
                f"File: {self._connections_file}"
            )

        # Build connection string from config
        conn_config = self._connections_cache[conn_name]
        return self._build_connection_string(conn_name, conn_config)

    def _load_connections_file(self) -> None:
        """
        Load and parse connections.yml file.

        Raises:
            ExecutionError: If file not found or invalid YAML
        """
        if not self._connections_file.exists():
            raise ExecutionError(
                f"connections.yml not found: {self._connections_file}\n"
                f"Create this file to use connection references like @prod\n"
                f"See examples/connections.yml.example for template"
            )

        try:
            with open(self._connections_file, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ExecutionError(
                f"Invalid YAML in connections.yml: {e}\n"
                f"File: {self._connections_file}"
            ) from e
        except Exception as e:
            raise ExecutionError(
                f"Failed to read connections.yml: {e}"
            ) from e

        if not isinstance(config, dict):
            raise ExecutionError(
                "connections.yml must contain a dictionary"
            )

        if 'connections' not in config:
            raise ExecutionError(
                "connections.yml must have a 'connections:' key"
            )

        self._connections_cache = config['connections']

        if not isinstance(self._connections_cache, dict):
            raise ExecutionError(
                "'connections' must be a dictionary"
            )

    def _build_connection_string(
        self,
        conn_name: str,
        config: Dict[str, Any]
    ) -> str:
        """
        Build connection string from connection config.

        Args:
            conn_name: Name of connection (for error messages)
            config: Connection configuration dictionary

        Returns:
            SQLAlchemy connection string

        Raises:
            ConfigurationError: If config is invalid
        """
        if not isinstance(config, dict):
            raise ConfigurationError(
                f"Connection '{conn_name}' must be a dictionary"
            )

        conn_type = config.get('type', '').lower()

        if not conn_type:
            raise ConfigurationError(
                f"Connection '{conn_name}' missing 'type' field"
            )

        if conn_type not in self.SUPPORTED_TYPES:
            supported = ", ".join(self.SUPPORTED_TYPES)
            raise ConfigurationError(
                f"Unsupported connection type '{conn_type}' for '{conn_name}'\n"
                f"Supported types: {supported}"
            )

        # Route to appropriate builder
        if conn_type in ('postgresql', 'postgres'):
            return self._build_postgresql_string(conn_name, config)
        elif conn_type in ('mysql', 'mariadb'):
            return self._build_mysql_string(conn_name, config)
        elif conn_type == 'bigquery':
            return self._build_bigquery_string(conn_name, config)
        elif conn_type == 'snowflake':
            return self._build_snowflake_string(conn_name, config)
        elif conn_type == 'sqlite':
            return self._build_sqlite_string(conn_name, config)
        elif conn_type in ('mssql', 'sqlserver'):
            return self._build_mssql_string(conn_name, config)
        else:
            raise ConfigurationError(f"Unsupported type: {conn_type}")

    def _build_postgresql_string(
        self,
        conn_name: str,
        config: Dict[str, Any]
    ) -> str:
        """Build PostgreSQL connection string."""
        host = self._resolve_config_value(config.get('host', 'localhost'))
        port = config.get('port', 5432)
        database = self._resolve_config_value(config.get('database', ''))
        user = self._resolve_config_value(config.get('user', ''))
        password = self._resolve_config_value(config.get('password', ''))

        if not database:
            raise ConfigurationError(
                f"Connection '{conn_name}': 'database' is required"
            )

        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        elif user:
            return f"postgresql://{user}@{host}:{port}/{database}"
        else:
            return f"postgresql://{host}:{port}/{database}"

    def _build_mysql_string(
        self,
        conn_name: str,
        config: Dict[str, Any]
    ) -> str:
        """Build MySQL connection string."""
        host = self._resolve_config_value(config.get('host', 'localhost'))
        port = config.get('port', 3306)
        database = self._resolve_config_value(config.get('database', ''))
        user = self._resolve_config_value(config.get('user', ''))
        password = self._resolve_config_value(config.get('password', ''))

        if not database:
            raise ConfigurationError(
                f"Connection '{conn_name}': 'database' is required"
            )

        # Use pymysql driver
        if password:
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        elif user:
            return f"mysql+pymysql://{user}@{host}:{port}/{database}"
        else:
            raise ConfigurationError(
                f"Connection '{conn_name}': 'user' is required for MySQL"
            )

    def _build_bigquery_string(
        self,
        conn_name: str,
        config: Dict[str, Any]
    ) -> str:
        """Build BigQuery connection string."""
        project_id = self._resolve_config_value(config.get('project_id'))

        if not project_id:
            raise ConfigurationError(
                f"Connection '{conn_name}': 'project_id' is required for BigQuery"
            )

        url = f"bigquery://{project_id}"

        # Optional dataset
        if dataset := config.get('dataset'):
            dataset = self._resolve_config_value(dataset)
            url += f"/{dataset}"

        # Optional query parameters
        params = []
        if creds_path := config.get('credentials_path'):
            creds_path = self._resolve_config_value(creds_path)
            params.append(f"credentials={creds_path}")

        if location := config.get('location'):
            location = self._resolve_config_value(location)
            params.append(f"location={location}")

        if params:
            url += "?" + "&".join(params)

        return url

    def _build_snowflake_string(
        self,
        conn_name: str,
        config: Dict[str, Any]
    ) -> str:
        """Build Snowflake connection string."""
        account = self._resolve_config_value(config.get('account'))
        user = self._resolve_config_value(config.get('user'))
        password = self._resolve_config_value(config.get('password'))
        database = self._resolve_config_value(config.get('database'))

        if not all([account, user, password, database]):
            raise ConfigurationError(
                f"Connection '{conn_name}': Snowflake requires "
                f"account, user, password, and database"
            )

        url = f"snowflake://{user}:{password}@{account}/{database}"

        # Optional parameters
        params = []
        if warehouse := config.get('warehouse'):
            warehouse = self._resolve_config_value(warehouse)
            params.append(f"warehouse={warehouse}")

        if schema := config.get('schema'):
            schema = self._resolve_config_value(schema)
            params.append(f"schema={schema}")

        if role := config.get('role'):
            role = self._resolve_config_value(role)
            params.append(f"role={role}")

        if params:
            url += "?" + "&".join(params)

        return url

    def _build_sqlite_string(
        self,
        conn_name: str,
        config: Dict[str, Any]
    ) -> str:
        """Build SQLite connection string."""
        path = self._resolve_config_value(config.get('path'))

        if not path:
            raise ConfigurationError(
                f"Connection '{conn_name}': 'path' is required for SQLite"
            )

        return f"sqlite:///{path}"

    def _build_mssql_string(
        self,
        conn_name: str,
        config: Dict[str, Any]
    ) -> str:
        """Build Microsoft SQL Server connection string."""
        host = self._resolve_config_value(config.get('host', 'localhost'))
        port = config.get('port', 1433)
        database = self._resolve_config_value(config.get('database', ''))
        user = self._resolve_config_value(config.get('user', ''))
        password = self._resolve_config_value(config.get('password', ''))
        driver = config.get('driver', 'ODBC Driver 17 for SQL Server')

        if not database:
            raise ConfigurationError(
                f"Connection '{conn_name}': 'database' is required"
            )

        if password:
            url = f"mssql+pyodbc://{user}:{password}@{host}:{port}/{database}"
        elif user:
            url = f"mssql+pyodbc://{user}@{host}:{port}/{database}"
        else:
            raise ConfigurationError(
                f"Connection '{conn_name}': 'user' is required for SQL Server"
            )

        url += f"?driver={driver}"
        return url

    def _resolve_config_value(self, value: Any) -> str:
        """
        Resolve a config value that might contain ${VAR} references.

        Args:
            value: Config value (string or other type)

        Returns:
            Resolved string value
        """
        if not isinstance(value, str):
            return str(value) if value is not None else ""

        value = value.strip()

        # Check if it's an environment variable reference
        if value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1].strip()
            env_value = os.environ.get(var_name)

            if env_value is None:
                raise ExecutionError(
                    f"Environment variable not found: {var_name}\n"
                    f"Required by connections.yml"
                )

            return env_value.strip()

        return value

    def _is_connection_string(self, reference: str) -> bool:
        """
        Check if reference looks like a valid connection string.

        Args:
            reference: String to check

        Returns:
            True if it looks like a connection string
        """
        try:
            parsed = urlparse(reference)

            # Must have a scheme
            if not parsed.scheme:
                return False

            # Check if scheme is a known database type
            return parsed.scheme.lower() in [
                'postgresql', 'postgres',
                'mysql',
                'bigquery',
                'snowflake',
                'sqlite',
                'mssql',
                'redshift',
            ]
        except Exception:
            return False

    def validate_connection(self, connection_string: str) -> bool:
        """
        Validate that a connection string can be parsed.

        Args:
            connection_string: Connection string to validate

        Returns:
            True if valid

        Raises:
            ConfigurationError: If connection string is invalid
        """
        try:
            parsed = urlparse(connection_string)

            if not parsed.scheme:
                raise ConfigurationError(
                    f"Invalid connection string (no scheme): {connection_string}"
                )

            return True
        except Exception as e:
            raise ConfigurationError(
                f"Invalid connection string: {e}"
            ) from e
```

### 2. Module Init File

**File**: `src/sqlsentinel/credentials/__init__.py`

```python
"""Credential management for SQL Sentinel."""

from .resolver import CredentialResolver

__all__ = ['CredentialResolver']
```

---

## Integration Points

### 1. ConfigLoader Integration

**File**: `src/sqlsentinel/config/loader.py` (MODIFY)

Add credential resolution when loading database configuration:

```python
# Add import at top of file
from ..credentials.resolver import CredentialResolver

class ConfigLoader:
    """Load and parse alert configuration from YAML files."""

    @staticmethod
    def load(config_path: str | Path) -> AppConfig:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to alerts.yaml file

        Returns:
            Parsed and validated AppConfig
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise ConfigurationError(f"Config file not found: {config_path}")

        # Load YAML
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)

        # MODIFICATION: Resolve database credentials
        config_dir = config_path.parent
        credential_resolver = CredentialResolver(config_dir=config_dir)

        if 'database' in raw_config and 'url' in raw_config['database']:
            original_url = raw_config['database']['url']
            try:
                resolved_url = credential_resolver.resolve(original_url)
                raw_config['database']['url'] = resolved_url
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to resolve database credentials: {e}"
                ) from e

        # Validate and parse config (existing code continues)
        validator = ConfigValidator()
        return validator.validate(raw_config)
```

### 2. CLI Integration (Optional Validation Flag)

**File**: `src/sqlsentinel/cli.py` (MODIFY)

Add `--validate-credentials` flag to test connections before running:

```python
@click.option(
    '--validate-credentials',
    is_flag=True,
    default=False,
    help='Validate database connection before running alerts'
)
def run_alert(
    config_file: str,
    alert: str | None,
    dry_run: bool,
    validate_credentials: bool,
    state_db: str,
    log_level: str
) -> None:
    """Run alerts from configuration file."""

    # Load config (credentials resolved automatically)
    config = ConfigLoader.load(config_file)

    # Optional: Validate connection
    if validate_credentials:
        click.echo("Validating database connection...")
        try:
            db_adapter = AdapterFactory.create_adapter(config.database.url)
            db_adapter.connect()
            click.echo("✓ Database connection successful")
            db_adapter.disconnect()
        except Exception as e:
            click.echo(f"✗ Database connection failed: {e}", err=True)
            raise click.Abort()

    # Continue with alert execution...
```

---

## Configuration Examples

### Example 1: Single Database (Environment Variable)

**File**: `examples/alerts-simple.yaml`

```yaml
database:
  url: "${DATABASE_URL}"

alerts:
  - name: "daily_revenue_check"
    description: "Alert when daily revenue is below threshold"
    query: |
      SELECT
        CASE WHEN SUM(revenue) < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        SUM(revenue) as actual_value,
        10000 as threshold
      FROM orders
      WHERE date = CURRENT_DATE
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["team@company.com"]
```

**Usage**:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/analytics"
poetry run sqlsentinel run examples/alerts-simple.yaml
```

### Example 2: Multiple Databases (connections.yml)

**File**: `examples/connections.yml.example`

```yaml
# SQL Sentinel Connections Configuration
#
# This file should NOT be committed to version control (.gitignore)
# Use environment variables for sensitive values: ${VAR_NAME}

connections:
  # Production PostgreSQL database
  prod:
    type: postgresql
    host: ${PROD_DB_HOST}          # export PROD_DB_HOST="prod-db.example.com"
    port: 5432
    user: ${PROD_DB_USER}          # export PROD_DB_USER="analytics_user"
    password: ${PROD_DB_PASSWORD}  # export PROD_DB_PASSWORD="secure-password"
    database: analytics_prod

  # Development PostgreSQL
  dev:
    type: postgresql
    host: localhost
    port: 5432
    user: dev_user
    password: dev_password
    database: analytics_dev

  # BigQuery analytics warehouse
  analytics_warehouse:
    type: bigquery
    project_id: ${GCP_PROJECT_ID}
    dataset: analytics
    credentials_path: ${GOOGLE_APPLICATION_CREDENTIALS}
    location: US

  # Snowflake data warehouse
  snowflake_prod:
    type: snowflake
    account: ${SNOWFLAKE_ACCOUNT}
    user: ${SNOWFLAKE_USER}
    password: ${SNOWFLAKE_PASSWORD}
    database: ANALYTICS
    warehouse: COMPUTE_WH
    schema: PUBLIC
    role: ANALYST

  # Local SQLite for testing
  local:
    type: sqlite
    path: ./test.db

  # MySQL database
  mysql_prod:
    type: mysql
    host: ${MYSQL_HOST}
    port: 3306
    user: ${MYSQL_USER}
    password: ${MYSQL_PASSWORD}
    database: production
```

**File**: `examples/alerts-multi-db.yaml`

```yaml
database:
  url: "@prod"  # References 'prod' connection from connections.yml

alerts:
  - name: "user_growth"
    query: |
      SELECT
        CASE WHEN COUNT(*) < 100 THEN 'ALERT' ELSE 'OK' END as status,
        COUNT(*) as actual_value,
        100 as threshold
      FROM users
      WHERE created_at >= CURRENT_DATE
    schedule: "0 10 * * *"
    notify:
      - channel: slack
        webhook_url: "${SLACK_WEBHOOK_URL}"
```

**Usage**:
```bash
# Set environment variables referenced in connections.yml
export PROD_DB_HOST="prod-db.example.com"
export PROD_DB_USER="analytics_user"
export PROD_DB_PASSWORD="secure-password"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Run alerts (credentials resolved automatically)
poetry run sqlsentinel run examples/alerts-multi-db.yaml
```

### Example 3: BigQuery with ADC

**File**: `examples/alerts-bigquery.yaml`

```yaml
database:
  url: "${BIGQUERY_URL}"

alerts:
  - name: "data_freshness"
    query: |
      SELECT
        CASE WHEN hours_old > 24 THEN 'ALERT' ELSE 'OK' END as status,
        hours_old as actual_value,
        24 as threshold
      FROM (
        SELECT TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(created_at), HOUR) as hours_old
        FROM `my-project.my_dataset.my_table`
      )
    schedule: "0 */6 * * *"
    notify:
      - channel: email
        recipients: ["data-team@company.com"]
```

**Usage**:
```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Set BigQuery URL
export BIGQUERY_URL="bigquery://my-project-id/my_dataset"

# Run alerts
poetry run sqlsentinel run examples/alerts-bigquery.yaml
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_credentials/test_resolver.py`

```python
"""Tests for CredentialResolver."""

import os
import tempfile
from pathlib import Path

import pytest

from sqlsentinel.credentials.resolver import CredentialResolver
from sqlsentinel.models.errors import ConfigurationError, ExecutionError


class TestEnvironmentVariableResolution:
    """Test ${VAR_NAME} resolution."""

    def test_resolve_existing_env_var(self, monkeypatch):
        """Test resolving an existing environment variable."""
        monkeypatch.setenv("TEST_DB_URL", "postgresql://localhost/test")

        resolver = CredentialResolver()
        result = resolver.resolve("${TEST_DB_URL}")

        assert result == "postgresql://localhost/test"

    def test_resolve_missing_env_var(self):
        """Test error when environment variable doesn't exist."""
        resolver = CredentialResolver()

        with pytest.raises(ExecutionError, match="Environment variable not found"):
            resolver.resolve("${NONEXISTENT_VAR}")

    def test_resolve_empty_env_var(self, monkeypatch):
        """Test error when environment variable is empty."""
        monkeypatch.setenv("EMPTY_VAR", "   ")

        resolver = CredentialResolver()

        with pytest.raises(ExecutionError, match="empty"):
            resolver.resolve("${EMPTY_VAR}")

    def test_resolve_env_var_with_whitespace(self, monkeypatch):
        """Test environment variable with leading/trailing whitespace."""
        monkeypatch.setenv("DB_URL", "  postgresql://localhost/test  ")

        resolver = CredentialResolver()
        result = resolver.resolve("${DB_URL}")

        assert result == "postgresql://localhost/test"


class TestConnectionReferenceResolution:
    """Test @name resolution from connections.yml."""

    @pytest.fixture
    def connections_file(self, tmp_path):
        """Create temporary connections.yml file."""
        connections_yaml = """
connections:
  test_pg:
    type: postgresql
    host: localhost
    port: 5432
    user: testuser
    password: testpass
    database: testdb

  test_bq:
    type: bigquery
    project_id: my-project
    dataset: my_dataset
    credentials_path: /path/to/key.json
"""
        conn_file = tmp_path / "connections.yml"
        conn_file.write_text(connections_yaml)
        return conn_file

    def test_resolve_postgresql_connection(self, connections_file):
        """Test resolving PostgreSQL connection."""
        resolver = CredentialResolver(connections_file=connections_file)
        result = resolver.resolve("@test_pg")

        assert result == "postgresql://testuser:testpass@localhost:5432/testdb"

    def test_resolve_bigquery_connection(self, connections_file):
        """Test resolving BigQuery connection."""
        resolver = CredentialResolver(connections_file=connections_file)
        result = resolver.resolve("@test_bq")

        expected = "bigquery://my-project/my_dataset?credentials=/path/to/key.json"
        assert result == expected

    def test_resolve_with_connection_prefix(self, connections_file):
        """Test @connection:name syntax."""
        resolver = CredentialResolver(connections_file=connections_file)
        result = resolver.resolve("@connection:test_pg")

        assert result == "postgresql://testuser:testpass@localhost:5432/testdb"

    def test_connection_not_found(self, connections_file):
        """Test error when connection doesn't exist."""
        resolver = CredentialResolver(connections_file=connections_file)

        with pytest.raises(ExecutionError, match="Connection 'nonexistent' not found"):
            resolver.resolve("@nonexistent")

    def test_connections_file_missing(self, tmp_path):
        """Test error when connections.yml doesn't exist."""
        resolver = CredentialResolver(config_dir=tmp_path)

        with pytest.raises(ExecutionError, match="connections.yml not found"):
            resolver.resolve("@prod")


class TestLiteralConnectionStrings:
    """Test literal connection string passthrough."""

    def test_postgresql_literal(self):
        """Test PostgreSQL connection string."""
        resolver = CredentialResolver()
        url = "postgresql://user:pass@host:5432/db"

        result = resolver.resolve(url)
        assert result == url

    def test_bigquery_literal(self):
        """Test BigQuery connection string."""
        resolver = CredentialResolver()
        url = "bigquery://my-project/dataset"

        result = resolver.resolve(url)
        assert result == url

    def test_sqlite_literal(self):
        """Test SQLite connection string."""
        resolver = CredentialResolver()
        url = "sqlite:///path/to/db.db"

        result = resolver.resolve(url)
        assert result == url


class TestConnectionStringBuilders:
    """Test individual connection string builders."""

    def test_postgresql_builder_with_password(self):
        """Test PostgreSQL with password."""
        resolver = CredentialResolver()
        config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'user': 'myuser',
            'password': 'mypass',
            'database': 'mydb',
        }

        result = resolver._build_connection_string('test', config)
        assert result == "postgresql://myuser:mypass@localhost:5432/mydb"

    def test_postgresql_builder_without_password(self):
        """Test PostgreSQL without password."""
        resolver = CredentialResolver()
        config = {
            'type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'user': 'myuser',
            'database': 'mydb',
        }

        result = resolver._build_connection_string('test', config)
        assert result == "postgresql://myuser@localhost:5432/mydb"

    def test_bigquery_builder_minimal(self):
        """Test BigQuery with minimal config."""
        resolver = CredentialResolver()
        config = {
            'type': 'bigquery',
            'project_id': 'my-project',
        }

        result = resolver._build_connection_string('test', config)
        assert result == "bigquery://my-project"

    def test_bigquery_builder_full(self):
        """Test BigQuery with all options."""
        resolver = CredentialResolver()
        config = {
            'type': 'bigquery',
            'project_id': 'my-project',
            'dataset': 'my_dataset',
            'credentials_path': '/path/to/key.json',
            'location': 'EU',
        }

        result = resolver._build_connection_string('test', config)
        assert result == "bigquery://my-project/my_dataset?credentials=/path/to/key.json&location=EU"

    def test_mysql_builder(self):
        """Test MySQL connection string."""
        resolver = CredentialResolver()
        config = {
            'type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'user': 'myuser',
            'password': 'mypass',
            'database': 'mydb',
        }

        result = resolver._build_connection_string('test', config)
        assert result == "mysql+pymysql://myuser:mypass@localhost:3306/mydb"

    def test_snowflake_builder(self):
        """Test Snowflake connection string."""
        resolver = CredentialResolver()
        config = {
            'type': 'snowflake',
            'account': 'myaccount',
            'user': 'myuser',
            'password': 'mypass',
            'database': 'MYDB',
            'warehouse': 'COMPUTE_WH',
            'schema': 'PUBLIC',
        }

        result = resolver._build_connection_string('test', config)
        assert "snowflake://myuser:mypass@myaccount/MYDB" in result
        assert "warehouse=COMPUTE_WH" in result
        assert "schema=PUBLIC" in result

    def test_sqlite_builder(self):
        """Test SQLite connection string."""
        resolver = CredentialResolver()
        config = {
            'type': 'sqlite',
            'path': '/path/to/db.db',
        }

        result = resolver._build_connection_string('test', config)
        assert result == "sqlite:////path/to/db.db"


class TestEnvironmentVariableSubstitution:
    """Test ${VAR} substitution within connections.yml."""

    def test_env_var_in_connection_config(self, tmp_path, monkeypatch):
        """Test environment variable in connection config."""
        monkeypatch.setenv("DB_PASSWORD", "secret123")

        connections_yaml = """
connections:
  prod:
    type: postgresql
    host: localhost
    user: myuser
    password: ${DB_PASSWORD}
    database: mydb
"""
        conn_file = tmp_path / "connections.yml"
        conn_file.write_text(connections_yaml)

        resolver = CredentialResolver(connections_file=conn_file)
        result = resolver.resolve("@prod")

        assert result == "postgresql://myuser:secret123@localhost:5432/mydb"

    def test_missing_env_var_in_config(self, tmp_path):
        """Test error when env var in config is missing."""
        connections_yaml = """
connections:
  prod:
    type: postgresql
    host: localhost
    password: ${MISSING_PASSWORD}
    database: mydb
"""
        conn_file = tmp_path / "connections.yml"
        conn_file.write_text(connections_yaml)

        resolver = CredentialResolver(connections_file=conn_file)

        with pytest.raises(ExecutionError, match="MISSING_PASSWORD"):
            resolver.resolve("@prod")


class TestErrorHandling:
    """Test error cases and messages."""

    def test_empty_reference(self):
        """Test error with empty reference."""
        resolver = CredentialResolver()

        with pytest.raises(ConfigurationError, match="cannot be empty"):
            resolver.resolve("")

    def test_invalid_format(self):
        """Test error with invalid format."""
        resolver = CredentialResolver()

        with pytest.raises(ConfigurationError, match="Invalid database URL format"):
            resolver.resolve("not-a-valid-reference")

    def test_missing_connection_type(self, tmp_path):
        """Test error when connection type is missing."""
        connections_yaml = """
connections:
  bad:
    host: localhost
"""
        conn_file = tmp_path / "connections.yml"
        conn_file.write_text(connections_yaml)

        resolver = CredentialResolver(connections_file=conn_file)

        with pytest.raises(ConfigurationError, match="missing 'type' field"):
            resolver.resolve("@bad")

    def test_unsupported_connection_type(self, tmp_path):
        """Test error with unsupported connection type."""
        connections_yaml = """
connections:
  bad:
    type: oracle
"""
        conn_file = tmp_path / "connections.yml"
        conn_file.write_text(connections_yaml)

        resolver = CredentialResolver(connections_file=conn_file)

        with pytest.raises(ConfigurationError, match="Unsupported connection type"):
            resolver.resolve("@bad")
```

### Integration Tests

**File**: `tests/test_credentials/test_integration.py`

```python
"""Integration tests for credential resolution with ConfigLoader."""

import os
from pathlib import Path
import tempfile

import pytest

from sqlsentinel.config.loader import ConfigLoader
from sqlsentinel.models.errors import ConfigurationError, ExecutionError


class TestConfigLoaderIntegration:
    """Test credential resolution integrated with ConfigLoader."""

    def test_load_config_with_env_var(self, tmp_path, monkeypatch):
        """Test loading config with environment variable."""
        monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://localhost/test")

        config_yaml = """
database:
  url: ${TEST_DATABASE_URL}

alerts:
  - name: test_alert
    query: SELECT 'OK' as status
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["test@example.com"]
"""
        config_file = tmp_path / "alerts.yaml"
        config_file.write_text(config_yaml)

        config = ConfigLoader.load(config_file)

        assert config.database.url == "postgresql://localhost/test"

    def test_load_config_with_connection_reference(self, tmp_path, monkeypatch):
        """Test loading config with @connection reference."""
        monkeypatch.setenv("DB_PASSWORD", "secret")

        connections_yaml = """
connections:
  prod:
    type: postgresql
    host: localhost
    user: testuser
    password: ${DB_PASSWORD}
    database: testdb
"""
        conn_file = tmp_path / "connections.yml"
        conn_file.write_text(connections_yaml)

        config_yaml = """
database:
  url: "@prod"

alerts:
  - name: test_alert
    query: SELECT 'OK' as status
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["test@example.com"]
"""
        config_file = tmp_path / "alerts.yaml"
        config_file.write_text(config_yaml)

        config = ConfigLoader.load(config_file)

        assert config.database.url == "postgresql://testuser:secret@localhost:5432/testdb"

    def test_load_config_with_literal_string(self, tmp_path):
        """Test loading config with literal connection string."""
        config_yaml = """
database:
  url: "sqlite:///test.db"

alerts:
  - name: test_alert
    query: SELECT 'OK' as status
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["test@example.com"]
"""
        config_file = tmp_path / "alerts.yaml"
        config_file.write_text(config_yaml)

        config = ConfigLoader.load(config_file)

        assert config.database.url == "sqlite:///test.db"

    def test_error_message_for_missing_env_var(self, tmp_path):
        """Test helpful error when environment variable is missing."""
        config_yaml = """
database:
  url: ${MISSING_VAR}

alerts:
  - name: test_alert
    query: SELECT 'OK' as status
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["test@example.com"]
"""
        config_file = tmp_path / "alerts.yaml"
        config_file.write_text(config_yaml)

        with pytest.raises(ConfigurationError, match="Failed to resolve database credentials"):
            ConfigLoader.load(config_file)
```

---

## Documentation Requirements

### Analyst-Focused Documentation

**File**: `docs/CREDENTIAL_GUIDE.md`

Structure:
1. **5-Minute Quick Start**
   - Single database setup with environment variable
   - Copy-paste examples

2. **Setup by Platform**
   - Local development
   - Docker
   - Kubernetes
   - AWS Lambda
   - Google Cloud Run
   - Azure Functions

3. **Multiple Databases**
   - When to use connections.yml
   - Example configurations
   - Best practices

4. **Security Checklist**
   - Never commit credentials
   - Use environment variables
   - Rotate credentials regularly
   - Service accounts vs personal credentials

5. **Troubleshooting**
   - Common error messages
   - How to debug connection issues
   - How to validate credentials

---

## Security Considerations

### Best Practices

1. **Never commit credentials to git**
   - Add `connections.yml` to `.gitignore`
   - Add `.env` to `.gitignore`
   - Add `*.json` (service account keys) to `.gitignore`

2. **Use environment variables for secrets**
   - Database passwords
   - API tokens
   - Service account keys (paths)

3. **Principle of least privilege**
   - Use read-only database users for alerts
   - Limit permissions to specific schemas/tables
   - Use separate credentials per environment

4. **Credential rotation**
   - Rotate passwords every 90 days
   - Use short-lived credentials when possible
   - Audit credential usage

5. **File permissions**
   - `chmod 600 connections.yml` (owner read/write only)
   - `chmod 600 service-account-key.json`

### Example .gitignore

```
# Credential files - NEVER COMMIT
connections.yml
.env
.env.*
*.json
!package.json
!pyproject.json

# State database
*.db
sqlsentinel.db

# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/

# IDE
.vscode/
.idea/
*.swp
```

---

## Summary

### Implementation Checklist

- [ ] Create `src/sqlsentinel/credentials/` module
- [ ] Implement `CredentialResolver` class with all resolution methods
- [ ] Integrate with `ConfigLoader`
- [ ] Add comprehensive unit tests
- [ ] Add integration tests
- [ ] Create `examples/connections.yml.example`
- [ ] Update `.gitignore`
- [ ] Update example alert files
- [ ] Create analyst documentation
- [ ] Add `--validate-credentials` CLI flag

### Key Features

✅ **Three resolution methods**: Environment variables, connection references, literal strings
✅ **Backward compatible**: Existing configs work without changes
✅ **Analyst-friendly**: Simple for basic use, powerful for complex scenarios
✅ **Secure by default**: Encourages environment variables and .gitignore
✅ **Helpful errors**: Clear messages with actionable guidance
✅ **Well-tested**: Comprehensive test coverage
✅ **Production-ready**: Works in all deployment environments

### Estimated Effort

- **Core implementation**: 2-3 hours
- **Testing**: 2-3 hours
- **Documentation**: 1-2 hours
- **Total**: 5-8 hours

---

## Quick Reference

### Syntax Guide

```yaml
# Environment variable
database:
  url: "${DATABASE_URL}"

# Connection reference (short form)
database:
  url: "@prod"

# Connection reference (long form)
database:
  url: "@connection:prod"

# Literal connection string
database:
  url: "postgresql://user:pass@host/db"
```

### Common Patterns

**Local development**:
```bash
export DATABASE_URL="sqlite:///dev.db"
sqlsentinel run alerts.yaml
```

**Docker**:
```bash
docker run -e DATABASE_URL="postgresql://..." sqlsentinel
```

**Kubernetes**:
```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: database-credentials
        key: url
```

**AWS Lambda**:
```bash
aws lambda update-function-configuration \
  --function-name sqlsentinel \
  --environment "Variables={DATABASE_URL=postgresql://...}"
```

---

**End of Implementation Guide**
