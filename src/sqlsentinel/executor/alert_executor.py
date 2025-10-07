"""Alert executor with state and history integration."""

import time
from datetime import datetime
from typing import Optional

from sqlalchemy.engine import Engine

from ..database.adapter import DatabaseAdapter
from ..models.alert import AlertConfig, ExecutionResult, QueryResult
from ..models.errors import ExecutionError, NotificationError
from ..notifications.factory import NotificationFactory
from .history import ExecutionHistory, ExecutionRecord
from .query import QueryExecutor
from .state import StateManager


class AlertExecutor:
    """Executes alerts with full state management and history tracking."""

    def __init__(
        self,
        engine: Engine,
        notification_factory: NotificationFactory,
        min_alert_interval_seconds: int = 0,
    ):
        """Initialize alert executor.

        Args:
            engine: SQLAlchemy engine for state/history database
            notification_factory: Factory for creating notification services
            min_alert_interval_seconds: Minimum seconds between alert notifications (0 = no limit)
        """
        self.engine = engine
        self.state_manager = StateManager(engine)
        self.history_manager = ExecutionHistory(engine)
        self.notification_factory = notification_factory
        self.min_alert_interval_seconds = min_alert_interval_seconds

    def execute_alert(
        self,
        alert: AlertConfig,
        db_adapter: DatabaseAdapter,
        triggered_by: str = "MANUAL",
        dry_run: bool = False,
    ) -> ExecutionResult:
        """Execute an alert with full workflow.

        Workflow:
        1. Get current alert state
        2. Execute query
        3. Update state
        4. Record execution in history
        5. Send notifications if needed

        Args:
            alert: Alert configuration
            db_adapter: Database adapter for executing alert query
            triggered_by: What triggered this execution (CRON, MANUAL, API)
            dry_run: If True, don't send notifications or update state

        Returns:
            ExecutionResult with status and metadata

        Raises:
            ExecutionError: If execution fails
        """
        start_time = time.time()
        query_result: Optional[QueryResult] = None
        error_message: Optional[str] = None
        notification_sent = False
        notification_error: Optional[str] = None

        try:
            # Step 1: Get current state
            state = self.state_manager.get_state(alert.name)

            # Step 2: Execute query
            executor = QueryExecutor(db_adapter)
            query_result = executor.execute(alert.query)

            # Step 3: Determine if we should notify
            should_notify = state.should_notify(
                query_result.status,
                min_interval_seconds=self.min_alert_interval_seconds,
            )

            # Step 4: Send notifications if needed
            if should_notify and not dry_run and alert.enabled:
                for notification_config in alert.notify:
                    try:
                        service = self.notification_factory.create_service(
                            notification_config.channel
                        )
                        service.send(alert, query_result, notification_config)
                        notification_sent = True
                    except (NotificationError, Exception) as e:
                        notification_error = str(e)
                        # Log error but continue - notification failure doesn't fail the alert
                        pass

            # Step 5: Update state (unless dry run)
            if not dry_run:
                self.state_manager.update_state(state, query_result.status)

        except (ExecutionError, Exception) as e:
            error_message = str(e)
            query_result = None

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Step 6: Record in history (unless dry run)
        if not dry_run:
            record = ExecutionRecord(
                alert_name=alert.name,
                executed_at=datetime.utcnow(),
                execution_duration_ms=duration_ms,
                status=query_result.status if query_result else "ERROR",
                query=alert.query,
                triggered_by=triggered_by,
                actual_value=query_result.actual_value if query_result else None,
                threshold=query_result.threshold if query_result else None,
                error_message=error_message,
                notification_sent=notification_sent,
                notification_error=notification_error,
                context_data=query_result.context if query_result else {},
            )
            self.history_manager.record_execution(record)

        # Map query status to execution status
        if error_message:
            exec_status = "error"
        elif query_result and query_result.status == "ALERT":
            exec_status = "failure"  # Alert condition met = failure state
        else:
            exec_status = "success"

        # Return execution result
        return ExecutionResult(
            alert_name=alert.name,
            timestamp=datetime.utcnow().isoformat(),
            status=exec_status,
            query_result=query_result,
            duration_ms=duration_ms,
            error=error_message,
        )
