# SQL Sentinel API Specification

Version: 1.0  
Date: 2025-01-XX  
Status: Draft

## Overview

This document defines the internal and external APIs for SQL Sentinel, including data models, interfaces, error handling, and usage patterns.

## 1. Core Data Models

### 1.1 Configuration Models (Implemented in Sprint 1.2 & 2.1)

```python
from pydantic import BaseModel, Field, field_validator
from typing import Any, Optional

class NotificationConfig(BaseModel):
    """Notification channel configuration."""

    channel: str = Field(..., description="Notification channel (email, slack, webhook)")
    recipients: Optional[list[str]] = Field(None, description="Email recipients")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for slack/webhook channels")
    subject: Optional[str] = Field(None, description="Email subject template")

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        """Validate notification channel."""
        if v not in ["email", "slack", "webhook"]:
            raise ValueError(f"Unsupported notification channel: {v}")
        return v

class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    url: str = Field(..., description="Database connection URL (SQLAlchemy format)")
    pool_size: int = Field(5, description="Connection pool size")
    timeout: int = Field(30, description="Connection timeout in seconds")

class AlertConfig(BaseModel):
    """Alert configuration from YAML (Sprint 1.2)."""

    name: str = Field(..., min_length=1, description="Alert name")
    description: Optional[str] = Field(None, description="Alert description")
    query: str = Field(..., min_length=1, description="SQL query to execute")
    schedule: str = Field(..., description="Cron schedule expression")
    notify: list[NotificationConfig] = Field(
        default_factory=list, description="Notification configurations"
    )
    enabled: bool = Field(True, description="Whether alert is enabled")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate SQL query."""
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v: str) -> str:
        """Validate cron schedule expression."""
        from croniter import croniter

        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron schedule: {v}")
        return v

# Note: Advanced features like AlertBehavior, AlertMetadata, and severity levels
# are planned for future sprints. Sprint 2.1 focuses on core execution.
```

### 1.2 Execution Models (Implemented in Sprint 2.1)

```python
from pydantic import BaseModel, Field, field_validator

class QueryResult(BaseModel):
    """Result from executing an alert query."""

    status: str = Field(..., description="Alert status: ALERT or OK")
    actual_value: Any = Field(None, description="The metric value that triggered the alert")
    threshold: Any = Field(None, description="The threshold that was exceeded")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context fields")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status field."""
        v = v.upper()
        if v not in ["ALERT", "OK"]:
            raise ValueError(f"Status must be 'ALERT' or 'OK', got '{v}'")
        return v

class ExecutionResult(BaseModel):
    """Result from executing an alert."""

    alert_name: str = Field(..., description="Name of the alert that was executed")
    timestamp: str = Field(..., description="Execution timestamp (ISO format)")
    status: str = Field(..., description="Execution status: success, failure, error")
    query_result: Optional[QueryResult] = Field(None, description="Query result if successful")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    error: Optional[str] = Field(None, description="Error message if execution failed")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate execution status."""
        v = v.lower()
        if v not in ["success", "failure", "error"]:
            raise ValueError(f"Status must be 'success', 'failure', or 'error', got '{v}'")
        return v

# Note: status field mapping:
# - "success": Query executed successfully and returned status='OK'
# - "failure": Query executed successfully but returned status='ALERT' (alert condition met)
# - "error": Query execution failed due to database error, connection issue, etc.
```

### 1.3 State Models (Implemented in Sprint 2.1)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class AlertState:
    """Alert state for deduplication and silencing (Sprint 2.1)."""

    alert_name: str
    current_status: Optional[str] = None  # 'ALERT', 'OK', 'ERROR'
    last_execution_at: Optional[datetime] = None
    last_alert_at: Optional[datetime] = None
    consecutive_alerts: int = 0
    consecutive_successes: int = 0
    silence_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def should_notify(self, new_status: str, min_interval_seconds: int = 0) -> bool:
        """Determine if notification should be sent based on state.

        Rules:
        - Only notify if new_status is 'ALERT'
        - Don't notify if currently silenced
        - Don't notify if within minimum notification interval
        - Don't notify if already alerting (deduplicate consecutive alerts)
        """
        if self.is_silenced():
            return False

        if new_status != "ALERT":
            return False

        # Check minimum interval between alerts
        if min_interval_seconds > 0 and self.last_alert_at:
            time_since_last = datetime.utcnow() - self.last_alert_at
            if time_since_last.total_seconds() < min_interval_seconds:
                return False

        # Only notify on status transition to ALERT (deduplication)
        if self.current_status != "ALERT":
            return True

        return False

    def is_silenced(self) -> bool:
        """Check if alert is currently silenced."""
        if self.silence_until is None:
            return False
        return datetime.utcnow() < self.silence_until

@dataclass
class ExecutionRecord:
    """Record of a single alert execution (Sprint 2.1)."""

    alert_name: str
    executed_at: datetime
    execution_duration_ms: float
    status: str  # 'success', 'failure', 'error'
    actual_value: Optional[float] = None
    threshold: Optional[float] = None
    query: Optional[str] = None
    error_message: Optional[str] = None
    triggered_by: str = "MANUAL"  # 'MANUAL', 'CRON', 'API'
    notification_sent: bool = False
    notification_error: Optional[str] = None
    context_data: Optional[dict] = None
```

## 2. Command-Line Interface (Implemented in Sprint 2.1)

### 2.1 CLI Commands

SQL Sentinel provides a command-line interface for manual alert execution and management:

```bash
# Initialize state database
sqlsentinel init --state-db <database_url>

# Validate alert configuration file
sqlsentinel validate <config_file>

# Run alerts manually
sqlsentinel run <config_file> [--alert <name>] [--dry-run] [--state-db <url>]

# View execution history
sqlsentinel history <config_file> [--alert <name>] [--limit <n>] [--state-db <url>]
```

**Command Details:**

- `init`: Creates the internal SQL Sentinel tables (sqlsentinel_state, sqlsentinel_executions, sqlsentinel_configs)
- `validate`: Validates YAML configuration file syntax and alert definitions
- `run`: Executes one or all alerts from config file
  - `--alert`: Run specific alert by name (default: run all enabled alerts)
  - `--dry-run`: Test mode - no notifications sent, no state updates
  - `--state-db`: Override state database URL (default: uses database.url from config)
- `history`: Shows execution history with statistics
  - `--alert`: Filter history for specific alert
  - `--limit`: Limit number of records (default: 10)

**Example Usage:**

```bash
# Set up state database
export STATE_DB_URL="sqlite:///sqlsentinel.db"
sqlsentinel init --state-db $STATE_DB_URL

# Validate configuration
sqlsentinel validate examples/alerts.yaml

# Test alert in dry-run mode
sqlsentinel run examples/alerts.yaml --alert daily_revenue_check --dry-run

# Execute all enabled alerts
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="alerts@company.com"
export SMTP_PASSWORD="app-password"
sqlsentinel run examples/alerts.yaml

# View execution history
sqlsentinel history examples/alerts.yaml --limit 20
```

## 3. Core Service APIs

### 3.1 Configuration Manager API (Implemented in Sprint 1.2)

```python
from abc import ABC, abstractmethod
from typing import Protocol

class ConfigurationStorage(Protocol):
    """Protocol for configuration storage backends"""
    
    def load_configs(self) -> List[AlertConfig]:
        """Load all active alert configurations"""
        ...
        
    def load_config(self, alert_name: str) -> Optional[AlertConfig]:
        """Load specific alert configuration"""
        ...
        
    def save_config(self, config: AlertConfig) -> bool:
        """Save alert configuration"""
        ...
        
    def delete_config(self, alert_name: str) -> bool:
        """Delete alert configuration"""
        ...

class ConfigManager:
    """Manages alert configurations with validation and storage"""
    
    def __init__(self, storage: ConfigurationStorage):
        self.storage = storage
        
    def load_all_configs(self) -> List[AlertConfig]:
        """Load and validate all configurations"""
        configs = self.storage.load_configs()
        validated_configs = []
        
        for config in configs:
            validation_result = self.validate_config(config)
            if validation_result.is_valid:
                validated_configs.append(config)
            else:
                # Log validation errors
                self._log_config_error(config.name, validation_result.errors)
                
        return validated_configs
    
    def validate_config(self, config: AlertConfig) -> "ValidationResult":
        """Comprehensive configuration validation"""
        errors = []
        warnings = []
        
        # Schema validation
        schema_errors = self._validate_schema(config)
        errors.extend(schema_errors)
        
        # SQL validation  
        sql_errors = self._validate_sql(config.query)
        errors.extend(sql_errors)
        
        # Schedule validation
        schedule_errors = self._validate_schedule(config.schedule, config.timezone)
        errors.extend(schedule_errors)
        
        # Notification validation
        notification_errors = self._validate_notifications(config.notifications)
        errors.extend(notification_errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def sync_from_git(self, git_configs: List[AlertConfig]) -> "SyncResult":
        """Sync configurations from Git to storage"""
        results = []
        
        for config in git_configs:
            try:
                validation_result = self.validate_config(config)
                if validation_result.is_valid:
                    success = self.storage.save_config(config)
                    results.append(ConfigSyncResult(
                        alert_name=config.name,
                        status="success" if success else "failed",
                        errors=[]
                    ))
                else:
                    results.append(ConfigSyncResult(
                        alert_name=config.name,
                        status="validation_failed",
                        errors=validation_result.errors
                    ))
            except Exception as e:
                results.append(ConfigSyncResult(
                    alert_name=config.name,
                    status="error",
                    errors=[str(e)]
                ))
                
        return SyncResult(results=results)
    
    def _validate_sql(self, query: str) -> List[str]:
        """Validate SQL query safety and syntax"""
        errors = []
        
        # Basic SQL injection prevention
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER']
        query_upper = query.upper()
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                errors.append(f"Dangerous SQL keyword detected: {keyword}")
        
        # TODO: Add proper SQL parsing and AST validation
        
        return errors
```

### 2.2 Alert Executor API

```python
class DataWarehouseConnection(Protocol):
    """Protocol for data warehouse connections"""
    
    def execute_query(self, query: str, timeout: int = 300) -> Dict[str, Any]:
        """Execute SQL query and return results"""
        ...
        
    def test_connection(self) -> bool:
        """Test database connectivity"""
        ...

class AlertExecutor:
    """Executes alert queries and processes results"""
    
    def __init__(self, connection: DataWarehouseConnection):
        self.connection = connection
        
    async def execute_alert(self, config: AlertConfig) -> ExecutionResult:
        """Execute a single alert and return result"""
        execution_id = self._generate_execution_id()
        start_time = datetime.utcnow()
        
        try:
            # Execute query with timeout
            raw_result = await self.connection.execute_query(
                config.query, 
                timeout=300
            )
            
            # Parse and validate result
            query_result = self._parse_query_result(raw_result)
            if not query_result.validate_contract():
                raise ValueError("Query result doesn't match expected contract")
            
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Determine execution status
            status = ExecutionStatus.ALERT if query_result.status == 'ALERT' else ExecutionStatus.SUCCESS
            
            return ExecutionResult(
                execution_id=execution_id,
                alert_name=config.name,
                status=status,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                query_result=query_result
            )
            
        except Exception as e:
            return ExecutionResult(
                execution_id=execution_id,
                alert_name=config.name,
                status=ExecutionStatus.ERROR,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=self._create_error_details(e)
            )
    
    async def execute_batch(self, configs: List[AlertConfig]) -> List[ExecutionResult]:
        """Execute multiple alerts concurrently"""
        import asyncio
        
        tasks = [self.execute_alert(config) for config in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error result for failed execution
                error_result = ExecutionResult(
                    execution_id=self._generate_execution_id(),
                    alert_name=configs[i].name,
                    status=ExecutionStatus.ERROR,
                    start_time=datetime.utcnow(),
                    error=self._create_error_details(result)
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
                
        return processed_results
    
    def _parse_query_result(self, raw_result: Dict[str, Any]) -> QueryResult:
        """Parse raw database result into QueryResult"""
        # Assuming raw_result is a dict with column names as keys
        # and the first row of results as values
        
        if not raw_result or 'status' not in raw_result:
            raise ValueError("Query result missing required 'status' column")
            
        return QueryResult(
            status=raw_result['status'],
            actual_value=raw_result.get('actual_value'),
            threshold=raw_result.get('threshold'),
            message=raw_result.get('message'),
            additional_data={k: v for k, v in raw_result.items() 
                           if k not in ['status', 'actual_value', 'threshold', 'message']}
        )
```

### 2.3 Notification Service API

```python
class NotificationProvider(Protocol):
    """Protocol for notification providers"""
    
    async def send_notification(self, message: str, config: NotificationConfig) -> bool:
        """Send notification via this provider"""
        ...

class NotificationService:
    """Manages notification delivery across multiple channels"""
    
    def __init__(self):
        self.providers: Dict[NotificationChannel, NotificationProvider] = {}
        
    def register_provider(self, channel: NotificationChannel, provider: NotificationProvider):
        """Register a notification provider for a channel"""
        self.providers[channel] = provider
        
    async def send_alert_notification(
        self, 
        execution_result: ExecutionResult, 
        config: AlertConfig,
        alert_state: AlertState
    ) -> List[str]:
        """Send notifications for alert result"""
        sent_notifications = []
        
        # Check if we should send notification based on state
        if not alert_state.should_send_notification(config.behavior):
            return sent_notifications
            
        for notification_config in config.notifications:
            if not notification_config.enabled:
                continue
                
            try:
                # Render notification template
                message = self._render_notification_template(
                    execution_result, 
                    config, 
                    notification_config
                )
                
                # Send notification
                provider = self.providers.get(notification_config.channel)
                if provider:
                    success = await provider.send_notification(message, notification_config)
                    if success:
                        sent_notifications.append(f"{notification_config.channel.value}")
                        
            except Exception as e:
                # Log notification error but don't fail entire execution
                self._log_notification_error(config.name, notification_config.channel, e)
                
        return sent_notifications
    
    def _render_notification_template(
        self, 
        execution_result: ExecutionResult, 
        config: AlertConfig,
        notification_config: NotificationConfig
    ) -> str:
        """Render notification message from template"""
        
        # Create template context
        context = {
            'alert_name': config.name,
            'description': config.description,
            'status': execution_result.query_result.status if execution_result.query_result else 'ERROR',
            'actual_value': execution_result.query_result.actual_value if execution_result.query_result else None,
            'threshold': execution_result.query_result.threshold if execution_result.query_result else None,
            'execution_time': execution_result.start_time.isoformat(),
            'duration_ms': execution_result.duration_ms,
            'severity': config.severity.value,
            'team': config.metadata.team,
            'runbook_url': config.metadata.runbook_url,
        }
        
        # Add query result additional data
        if execution_result.query_result:
            context.update(execution_result.query_result.additional_data)
        
        # Use template or default format
        template = notification_config.body_template or self._get_default_template(notification_config.channel)
        
        # Simple template rendering (replace with proper template engine)
        rendered = template
        for key, value in context.items():
            if value is not None:
                rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
                
        return rendered
```

### 2.4 State Manager API

```python
class StateStorage(Protocol):
    """Protocol for state storage"""
    
    def load_state(self, alert_name: str) -> Optional[AlertState]:
        """Load alert state"""
        ...
        
    def save_state(self, state: AlertState) -> bool:
        """Save alert state"""
        ...
        
    def load_execution_history(self, alert_name: str, limit: int = 100) -> List[ExecutionResult]:
        """Load recent execution history"""
        ...
        
    def save_execution_result(self, result: ExecutionResult) -> bool:
        """Save execution result"""
        ...

class StateManager:
    """Manages alert state and execution history"""
    
    def __init__(self, storage: StateStorage):
        self.storage = storage
        
    def update_state_after_execution(
        self, 
        execution_result: ExecutionResult, 
        config: AlertConfig
    ) -> AlertState:
        """Update alert state based on execution result"""
        
        # Load current state or create new
        state = self.storage.load_state(execution_result.alert_name) or AlertState(
            alert_name=execution_result.alert_name
        )
        
        # Update state based on execution result
        state.last_status = execution_result.status
        state.last_execution_time = execution_result.start_time
        state.total_executions += 1
        
        if execution_result.status == ExecutionStatus.ALERT:
            state.consecutive_alerts += 1
            state.consecutive_successes = 0
            state.last_alert_time = execution_result.start_time
            state.total_alerts += 1
        elif execution_result.status == ExecutionStatus.SUCCESS:
            state.consecutive_alerts = 0
            state.consecutive_successes += 1
            
        state.updated_at = datetime.utcnow()
        
        # Save updated state
        self.storage.save_state(state)
        
        # Save execution result
        self.storage.save_execution_result(execution_result)
        
        return state
```

## 3. Supporting Models

### 3.1 Validation Models

```python
@dataclass
class ValidationError:
    field: str
    message: str
    code: str
    
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

@dataclass  
class ConfigSyncResult:
    alert_name: str
    status: str  # 'success', 'failed', 'validation_failed', 'error'
    errors: List[str] = field(default_factory=list)
    
@dataclass
class SyncResult:
    results: List[ConfigSyncResult]
    
    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.status == 'success')
        
    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.status != 'success')
```

## 4. Implemented Service APIs (Sprint 2.1)

### 4.1 Alert Executor

```python
from sqlalchemy import Engine

class AlertExecutor:
    """Executes alerts with state management and notifications (Sprint 2.1)."""

    def __init__(
        self,
        state_db_engine: Engine,
        notification_factory: NotificationFactory,
        min_alert_interval_seconds: int = 0,
    ):
        self.state_manager = StateManager(state_db_engine)
        self.history_manager = ExecutionHistory(state_db_engine)
        self.notification_factory = notification_factory
        self.min_alert_interval_seconds = min_alert_interval_seconds

    def execute_alert(
        self,
        alert: AlertConfig,
        db_adapter: DatabaseAdapter,
        triggered_by: str = "MANUAL",
        dry_run: bool = False,
    ) -> ExecutionResult:
        """Execute alert with full workflow: state → execute → notify → update → record."""
```

### 4.2 State Manager

```python
from sqlalchemy import Engine

class StateManager:
    """Manages alert state in database (Sprint 2.1)."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def get_state(self, alert_name: str) -> AlertState:
        """Get current state for alert (creates new if doesn't exist)."""

    def update_state(self, state: AlertState, new_status: str) -> None:
        """Update state after alert execution."""

    def silence_alert(self, alert_name: str, until: datetime) -> None:
        """Silence alert until specified time."""

    def unsilence_alert(self, alert_name: str) -> None:
        """Remove alert silence."""
```

### 4.3 Execution History

```python
from sqlalchemy import Engine

class ExecutionHistory:
    """Tracks alert execution history (Sprint 2.1)."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def record_execution(self, record: ExecutionRecord) -> int:
        """Record an execution to history. Returns execution ID."""

    def get_recent_executions(
        self, alert_name: Optional[str] = None, limit: int = 10
    ) -> list[ExecutionRecord]:
        """Get recent executions, optionally filtered by alert."""

    def get_statistics(self, alert_name: Optional[str] = None) -> dict:
        """Get execution statistics (totals, averages, durations)."""
```

### 4.4 Notification Services

```python
class NotificationFactory:
    """Creates notification services with environment-based config (Sprint 2.1)."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,  # Falls back to SMTP_HOST env var
        smtp_port: Optional[int] = None,  # Falls back to SMTP_PORT env var
        smtp_username: Optional[str] = None,  # Falls back to SMTP_USERNAME env var
        smtp_password: Optional[str] = None,  # Falls back to SMTP_PASSWORD env var
        smtp_use_tls: Optional[bool] = None,  # Falls back to SMTP_USE_TLS env var
        from_address: Optional[str] = None,  # Falls back to SMTP_FROM_ADDRESS env var
    ):
        pass

    def create_service(self, channel: str) -> NotificationService:
        """Create notification service for channel (email, slack, webhook)."""

class EmailNotificationService(NotificationService):
    """SMTP email notification service with retry logic (Sprint 2.1)."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = True,
        from_address: Optional[str] = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 2,
    ):
        pass

    def send(
        self,
        alert: AlertConfig,
        result: QueryResult,
        notification_config: NotificationConfig,
    ) -> None:
        """Send email notification with exponential backoff retry."""
```

### 4.5 Database Schema Manager

```python
from sqlalchemy import Engine

class SchemaManager:
    """Manages SQL Sentinel internal database schema (Sprint 2.1)."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def create_schema(self) -> None:
        """Create all SQL Sentinel tables."""

    def drop_schema(self) -> None:
        """Drop all SQL Sentinel tables."""

    def schema_exists(self) -> bool:
        """Check if schema exists."""

    def initialize_schema(self) -> None:
        """Initialize schema if it doesn't exist."""
```

## 5. External REST API (Planned - Future Sprint)

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse

app = FastAPI(title="SQL Sentinel API", version="1.0.0")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Alert management
@app.get("/api/v1/alerts")
async def list_alerts():
    """List all active alerts"""
    pass

@app.get("/api/v1/alerts/{alert_name}")
async def get_alert(alert_name: str):
    """Get specific alert configuration"""
    pass

@app.post("/api/v1/alerts/{alert_name}/execute")
async def trigger_alert(alert_name: str):
    """Manually trigger alert execution"""
    pass

@app.get("/api/v1/alerts/{alert_name}/history")
async def get_alert_history(alert_name: str, limit: int = 50):
    """Get alert execution history"""
    pass

@app.post("/api/v1/alerts/{alert_name}/silence")
async def silence_alert(alert_name: str, duration_hours: int):
    """Silence alert for specified duration"""
    pass

@app.delete("/api/v1/alerts/{alert_name}/silence")
async def unsilence_alert(alert_name: str):
    """Remove alert silence"""
    pass

# System monitoring
@app.get("/api/v1/stats")
async def get_system_stats():
    """Get system statistics"""
    pass

@app.get("/api/v1/alerts/{alert_name}/status")
async def get_alert_status(alert_name: str):
    """Get current alert status and state"""
    pass
```

## 6. Error Handling Patterns (Implemented in Sprint 1.2 & 2.1)

### 6.1 Exception Hierarchy

```python
class SQLSentinelError(Exception):
    """Base exception for SQL Sentinel."""
    pass

class ConfigurationError(SQLSentinelError):
    """Configuration related errors (YAML parsing, validation)."""
    pass

class ValidationError(SQLSentinelError):
    """Configuration validation errors."""
    pass

class ExecutionError(SQLSentinelError):
    """Query execution and database errors."""
    pass

class NotificationError(SQLSentinelError):
    """Notification delivery errors (non-fatal, logged but don't stop execution)."""
    pass
```

### 6.2 Retry Logic (Implemented in Sprint 2.1)

Email notifications implement retry logic with exponential backoff:

```python
class EmailNotificationService:
    def __init__(self, max_retries: int = 3, retry_delay_seconds: int = 2):
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def send(self, alert, result, notification_config):
        """Send email with retry logic."""
        for attempt in range(self.max_retries):
            try:
                self._send_email(recipients, subject, body)
                return
            except Exception as e:
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 2s, 4s, 8s
                    delay = self.retry_delay_seconds * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise NotificationError(f"Failed to send email after {self.max_retries} attempts: {e}")
```

## 7. Usage Examples (Sprint 2.1 Implementation)

### 7.1 Basic Alert Execution

```python
from sqlalchemy import create_engine
from sqlsentinel.config import ConfigLoader, ConfigValidator
from sqlsentinel.database import DatabaseAdapter
from sqlsentinel.executor import AlertExecutor
from sqlsentinel.notifications import NotificationFactory

# Load configuration
loader = ConfigLoader("alerts.yaml")
config_data = loader.load()
validator = ConfigValidator()
alerts = validator.validate(config_data)

# Set up database connections
data_db_engine = create_engine(config_data["database"]["url"])
state_db_engine = create_engine("sqlite:///sqlsentinel.db")

# Initialize services
db_adapter = DatabaseAdapter(data_db_engine)
notification_factory = NotificationFactory(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    smtp_username="alerts@company.com",
    smtp_password="app-password"
)

# Create executor with state management
executor = AlertExecutor(
    state_db_engine=state_db_engine,
    notification_factory=notification_factory,
    min_alert_interval_seconds=3600  # 1 hour minimum between alerts
)

# Execute alerts
for alert in alerts:
    if not alert.enabled:
        continue

    result = executor.execute_alert(
        alert=alert,
        db_adapter=db_adapter,
        triggered_by="MANUAL",
        dry_run=False
    )

    print(f"Alert: {result.alert_name}")
    print(f"Status: {result.status}")
    print(f"Duration: {result.duration_ms}ms")
```

### 7.2 Using Execution History

```python
from sqlalchemy import create_engine
from sqlsentinel.executor import ExecutionHistory

# Connect to state database
state_engine = create_engine("sqlite:///sqlsentinel.db")
history = ExecutionHistory(state_engine)

# Get recent executions
recent = history.get_recent_executions(alert_name="daily_revenue_check", limit=10)
for record in recent:
    print(f"{record.executed_at}: {record.status} - {record.actual_value}")

# Get statistics
stats = history.get_statistics(alert_name="daily_revenue_check")
print(f"Total executions: {stats['total_executions']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Average duration: {stats['avg_duration_ms']:.0f}ms")
```

### 7.3 State Management and Silencing

```python
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlsentinel.executor import StateManager

state_engine = create_engine("sqlite:///sqlsentinel.db")
state_manager = StateManager(state_engine)

# Get current state
state = state_manager.get_state("daily_revenue_check")
print(f"Current status: {state.current_status}")
print(f"Consecutive alerts: {state.consecutive_alerts}")

# Silence an alert for 24 hours
silence_until = datetime.utcnow() + timedelta(hours=24)
state_manager.silence_alert("daily_revenue_check", until=silence_until)

# Unsilence
state_manager.unsilence_alert("daily_revenue_check")
```

---

## Implementation Status Summary

**Sprint 1.2 (Completed):**
- ✅ Configuration models (AlertConfig, NotificationConfig, DatabaseConfig)
- ✅ Query result models (QueryResult with contract validation)
- ✅ ConfigLoader and ConfigValidator
- ✅ DatabaseAdapter with SQLAlchemy
- ✅ QueryExecutor with result parsing

**Sprint 2.1 (Completed):**
- ✅ Execution models (ExecutionResult, ExecutionRecord)
- ✅ State models (AlertState with deduplication logic)
- ✅ AlertExecutor (full workflow orchestration)
- ✅ StateManager (database-backed state tracking)
- ✅ ExecutionHistory (tracking with statistics)
- ✅ EmailNotificationService (SMTP with retry logic)
- ✅ NotificationFactory (environment-based config)
- ✅ SchemaManager (internal table management)
- ✅ CLI tool (init, validate, run, history commands)

**Future Sprints (Planned):**
- ⏳ Scheduler service (cron-based automation)
- ⏳ Slack/webhook notifications
- ⏳ REST API for programmatic access
- ⏳ GitOps configuration sync
- ⏳ Multi-cloud deployment scripts
