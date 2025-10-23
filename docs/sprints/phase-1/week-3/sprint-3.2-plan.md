# Sprint 3.2 Plan: BigQuery Integration

**Sprint:** 3.2 - BigQuery Integration
**Phase:** 1 (Core MVP)
**Week:** 3
**Duration:** Days 19-22 (4 days)
**Status:** 🟢 READY TO START
**Started:** TBD
**Target Completion:** TBD

---

## Sprint Goal

Add BigQuery support to SQL Sentinel, enabling alerts to query Google Cloud Platform's analytics warehouse. This completes the Week 3 deliverables and provides the first cloud data warehouse integration.

---

## Executive Summary

### Context from Sprint 3.1

Sprint 3.1 delivered automated scheduling with daemon mode:
- ✅ 334 tests passing with 89% coverage
- ✅ APScheduler integration for cron-based scheduling
- ✅ `sqlsentinel daemon` command with graceful shutdown
- ✅ Configuration hot reload with file watching
- ✅ Docker daemon mode (runs by default)
- ✅ Comprehensive documentation (3 guides, 1930+ lines)

**Current State:** SQL Sentinel supports SQLite, PostgreSQL, MySQL, and any SQLAlchemy-compatible database via connection strings.

### Sprint 3.2 Objective

Add native BigQuery support to enable:
1. **BigQuery connectivity** - Connect to GCP BigQuery datasets using google-cloud-bigquery
2. **Alert execution** - Run alert queries against BigQuery tables
3. **Authentication** - Support service account keys and Application Default Credentials (ADC)
4. **Cost awareness** - Query dry-run support to estimate costs before execution
5. **Performance** - Leverage BigQuery's performance characteristics (query caching, partitioning)

---

## Scope & Deliverables

### In Scope ✅

1. **BigQuery Connection Adapter**
   - Google Cloud BigQuery SDK integration
   - Service account authentication (JSON key file)
   - Application Default Credentials (ADC) support
   - Connection validation and health checks
   - Error handling for BigQuery-specific errors

2. **Query Execution**
   - Execute alert queries against BigQuery datasets
   - Result set conversion to SQL Sentinel's QueryResult format
   - Query dry-run for cost estimation
   - Query timeout handling
   - Large result set handling

3. **Database Adapter Extension**
   - Extend DatabaseAdapter to support BigQuery URLs
   - Auto-detect BigQuery connection strings (bigquery://)
   - Transparent integration with existing AlertExecutor
   - Backward compatibility with SQLAlchemy adapters

4. **Authentication & Configuration**
   - Service account key file support
   - Environment variable configuration (GOOGLE_APPLICATION_CREDENTIALS)
   - ADC for local development and GCP environments
   - Project ID configuration

5. **Testing & Quality**
   - Unit tests for BigQuery adapter (>80% coverage)
   - Integration tests with BigQuery emulator or test project
   - Error scenario testing
   - Mock-based testing for CI/CD

6. **Documentation**
   - BigQuery setup guide
   - Authentication configuration guide
   - Cost management best practices
   - Example alerts for BigQuery
   - Troubleshooting guide

### Out of Scope 🚫

1. **BigQuery Storage Backend** - Deferred (state/history stored in SQLite/PostgreSQL for MVP)
2. **BigQuery API Advanced Features** - No streaming inserts, no job management UI
3. **Multi-Region Configuration** - Single region only for MVP
4. **Cost Quotas/Limits** - No automated cost limit enforcement (documented only)
5. **BigQuery ML Integration** - No ML model queries in MVP
6. **Data Transfer Service** - No scheduled imports/exports

---

## Technical Architecture

### BigQuery Adapter Design

```
src/sqlsentinel/database/
├── __init__.py                    # Exports DatabaseAdapter
├── adapter.py                     # Base DatabaseAdapter (existing)
├── bigquery_adapter.py            # NEW: BigQuery-specific adapter
└── factory.py                     # NEW: Adapter factory (URL-based routing)
```

### BigQuery Adapter Class

```python
class BigQueryAdapter:
    """
    BigQuery-specific database adapter.

    Responsibilities:
    - Connect to BigQuery using google-cloud-bigquery client
    - Execute queries and convert results to standard format
    - Handle BigQuery-specific errors
    - Support dry-run for cost estimation
    - Implement query timeout and retry logic
    """

    def __init__(
        self,
        project_id: str,
        credentials_path: str | None = None,
        location: str = "US"
    ):
        """
        Initialize BigQuery adapter.

        Args:
            project_id: GCP project ID
            credentials_path: Path to service account JSON key (optional)
            location: BigQuery dataset location (default: US)
        """
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.location = location
        self._client: bigquery.Client | None = None

    def connect(self) -> None:
        """Establish BigQuery connection."""

    def disconnect(self) -> None:
        """Close BigQuery connection."""

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """
        Execute BigQuery query and return results.

        Returns:
            List of dictionaries (same format as DatabaseAdapter)
        """

    def dry_run(self, query: str) -> dict[str, Any]:
        """
        Perform query dry-run to estimate cost.

        Returns:
            Dict with bytes_processed and estimated_cost_usd
        """

    def __enter__(self) -> "BigQueryAdapter":
        """Context manager entry."""

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
```

### Adapter Factory Pattern

```python
class AdapterFactory:
    """
    Factory for creating database adapters based on connection string.

    Supports:
    - bigquery://project-id/dataset  -> BigQueryAdapter
    - postgresql://...               -> DatabaseAdapter (SQLAlchemy)
    - mysql://...                    -> DatabaseAdapter (SQLAlchemy)
    - sqlite://...                   -> DatabaseAdapter (SQLAlchemy)
    """

    @staticmethod
    def create_adapter(connection_string: str) -> DatabaseAdapter | BigQueryAdapter:
        """
        Create appropriate adapter based on connection string scheme.

        Args:
            connection_string: Database connection string

        Returns:
            DatabaseAdapter or BigQueryAdapter instance
        """
        if connection_string.startswith("bigquery://"):
            return AdapterFactory._create_bigquery_adapter(connection_string)
        else:
            return DatabaseAdapter(connection_string)

    @staticmethod
    def _create_bigquery_adapter(connection_string: str) -> BigQueryAdapter:
        """Parse BigQuery connection string and create adapter."""
        # Parse: bigquery://project-id/dataset?credentials=/path/to/key.json
```

### Integration with Existing Code

**No Breaking Changes** - Existing code continues to work:

```python
# Before (Sprint 3.1 and earlier) - Still works!
adapter = DatabaseAdapter("postgresql://user:pass@host/db")

# After (Sprint 3.2) - New BigQuery support
adapter = AdapterFactory.create_adapter("bigquery://my-project/my-dataset")
```

**CLI Integration** - Transparent to users:

```yaml
# alerts.yaml - Works automatically with BigQuery!
alerts:
  - name: "bigquery_revenue_check"
    query: |
      SELECT
        CASE WHEN total_revenue < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        total_revenue as actual_value,
        10000 as threshold
      FROM `my-project.analytics.daily_revenue`
      WHERE date = CURRENT_DATE() - 1
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["team@company.com"]
```

```bash
# CLI usage - Just set DATABASE_URL to BigQuery!
export DATABASE_URL="bigquery://my-project/analytics"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

sqlsentinel daemon /config/alerts.yaml
```

---

## Implementation Plan

### Phase 1: BigQuery SDK Setup (Day 19 - Morning)

**Goal:** Add BigQuery client library and validate connectivity

**Tasks:**
1. Add `google-cloud-bigquery` to pyproject.toml dependencies
2. Add `google-auth` to dependencies (authentication)
3. Create `src/sqlsentinel/database/bigquery_adapter.py`
4. Implement basic BigQueryAdapter class structure
5. Implement `connect()` and `disconnect()` methods
6. Write initial unit tests with mocks

**Deliverables:**
- [ ] Dependencies added to pyproject.toml
- [ ] BigQueryAdapter skeleton class
- [ ] Connection/disconnection logic
- [ ] 5+ unit tests (mocked BigQuery client)

**Success Criteria:**
- BigQuery client initializes with credentials
- Connection validation works
- All tests pass with mocked BigQuery
- No breaking changes to existing code

**Files to Create:**
```
src/sqlsentinel/database/bigquery_adapter.py
tests/database/test_bigquery_adapter.py
```

---

### Phase 2: Query Execution (Day 19 - Afternoon)

**Goal:** Execute BigQuery queries and convert results

**Tasks:**
1. Implement `execute_query()` method
2. Convert BigQuery Row objects to dict format
3. Handle BigQuery data types (DATE, TIMESTAMP, STRUCT, ARRAY)
4. Implement error handling for BigQuery-specific errors
5. Add timeout handling
6. Write query execution tests

**Deliverables:**
- [ ] Query execution working
- [ ] Result conversion to standard format
- [ ] Data type handling
- [ ] 10+ unit tests

**Success Criteria:**
- Queries execute successfully against BigQuery
- Results match DatabaseAdapter format
- BigQuery data types convert correctly
- Timeouts handled gracefully

**Files to Modify:**
```
src/sqlsentinel/database/bigquery_adapter.py (add execute_query)
tests/database/test_bigquery_adapter.py (add execution tests)
```

---

### Phase 3: Adapter Factory (Day 20 - Morning)

**Goal:** Create factory pattern for adapter selection

**Tasks:**
1. Create `src/sqlsentinel/database/factory.py`
2. Implement AdapterFactory.create_adapter()
3. Parse BigQuery connection strings
4. Support query parameters (credentials, location)
5. Update AlertExecutor to use factory
6. Write factory tests

**Deliverables:**
- [ ] Adapter factory implementation
- [ ] BigQuery URL parsing
- [ ] Integration with AlertExecutor
- [ ] 8+ unit tests

**Success Criteria:**
- Factory creates correct adapter based on URL scheme
- BigQuery URLs parsed correctly
- SQLAlchemy URLs still work (backward compatible)
- No changes required to alert YAML files

**Files to Create:**
```
src/sqlsentinel/database/factory.py
tests/database/test_factory.py
```

**Files to Modify:**
```
src/sqlsentinel/executor/alert_executor.py (use factory)
src/sqlsentinel/database/__init__.py (export factory)
```

---

### Phase 4: Authentication & Configuration (Day 20 - Afternoon)

**Goal:** Support multiple authentication methods

**Tasks:**
1. Service account key file authentication
2. Application Default Credentials (ADC) support
3. Environment variable configuration
4. Credential validation
5. Write authentication tests

**Deliverables:**
- [ ] Service account key support
- [ ] ADC support
- [ ] Environment variable handling
- [ ] 6+ tests

**Success Criteria:**
- Service account JSON keys work
- ADC works in local and GCP environments
- GOOGLE_APPLICATION_CREDENTIALS respected
- Clear error messages for auth failures

**Files to Modify:**
```
src/sqlsentinel/database/bigquery_adapter.py (auth logic)
tests/database/test_bigquery_adapter.py (auth tests)
```

---

### Phase 5: Cost Awareness & Optimization (Day 21 - Morning)

**Goal:** Add query dry-run and cost estimation

**Tasks:**
1. Implement `dry_run()` method
2. Calculate estimated cost from bytes scanned
3. Add optional dry-run validation to CLI
4. Document cost management best practices
5. Write dry-run tests

**Deliverables:**
- [ ] Dry-run method implementation
- [ ] Cost estimation logic
- [ ] CLI flag for dry-run validation
- [ ] 5+ tests

**Success Criteria:**
- Dry-run estimates bytes processed
- Cost calculated correctly ($5 per TB)
- Users can validate queries before scheduling
- Documentation explains cost implications

**Files to Modify:**
```
src/sqlsentinel/database/bigquery_adapter.py (dry_run method)
src/sqlsentinel/cli.py (optional: --dry-run flag)
tests/database/test_bigquery_adapter.py (dry-run tests)
```

---

### Phase 6: Integration Testing (Day 21 - Afternoon)

**Goal:** End-to-end testing with BigQuery

**Tasks:**
1. Create BigQuery test project/dataset (or use emulator)
2. Write integration tests with real BigQuery
3. Test alert execution end-to-end
4. Test daemon mode with BigQuery
5. Test all notification channels

**Deliverables:**
- [ ] Integration test suite
- [ ] Example BigQuery alerts
- [ ] End-to-end test scenarios
- [ ] 8+ integration tests

**Success Criteria:**
- Alerts execute against BigQuery datasets
- Results trigger notifications correctly
- State management works with BigQuery
- History records BigQuery executions

**Files to Create:**
```
tests/integration/test_bigquery_alerts.py
examples/bigquery-alerts.yaml
```

---

### Phase 7: Testing & Quality (Day 22 - Morning)

**Goal:** Comprehensive testing and code quality

**Tasks:**
1. Achieve >80% coverage on BigQuery adapter
2. Test error scenarios (auth failures, query errors, timeouts)
3. Test backward compatibility with existing databases
4. Run full test suite (all 334+ existing tests)
5. Fix any linting issues

**Deliverables:**
- [ ] >80% coverage on BigQuery module
- [ ] Error scenario tests
- [ ] Backward compatibility validated
- [ ] All 360+ tests passing

**Success Criteria:**
- All tests passing (334 existing + 30 new)
- >85% overall coverage maintained
- No regressions in existing functionality
- Black, Ruff, mypy all passing

**Test Coverage Targets:**
```
database/bigquery_adapter.py:  >85%
database/factory.py:           >90%
Overall:                       >85%
```

---

### Phase 8: Documentation (Day 22 - Afternoon)

**Goal:** Complete BigQuery documentation

**Tasks:**
1. Write BigQuery setup guide
2. Write authentication guide
3. Create example alerts for BigQuery
4. Document cost management
5. Update main README
6. Create sprint completion report

**Deliverables:**
- [ ] docs/guides/bigquery-setup.md
- [ ] docs/guides/bigquery-authentication.md
- [ ] docs/guides/bigquery-cost-management.md
- [ ] examples/bigquery-alerts.yaml
- [ ] Updated README.md
- [ ] docs/sprints/phase-1/week-3/sprint-3.2-completion.md

**Success Criteria:**
- Clear step-by-step setup instructions
- Authentication methods documented
- Cost implications explained
- Working examples provided

**Files to Create:**
```
docs/guides/bigquery-setup.md
docs/guides/bigquery-authentication.md
docs/guides/bigquery-cost-management.md
examples/bigquery-alerts.yaml
docs/sprints/phase-1/week-3/sprint-3.2-completion.md
```

---

## Dependencies & Risks

### Dependencies

**New Python Packages:**
1. **google-cloud-bigquery** (^3.14) - BigQuery client library
   - Mature library maintained by Google
   - Comprehensive API coverage
   - Active development and support
   - Includes result pagination, dry-run, etc.

2. **google-auth** (^2.25) - Google authentication library
   - Required for service account auth
   - Supports ADC (Application Default Credentials)
   - Used by google-cloud-bigquery

**GCP Requirements:**
- GCP project with BigQuery API enabled
- Service account with BigQuery Job User role (minimum)
- BigQuery Data Viewer role for reading datasets
- (Optional) BigQuery test dataset for integration tests

### Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Query costs** | High | Medium | Dry-run support, cost documentation, best practices guide |
| **Authentication complexity** | Medium | Medium | Support ADC for simplicity, clear documentation, examples |
| **Large result sets** | Medium | Low | Implement pagination, document query best practices |
| **BigQuery quotas** | Medium | Low | Document quota limits, implement retry with backoff |
| **Integration test costs** | Low | High | Use BigQuery sandbox or minimal test data, mock tests in CI |
| **Backward compatibility** | High | Low | Factory pattern, extensive testing, no breaking changes |

**Risk Mitigation Strategy:**
- Start with mock-based tests (no BigQuery costs in CI)
- Optional integration tests with real BigQuery
- Comprehensive documentation on cost management
- Dry-run before scheduling queries

---

## Testing Strategy

### Unit Tests (25 tests)

**BigQuery Adapter Tests (tests/database/test_bigquery_adapter.py):**
```python
class TestBigQueryAdapter:
    def test_initialization(self):
        """Test adapter initializes with project ID."""

    def test_connect_with_service_account(self):
        """Test connection with service account key."""

    def test_connect_with_adc(self):
        """Test connection with Application Default Credentials."""

    def test_execute_query(self):
        """Test query execution returns correct format."""

    def test_execute_query_with_parameters(self):
        """Test parameterized queries."""

    def test_data_type_conversion(self):
        """Test BigQuery data types convert correctly."""

    def test_error_handling(self):
        """Test BigQuery-specific errors handled."""

    def test_timeout_handling(self):
        """Test query timeout handling."""

    def test_dry_run(self):
        """Test dry-run cost estimation."""

    @pytest.mark.parametrize("query,expected_bytes", [
        ("SELECT * FROM large_table", 1000000000),
        ("SELECT status FROM small_table", 1000),
    ])
    def test_dry_run_estimates(self, query, expected_bytes):
        """Test dry-run estimates for different queries."""
```

**Adapter Factory Tests (tests/database/test_factory.py):**
```python
class TestAdapterFactory:
    def test_create_bigquery_adapter(self):
        """Test factory creates BigQuery adapter for bigquery:// URLs."""

    def test_create_sqlalchemy_adapter(self):
        """Test factory creates SQLAlchemy adapter for other URLs."""

    def test_parse_bigquery_url(self):
        """Test BigQuery URL parsing."""

    @pytest.mark.parametrize("url,expected_type", [
        ("bigquery://project/dataset", BigQueryAdapter),
        ("postgresql://localhost/db", DatabaseAdapter),
        ("sqlite:///test.db", DatabaseAdapter),
    ])
    def test_adapter_type_detection(self, url, expected_type):
        """Test correct adapter type created."""
```

### Integration Tests (8 tests)

**BigQuery Integration Tests (tests/integration/test_bigquery_alerts.py):**
```python
@pytest.mark.integration
@pytest.mark.bigquery
class TestBigQueryIntegration:
    """Integration tests requiring real BigQuery access."""

    def test_execute_alert_against_bigquery(self):
        """Test alert execution against BigQuery dataset."""

    def test_bigquery_alert_with_notifications(self):
        """Test BigQuery alert triggers notifications."""

    def test_bigquery_state_management(self):
        """Test state management with BigQuery alerts."""

    def test_bigquery_execution_history(self):
        """Test history records BigQuery executions."""

    def test_daemon_mode_with_bigquery(self):
        """Test daemon schedules BigQuery alerts."""
```

### Mock Tests (15 tests)

**Mock-based tests for CI/CD (no BigQuery required):**
```python
class TestBigQueryAdapterMocked:
    """Tests using mocked BigQuery client for CI/CD."""

    @patch('google.cloud.bigquery.Client')
    def test_query_execution_mocked(self, mock_client):
        """Test query execution with mocked client."""
```

---

## Success Criteria

### Feature Completeness ✅

- [ ] BigQuery alerts execute successfully
- [ ] Results convert to standard format correctly
- [ ] Service account authentication works
- [ ] Application Default Credentials work
- [ ] Dry-run cost estimation functional
- [ ] Backward compatibility maintained

### Quality Metrics ✅

- [ ] >30 new tests added (364+ total)
- [ ] >80% coverage on BigQuery module
- [ ] >85% overall coverage maintained
- [ ] All linting checks passing (Black, Ruff, mypy)
- [ ] No regressions in existing functionality

### Integration ✅

- [ ] AlertExecutor works with BigQuery
- [ ] State management works with BigQuery
- [ ] Notifications sent for BigQuery alerts
- [ ] History records BigQuery executions
- [ ] Daemon schedules BigQuery alerts

### Documentation ✅

- [ ] BigQuery setup guide complete
- [ ] Authentication guide complete
- [ ] Cost management documented
- [ ] Example alerts provided
- [ ] Sprint completion report written

---

## Timeline

| Day | Phase | Focus | Key Deliverables |
|-----|-------|-------|------------------|
| **Day 19** | 1-2 | SDK setup + Query execution | BigQueryAdapter class, execute_query, 15 tests |
| **Day 20** | 3-4 | Factory + Authentication | Adapter factory, auth methods, 14 tests |
| **Day 21** | 5-6 | Cost awareness + Integration | Dry-run, integration tests, examples |
| **Day 22** | 7-8 | Testing + Documentation | Full coverage, docs, completion report |

---

## Examples & Use Cases

### Example 1: BigQuery Revenue Alert

```yaml
# alerts.yaml
alerts:
  - name: "bigquery_revenue_check"
    description: "Alert when daily revenue falls below threshold"
    enabled: true
    query: |
      SELECT
        CASE WHEN total_revenue < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        total_revenue as actual_value,
        10000 as threshold,
        date
      FROM `my-project.analytics.daily_revenue`
      WHERE date = CURRENT_DATE() - 1
    schedule: "0 9 * * *"  # 9 AM daily
    notify:
      - channel: email
        recipients: ["finance@company.com"]
```

**Setup:**
```bash
# Set environment variables
export DATABASE_URL="bigquery://my-project/analytics"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# Run daemon
sqlsentinel daemon alerts.yaml
```

### Example 2: BigQuery Data Quality Check

```yaml
alerts:
  - name: "bigquery_null_check"
    description: "Alert when null percentages exceed threshold"
    query: |
      SELECT
        CASE
          WHEN null_percentage > 5 THEN 'ALERT'
          ELSE 'OK'
        END as status,
        null_percentage as actual_value,
        5 as threshold,
        table_name
      FROM (
        SELECT
          'users' as table_name,
          COUNTIF(email IS NULL) * 100.0 / COUNT(*) as null_percentage
        FROM `my-project.prod.users`
        WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
      )
    schedule: "0 */6 * * *"  # Every 6 hours
    notify:
      - channel: slack
        webhook_url: "${SLACK_WEBHOOK_URL}"
```

### Example 3: Cost-Aware Query Development

```bash
# Validate query cost before scheduling
export DATABASE_URL="bigquery://my-project/analytics"

# Dry-run to estimate cost (future enhancement)
sqlsentinel validate alerts.yaml --dry-run

# Output:
# ✓ Alert 'bigquery_revenue_check':
#   - Query valid
#   - Estimated bytes: 1.2 GB
#   - Estimated cost: $0.006 per execution
#   - Daily cost (9 AM schedule): $0.006
#   - Monthly cost: ~$0.18
```

### Example 4: Multiple BigQuery Projects

```yaml
# Different alerts can query different projects
alerts:
  - name: "production_metrics"
    database_url: "bigquery://prod-project/analytics"
    query: "SELECT CASE WHEN errors > 100 THEN 'ALERT' ELSE 'OK' END as status FROM errors_table"
    schedule: "*/5 * * * *"

  - name: "staging_metrics"
    database_url: "bigquery://staging-project/analytics"
    query: "SELECT CASE WHEN tests_failed > 0 THEN 'ALERT' ELSE 'OK' END as status FROM test_results"
    schedule: "0 * * * *"
```

---

## BigQuery Connection String Format

### Standard Format

```
bigquery://PROJECT_ID/DATASET?credentials=/path/to/key.json&location=US
```

**Components:**
- `PROJECT_ID`: GCP project ID (required)
- `DATASET`: Default dataset for queries (optional)
- `credentials`: Path to service account JSON key (optional, uses ADC if not provided)
- `location`: BigQuery location (optional, default: US)

### Examples

```bash
# Minimal (uses ADC)
bigquery://my-project

# With dataset
bigquery://my-project/analytics

# With service account
bigquery://my-project/analytics?credentials=/keys/service-account.json

# With location
bigquery://my-project/analytics?location=EU

# Full specification
bigquery://my-project/analytics?credentials=/keys/sa.json&location=US
```

---

## Definition of Done

Sprint 3.2 is complete when:

1. ✅ All 8 phases delivered
2. ✅ >364 tests passing (334 existing + 30 new)
3. ✅ >85% overall code coverage
4. ✅ All linting checks passing
5. ✅ BigQuery alerts execute successfully
6. ✅ Both authentication methods work (service account + ADC)
7. ✅ Complete documentation delivered
8. ✅ Sprint completion report written
9. ✅ Demo showing BigQuery alert execution
10. ✅ All success criteria met
11. ✅ No breaking changes to existing functionality

---

## Next Steps

### Immediate Actions

1. **Review this plan** - Team approval
2. **Create GCP test project** - For integration testing
3. **Add google-cloud-bigquery dependency** - Update pyproject.toml
4. **Create BigQuery adapter module** - File structure
5. **Start Phase 1** - BigQuery adapter implementation

### After Sprint 3.2

**Sprint 4.1: Docker & Deployment** (Per roadmap - Week 4)
- Production Docker image optimization
- Docker Compose deployment
- Health monitoring
- Basic metrics and logging

**Phase 1 Completion:**
After Sprint 3.2, Phase 1 (Core MVP) will be complete with:
- ✅ Core alert execution engine
- ✅ Multi-channel notifications (Email, Slack, Webhook)
- ✅ Automated scheduling (daemon mode)
- ✅ BigQuery support (first cloud warehouse!)
- ✅ Docker deployment ready

---

## References

- [IMPLEMENTATION_ROADMAP.md](../../../IMPLEMENTATION_ROADMAP.md) - Overall project plan
- [Sprint 3.1 Completion](sprint-3.1-completion.md) - Previous sprint results
- [Google Cloud BigQuery Documentation](https://cloud.google.com/bigquery/docs) - Official docs
- [google-cloud-bigquery Python Library](https://googleapis.dev/python/bigquery/latest/) - SDK docs
- [BigQuery Pricing](https://cloud.google.com/bigquery/pricing) - Cost information

---

**Prepared by:** Claude (AI Assistant)
**Date:** 2025-10-20
**Sprint:** 3.2 - BigQuery Integration
**Status:** 🟢 READY TO START
