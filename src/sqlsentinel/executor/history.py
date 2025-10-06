"""Execution history tracking for SQL Sentinel."""

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..models.errors import ExecutionError


class ExecutionRecord:
    """Represents a single alert execution record."""

    def __init__(
        self,
        alert_name: str,
        executed_at: datetime,
        execution_duration_ms: float,
        status: str,
        query: str,
        triggered_by: str,
        actual_value: Optional[float] = None,
        threshold: Optional[float] = None,
        error_message: Optional[str] = None,
        notification_sent: bool = False,
        notification_error: Optional[str] = None,
        context_data: Optional[dict[str, Any]] = None,
        record_id: Optional[int] = None,
    ):
        """Initialize execution record.

        Args:
            alert_name: Name of the alert
            executed_at: Timestamp of execution
            execution_duration_ms: Execution duration in milliseconds
            status: Execution status (ALERT, OK, ERROR)
            query: SQL query that was executed
            triggered_by: What triggered execution (CRON, MANUAL, API)
            actual_value: Actual metric value (optional)
            threshold: Threshold value (optional)
            error_message: Error message if status is ERROR (optional)
            notification_sent: Whether notification was sent successfully
            notification_error: Error message from notification attempt (optional)
            context_data: Additional context data as dictionary (optional)
            record_id: Database record ID (optional, set after insert)
        """
        self.alert_name = alert_name
        self.executed_at = executed_at
        self.execution_duration_ms = execution_duration_ms
        self.status = status
        self.query = query
        self.triggered_by = triggered_by
        self.actual_value = actual_value
        self.threshold = threshold
        self.error_message = error_message
        self.notification_sent = notification_sent
        self.notification_error = notification_error
        self.context_data = context_data or {}
        self.record_id = record_id


class ExecutionHistory:
    """Manages execution history in database."""

    def __init__(self, engine: Engine):
        """Initialize execution history manager.

        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine

    def record_execution(self, record: ExecutionRecord) -> int:
        """Record an alert execution in history.

        Args:
            record: ExecutionRecord to save

        Returns:
            ID of the created record

        Raises:
            ExecutionError: If database insert fails
        """
        try:
            # Serialize context_data to JSON
            context_json = json.dumps(record.context_data) if record.context_data else None

            with self.engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                        INSERT INTO sqlsentinel_executions (
                            alert_name,
                            executed_at,
                            execution_duration_ms,
                            status,
                            actual_value,
                            threshold,
                            query,
                            error_message,
                            triggered_by,
                            notification_sent,
                            notification_error,
                            context_data
                        ) VALUES (
                            :alert_name,
                            :executed_at,
                            :execution_duration_ms,
                            :status,
                            :actual_value,
                            :threshold,
                            :query,
                            :error_message,
                            :triggered_by,
                            :notification_sent,
                            :notification_error,
                            :context_data
                        )
                        """
                    ),
                    {
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
                        "context_data": context_json,
                    },
                )
                # Get last inserted row ID
                return result.lastrowid or 0

        except SQLAlchemyError as e:
            raise ExecutionError(f"Failed to record execution: {e}") from e

    def get_executions(
        self,
        alert_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExecutionRecord]:
        """Get execution history records.

        Args:
            alert_name: Filter by alert name (optional, None = all alerts)
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of ExecutionRecord instances

        Raises:
            ExecutionError: If database query fails
        """
        try:
            with self.engine.connect() as conn:
                if alert_name:
                    query = text(
                        """
                        SELECT
                            id,
                            alert_name,
                            executed_at,
                            execution_duration_ms,
                            status,
                            actual_value,
                            threshold,
                            query,
                            error_message,
                            triggered_by,
                            notification_sent,
                            notification_error,
                            context_data
                        FROM sqlsentinel_executions
                        WHERE alert_name = :alert_name
                        ORDER BY executed_at DESC
                        LIMIT :limit OFFSET :offset
                        """
                    )
                    result = conn.execute(
                        query,
                        {"alert_name": alert_name, "limit": limit, "offset": offset},
                    )
                else:
                    query = text(
                        """
                        SELECT
                            id,
                            alert_name,
                            executed_at,
                            execution_duration_ms,
                            status,
                            actual_value,
                            threshold,
                            query,
                            error_message,
                            triggered_by,
                            notification_sent,
                            notification_error,
                            context_data
                        FROM sqlsentinel_executions
                        ORDER BY executed_at DESC
                        LIMIT :limit OFFSET :offset
                        """
                    )
                    result = conn.execute(query, {"limit": limit, "offset": offset})

                records = []
                for row in result:
                    # Parse context_data JSON
                    context_data = None
                    if row[12]:  # context_data column
                        try:
                            context_data = json.loads(row[12])
                        except json.JSONDecodeError:
                            context_data = {}

                    # Parse datetime if string (SQLite)
                    executed_at = row[2]
                    if isinstance(executed_at, str):
                        executed_at = datetime.fromisoformat(
                            executed_at.replace("Z", "+00:00")
                        )

                    records.append(
                        ExecutionRecord(
                            record_id=row[0],
                            alert_name=row[1],
                            executed_at=executed_at,
                            execution_duration_ms=row[3],
                            status=row[4],
                            actual_value=row[5],
                            threshold=row[6],
                            query=row[7],
                            error_message=row[8],
                            triggered_by=row[9],
                            notification_sent=bool(row[10]),
                            notification_error=row[11],
                            context_data=context_data,
                        )
                    )

                return records

        except SQLAlchemyError as e:
            raise ExecutionError(f"Failed to get execution history: {e}") from e

    def get_latest_execution(self, alert_name: str) -> Optional[ExecutionRecord]:
        """Get the most recent execution for an alert.

        Args:
            alert_name: Name of the alert

        Returns:
            ExecutionRecord or None if no executions found

        Raises:
            ExecutionError: If database query fails
        """
        records = self.get_executions(alert_name=alert_name, limit=1)
        return records[0] if records else None

    def delete_old_executions(
        self, alert_name: Optional[str] = None, days: int = 30
    ) -> int:
        """Delete execution records older than specified days.

        Args:
            alert_name: Filter by alert name (optional, None = all alerts)
            days: Delete records older than this many days

        Returns:
            Number of records deleted

        Raises:
            ExecutionError: If database delete fails
        """
        if days <= 0:
            raise ExecutionError("Days must be positive")

        try:
            cutoff_date = datetime.utcnow()
            cutoff_date = cutoff_date.replace(
                day=cutoff_date.day - days if cutoff_date.day > days else 1
            )

            with self.engine.begin() as conn:
                if alert_name:
                    result = conn.execute(
                        text(
                            """
                            DELETE FROM sqlsentinel_executions
                            WHERE alert_name = :alert_name
                            AND executed_at < :cutoff_date
                            """
                        ),
                        {"alert_name": alert_name, "cutoff_date": cutoff_date},
                    )
                else:
                    result = conn.execute(
                        text(
                            """
                            DELETE FROM sqlsentinel_executions
                            WHERE executed_at < :cutoff_date
                            """
                        ),
                        {"cutoff_date": cutoff_date},
                    )

                return result.rowcount or 0

        except SQLAlchemyError as e:
            raise ExecutionError(f"Failed to delete old executions: {e}") from e

    def get_statistics(self, alert_name: str, days: int = 7) -> dict[str, Any]:
        """Get execution statistics for an alert.

        Args:
            alert_name: Name of the alert
            days: Number of days to include in statistics

        Returns:
            Dictionary with statistics (total, alerts, errors, avg_duration_ms, etc.)

        Raises:
            ExecutionError: If database query fails
        """
        if days <= 0:
            raise ExecutionError("Days must be positive")

        try:
            with self.engine.connect() as conn:
                # Calculate cutoff date
                cutoff_date = datetime.utcnow()
                from datetime import timedelta

                cutoff_date = cutoff_date - timedelta(days=days)

                result = conn.execute(
                    text(
                        """
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN status = 'ALERT' THEN 1 ELSE 0 END) as alerts,
                            SUM(CASE WHEN status = 'OK' THEN 1 ELSE 0 END) as oks,
                            SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) as errors,
                            AVG(execution_duration_ms) as avg_duration_ms,
                            MIN(execution_duration_ms) as min_duration_ms,
                            MAX(execution_duration_ms) as max_duration_ms
                        FROM sqlsentinel_executions
                        WHERE alert_name = :alert_name
                        AND executed_at >= :cutoff_date
                        """
                    ),
                    {"alert_name": alert_name, "cutoff_date": cutoff_date},
                )

                row = result.fetchone()
                if row is None:
                    return {
                        "total": 0,
                        "alerts": 0,
                        "oks": 0,
                        "errors": 0,
                        "avg_duration_ms": 0.0,
                        "min_duration_ms": 0.0,
                        "max_duration_ms": 0.0,
                    }

                return {
                    "total": row[0] or 0,
                    "alerts": row[1] or 0,
                    "oks": row[2] or 0,
                    "errors": row[3] or 0,
                    "avg_duration_ms": round(row[4], 2) if row[4] else 0.0,
                    "min_duration_ms": round(row[5], 2) if row[5] else 0.0,
                    "max_duration_ms": round(row[6], 2) if row[6] else 0.0,
                }

        except SQLAlchemyError as e:
            raise ExecutionError(f"Failed to get execution statistics: {e}") from e
