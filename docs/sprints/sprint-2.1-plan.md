# Sprint 2.1: Alert Scheduler & Execution Engine

**Duration:** Days 8-11 (4 days)
**Sprint Goal:** Build the core alert execution engine with scheduling capabilities, state management to prevent duplicate alerts, and basic email notification support. This sprint transforms our configuration and database foundation into a working alerting system.
**Status:** Ready to Start

## What We're Building On

**Completed in Sprint 1.1:**
- Core data models (AlertConfig, QueryResult, NotificationConfig, etc.)
- Custom exception hierarchy
- 98% test coverage foundation

**Completed in Sprint 1.2:**
- YAML configuration loading and validation
- Database connectivity via SQLAlchemy
- Query execution with result validation
- 97% test coverage on config layer

## Success Criteria

- [ ] Scheduler can evaluate cron expressions and trigger alerts at correct times
- [ ] Alerts execute on schedule without manual intervention
- [ ] Email notifications sent successfully when status = 'ALERT'
- [ ] Duplicate alerts prevented within configurable time window
- [ ] Execution history recorded in `sqlsentinel_executions` table
- [ ] State tracking prevents alert fatigue (consecutive alerts)
- [ ] CLI tool can run alerts manually for testing
- [ ] All tests pass with >80% code coverage
- [ ] Can run end-to-end: load config → schedule → execute → notify → record

## Work Items

### 1. Execution State Management (Priority: HIGH)
**Files:** `src/sqlsentinel/executor/state.py`

- [ ] Create `StateManager` class to track alert execution state
- [ ] Implement methods to check last alert time (deduplication)
- [ ] Track consecutive alert/success counts
- [ ] Support alert silencing with timeout
- [ ] Create/update `sqlsentinel_state` table
- [ ] Thread-safe state updates for concurrent execution
- [ ] State cleanup for deleted alerts

**Tests:** 15+ unit tests covering state transitions

### 2. Execution History Tracking (Priority: HIGH)
**Files:** `src/sqlsentinel/executor/history.py`

- [ ] Create `ExecutionHistory` class
- [ ] Record all alert executions in `sqlsentinel_executions` table
- [ ] Capture execution metadata (duration, status, values, errors)
- [ ] Query history for reporting and debugging
- [ ] Implement retention policies (optional)
- [ ] Support for triggered_by field (CRON, MANUAL, API)

**Tests:** 12+ unit tests for history recording

### 3. Production Query Executor Enhancement (Priority: HIGH)
**Files:** Enhance existing `src/sqlsentinel/executor/query.py`

- [ ] Add integration with StateManager for deduplication
- [ ] Add integration with ExecutionHistory for tracking
- [ ] Implement execution workflow: check state → execute → evaluate → record
- [ ] Add query timeout enforcement (from config)
- [ ] Track query execution duration
- [ ] Handle database connection failures gracefully
- [ ] Support dry-run mode for testing

**Tests:** 20+ unit tests for enhanced executor

### 4. Alert Scheduler (Priority: HIGH)
**Files:** `src/sqlsentinel/scheduler/scheduler.py`

- [ ] Create `AlertScheduler` class using croniter
- [ ] Evaluate cron expressions to determine next execution time
- [ ] Maintain in-memory schedule of pending alerts
- [ ] Trigger alert execution at scheduled times
- [ ] Support for immediate execution (manual trigger)
- [ ] Handle overlapping executions (skip if still running)
- [ ] Graceful shutdown and restart support

**Tests:** 18+ unit tests for scheduling logic

### 5. Email Notification Service (Priority: HIGH)
**Files:** `src/sqlsentinel/notifications/email.py`

- [ ] Create `EmailNotificationService` class
- [ ] Support SMTP configuration (host, port, credentials)
- [ ] Render email templates with alert context
- [ ] Send emails with alert details (status, actual_value, threshold)
- [ ] Handle SMTP authentication and TLS
- [ ] Retry logic for failed sends (3 attempts with backoff)
- [ ] Support for HTML and plain text emails
- [ ] Configuration via environment variables

**Tests:** 15+ unit tests with mocked SMTP

### 6. Notification Factory & Routing (Priority: MEDIUM)
**Files:** `src/sqlsentinel/notifications/factory.py`

- [ ] Create `NotificationFactory` to select channel (email/slack/webhook)
- [ ] Route notifications based on alert configuration
- [ ] Support multiple notification channels per alert
- [ ] Handle notification failures gracefully
- [ ] Log notification delivery status
- [ ] Placeholder classes for Slack/Webhook (Phase 2)

**Tests:** 10+ unit tests for routing

### 7. Command-Line Interface (Priority: MEDIUM)
**Files:** `src/sqlsentinel/cli.py`

- [ ] Create CLI using Click or argparse
- [ ] Command: `sqlsentinel run <config_file>` - Run all alerts once
- [ ] Command: `sqlsentinel run <config_file> --watch` - Run scheduler continuously
- [ ] Command: `sqlsentinel test <config_file>` - Validate configuration
- [ ] Command: `sqlsentinel execute <alert_name>` - Run single alert manually
- [ ] Command: `sqlsentinel history <alert_name>` - Show execution history
- [ ] Logging configuration (console output, log levels)
- [ ] Graceful shutdown on SIGINT/SIGTERM

**Tests:** 12+ integration tests for CLI commands

### 8. Database Schema Setup (Priority: HIGH)
**Files:** `src/sqlsentinel/database/schema.py`

- [ ] Create schema initialization script
- [ ] Table creation for `sqlsentinel_configs`
- [ ] Table creation for `sqlsentinel_executions`
- [ ] Table creation for `sqlsentinel_state`
- [ ] Index creation for performance
- [ ] Support for SQLite, PostgreSQL (future)
- [ ] Schema migration support (basic)

**Tests:** 8+ tests for schema operations

### 9. Integration Tests (Priority: HIGH)
**Files:** `tests/integration/test_end_to_end.py`

- [ ] End-to-end test: load config → schedule → execute → notify
- [ ] Test with in-memory SQLite database
- [ ] Mock email sending
- [ ] Verify state management prevents duplicates
- [ ] Verify execution history recorded correctly
- [ ] Test error handling scenarios
- [ ] Test concurrent alert execution

**Tests:** 10+ integration tests

### 10. Example Configuration & Documentation (Priority: MEDIUM)
**Files:** `examples/`, `docs/`

- [ ] Create working example with SQLite database
- [ ] Example alerts with sample data
- [ ] Setup instructions for local testing
- [ ] Email configuration guide
- [ ] Troubleshooting common issues
- [ ] Architecture diagram for execution flow

## Technical Decisions

### Scheduler Implementation
- **Library:** Python's `croniter` (already in dependencies)
- **Approach:** Single-threaded event loop (Phase 1), multi-threaded in Phase 2
- **Scheduling Model:** Calculate next run time, sleep until then, execute
- **Concurrency:** Sequential execution in MVP, parallel in Phase 2

### State Management
- **Storage:** Database tables (sqlsentinel_state)
- **Deduplication Strategy:** Check last_alert_time, enforce minimum interval
- **Thread Safety:** Row-level locking for concurrent updates

### Email Delivery
- **Library:** Python's built-in `smtplib` and `email` modules
- **Configuration:** SMTP settings via environment variables
- **Templates:** Simple string formatting (Jinja2 in Phase 2)
- **Retry Logic:** 3 attempts with exponential backoff

### Error Handling
- **Execution Errors:** Log, record in history, continue to next alert
- **Notification Errors:** Log, mark notification_sent=False, continue
- **Database Errors:** Retry connection, fail gracefully

## File Structure

```
src/sqlsentinel/
├── cli.py                     # NEW: Command-line interface
├── scheduler/
│   ├── __init__.py
│   └── scheduler.py           # NEW: Alert scheduler
├── executor/
│   ├── __init__.py
│   ├── query.py               # ENHANCED: Add state/history integration
│   ├── state.py               # NEW: State management
│   └── history.py             # NEW: Execution history
├── notifications/
│   ├── __init__.py
│   ├── factory.py             # NEW: Notification routing
│   ├── email.py               # NEW: Email service
│   └── base.py                # NEW: Base notification interface
├── database/
│   ├── schema.py              # NEW: Schema setup
│   └── adapter.py             # EXISTING
└── models/                    # EXISTING

tests/
├── integration/
│   ├── __init__.py
│   └── test_end_to_end.py     # NEW: E2E tests
├── scheduler/
│   └── test_scheduler.py      # NEW
├── executor/
│   ├── test_state.py          # NEW
│   └── test_history.py        # NEW
├── notifications/
│   ├── test_email.py          # NEW
│   └── test_factory.py        # NEW
└── test_cli.py                # NEW

examples/
├── alerts.yaml                # Working example
├── sample_data.sql            # Sample SQLite database
└── README.md                  # Setup instructions
```

## Dependencies

**No new external dependencies needed!** All required libraries already in place:
- `croniter>=2.0` - Cron expression parsing
- `sqlalchemy>=2.0` - Database operations
- `pydantic>=2.0` - Data validation
- Built-in Python: `smtplib`, `email`, `argparse`/`click`, `threading`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scheduler timing accuracy | Medium | Use croniter, test extensively, document limitations |
| Email delivery failures | High | Retry logic, clear error messages, test with real SMTP |
| State race conditions | Medium | Database row locking, test concurrent scenarios |
| Alert execution timeouts | High | Configurable timeouts, graceful termination |
| Memory leaks in long-running scheduler | Medium | Monitor resources, implement cleanup routines |

## Deliverables

1. Working alert scheduler with cron-based execution
2. Complete execution engine with state management
3. Email notification service with retry logic
4. CLI tool for running and testing alerts
5. Database schema initialization
6. Comprehensive test suite (>120 new tests)
7. End-to-end integration tests
8. Working example with sample data
9. Usage documentation and troubleshooting guide

## Definition of Done

- [ ] All work items completed
- [ ] 130+ new tests written (targeting 120+ total tests)
- [ ] Code coverage >80% overall
- [ ] All linting checks pass (black, mypy, ruff)
- [ ] Can run scheduler continuously without crashes
- [ ] Email notifications delivered successfully
- [ ] No duplicate alerts sent within deduplication window
- [ ] Execution history accurately recorded
- [ ] CLI commands work as documented
- [ ] End-to-end integration tests passing
- [ ] Example configuration runs successfully
- [ ] Documentation updated with usage guide

## Expected Metrics

- **New Tests:** ~120 tests (bringing total to ~220)
- **Target Coverage:** 85%+
- **New Source Files:** 10-12 files
- **Lines of Code:** ~1,500-2,000 new lines
- **Days to Complete:** 4 days

## Next Sprint Preview

**Sprint 2.2** (Days 12-15) will add:
- Slack and webhook notification channels
- Advanced state management (silence periods, escalation)
- Multi-database support (PostgreSQL, MySQL)
- Web UI for viewing execution history
- Helm charts and Terraform modules

## Notes

- This sprint delivers a fully functional alerting system
- Focus on reliability and error handling
- Keep code simple and maintainable
- Prioritize test coverage for state management
- Document configuration options thoroughly
