# SQL Sentinel API Specification

Version: 1.0  
Date: 2025-01-XX  
Status: Draft

## Overview

This document defines the internal and external APIs for SQL Sentinel, including data models, interfaces, error handling, and usage patterns.

## 1. Core Data Models

### 1.1 Configuration Models

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class NotificationChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    TEAMS = "teams"
    PAGERDUTY = "pagerduty"

@dataclass
class NotificationConfig:
    channel: NotificationChannel
    recipients: Optional[List[str]] = None
    webhook_secret: Optional[str] = None
    webhook_url: Optional[str] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    enabled: bool = True

@dataclass  
class AlertBehavior:
    deduplication_window: timedelta = timedelta(hours=1)
    max_consecutive_alerts: int = 5
    auto_resolve: bool = True
    silence_on_weekends: bool = False
    silence_on_holidays: bool = False
    rate_limit: Optional[str] = None  # "5/hour", "1/day"

@dataclass
class AlertMetadata:
    team: Optional[str] = None
    documentation_url: Optional[str] = None
    runbook_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_by: Optional[str] = None
    
@dataclass
class AlertConfig:
    name: str
    description: str
    query: str
    schedule: str  # Cron expression
    notifications: List[NotificationConfig]
    severity: AlertSeverity = AlertSeverity.MEDIUM
    timezone: str = "UTC"
    behavior: AlertBehavior = field(default_factory=AlertBehavior)
    metadata: AlertMetadata = field(default_factory=AlertMetadata)
    is_active: bool = True
    version: int = 1
    
    def validate(self) -> "ValidationResult":
        """Validate alert configuration"""
        pass
```

### 1.2 Execution Models

```python
class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ALERT = "alert"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class ErrorType(Enum):
    CONFIG_ERROR = "config_error"
    QUERY_ERROR = "query_error" 
    CONNECTION_ERROR = "connection_error"
    TIMEOUT_ERROR = "timeout_error"
    NOTIFICATION_ERROR = "notification_error"
    PERMISSION_ERROR = "permission_error"

@dataclass
class QueryResult:
    status: str  # 'ALERT' or 'OK'
    actual_value: Optional[float] = None
    threshold: Optional[float] = None
    message: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def validate_contract(self) -> bool:
        """Validate query result matches expected contract"""
        return self.status in ['ALERT', 'OK']

@dataclass
class ErrorDetails:
    error_type: ErrorType
    error_code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    retry_after: Optional[int] = None
    recoverable: bool = False

@dataclass
class ExecutionResult:
    execution_id: str
    alert_name: str
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    query_result: Optional[QueryResult] = None
    error: Optional[ErrorDetails] = None
    triggered_by: str = "cron"  # 'cron', 'manual', 'api'
    notifications_sent: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[timedelta]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
```

### 1.3 State Models

```python
@dataclass
class AlertState:
    alert_name: str
    last_status: Optional[ExecutionStatus] = None
    last_execution_time: Optional[datetime] = None
    last_alert_time: Optional[datetime] = None
    consecutive_alerts: int = 0
    consecutive_successes: int = 0
    is_silenced: bool = False
    silence_until: Optional[datetime] = None
    total_executions: int = 0
    total_alerts: int = 0
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def should_send_notification(self, behavior: AlertBehavior) -> bool:
        """Determine if notification should be sent based on state and behavior"""
        pass
        
    def is_in_deduplication_window(self, behavior: AlertBehavior) -> bool:
        """Check if we're within deduplication window"""
        pass
```

## 2. Core Service APIs

### 2.1 Configuration Manager API

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

## 4. External REST API (Optional)

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

## 5. Error Handling Patterns

### 5.1 Exception Hierarchy

```python
class SQLSentinelError(Exception):
    """Base exception for SQL Sentinel"""
    pass

class ConfigurationError(SQLSentinelError):
    """Configuration related errors"""
    pass

class QueryExecutionError(SQLSentinelError):
    """Query execution errors"""
    pass

class NotificationError(SQLSentinelError):
    """Notification delivery errors"""
    pass

class ConnectionError(SQLSentinelError):
    """Database connection errors"""
    pass
```

### 5.2 Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class RetryableOperation:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def execute_with_retry(self, operation):
        """Execute operation with exponential backoff retry"""
        return await operation()
```

## 6. Usage Examples

### 6.1 Basic Alert Execution

```python
# Initialize services
config_manager = ConfigManager(storage=DataWarehouseConfigStorage())
executor = AlertExecutor(connection=BigQueryConnection())
notification_service = NotificationService()
state_manager = StateManager(storage=DataWarehouseStateStorage())

# Load and execute alerts
configs = config_manager.load_all_configs()
for config in configs:
    # Execute alert
    result = await executor.execute_alert(config)
    
    # Update state
    state = state_manager.update_state_after_execution(result, config)
    
    # Send notifications if needed
    if result.status == ExecutionStatus.ALERT:
        await notification_service.send_alert_notification(result, config, state)
```

### 6.2 Configuration Sync

```python
# Sync configurations from Git
git_configs = load_configs_from_git_repo()
sync_result = config_manager.sync_from_git(git_configs)

print(f"Synced {sync_result.success_count} configs successfully")
print(f"Failed to sync {sync_result.error_count} configs")
```

This refined API specification provides a complete, implementable interface for SQL Sentinel with proper error handling, async support, and clear separation of concerns.
