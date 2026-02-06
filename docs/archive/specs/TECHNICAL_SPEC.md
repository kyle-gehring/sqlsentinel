# SQL Sentinel Technical Specification

Version: 1.0  
Date: 2025-01-XX  
Status: Draft

## 1. Overview

SQL Sentinel is a data warehouse-native alerting system that enables data analysts to monitor business metrics using SQL queries. This specification defines the system architecture, interfaces, and implementation requirements.

### 1.1 Core Principles

- **SQL-First**: All alert logic expressed in standard SQL
- **Data Warehouse-Native**: State and configuration stored in data warehouse
- **Cloud-Agnostic**: Runs on any major cloud platform or self-hosted
- **GitOps-Ready**: Configuration as code with version control
- **Serverless-Optimized**: Designed for serverless compute platforms

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Git Repository                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ alerts/     │  │ .github/    │  │ config/     │          │
│  │ *.yaml      │  │ workflows/  │  │ deploy.yml  │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└────────────────────┬────────────────────────────────────────┘
                     │ CI/CD Sync
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Serverless Runtime                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Config      │  │ Scheduler   │  │ Executor    │          │
│  │ Manager     │  │ Service     │  │ Service     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬─────────────┐
        ▼            ▼            ▼             ▼
┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐
│Data         │ │ Secret   │ │ Cloud    │ │ Notification│
│Warehouse    │ │ Manager  │ │ Scheduler│ │ Services    │
│(SQL Engine) │ │          │ │          │ │             │
└─────────────┘ └──────────┘ └──────────┘ └─────────────┘
```

### 2.2 Component Architecture

#### 2.2.1 Core Services

**Config Manager**
- Loads alert configurations from data warehouse
- Validates YAML schema and SQL syntax
- Manages configuration lifecycle

**Scheduler Service** 
- Evaluates cron expressions
- Triggers alert executions
- Manages execution state

**Executor Service**
- Executes SQL queries against data warehouse
- Evaluates alert conditions
- Sends notifications
- Records execution results

#### 2.2.2 External Dependencies

**Data Warehouse** (Primary Storage)
- Alert configurations (JSON)
- Execution history
- Alert state tracking
- Business data (monitored datasets)

**Secret Manager** (Credential Storage)
- Database connection strings
- Notification service API keys
- SMTP credentials

**Cloud Scheduler** (Trigger System)
- Cron-based alert scheduling
- Event-driven execution
- Retry logic for failed executions

## 3. Data Models

### 3.1 Configuration Schema

```sql
-- Alert configuration storage
CREATE TABLE sqlsentinel_configs (
  alert_name VARCHAR(255) PRIMARY KEY,
  config JSON NOT NULL,
  version INTEGER DEFAULT 1,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by VARCHAR(255),
  git_commit_hash VARCHAR(40)
);

-- Indexes
CREATE INDEX idx_configs_active ON sqlsentinel_configs(is_active);
CREATE INDEX idx_configs_updated ON sqlsentinel_configs(updated_at);
```

### 3.2 Execution Tracking

```sql
-- Alert execution history (implemented in Sprint 2.1)
CREATE TABLE sqlsentinel_executions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  alert_name TEXT NOT NULL,
  executed_at TIMESTAMP NOT NULL,
  execution_duration_ms REAL NOT NULL,
  status TEXT NOT NULL, -- 'success', 'failure', 'error'
  actual_value REAL,
  threshold REAL,
  query TEXT,
  error_message TEXT,
  triggered_by TEXT NOT NULL, -- 'MANUAL', 'CRON', 'API'
  notification_sent BOOLEAN DEFAULT 0,
  notification_error TEXT,
  context_data TEXT -- JSON string
);

-- Indexes
CREATE INDEX idx_executions_alert ON sqlsentinel_executions(alert_name);
CREATE INDEX idx_executions_time ON sqlsentinel_executions(executed_at DESC);
CREATE INDEX idx_executions_status ON sqlsentinel_executions(status);
```

### 3.3 Alert State Management

```sql
-- Current alert state (for deduplication and rate limiting, implemented in Sprint 2.1)
CREATE TABLE sqlsentinel_state (
  alert_name TEXT PRIMARY KEY,
  current_status TEXT, -- 'ALERT', 'OK', 'ERROR'
  last_execution_at TIMESTAMP,
  last_alert_at TIMESTAMP,
  consecutive_alerts INTEGER DEFAULT 0,
  consecutive_successes INTEGER DEFAULT 0,
  silence_until TIMESTAMP,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

## 4. Configuration Specification

### 4.1 Alert Configuration Schema

```yaml
# alerts/revenue_monitoring.yaml
# Database configuration (single connection for all alerts in this file)
database:
  url: "${DATABASE_URL}"  # e.g., "postgresql://...", "sqlite:///alerts.db"
  pool_size: 5
  timeout: 30

alerts:
  - name: "daily_revenue_drop"
    description: "Alert when daily revenue drops below threshold"
    enabled: true

    # SQL Query Requirements (runs against the database configured above)
    query: |
      SELECT
        CASE WHEN daily_revenue < 50000 THEN 'ALERT' ELSE 'OK' END as status,
        daily_revenue as actual_value,
        50000 as threshold,
        order_count,
        DATE(order_date) as date
      FROM (
        SELECT
          SUM(amount) as daily_revenue,
          COUNT(*) as order_count,
          MAX(created_at) as order_date
        FROM orders
        WHERE DATE(created_at) = CURRENT_DATE - 1
      )

    # Scheduling
    schedule: "0 9 * * *"  # Daily at 9 AM UTC

    # Notification Configuration (implemented in Sprint 2.1)
    notify:
      - channel: email
        recipients:
          - "revenue-team@company.com"
        subject: "Revenue Alert: {alert_name}"

      - channel: slack
        webhook_url: "${SLACK_REVENUE_WEBHOOK}"
        channel: "#revenue-alerts"

# Note: Advanced features like behavior policies (deduplication_window,
# max_consecutive_alerts), metadata, timezone support, and global configuration
# will be added in Phase 2/3. Phase 1 MVP focuses on core alerting functionality.
```

### 4.2 Query Contract

All alert queries MUST return a result set with:

**Required Columns:**
- `status`: STRING - 'ALERT' or 'OK'

**Optional Columns:**
- `actual_value`: NUMERIC - The measured value
- `threshold`: NUMERIC - The threshold value
- `message`: STRING - Custom alert message
- Additional context columns for notifications

### 4.3 Configuration Validation

**Schema Validation:**
- YAML structure validation against JSON Schema
- Required fields validation
- Data type validation

**SQL Validation:**
- Syntax validation using SQL parser
- Query contract validation (required columns)
- Execution safety checks (no DML operations)

**Schedule Validation:**
- Cron expression validation
- Timezone validation
- Reasonable frequency limits (min 1 minute intervals)

## 5. API Specification

### 5.1 Internal APIs

#### Configuration Management API

```python
class ConfigManager:
    def load_configs() -> List[AlertConfig]:
        """Load all active alert configurations from data warehouse"""
        
    def validate_config(config: AlertConfig) -> ValidationResult:
        """Validate alert configuration"""
        
    def sync_from_git(git_configs: List[AlertConfig]) -> SyncResult:
        """Sync configurations from Git repository to data warehouse"""
```

#### Execution API

```python
class AlertExecutor:
    def execute_alert(alert_name: str) -> ExecutionResult:
        """Execute a single alert"""
        
    def execute_batch(alert_names: List[str]) -> List[ExecutionResult]:
        """Execute multiple alerts in batch"""
        
    def validate_query(query: str, connection: Connection) -> ValidationResult:
        """Validate SQL query without execution"""
```

#### Notification API

```python
class NotificationService:
    def send_notification(alert_result: AlertResult, config: NotificationConfig) -> bool:
        """Send notification via configured channel"""
        
    def render_template(template: str, context: Dict) -> str:
        """Render notification template with alert context"""
```

### 5.2 External APIs (Optional)

```python
# REST API for manual triggers and monitoring
POST /api/v1/alerts/{alert_name}/execute
GET  /api/v1/alerts/{alert_name}/history
GET  /api/v1/alerts/{alert_name}/status
POST /api/v1/alerts/{alert_name}/silence
GET  /api/v1/health
```

## 6. Error Handling & Observability

### 6.1 Error Categories

**Configuration Errors:**
- Invalid YAML syntax
- Schema validation failures
- SQL syntax errors
- Missing required fields

**Execution Errors:**
- Database connection failures
- Query timeout errors
- Permission errors
- Resource exhaustion

**Notification Errors:**
- API rate limits
- Authentication failures
- Network timeouts
- Invalid templates

### 6.2 Error Handling Strategy

```python
@dataclass
class ExecutionResult:
    alert_name: str
    status: str  # 'SUCCESS', 'ALERT', 'ERROR'
    execution_time: datetime
    duration_ms: int
    error: Optional[ErrorDetails] = None
    query_result: Optional[Dict] = None

@dataclass  
class ErrorDetails:
    error_type: str  # 'CONFIG_ERROR', 'QUERY_ERROR', 'NOTIFICATION_ERROR'
    error_code: str
    message: str
    details: Dict
    retry_after: Optional[int] = None
```

### 6.3 Logging & Monitoring

**Structured Logging:**
```json
{
  "timestamp": "2025-01-15T09:00:00Z",
  "level": "INFO",
  "component": "executor",
  "alert_name": "daily_revenue_drop", 
  "execution_id": "uuid-here",
  "status": "ALERT",
  "duration_ms": 1250,
  "actual_value": 45000,
  "threshold": 50000
}
```

**Metrics:**
- Alert execution count by status
- Query execution duration
- Notification delivery rate
- Error rate by category

## 7. Security Requirements

### 7.1 Authentication & Authorization

**Data Warehouse Access:**
- Service account authentication
- Principle of least privilege
- Read-only access to business data
- Read/write access to sqlsentinel_* tables only

**Secret Management:**
- External secret manager integration
- No secrets in configuration files
- Automatic secret rotation support

### 7.2 SQL Injection Prevention

**Query Validation:**
- SQL parsing and AST analysis
- Block DML operations (INSERT, UPDATE, DELETE)
- Block DDL operations (CREATE, DROP, ALTER)
- Allow SELECT statements only

**Parameterization:**
- No dynamic SQL construction
- Template variables in notifications only
- Sanitize all user inputs

### 7.3 Network Security

**Data Warehouse Connections:**
- TLS/SSL encryption required
- VPC/network isolation when possible
- Connection pooling with authentication

**Notification Services:**
- HTTPS for all webhook calls
- API key authentication
- Rate limiting and retry logic

## 8. Performance Requirements

### 8.1 Execution Performance

**Query Execution:**
- Maximum query duration: 5 minutes
- Concurrent execution limit: 10 alerts
- Memory limit per execution: 512MB

**Notification Delivery:**
- Maximum delivery time: 30 seconds
- Retry attempts: 3 with exponential backoff
- Batch notification support

### 8.2 Scalability

**Alert Volume:**
- Support 1000+ active alerts
- Support 10,000+ executions per day
- Horizontal scaling via serverless functions

**Data Warehouse Load:**
- Minimize query frequency through caching
- Use connection pooling
- Implement query result caching (optional)

## 9. Deployment Architecture

### 9.1 Multi-Cloud Support

**Google Cloud Platform:**
```yaml
services:
  compute: Cloud Run
  scheduler: Cloud Scheduler  
  secrets: Secret Manager
  data_warehouse: BigQuery
```

**Amazon Web Services:**
```yaml
services:
  compute: Lambda
  scheduler: EventBridge
  secrets: Secrets Manager
  data_warehouse: Redshift
```

**Microsoft Azure:**
```yaml
services:
  compute: Container Instances
  scheduler: Logic Apps
  secrets: Key Vault  
  data_warehouse: Synapse Analytics
```

### 9.2 Infrastructure as Code

**Terraform Modules:**
- Cloud-specific deployment modules
- Shared configuration templates
- Environment management (dev/staging/prod)

**Container Image:**
- Multi-architecture support (amd64, arm64)
- Minimal base image (Alpine Linux)
- Security scanning integration

## 10. Testing Strategy

### 10.1 Unit Testing

**Component Coverage:**
- Configuration parsing and validation
- SQL query execution and result processing  
- Notification templating and delivery
- Error handling and retry logic

### 10.2 Integration Testing

**End-to-End Scenarios:**
- Full alert execution workflow
- Multi-cloud deployment validation
- Database connectivity testing
- Notification delivery testing

### 10.3 Performance Testing

**Load Testing:**
- Concurrent alert execution
- High-frequency alert scenarios
- Large result set processing
- Memory and CPU profiling

## 11. Implementation Status

**Current Version:** 0.3.0 (Sprint 2.1)
**Last Updated:** 2025-01-XX

### Completed Features ✅

**Configuration & Validation** (Sprint 1.1-1.2)
- YAML configuration loader and validator
- Database connection management (SQLAlchemy)
- Query executor with contract validation
- Comprehensive error handling

**Alert Execution Engine** (Sprint 2.1)
- Full alert execution workflow orchestration
- State management with deduplication logic
- Execution history tracking with statistics
- Email notifications with retry logic
- CLI tool (init, validate, run, history)
- Database schema management

### In Progress 🚧

**Automated Scheduling** (Sprint 3.1 - Next)
- Cron-based scheduler service
- Automated alert execution
- Slack/webhook notifications

### Planned Features 📋

**Production Readiness** (Phase 2)
- Multi-cloud deployment (GCP, AWS, Azure)
- PostgreSQL/BigQuery explicit support
- Docker containerization
- Advanced notification channels

**Advanced Features** (Phase 3)
- Web UI for monitoring
- Advanced analytics and reporting
- Multi-tenant support
- Enhanced security features

> **Note:** For detailed sprint planning and task breakdowns, see [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)

## 12. Success Criteria

### 12.1 Functional Requirements
- ✅ Execute SQL alerts on schedule
- ✅ Send notifications on alert conditions
- ✅ Prevent duplicate alerts
- ✅ Support multiple data warehouses
- ✅ GitOps configuration management

### 12.2 Non-Functional Requirements
- ✅ 99.9% alert delivery reliability
- ✅ <5 minute end-to-end alert latency
- ✅ <15 minute deployment time
- ✅ Support 1000+ concurrent alerts
- ✅ <$30/month operational cost

---

**Next Steps:**
1. Review and approve this technical specification
2. Create detailed implementation plan
3. Set up development environment and CI/CD
4. Begin Phase 1 implementation
5. Establish testing and quality gates