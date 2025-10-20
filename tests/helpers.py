"""Test helper utilities for integration and unit tests."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from sqlsentinel.executor.history import ExecutionHistory
from sqlsentinel.executor.state import StateManager
from sqlsentinel.models.alert import QueryResult


def insert_test_orders(engine: Engine, orders: List[Dict[str, Any]]) -> None:
    """Insert test order data into the orders table.

    Args:
        engine: SQLAlchemy engine connected to test database
        orders: List of order dictionaries with keys: id, amount, created_at, status
    """
    with engine.connect() as conn:
        for order in orders:
            conn.execute(
                text(
                    """
                INSERT INTO orders (id, amount, created_at, status)
                VALUES (:id, :amount, :created_at, :status)
                """
                ),
                order,
            )
        conn.commit()


def insert_test_metrics(engine: Engine, metrics: List[Dict[str, Any]]) -> None:
    """Insert test metric data into the metrics table.

    Args:
        engine: SQLAlchemy engine connected to test database
        metrics: List of metric dictionaries with keys: id, metric_name, value, recorded_at
    """
    with engine.connect() as conn:
        for metric in metrics:
            conn.execute(
                text(
                    """
                INSERT INTO metrics (id, metric_name, value, recorded_at)
                VALUES (:id, :metric_name, :value, :recorded_at)
                """
                ),
                metric,
            )
        conn.commit()


def get_execution_count(engine: Engine, alert_name: Optional[str] = None) -> int:
    """Get the count of executions in history.

    Args:
        engine: SQLAlchemy engine connected to state/history database
        alert_name: Optional alert name to filter by

    Returns:
        Count of execution records
    """
    history = ExecutionHistory(engine)
    records = history.get_executions(alert_name=alert_name, limit=1000)
    return len(records)


def get_last_execution(engine: Engine, alert_name: str) -> Optional[Dict[str, Any]]:
    """Get the most recent execution record for an alert.

    Args:
        engine: SQLAlchemy engine connected to state/history database
        alert_name: Alert name to look up

    Returns:
        Execution record as dictionary or None if not found
    """
    history = ExecutionHistory(engine)
    record = history.get_latest_execution(alert_name)
    if not record:
        return None
    return {
        "id": record.record_id,
        "alert_name": record.alert_name,
        "executed_at": record.executed_at,
        "execution_duration_ms": record.execution_duration_ms,
        "status": record.status,
        "actual_value": record.actual_value,
        "threshold": record.threshold,
        "query": record.query,
        "error_message": record.error_message,
        "triggered_by": record.triggered_by,
        "notification_sent": record.notification_sent,
        "notification_error": record.notification_error,
        "context_data": record.context_data,
    }


def get_alert_state(engine: Engine, alert_name: str) -> Optional[Dict[str, Any]]:
    """Get the current state for an alert.

    Args:
        engine: SQLAlchemy engine connected to state/history database
        alert_name: Alert name to look up

    Returns:
        State information as dictionary or None if not found
    """
    state_manager = StateManager(engine)
    state = state_manager.get_state(alert_name)

    return {
        "alert_name": state.alert_name,
        "current_status": state.current_status,
        "last_executed_at": state.last_executed_at,
        "last_alert_at": state.last_alert_at,
        "last_ok_at": state.last_ok_at,
        "consecutive_alerts": state.consecutive_alerts,
        "consecutive_oks": state.consecutive_oks,
        "silenced_until": state.silenced_until,
        "escalation_count": state.escalation_count,
        "notification_failures": state.notification_failures,
        "last_notification_channel": state.last_notification_channel,
        "updated_at": state.updated_at,
    }


def verify_execution_recorded(
    engine: Engine,
    alert_name: str,
    expected_status: str,
    expected_notification_sent: bool = False,
) -> bool:
    """Verify that an execution was recorded with expected values.

    Args:
        engine: SQLAlchemy engine connected to state/history database
        alert_name: Alert name to verify
        expected_status: Expected execution status (ALERT, OK, ERROR)
        expected_notification_sent: Whether notification should have been sent

    Returns:
        True if execution matches expectations, False otherwise
    """
    execution = get_last_execution(engine, alert_name)
    if not execution:
        return False

    if execution["status"] != expected_status:
        return False

    if execution["notification_sent"] != expected_notification_sent:
        return False

    return True


def verify_state_updated(
    engine: Engine,
    alert_name: str,
    expected_status: str,
    expected_consecutive_alerts: Optional[int] = None,
    expected_consecutive_oks: Optional[int] = None,
) -> bool:
    """Verify that alert state was updated with expected values.

    Args:
        engine: SQLAlchemy engine connected to state/history database
        alert_name: Alert name to verify
        expected_status: Expected current status (ALERT, OK, ERROR)
        expected_consecutive_alerts: Expected consecutive alert count (optional)
        expected_consecutive_oks: Expected consecutive OK count (optional)

    Returns:
        True if state matches expectations, False otherwise
    """
    state = get_alert_state(engine, alert_name)
    if not state:
        return False

    if state["current_status"] != expected_status:
        return False

    if expected_consecutive_alerts is not None:
        if state["consecutive_alerts"] != expected_consecutive_alerts:
            return False

    if expected_consecutive_oks is not None:
        if state["consecutive_oks"] != expected_consecutive_oks:
            return False

    return True


def create_query_result(
    status: str = "ALERT",
    actual_value: Any = 100,
    threshold: Any = 50,
    context: Optional[Dict[str, Any]] = None,
) -> QueryResult:
    """Create a QueryResult instance for testing.

    Args:
        status: Alert status (ALERT or OK)
        actual_value: Actual metric value
        threshold: Threshold value
        context: Additional context fields

    Returns:
        QueryResult instance
    """
    return QueryResult(
        status=status,
        actual_value=actual_value,
        threshold=threshold,
        context=context or {},
    )


def assert_execution_result(
    result,
    expected_status: str,
    expected_has_query_result: bool = True,
    expected_has_error: bool = False,
) -> None:
    """Assert that an ExecutionResult matches expectations.

    Args:
        result: ExecutionResult to verify
        expected_status: Expected execution status (success, failure, error)
        expected_has_query_result: Whether query result should be present
        expected_has_error: Whether error should be present

    Raises:
        AssertionError: If result doesn't match expectations
    """
    assert result.status == expected_status, f"Expected status {expected_status}, got {result.status}"

    if expected_has_query_result:
        assert result.query_result is not None, "Expected query result to be present"
    else:
        assert result.query_result is None, "Expected no query result"

    if expected_has_error:
        assert result.error is not None, "Expected error to be present"
    else:
        assert result.error is None, f"Expected no error, got {result.error}"

    assert result.duration_ms >= 0, "Duration should be non-negative"
    assert result.alert_name, "Alert name should be present"
    assert result.timestamp, "Timestamp should be present"
