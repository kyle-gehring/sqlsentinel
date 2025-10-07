# Sprint 2.2: Multi-Channel Notifications & Enhanced Features

**Duration:** Days 11-14 (4 days)
**Sprint Goal:** Expand notification capabilities with Slack and webhook support, enhance state management features, improve testing infrastructure, and add Docker containerization. Transform SQL Sentinel from email-only alerts to a multi-channel notification system.
**Status:** In Progress (Day 11)

## Progress Summary (Day 11)

**Completed:**
- ✅ Slack Notification Service (18 tests, 99% coverage)
- ✅ Webhook Notification Service (26 tests, 99% coverage)
- ✅ Enhanced Notification Factory (7 new tests, 98% coverage)
- ✅ Updated package exports and imports

**Metrics:**
- **Tests:** 254 total (up from 191) - **63 new tests added**
- **Overall Coverage:** 77% (target: 85%)
- **Notification Coverage:** 98-99% across all services
- **State Management Coverage:** 83%

**Completed (Day 11 - Phase 4):**
- ✅ Enhanced State Management with:
  - Escalation counter tracking
  - Notification failure tracking
  - Last notification channel tracking
  - Comprehensive state transition logging
- ✅ 12 new state management tests (38 total, 83% coverage)

**Remaining:**
- End-to-end integration tests (15+ tests)
- Testing infrastructure enhancements
- Docker container & docker-compose
- CLI enhancements (silence/status commands)
- Documentation and examples

## What We're Building On

**Completed in Sprint 1.1:**
- Core data models (AlertConfig, QueryResult, NotificationConfig, etc.)
- Custom exception hierarchy
- 98% test coverage foundation

**Completed in Sprint 1.2:**
- YAML configuration loading and validation
- Database connectivity via SQLAlchemy
- Query execution with result validation
- Multi-channel notification config support (email, slack, webhook)
- 97% test coverage on config layer

**Completed in Sprint 2.1:**
- Complete alert execution engine with state/history integration
- Email notification system with retry logic
- CLI tool with 4 commands (init, validate, run, history)
- State management with deduplication
- Execution history tracking
- 191 tests passing with 90%+ coverage on core modules

## Success Criteria

- [x] Slack notifications send successfully via webhook
- [x] Generic webhook notifications support custom payloads
- [ ] Multi-channel alerts send to all configured channels
- [x] All notification channels have retry logic with exponential backoff
- [ ] Docker image builds and runs successfully
- [ ] End-to-end integration tests verify complete workflows
- [ ] Alert silencing can be set/cleared via state management
- [ ] All tests pass with >85% code coverage (including CLI)
- [ ] Documentation covers all notification channels with examples

## Work Items

### 1. Slack Notification Service (Priority: HIGH) ✅
**Files:** `src/sqlsentinel/notifications/slack.py`

- [x] Create `SlackNotificationService` class
- [x] Implement webhook-based message delivery
- [x] Support rich message formatting (Slack blocks/attachments)
- [x] Include alert details in structured format
- [x] Add retry logic with exponential backoff (3 attempts)
- [x] Handle Slack API errors gracefully
- [x] Support custom webhook URLs per alert
- [x] Environment variable configuration (SLACK_WEBHOOK_URL)
- [x] Thread support for grouping related alerts (optional)

**Message Format:**
- Alert name and description
- Status (ALERT/OK) with color coding (red/green)
- Actual value vs threshold
- Additional context fields
- Timestamp and execution metadata

**Tests:** 18 unit tests with mocked HTTP requests (target: 15+) ✅
**Coverage:** 99% ✅

### 2. Webhook Notification Service (Priority: HIGH) ✅
**Files:** `src/sqlsentinel/notifications/webhook.py`

- [x] Create `WebhookNotificationService` class
- [x] Support configurable HTTP methods (POST, PUT, PATCH, GET)
- [x] Custom headers support (authentication, content-type)
- [x] Flexible payload templates (JSON format)
- [x] Retry logic with exponential backoff (configurable attempts)
- [x] Timeout configuration
- [x] SSL certificate verification (configurable)
- [x] Response status validation
- [x] Error logging with response details

**Features:**
- Template variables: {alert_name}, {status}, {actual_value}, {threshold}, {context}
- Custom authentication (Bearer tokens, API keys, Basic auth)
- Webhook validation (pre-flight checks)

**Tests:** 26 unit tests with mocked HTTP server (target: 18+) ✅
**Coverage:** 99% ✅

### 3. Notification Factory Enhancement (Priority: HIGH) ✅
**Files:** Update `src/sqlsentinel/notifications/factory.py`

- [x] Add Slack service creation
- [x] Add Webhook service creation
- [x] Support environment variables for Slack/Webhook config
- [x] Handle missing configuration gracefully
- [x] Update channel routing logic
- [x] Add validation for channel-specific configuration
- [x] Support multiple webhooks per alert

**Environment Variables:**
- `SLACK_WEBHOOK_URL` - Default Slack webhook
- `WEBHOOK_URL` - Default webhook URL
- `WEBHOOK_AUTH_HEADER` - Default webhook authentication

**Tests:** 7 new factory tests (19 total, target: 12+) ✅
**Coverage:** 98% ✅

### 4. Enhanced State Management (Priority: MEDIUM) ✅
**Files:** Update `src/sqlsentinel/executor/state.py`

- [x] Add `set_silence()` method with duration parameter → `silence_alert()`
- [x] Add `clear_silence()` method → `unsilence_alert()`
- [x] Add `is_silenced()` helper method
- [x] Improve silence timeout handling
- [x] Add escalation counter tracking
- [x] Track notification failures in state
- [x] Add last_notification_channel field
- [x] Improve state transition logging

**New Features:**
- Manual silence periods (1h, 24h, custom)
- Automatic silence clearing after timeout
- Escalation tracking (alert sent 3x → escalate)

**Tests:** 12 additional tests for new features ✅
**Coverage:** 83% on state.py ✅

### 5. End-to-End Integration Tests (Priority: HIGH)
**Files:** `tests/integration/test_end_to_end.py`

- [ ] Test complete alert workflow (load → execute → notify → record)
- [ ] Test all notification channels (email, slack, webhook)
- [ ] Test multi-channel alerts (send to multiple channels simultaneously)
- [ ] Test state deduplication prevents duplicate notifications
- [ ] Test execution history records all channels
- [ ] Test error scenarios (database failures, notification failures)
- [ ] Test dry-run mode with all channels
- [ ] Test concurrent alert execution
- [ ] Use in-memory SQLite database
- [ ] Mock all external services (SMTP, HTTP)

**Scenarios:**
1. Single alert with email notification
2. Single alert with Slack notification
3. Single alert with webhook notification
4. Alert with multiple notification channels
5. Consecutive alerts with deduplication
6. Silenced alert (no notification)
7. Failed notification (retry logic)
8. Complete execution cycle verification

**Tests:** 15+ integration tests

### 6. Docker Container (Priority: MEDIUM)
**Files:** `Dockerfile`, `docker-compose.yaml`, `.dockerignore`

- [ ] Create production-ready Dockerfile
- [ ] Multi-stage build for smaller image size
- [ ] Security hardening (non-root user, minimal base image)
- [ ] Environment variable configuration support
- [ ] Health check endpoint preparation
- [ ] ENTRYPOINT configuration for CLI
- [ ] Docker Compose setup for local testing
- [ ] Sample environment file (.env.example)
- [ ] Volume mounts for configuration and state

**Dockerfile Features:**
- Base image: python:3.11-slim
- Poetry for dependency management
- Non-root user for security
- COPY only necessary files
- Layer caching optimization

**Docker Compose Features:**
- SQL Sentinel service
- Sample SQLite database volume
- Environment variable configuration
- Network setup for future services

**Tests:** Manual verification of container builds and runs

### 7. CLI Enhancement (Priority: MEDIUM)
**Files:** Update `src/sqlsentinel/cli.py`

- [ ] Add `silence` command to silence alerts
- [ ] Add `unsilence` command to clear silence
- [ ] Add `status` command to show alert states
- [ ] Improve error messages and logging
- [ ] Add `--channel` filter for history command
- [ ] Add color output for better readability
- [ ] Add `--json` output format option
- [ ] Improve help text and examples

**New Commands:**
```bash
# Silence an alert for 1 hour
sqlsentinel silence <config_file> --alert NAME --duration 1h

# Clear silence on an alert
sqlsentinel unsilence <config_file> --alert NAME

# Show alert status
sqlsentinel status <config_file> [--alert NAME]
```

**Tests:** Manual testing (CLI tests deferred)

### 8. Testing Infrastructure (Priority: MEDIUM)
**Files:** `tests/conftest.py`, `tests/helpers.py`

- [ ] Create shared test fixtures for integration tests
- [ ] Mock HTTP server for webhook/Slack testing
- [ ] Mock SMTP server helper
- [ ] Sample alert configurations
- [ ] In-memory database fixtures
- [ ] Utility functions for test assertions
- [ ] Cleanup helpers for test isolation

**Fixtures:**
- `mock_smtp_server` - Mocked SMTP for email tests
- `mock_http_server` - Mocked HTTP for webhook/Slack tests
- `sample_config` - Pre-loaded alert configuration
- `temp_state_db` - Temporary in-memory state database
- `sample_query_result` - Canned query results

**Tests:** Supporting infrastructure (no direct tests)

### 9. Documentation & Examples (Priority: MEDIUM)
**Files:** `examples/`, `docs/notifications/`, `README.md`

- [ ] Update examples/alerts.yaml with Slack/webhook examples
- [ ] Create Slack integration guide
- [ ] Create webhook integration guide
- [ ] Update README with notification channel documentation
- [ ] Add troubleshooting guide for notifications
- [ ] Create example webhook payload templates
- [ ] Add Docker quick start guide
- [ ] Update architecture diagram with notification flow

**Documentation:**
- Slack setup (webhook URL creation)
- Webhook authentication patterns
- Multi-channel alert configuration
- Notification retry behavior
- State management guide

### 10. Notification Testing & Validation (Priority: LOW)
**Files:** `tests/notifications/test_slack.py`, `tests/notifications/test_webhook.py`

- [ ] Unit tests for SlackNotificationService (15+ tests)
- [ ] Unit tests for WebhookNotificationService (18+ tests)
- [ ] Test retry logic for all channels
- [ ] Test error handling for network failures
- [ ] Test authentication mechanisms
- [ ] Test payload formatting
- [ ] Test template variable substitution

## Technical Decisions

### Slack Integration
- **Library:** Python's built-in `urllib` or `requests` (if already in dependencies)
- **Approach:** Webhook-based (no Slack SDK needed for MVP)
- **Message Format:** Slack Block Kit for rich formatting
- **Authentication:** Webhook URL is the authentication token
- **Retry Logic:** 3 attempts with exponential backoff (1s, 2s, 4s)

### Webhook Integration
- **Library:** `requests` library (add if not present, otherwise `urllib`)
- **Flexibility:** Support any webhook-compatible service
- **Payload Format:** JSON by default, customizable via templates
- **Authentication:** Flexible (headers, query params, body)
- **Validation:** HTTP status code checking (2xx = success)

### Docker Container
- **Base Image:** python:3.11-slim (security + size)
- **Build Tool:** Poetry for dependency management
- **Size Target:** <200MB final image
- **Security:** Non-root user, minimal packages
- **Configuration:** Environment variables + volume mounts

### Integration Testing
- **Database:** In-memory SQLite (no external dependencies)
- **Mocking:** Mock all external services (SMTP, HTTP)
- **Isolation:** Each test gets fresh database
- **Coverage:** Aim for all user workflows

### Error Handling
- **Notification Failures:** Log, record in history, continue execution
- **Retry Logic:** Exponential backoff for all channels
- **Timeout Handling:** Configurable timeouts per channel
- **State Consistency:** Atomic state updates, rollback on failure

## File Structure

```
src/sqlsentinel/
├── cli.py                     # ENHANCED: Add silence/status commands
├── notifications/
│   ├── __init__.py            # Updated exports
│   ├── base.py                # EXISTING
│   ├── email.py               # EXISTING
│   ├── factory.py             # ENHANCED: Add Slack/Webhook
│   ├── slack.py               # NEW: Slack webhook service
│   └── webhook.py             # NEW: Generic webhook service
├── executor/
│   ├── state.py               # ENHANCED: Add silence methods
│   └── ...                    # Other existing files
└── ...

tests/
├── conftest.py                # ENHANCED: Add shared fixtures
├── helpers.py                 # NEW: Test utilities
├── integration/
│   ├── __init__.py
│   └── test_end_to_end.py     # NEW: Complete workflow tests
├── notifications/
│   ├── test_slack.py          # NEW: Slack tests
│   ├── test_webhook.py        # NEW: Webhook tests
│   └── test_factory.py        # ENHANCED: Add new channels
└── executor/
    └── test_state.py          # ENHANCED: Add silence tests

examples/
├── alerts.yaml                # ENHANCED: Add Slack/webhook examples
├── alerts-multi-channel.yaml  # NEW: Multi-channel example
├── webhook-templates/         # NEW: Example webhook payloads
│   ├── generic.json
│   ├── pagerduty.json
│   └── custom.json
└── README.md                  # ENHANCED: Add notification guides

docs/
├── notifications/
│   ├── slack.md               # NEW: Slack integration guide
│   ├── webhook.md             # NEW: Webhook integration guide
│   └── multi-channel.md       # NEW: Multi-channel setup
└── docker/
    └── quickstart.md          # NEW: Docker quick start

# Docker files (root level)
Dockerfile                      # NEW: Production container
docker-compose.yaml             # NEW: Local development setup
.dockerignore                   # NEW: Exclude unnecessary files
.env.example                    # NEW: Sample environment variables
```

## Dependencies

### New Dependencies (Minimal)
- `requests>=2.31.0` - For HTTP/webhook calls (if not already present)
  - Alternative: Use built-in `urllib` if avoiding new dependencies

### Existing Dependencies (Sufficient)
- ✅ `pydantic>=2.0` - Validation
- ✅ `sqlalchemy>=2.0` - Database
- ✅ `pyyaml>=6.0` - Configuration
- ✅ `croniter>=2.0` - Scheduling (future)
- ✅ Built-in: `smtplib`, `email`, `json`, `urllib`

**Decision:** Prefer using built-in `urllib` over adding `requests` to minimize dependencies. If `requests` is already present from other dependencies, use it for cleaner code.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Slack webhook rate limits | Medium | Implement rate limiting, document limits |
| Webhook authentication complexity | Medium | Support multiple auth methods, provide examples |
| Docker image size bloat | Low | Multi-stage build, minimal base image |
| Integration test flakiness | Medium | Proper mocking, test isolation, retries |
| Notification channel failures | High | Comprehensive retry logic, clear error messages |
| External service dependencies | Medium | Mock all external services in tests |

## Deliverables

1. ✅ **Slack notification service with webhook integration** (COMPLETE - 18 tests, 99% coverage)
2. ✅ **Generic webhook notification service with flexible configuration** (COMPLETE - 26 tests, 99% coverage)
3. ✅ **Enhanced notification factory supporting all three channels** (COMPLETE - 7 new tests, 98% coverage)
4. ✅ **Enhanced state management with silence capabilities** (COMPLETE - 12 new tests, 83% coverage)
5. ⏳ Comprehensive end-to-end integration tests (NEXT)
6. ⬜ Docker container with docker-compose setup
7. ⬜ Enhanced CLI with silence/status commands
8. ⬜ Complete documentation for all notification channels
9. ⬜ Working examples with multi-channel alerts
10. ✅ **Test suite with 60+ new tests** (COMPLETE - 63 new tests, 254 total)

## Definition of Done

- [ ] All work items completed (4/10 complete)
- [x] 50+ new tests written (63 new tests, 254 total)
- [ ] Code coverage >85% overall (currently 77%)
- [x] All linting checks pass (black, ruff - mypy pending)
- [x] Slack notifications send successfully
- [x] Webhook notifications send successfully
- [ ] Multi-channel alerts work correctly
- [ ] Docker container builds (image <200MB)
- [ ] Docker Compose stack runs successfully
- [ ] End-to-end integration tests passing
- [x] All notification channels have retry logic
- [x] State management tracks escalation and failures
- [ ] Documentation complete for all channels
- [ ] Example configurations work as documented

## Expected Metrics

- **New Tests:** ~100-120 tests (bringing total to ~300)
- **Target Coverage:** 85%+ (with CLI testing)
- **New Source Files:** 8-10 files
- **Enhanced Files:** 4-6 files
- **Lines of Code:** ~1,200-1,500 new lines
- **Docker Image Size:** <200MB
- **Days to Complete:** 4 days

## Example Configurations

### Slack Alert
```yaml
alerts:
  - name: "high_error_rate_slack"
    description: "Alert via Slack when API errors exceed 5%"
    query: |
      SELECT
        CASE WHEN error_pct > 5 THEN 'ALERT' ELSE 'OK' END as status,
        error_pct as actual_value,
        5 as threshold
      FROM api_metrics
      WHERE timestamp > datetime('now', '-5 minutes')
    schedule: "*/5 * * * *"
    notify:
      - channel: slack
        config:
          webhook_url: "${SLACK_WEBHOOK_URL}"
```

### Webhook Alert
```yaml
alerts:
  - name: "revenue_webhook"
    description: "Alert via webhook when revenue drops"
    query: |
      SELECT
        CASE WHEN revenue < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        revenue as actual_value,
        10000 as threshold
      FROM daily_revenue
      WHERE date = date('now', '-1 day')
    schedule: "0 9 * * *"
    notify:
      - channel: webhook
        config:
          url: "https://api.example.com/alerts"
          method: "POST"
          headers:
            Authorization: "Bearer ${WEBHOOK_TOKEN}"
            Content-Type: "application/json"
```

### Multi-Channel Alert
```yaml
alerts:
  - name: "critical_data_quality"
    description: "Alert via multiple channels for critical issues"
    query: |
      SELECT
        CASE WHEN null_pct > 10 THEN 'ALERT' ELSE 'OK' END as status,
        null_pct as actual_value,
        10 as threshold
      FROM data_quality_check
    schedule: "0 */2 * * *"
    notify:
      - channel: email
        config:
          recipients: ["team@company.com"]
          subject: "Critical: Data Quality Alert"
      - channel: slack
        config:
          webhook_url: "${SLACK_WEBHOOK_URL}"
      - channel: webhook
        config:
          url: "${PAGERDUTY_WEBHOOK}"
```

## Next Sprint Preview

**Sprint 3.1** (Days 15-18) will add:
- Automated cron-based scheduling (moved from Sprint 2.1)
- Continuous alert monitoring daemon
- Background job execution
- Scheduler health checks
- Log rotation and monitoring

**Sprint 3.2** (Days 18-21) will add:
- BigQuery database support
- Multi-database configuration
- Database-specific optimizations
- Connection pooling enhancements

## Notes

- This sprint focuses on expanding notification capabilities
- Email service from Sprint 2.1 serves as template for new channels
- Docker containerization prepares for production deployment
- Integration tests ensure all components work together
- Keep notification services independent and testable
- Document all environment variables clearly
- Prioritize reliability over features
- All external calls must have timeouts and retry logic

## Sprint 2.2 Scope Summary

**Core Focus:** Multi-channel notifications (Slack, Webhook) + Docker + Integration Tests

**Key Deliverables:**
1. Two new notification channels with retry logic
2. Docker container for production deployment
3. Comprehensive end-to-end integration tests
4. Enhanced state management with silence features
5. Complete documentation with examples

**Success Indicator:** User can send alerts to Slack/Webhooks, run SQL Sentinel in Docker, and have confidence from integration tests that everything works together.
