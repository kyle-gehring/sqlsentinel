# Sprint 3.1 Plan: Automated Scheduling & Daemon

**Sprint:** 3.1 - Cron Scheduling
**Phase:** 1 (Core MVP)
**Week:** 3
**Duration:** Days 15-18 (4 days)
**Status:** 🟢 READY TO START
**Started:** TBD
**Target Completion:** TBD

---

## Sprint Goal

Transform SQL Sentinel from a manual execution tool into an automated monitoring system with cron-based scheduling, enabling continuous background execution of alerts without manual intervention.

---

## Executive Summary

### Context from Sprint 2.2

Sprint 2.2 delivered a production-ready manual alerting system with:
- ✅ 288 tests passing with 87.55% coverage
- ✅ 3 notification channels (Email, Slack, Webhook)
- ✅ 7 CLI commands for manual execution
- ✅ Complete state management with deduplication
- ✅ Docker containerization
- ✅ Comprehensive documentation

**Gap:** All alerts must be manually triggered via `sqlsentinel run` CLI command

### Sprint 3.1 Objective

Add automated scheduling to enable:
1. **Automatic execution** - Alerts run on cron schedules without manual intervention
2. **Daemon process** - Background service continuously monitoring schedules
3. **Job management** - Dynamic alert loading, enabling/disabling
4. **Production deployment** - Docker container runs scheduler by default

---

## Scope & Deliverables

### In Scope ✅

1. **APScheduler Integration**
   - Add APScheduler dependency
   - Implement scheduler wrapper service
   - Cron expression parsing via croniter (already available)
   - Job persistence (in-memory for MVP)

2. **Scheduler Service**
   - Load alerts from YAML configuration
   - Create scheduled jobs from alert configs
   - Execute alerts via existing AlertExecutor
   - Handle timezone awareness (UTC default)

3. **CLI Daemon Command**
   - `sqlsentinel daemon` command to start scheduler
   - Graceful shutdown (SIGTERM/SIGINT handling)
   - Configuration file watching (reload on changes)
   - Health check logging

4. **Job Management**
   - Enable/disable alerts without restart
   - Dynamic job addition/removal
   - Job status reporting
   - Next execution time calculation

5. **Testing & Quality**
   - Unit tests for scheduler components (>80% coverage)
   - Integration tests for end-to-end scheduling
   - Timezone handling tests
   - Job lifecycle tests

6. **Docker Integration**
   - Update Dockerfile CMD to run daemon
   - Environment variable configuration
   - Logging configuration for daemon mode
   - Health check endpoint (optional)

7. **Documentation**
   - Scheduler architecture documentation
   - Daemon usage guide
   - Troubleshooting guide
   - Updated examples with scheduling

### Out of Scope 🚫

1. **Database Job Persistence** - Deferred to Phase 2 (in-memory only for MVP)
2. **Multi-instance Coordination** - Deferred to Phase 2 (single instance only)
3. **Web UI** - Deferred to Phase 3
4. **Advanced Scheduling** - No dependencies between alerts, no workflow orchestration
5. **Manual Triggers via API** - CLI only (API in Phase 3)

---

## Technical Architecture

### Scheduler Components

```
src/sqlsentinel/scheduler/
├── __init__.py                    # Exports SchedulerService
├── scheduler.py                   # Main APScheduler wrapper
├── job_manager.py                 # Job lifecycle management
├── config_watcher.py              # Configuration file monitoring
└── models.py                      # Job state models (optional)
```

### Scheduler Service Design

```python
class SchedulerService:
    """
    Manages scheduled execution of SQL Sentinel alerts using APScheduler.

    Responsibilities:
    - Load alert configurations from YAML
    - Create scheduled jobs from alert configs
    - Execute alerts via AlertExecutor
    - Handle configuration reloading
    - Graceful shutdown
    """

    def __init__(
        self,
        config_path: str,
        state_db_url: str,
        timezone: str = "UTC"
    ):
        self.config_path = config_path
        self.state_db_url = state_db_url
        self.scheduler = BackgroundScheduler(timezone=timezone)
        self.alert_configs: Dict[str, AlertConfig] = {}

    def start(self) -> None:
        """Load configuration and start scheduler."""

    def stop(self, wait: bool = True) -> None:
        """Gracefully shutdown scheduler."""

    def reload_config(self) -> None:
        """Reload configuration and update jobs."""

    def add_alert_job(self, alert: AlertConfig) -> None:
        """Add or update a scheduled job for an alert."""

    def remove_alert_job(self, alert_name: str) -> None:
        """Remove a scheduled job."""

    def get_job_status(self) -> List[JobStatus]:
        """Get status of all scheduled jobs."""
```

### Job Execution Flow

```
1. APScheduler triggers job at scheduled time
2. Scheduler calls execute_alert_job(alert_name)
3. Job function:
   a. Load alert config from self.alert_configs
   b. Create DatabaseAdapter
   c. Call AlertExecutor.execute_alert()
   d. Log result
   e. Handle exceptions
4. AlertExecutor handles:
   - Query execution
   - State management
   - Notifications
   - History recording
```

### Integration Points

**Existing Components (Reuse):**
- ✅ `AlertExecutor.execute_alert()` - Already handles full execution workflow
- ✅ `ConfigLoader.load_config()` - Already loads and validates YAML
- ✅ `StateManager` - Already manages deduplication
- ✅ `ExecutionHistory` - Already records execution history
- ✅ `NotificationFactory` - Already sends notifications

**New Components:**
- 🆕 `SchedulerService` - Wraps APScheduler
- 🆕 `daemon` CLI command - Starts scheduler service
- 🆕 Configuration watcher - Detects config file changes

---

## Implementation Plan

### Phase 1: APScheduler Setup (Day 15)

**Goal:** Add APScheduler and create basic scheduler wrapper

**Tasks:**
1. Add APScheduler to pyproject.toml dependencies
2. Create `src/sqlsentinel/scheduler/` module structure
3. Implement basic `SchedulerService` class
4. Implement job execution callback
5. Write unit tests for scheduler initialization

**Deliverables:**
- [ ] APScheduler dependency added
- [ ] `scheduler.py` with SchedulerService class
- [ ] Basic job execution function
- [ ] 10+ unit tests for scheduler basics

**Success Criteria:**
- Scheduler can start and stop
- Can add jobs programmatically
- Jobs execute callback function
- All tests pass

**Files to Create:**
```
src/sqlsentinel/scheduler/__init__.py
src/sqlsentinel/scheduler/scheduler.py
tests/scheduler/__init__.py
tests/scheduler/test_scheduler.py
```

---

### Phase 2: Alert Job Management (Day 15-16)

**Goal:** Load alerts from config and create scheduled jobs

**Tasks:**
1. Implement `load_alerts_from_config()` method
2. Implement `add_alert_job()` using cron triggers
3. Implement `remove_alert_job()` for cleanup
4. Implement `reload_config()` for dynamic updates
5. Write tests for job management

**Deliverables:**
- [ ] Alert config loading integrated
- [ ] Job creation from AlertConfig
- [ ] Dynamic job updates
- [ ] 15+ tests for job management

**Success Criteria:**
- Alerts loaded from YAML create scheduled jobs
- Cron expressions properly parsed
- Jobs can be added/removed dynamically
- Config changes trigger job updates

**Files to Modify:**
```
src/sqlsentinel/scheduler/scheduler.py (add methods)
tests/scheduler/test_scheduler.py (add tests)
```

---

### Phase 3: Alert Execution Integration (Day 16)

**Goal:** Execute alerts via existing AlertExecutor

**Tasks:**
1. Implement `execute_alert_job(alert_name)` callback
2. Integrate with DatabaseAdapter
3. Integrate with AlertExecutor
4. Add error handling and logging
5. Write integration tests

**Deliverables:**
- [ ] Job callback executes alerts
- [ ] Proper error handling
- [ ] Execution logging
- [ ] 10+ integration tests

**Success Criteria:**
- Scheduled alerts execute successfully
- Results recorded in history with `triggered_by="CRON"`
- Notifications sent as expected
- Errors logged but don't crash scheduler

**Files to Modify:**
```
src/sqlsentinel/scheduler/scheduler.py (execution logic)
tests/scheduler/test_integration.py (new file)
```

---

### Phase 4: CLI Daemon Command (Day 16-17)

**Goal:** Add `daemon` CLI command to run scheduler

**Tasks:**
1. Implement `daemon` command in cli.py
2. Add signal handling (SIGTERM, SIGINT)
3. Add configuration file watching
4. Implement graceful shutdown
5. Add daemon-specific logging
6. Write CLI tests for daemon command

**Deliverables:**
- [ ] `sqlsentinel daemon` command
- [ ] Graceful shutdown on signals
- [ ] Configuration reload support
- [ ] 10+ CLI tests

**Success Criteria:**
- Daemon starts and runs indefinitely
- Ctrl+C triggers graceful shutdown
- Config changes reload jobs
- Proper logging output

**Command Interface:**
```bash
sqlsentinel daemon CONFIG_FILE [OPTIONS]

Options:
  --state-db TEXT          State database URL
  --reload                 Watch config file for changes
  --log-level TEXT         Logging level (DEBUG, INFO, WARNING, ERROR)
  --timezone TEXT          Timezone for scheduling (default: UTC)
```

**Files to Modify:**
```
src/sqlsentinel/cli.py (add daemon command)
tests/test_cli.py (add daemon tests)
```

---

### Phase 5: Configuration Watcher (Day 17)

**Goal:** Automatically reload configuration on file changes

**Tasks:**
1. Implement file watcher using watchdog library
2. Integrate with SchedulerService
3. Add debouncing (avoid rapid reloads)
4. Write tests for config watching

**Deliverables:**
- [ ] Configuration file monitoring
- [ ] Automatic job reloading
- [ ] Debounce logic
- [ ] 8+ tests

**Success Criteria:**
- Config file changes trigger reload
- Jobs updated without restart
- Multiple rapid changes handled gracefully
- Errors in config don't crash daemon

**Files to Create:**
```
src/sqlsentinel/scheduler/config_watcher.py
tests/scheduler/test_config_watcher.py
```

---

### Phase 6: Docker Integration (Day 17)

**Goal:** Update Docker setup to run scheduler by default

**Tasks:**
1. Update Dockerfile CMD to run daemon
2. Add environment variables for scheduler config
3. Update docker-compose.yaml
4. Test Docker container scheduling
5. Update .env.example

**Deliverables:**
- [ ] Updated Dockerfile
- [ ] Updated docker-compose.yaml
- [ ] Environment variable documentation
- [ ] Docker smoke test

**Success Criteria:**
- `docker run` starts scheduler automatically
- Environment variables configure scheduler
- Container logs show scheduled executions
- Graceful shutdown on container stop

**Files to Modify:**
```
Dockerfile (update CMD)
docker-compose.yaml (add scheduler config)
.env.example (add scheduler variables)
```

**Dockerfile Changes:**
```dockerfile
# Before:
CMD ["sqlsentinel", "--help"]

# After:
CMD ["sqlsentinel", "daemon", "/config/alerts.yaml", "--state-db", "${STATE_DB_URL}"]
```

---

### Phase 7: Testing & Quality (Day 18)

**Goal:** Comprehensive testing and code quality

**Tasks:**
1. Write timezone handling tests
2. Write job lifecycle tests (start/stop/reload)
3. Write error scenario tests
4. Achieve >80% coverage on scheduler module
5. Run full test suite
6. Fix any linting issues

**Deliverables:**
- [ ] 50+ total scheduler tests
- [ ] >80% coverage on scheduler module
- [ ] All linting checks passing
- [ ] Integration tests passing

**Success Criteria:**
- All 338+ tests passing (288 existing + 50 new)
- Coverage >85% overall (maintain Sprint 2.2 level)
- No regressions in existing functionality
- Black, Ruff, mypy all passing

**Test Coverage Targets:**
```
scheduler/scheduler.py:       >85%
scheduler/config_watcher.py:  >80%
cli.py:                       >70% (improved from 69%)
Overall:                      >85%
```

---

### Phase 8: Documentation (Day 18)

**Goal:** Complete documentation for scheduling

**Tasks:**
1. Write scheduler architecture documentation
2. Write daemon usage guide
3. Update main README with scheduling examples
4. Write troubleshooting guide
5. Create sprint completion report

**Deliverables:**
- [ ] docs/architecture/scheduler.md
- [ ] docs/guides/daemon-usage.md
- [ ] docs/guides/troubleshooting-scheduler.md
- [ ] Updated README.md
- [ ] docs/sprints/sprint-3.1-completion.md

**Success Criteria:**
- Clear architecture explanation
- Step-by-step daemon setup guide
- Common issues documented
- Examples covering various schedules

**Files to Create:**
```
docs/architecture/scheduler.md
docs/guides/daemon-usage.md
docs/guides/troubleshooting-scheduler.md
docs/sprints/phase-1/week-3/sprint-3.1-completion.md
```

---

## Dependencies & Risks

### Dependencies

**New Python Packages:**
1. **APScheduler** (^3.10) - Production-ready scheduler
   - Mature library (10+ years)
   - Multiple backends supported
   - Cron, interval, and date triggers
   - Timezone support

2. **watchdog** (^3.0) - File system monitoring
   - Cross-platform file watching
   - Minimal overhead
   - Used for config file monitoring

**Existing Packages (Leverage):**
- ✅ croniter - Already available for cron validation
- ✅ SQLAlchemy - Database connections
- ✅ Pydantic - Configuration validation

### Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **APScheduler complexity** | High | Low | Use BackgroundScheduler (simplest mode), extensive testing |
| **Timezone edge cases** | Medium | Medium | Default to UTC, test DST transitions, document clearly |
| **Config reload errors** | Medium | Medium | Validate before reloading, rollback on errors, log issues |
| **Long-running queries** | High | Medium | Document timeout recommendations, add future timeout support |
| **Memory leaks in daemon** | High | Low | Proper cleanup in tests, monitor in production |
| **Signal handling issues** | Medium | Low | Test on Linux/Mac/Windows, follow Python best practices |

**Risk Mitigation Strategy:**
- Start simple (in-memory jobs only)
- Extensive error handling and logging
- Comprehensive test coverage
- Clear documentation for operators

---

## Testing Strategy

### Unit Tests (35 tests)

**Scheduler Tests (tests/scheduler/test_scheduler.py):**
```python
class TestSchedulerService:
    def test_initialization(self):
        """Test scheduler initializes correctly."""

    def test_start_stop(self):
        """Test scheduler starts and stops gracefully."""

    def test_add_alert_job(self):
        """Test adding a job from AlertConfig."""

    def test_remove_alert_job(self):
        """Test removing a job."""

    def test_reload_config(self):
        """Test configuration reloading."""

    def test_cron_parsing(self):
        """Test various cron expressions."""

    @pytest.mark.parametrize("schedule,expected", [
        ("0 9 * * *", 9),      # Daily at 9 AM
        ("*/15 * * * *", 15),  # Every 15 minutes
        ("0 0 * * 0", 0),      # Weekly on Sunday
    ])
    def test_cron_schedules(self, schedule, expected):
        """Test different cron schedule types."""
```

**Config Watcher Tests (tests/scheduler/test_config_watcher.py):**
```python
class TestConfigWatcher:
    def test_file_change_detection(self):
        """Test watcher detects file changes."""

    def test_debouncing(self):
        """Test debounce prevents rapid reloads."""

    def test_error_handling(self):
        """Test invalid config doesn't crash watcher."""
```

### Integration Tests (15 tests)

**End-to-End Tests (tests/scheduler/test_integration.py):**
```python
class TestSchedulerIntegration:
    def test_alert_execution_on_schedule(self):
        """Test alert executes at scheduled time."""

    def test_multiple_alerts_different_schedules(self):
        """Test multiple alerts with different schedules."""

    def test_notification_sent_on_scheduled_alert(self):
        """Test notifications work for scheduled alerts."""

    def test_history_records_cron_trigger(self):
        """Test history shows triggered_by='CRON'."""

    def test_state_deduplication_with_scheduler(self):
        """Test state management works with scheduled execution."""
```

### CLI Tests (10 tests)

**Daemon Command Tests (tests/test_cli.py):**
```python
class TestDaemonCommand:
    def test_daemon_starts(self):
        """Test daemon command starts scheduler."""

    def test_daemon_shutdown(self):
        """Test daemon handles SIGTERM gracefully."""

    def test_daemon_config_reload(self):
        """Test daemon reloads config on changes."""
```

---

## Success Criteria

### Feature Completeness ✅

- [ ] Alerts execute automatically on cron schedules
- [ ] `sqlsentinel daemon` command works
- [ ] Configuration reloading works
- [ ] Multiple alerts with different schedules supported
- [ ] Timezone handling works correctly
- [ ] Graceful shutdown on signals

### Quality Metrics ✅

- [ ] >50 new tests added (338+ total)
- [ ] >80% coverage on scheduler module
- [ ] >85% overall coverage maintained
- [ ] All linting checks passing (Black, Ruff, mypy)
- [ ] No regressions in existing functionality

### Integration ✅

- [ ] History records show `triggered_by="CRON"`
- [ ] State management works with scheduled execution
- [ ] Notifications sent for scheduled alerts
- [ ] Docker container runs scheduler by default
- [ ] Environment variables configure scheduler

### Documentation ✅

- [ ] Scheduler architecture documented
- [ ] Daemon usage guide complete
- [ ] Troubleshooting guide available
- [ ] Examples updated with scheduling
- [ ] Sprint completion report written

---

## Timeline

| Day | Phase | Focus | Key Deliverables |
|-----|-------|-------|------------------|
| **Day 15** | 1-2 | APScheduler setup + Job management | SchedulerService class, job management methods, 25 tests |
| **Day 16** | 3-4 | Alert execution + CLI daemon | Alert execution integration, daemon command, 20 tests |
| **Day 17** | 5-6 | Config watching + Docker | File watcher, Docker updates, 15 tests |
| **Day 18** | 7-8 | Testing + Documentation | Full coverage, docs, completion report |

---

## Examples & Use Cases

### Example 1: Daily Revenue Check

```yaml
alerts:
  - name: "daily_revenue_check"
    description: "Alert when daily revenue falls below $10,000"
    enabled: true
    query: |
      SELECT
        CASE WHEN SUM(revenue) < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        SUM(revenue) as actual_value,
        10000 as threshold
      FROM orders
      WHERE date = CURRENT_DATE - 1
    schedule: "0 9 * * *"  # 9 AM daily (automatically executed!)
    notify:
      - channel: email
        recipients: ["finance@company.com"]
```

**Before Sprint 3.1:** Requires manual `sqlsentinel run alerts.yaml --alert daily_revenue_check`
**After Sprint 3.1:** Automatically runs every day at 9 AM

### Example 2: Continuous Error Monitoring

```yaml
alerts:
  - name: "api_error_rate"
    description: "Alert when API error rate exceeds 5%"
    enabled: true
    query: |
      SELECT
        CASE WHEN error_rate > 5 THEN 'ALERT' ELSE 'OK' END as status,
        error_rate as actual_value,
        5 as threshold
      FROM (
        SELECT (COUNT(*) FILTER (WHERE status >= 500) * 100.0 / COUNT(*)) as error_rate
        FROM api_logs
        WHERE timestamp >= NOW() - INTERVAL '5 minutes'
      )
    schedule: "*/5 * * * *"  # Every 5 minutes (24/7 monitoring!)
    notify:
      - channel: slack
        webhook_url: "${SLACK_WEBHOOK_URL}"
```

**Before Sprint 3.1:** No continuous monitoring
**After Sprint 3.1:** Automatically checks every 5 minutes

### Example 3: Daemon Usage

```bash
# Start daemon in foreground
sqlsentinel daemon /config/alerts.yaml --state-db sqlite:///data/state.db

# Start daemon with config reloading
sqlsentinel daemon /config/alerts.yaml --reload --log-level INFO

# Run in Docker
docker run -d \
  -v $(pwd)/alerts.yaml:/config/alerts.yaml \
  -v sqlsentinel-state:/data \
  -e DATABASE_URL="postgresql://user:pass@host/db" \
  -e SMTP_HOST="smtp.gmail.com" \
  -e SMTP_USERNAME="alerts@company.com" \
  -e SMTP_PASSWORD="secret" \
  sqlsentinel/sqlsentinel:latest
# Daemon starts automatically, runs alerts on schedule!
```

---

## Definition of Done

Sprint 3.1 is complete when:

1. ✅ All 8 phases delivered
2. ✅ >338 tests passing (288 existing + 50 new)
3. ✅ >85% overall code coverage
4. ✅ All linting checks passing
5. ✅ `sqlsentinel daemon` command works end-to-end
6. ✅ Docker container runs scheduler automatically
7. ✅ Complete documentation delivered
8. ✅ Sprint completion report written
9. ✅ Demo showing automated scheduling
10. ✅ All success criteria met

---

## Next Steps

### Immediate Actions

1. **Review this plan** - Team approval
2. **Add APScheduler dependency** - Update pyproject.toml
3. **Create scheduler module** - Directory structure
4. **Start Phase 1** - Scheduler service implementation

### After Sprint 3.1

**Sprint 3.2: BigQuery Integration** (Per roadmap)
- BigQuery connection adapter
- BigQuery storage backend
- Multi-backend configuration
- Performance optimization

---

## References

- [IMPLEMENTATION_ROADMAP.md](../../../IMPLEMENTATION_ROADMAP.md) - Overall project plan
- [Sprint 2.2 Completion](../week-2/sprint-2.2-completion.md) - Previous sprint results
- [APScheduler Docs](https://apscheduler.readthedocs.io/) - Scheduler library
- [croniter Docs](https://github.com/kiorky/croniter) - Cron expression parsing

---

**Prepared by:** Claude (AI Assistant)
**Date:** 2025-10-19
**Sprint:** 3.1 - Cron Scheduling
**Status:** 🟢 READY TO START
