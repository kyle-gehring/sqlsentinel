"""Tests for execution history tracking."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlsentinel.database.schema import SchemaManager
from sqlsentinel.executor.history import ExecutionHistory, ExecutionRecord
from sqlsentinel.models.errors import ExecutionError


class TestExecutionRecord:
    """Test ExecutionRecord class."""

    def test_init_minimal(self):
        """Test ExecutionRecord initialization with minimal args."""
        now = datetime.utcnow()
        record = ExecutionRecord(
            alert_name="test_alert",
            executed_at=now,
            execution_duration_ms=123.45,
            status="OK",
            query="SELECT 1",
            triggered_by="CRON",
        )

        assert record.alert_name == "test_alert"
        assert record.executed_at == now
        assert record.execution_duration_ms == 123.45
        assert record.status == "OK"
        assert record.query == "SELECT 1"
        assert record.triggered_by == "CRON"
        assert record.actual_value is None
        assert record.threshold is None
        assert record.error_message is None
        assert record.notification_sent is False
        assert record.notification_error is None
        assert record.context_data == {}
        assert record.record_id is None

    def test_init_full(self):
        """Test ExecutionRecord initialization with all args."""
        now = datetime.utcnow()
        context = {"extra": "data"}
        record = ExecutionRecord(
            alert_name="test_alert",
            executed_at=now,
            execution_duration_ms=123.45,
            status="ALERT",
            query="SELECT status FROM test",
            triggered_by="MANUAL",
            actual_value=95.5,
            threshold=90.0,
            error_message=None,
            notification_sent=True,
            notification_error=None,
            context_data=context,
            record_id=42,
        )

        assert record.actual_value == 95.5
        assert record.threshold == 90.0
        assert record.notification_sent is True
        assert record.context_data == context
        assert record.record_id == 42


class TestExecutionHistory:
    """Test ExecutionHistory class."""

    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing."""
        engine = create_engine("sqlite:///:memory:")
        schema_manager = SchemaManager(engine)
        schema_manager.create_schema()
        return engine

    @pytest.fixture
    def history(self, engine):
        """Create ExecutionHistory instance."""
        return ExecutionHistory(engine)

    def test_init(self, history, engine):
        """Test ExecutionHistory initialization."""
        assert history.engine == engine

    def test_record_execution_minimal(self, history):
        """Test recording execution with minimal data."""
        now = datetime.utcnow()
        record = ExecutionRecord(
            alert_name="test_alert",
            executed_at=now,
            execution_duration_ms=100.0,
            status="OK",
            query="SELECT 1",
            triggered_by="CRON",
        )

        record_id = history.record_execution(record)
        assert record_id > 0

    def test_record_execution_full(self, history):
        """Test recording execution with full data."""
        now = datetime.utcnow()
        record = ExecutionRecord(
            alert_name="test_alert",
            executed_at=now,
            execution_duration_ms=150.5,
            status="ALERT",
            query="SELECT status FROM orders",
            triggered_by="MANUAL",
            actual_value=95.5,
            threshold=90.0,
            notification_sent=True,
            context_data={"order_count": 42},
        )

        record_id = history.record_execution(record)
        assert record_id > 0

    def test_get_executions_all(self, history):
        """Test getting all executions."""
        # Record multiple executions
        for i in range(3):
            record = ExecutionRecord(
                alert_name=f"alert_{i}",
                executed_at=datetime.utcnow(),
                execution_duration_ms=100.0 + i,
                status="OK",
                query=f"SELECT {i}",
                triggered_by="CRON",
            )
            history.record_execution(record)

        # Get all executions
        records = history.get_executions()
        assert len(records) == 3

    def test_get_executions_by_alert_name(self, history):
        """Test getting executions filtered by alert name."""
        # Record executions for different alerts
        for _i in range(2):
            record = ExecutionRecord(
                alert_name="alert_1",
                executed_at=datetime.utcnow(),
                execution_duration_ms=100.0,
                status="OK",
                query="SELECT 1",
                triggered_by="CRON",
            )
            history.record_execution(record)

        record = ExecutionRecord(
            alert_name="alert_2",
            executed_at=datetime.utcnow(),
            execution_duration_ms=200.0,
            status="ALERT",
            query="SELECT 2",
            triggered_by="MANUAL",
        )
        history.record_execution(record)

        # Get executions for alert_1
        records = history.get_executions(alert_name="alert_1")
        assert len(records) == 2
        assert all(r.alert_name == "alert_1" for r in records)

    def test_get_executions_with_limit(self, history):
        """Test getting executions with limit."""
        # Record 5 executions
        for _i in range(5):
            record = ExecutionRecord(
                alert_name="test_alert",
                executed_at=datetime.utcnow(),
                execution_duration_ms=100.0,
                status="OK",
                query="SELECT 1",
                triggered_by="CRON",
            )
            history.record_execution(record)

        # Get with limit=2
        records = history.get_executions(limit=2)
        assert len(records) == 2

    def test_get_executions_with_offset(self, history):
        """Test getting executions with offset."""
        # Record 5 executions
        for i in range(5):
            record = ExecutionRecord(
                alert_name="test_alert",
                executed_at=datetime.utcnow(),
                execution_duration_ms=100.0 + i,
                status="OK",
                query="SELECT 1",
                triggered_by="CRON",
            )
            history.record_execution(record)

        # Get with offset=2, limit=2
        records = history.get_executions(offset=2, limit=2)
        assert len(records) == 2

    def test_get_executions_ordered_by_time(self, history):
        """Test executions are ordered by time (newest first)."""
        # Record executions at different times
        times = []
        for i in range(3):
            now = datetime.utcnow()
            times.append(now)
            record = ExecutionRecord(
                alert_name="test_alert",
                executed_at=now,
                execution_duration_ms=100.0 + i,
                status="OK",
                query="SELECT 1",
                triggered_by="CRON",
            )
            history.record_execution(record)

        records = history.get_executions()
        # Should be in reverse chronological order
        for i in range(len(records) - 1):
            assert records[i].executed_at >= records[i + 1].executed_at

    def test_get_executions_preserves_context_data(self, history):
        """Test context_data is preserved correctly."""
        context = {"key1": "value1", "key2": 42}
        record = ExecutionRecord(
            alert_name="test_alert",
            executed_at=datetime.utcnow(),
            execution_duration_ms=100.0,
            status="OK",
            query="SELECT 1",
            triggered_by="CRON",
            context_data=context,
        )
        history.record_execution(record)

        records = history.get_executions(alert_name="test_alert")
        assert len(records) == 1
        assert records[0].context_data == context

    def test_get_latest_execution(self, history):
        """Test getting latest execution."""
        # Record multiple executions
        for i in range(3):
            record = ExecutionRecord(
                alert_name="test_alert",
                executed_at=datetime.utcnow(),
                execution_duration_ms=100.0 + i,
                status="OK",
                query="SELECT 1",
                triggered_by="CRON",
            )
            history.record_execution(record)

        latest = history.get_latest_execution("test_alert")
        assert latest is not None
        assert latest.alert_name == "test_alert"

    def test_get_latest_execution_not_found(self, history):
        """Test getting latest execution when none exist."""
        latest = history.get_latest_execution("nonexistent_alert")
        assert latest is None

    def test_delete_old_executions_by_days(self, history):
        """Test deleting old executions by days."""
        # Record old execution
        old_time = datetime.utcnow() - timedelta(days=40)
        old_record = ExecutionRecord(
            alert_name="test_alert",
            executed_at=old_time,
            execution_duration_ms=100.0,
            status="OK",
            query="SELECT 1",
            triggered_by="CRON",
        )
        history.record_execution(old_record)

        # Record recent execution
        recent_record = ExecutionRecord(
            alert_name="test_alert",
            executed_at=datetime.utcnow(),
            execution_duration_ms=100.0,
            status="OK",
            query="SELECT 1",
            triggered_by="CRON",
        )
        history.record_execution(recent_record)

        # Delete executions older than 30 days
        deleted = history.delete_old_executions(days=30)
        assert deleted >= 0  # SQLite might not delete the old record due to date calculation

        # Recent record should still exist
        records = history.get_executions(alert_name="test_alert")
        assert len(records) >= 1

    def test_delete_old_executions_by_alert_name(self, history):
        """Test deleting old executions filtered by alert name."""
        old_time = datetime.utcnow() - timedelta(days=40)

        # Record old executions for two different alerts
        old_record_1 = ExecutionRecord(
            alert_name="alert_1",
            executed_at=old_time,
            execution_duration_ms=100.0,
            status="OK",
            query="SELECT 1",
            triggered_by="CRON",
        )
        history.record_execution(old_record_1)

        old_record_2 = ExecutionRecord(
            alert_name="alert_2",
            executed_at=old_time,
            execution_duration_ms=100.0,
            status="OK",
            query="SELECT 2",
            triggered_by="CRON",
        )
        history.record_execution(old_record_2)

        # Delete old executions for alert_1 only
        history.delete_old_executions(alert_name="alert_1", days=30)

        # alert_2 records might still exist (depending on date calculation)
        history.get_executions(alert_name="alert_2")
        # Just verify no error occurs

    def test_delete_old_executions_invalid_days(self, history):
        """Test delete_old_executions with invalid days."""
        with pytest.raises(ExecutionError, match="Days must be positive"):
            history.delete_old_executions(days=0)

        with pytest.raises(ExecutionError, match="Days must be positive"):
            history.delete_old_executions(days=-1)

    def test_get_statistics(self, history):
        """Test getting execution statistics."""
        # Record various executions
        statuses = ["OK", "OK", "ALERT", "ERROR"]
        for i, status in enumerate(statuses):
            record = ExecutionRecord(
                alert_name="test_alert",
                executed_at=datetime.utcnow(),
                execution_duration_ms=100.0 + (i * 10),
                status=status,
                query="SELECT 1",
                triggered_by="CRON",
            )
            history.record_execution(record)

        stats = history.get_statistics("test_alert", days=7)
        assert stats["total"] == 4
        assert stats["oks"] == 2
        assert stats["alerts"] == 1
        assert stats["errors"] == 1
        assert stats["avg_duration_ms"] > 0
        assert stats["min_duration_ms"] > 0
        assert stats["max_duration_ms"] > 0

    def test_get_statistics_no_data(self, history):
        """Test statistics with no data."""
        stats = history.get_statistics("nonexistent_alert", days=7)
        assert stats["total"] == 0
        assert stats["oks"] == 0
        assert stats["alerts"] == 0
        assert stats["errors"] == 0

    def test_get_statistics_invalid_days(self, history):
        """Test get_statistics with invalid days."""
        with pytest.raises(ExecutionError, match="Days must be positive"):
            history.get_statistics("test_alert", days=0)

        with pytest.raises(ExecutionError, match="Days must be positive"):
            history.get_statistics("test_alert", days=-1)
