"""Alert state management for SQL Sentinel."""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..models.errors import ExecutionError

logger = logging.getLogger(__name__)


class AlertState:
    """Represents the current state of an alert."""

    def __init__(
        self,
        alert_name: str,
        last_executed_at: datetime | None = None,
        last_alert_at: datetime | None = None,
        last_ok_at: datetime | None = None,
        consecutive_alerts: int = 0,
        consecutive_oks: int = 0,
        current_status: str | None = None,
        silenced_until: datetime | None = None,
        escalation_count: int = 0,
        notification_failures: int = 0,
        last_notification_channel: str | None = None,
        updated_at: datetime | None = None,
    ):
        """Initialize alert state.

        Args:
            alert_name: Name of the alert
            last_executed_at: Timestamp of last execution
            last_alert_at: Timestamp of last ALERT status
            last_ok_at: Timestamp of last OK status
            consecutive_alerts: Number of consecutive ALERT statuses
            consecutive_oks: Number of consecutive OK statuses
            current_status: Current status (ALERT, OK, ERROR)
            silenced_until: Timestamp until which alert is silenced
            escalation_count: Number of times alert has been escalated
            notification_failures: Number of consecutive notification failures
            last_notification_channel: Last channel used for notification
            updated_at: Timestamp of last state update
        """
        self.alert_name = alert_name
        self.last_executed_at = last_executed_at
        self.last_alert_at = last_alert_at
        self.last_ok_at = last_ok_at
        self.consecutive_alerts = consecutive_alerts
        self.consecutive_oks = consecutive_oks
        self.current_status = current_status
        self.silenced_until = silenced_until
        self.escalation_count = escalation_count
        self.notification_failures = notification_failures
        self.last_notification_channel = last_notification_channel
        self.updated_at = updated_at or datetime.utcnow()

    def is_silenced(self) -> bool:
        """Check if alert is currently silenced.

        Returns:
            True if alert is silenced, False otherwise
        """
        if self.silenced_until is None:
            return False
        return datetime.utcnow() < self.silenced_until

    def should_escalate(self, escalation_threshold: int = 3) -> bool:
        """Determine if alert should be escalated.

        Args:
            escalation_threshold: Number of consecutive alerts before escalation

        Returns:
            True if alert should be escalated, False otherwise
        """
        return self.consecutive_alerts >= escalation_threshold

    def should_notify(self, new_status: str, min_interval_seconds: int = 0) -> bool:
        """Determine if notification should be sent based on state.

        Args:
            new_status: New status (ALERT, OK, ERROR)
            min_interval_seconds: Minimum seconds between alerts (0 = no limit)

        Returns:
            True if notification should be sent, False otherwise
        """
        # Don't notify if silenced
        if self.is_silenced():
            return False

        # Don't notify for OK status
        if new_status != "ALERT":
            return False

        # Don't notify for ERROR status
        if new_status == "ERROR":
            return False

        # Check minimum interval
        if min_interval_seconds > 0 and self.last_alert_at:
            time_since_last_alert = datetime.utcnow() - self.last_alert_at
            if time_since_last_alert.total_seconds() < min_interval_seconds:
                return False

        # Always notify on first alert or status change from OK to ALERT
        if self.current_status != "ALERT":
            return True

        # For consecutive alerts, only notify on first one (already handled above)
        return False


class StateManager:
    """Manages alert execution state in database."""

    def __init__(self, engine: Engine):
        """Initialize state manager.

        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine

    def _parse_datetime(self, value: Any) -> datetime | None:
        """Parse datetime from database (handles string and datetime types).

        Args:
            value: Value from database (could be string or datetime)

        Returns:
            datetime object or None
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Parse ISO format datetime strings from SQLite
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return None

    def get_state(self, alert_name: str) -> AlertState:
        """Get current state for an alert.

        Args:
            alert_name: Name of the alert

        Returns:
            AlertState instance (new state if not found in database)

        Raises:
            ExecutionError: If database query fails
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        SELECT
                            alert_name,
                            last_executed_at,
                            last_alert_at,
                            last_ok_at,
                            consecutive_alerts,
                            consecutive_oks,
                            current_status,
                            silenced_until,
                            escalation_count,
                            notification_failures,
                            last_notification_channel,
                            updated_at
                        FROM sqlsentinel_state
                        WHERE alert_name = :alert_name
                        """
                    ),
                    {"alert_name": alert_name},
                )
                row = result.fetchone()

                if row is None:
                    # Return new state if not found
                    return AlertState(alert_name=alert_name)

                return AlertState(
                    alert_name=row[0],
                    last_executed_at=self._parse_datetime(row[1]),
                    last_alert_at=self._parse_datetime(row[2]),
                    last_ok_at=self._parse_datetime(row[3]),
                    consecutive_alerts=row[4],
                    consecutive_oks=row[5],
                    current_status=row[6],
                    silenced_until=self._parse_datetime(row[7]),
                    escalation_count=row[8] if row[8] is not None else 0,
                    notification_failures=row[9] if row[9] is not None else 0,
                    last_notification_channel=row[10],
                    updated_at=self._parse_datetime(row[11]),
                )
        except SQLAlchemyError as e:
            raise ExecutionError(f"Failed to get alert state: {e}") from e

    def update_state(
        self,
        state: AlertState,
        new_status: str,
        notification_channel: str | None = None,
    ) -> None:
        """Update alert state based on new execution status.

        Args:
            state: Current alert state
            new_status: New status (ALERT, OK, ERROR)
            notification_channel: Channel used for notification (if any)

        Raises:
            ExecutionError: If database update fails
        """
        now = datetime.utcnow()

        # Log state transition
        if state.current_status != new_status:
            logger.info(
                f"State transition for alert '{state.alert_name}': "
                f"{state.current_status} -> {new_status}"
            )

        # Update consecutive counts
        last_alert_at: datetime | None
        last_ok_at: datetime | None
        if new_status == "ALERT":
            consecutive_alerts = state.consecutive_alerts + 1
            consecutive_oks = 0
            last_alert_at = now
            last_ok_at = state.last_ok_at
            logger.debug(f"Alert '{state.alert_name}' consecutive alerts: {consecutive_alerts}")
        elif new_status == "OK":
            consecutive_alerts = 0
            consecutive_oks = state.consecutive_oks + 1
            last_alert_at = state.last_alert_at
            last_ok_at = now
            logger.debug(f"Alert '{state.alert_name}' consecutive OKs: {consecutive_oks}")
        else:  # ERROR
            consecutive_alerts = state.consecutive_alerts
            consecutive_oks = state.consecutive_oks
            last_alert_at = state.last_alert_at
            last_ok_at = state.last_ok_at
            logger.warning(f"Alert '{state.alert_name}' execution error")

        try:
            with self.engine.begin() as conn:
                # Try to update existing record
                result = conn.execute(
                    text(
                        """
                        UPDATE sqlsentinel_state
                        SET
                            last_executed_at = :last_executed_at,
                            last_alert_at = :last_alert_at,
                            last_ok_at = :last_ok_at,
                            consecutive_alerts = :consecutive_alerts,
                            consecutive_oks = :consecutive_oks,
                            current_status = :current_status,
                            last_notification_channel = :last_notification_channel,
                            updated_at = :updated_at
                        WHERE alert_name = :alert_name
                        """
                    ),
                    {
                        "alert_name": state.alert_name,
                        "last_executed_at": now,
                        "last_alert_at": last_alert_at,
                        "last_ok_at": last_ok_at,
                        "consecutive_alerts": consecutive_alerts,
                        "consecutive_oks": consecutive_oks,
                        "current_status": new_status,
                        "last_notification_channel": notification_channel,
                        "updated_at": now,
                    },
                )

                # If no rows updated, insert new record
                if result.rowcount == 0:
                    conn.execute(
                        text(
                            """
                            INSERT INTO sqlsentinel_state (
                                alert_name,
                                last_executed_at,
                                last_alert_at,
                                last_ok_at,
                                consecutive_alerts,
                                consecutive_oks,
                                current_status,
                                silenced_until,
                                escalation_count,
                                notification_failures,
                                last_notification_channel,
                                updated_at
                            ) VALUES (
                                :alert_name,
                                :last_executed_at,
                                :last_alert_at,
                                :last_ok_at,
                                :consecutive_alerts,
                                :consecutive_oks,
                                :current_status,
                                :silenced_until,
                                0,
                                0,
                                :last_notification_channel,
                                :updated_at
                            )
                            """
                        ),
                        {
                            "alert_name": state.alert_name,
                            "last_executed_at": now,
                            "last_alert_at": last_alert_at,
                            "last_ok_at": last_ok_at,
                            "consecutive_alerts": consecutive_alerts,
                            "consecutive_oks": consecutive_oks,
                            "current_status": new_status,
                            "silenced_until": None,
                            "last_notification_channel": notification_channel,
                            "updated_at": now,
                        },
                    )

        except SQLAlchemyError as e:
            logger.error(f"Failed to update state for alert '{state.alert_name}': {e}")
            raise ExecutionError(f"Failed to update alert state: {e}") from e

    def silence_alert(self, alert_name: str, duration_seconds: int) -> None:
        """Silence an alert for a specified duration.

        Args:
            alert_name: Name of the alert to silence
            duration_seconds: Duration in seconds to silence the alert

        Raises:
            ExecutionError: If database update fails
        """
        if duration_seconds <= 0:
            raise ExecutionError("Silence duration must be positive")

        silenced_until = datetime.utcnow() + timedelta(seconds=duration_seconds)

        try:
            with self.engine.begin() as conn:
                # Update or insert with silenced_until
                result = conn.execute(
                    text(
                        """
                        UPDATE sqlsentinel_state
                        SET
                            silenced_until = :silenced_until,
                            updated_at = :updated_at
                        WHERE alert_name = :alert_name
                        """
                    ),
                    {
                        "alert_name": alert_name,
                        "silenced_until": silenced_until,
                        "updated_at": datetime.utcnow(),
                    },
                )

                # If no rows updated, insert new record
                if result.rowcount == 0:
                    conn.execute(
                        text(
                            """
                            INSERT INTO sqlsentinel_state (
                                alert_name,
                                last_executed_at,
                                last_alert_at,
                                last_ok_at,
                                consecutive_alerts,
                                consecutive_oks,
                                current_status,
                                silenced_until,
                                escalation_count,
                                notification_failures,
                                last_notification_channel,
                                updated_at
                            ) VALUES (
                                :alert_name,
                                NULL,
                                NULL,
                                NULL,
                                0,
                                0,
                                NULL,
                                :silenced_until,
                                0,
                                0,
                                NULL,
                                :updated_at
                            )
                            """
                        ),
                        {
                            "alert_name": alert_name,
                            "silenced_until": silenced_until,
                            "updated_at": datetime.utcnow(),
                        },
                    )

        except SQLAlchemyError as e:
            raise ExecutionError(f"Failed to silence alert: {e}") from e

    def unsilence_alert(self, alert_name: str) -> None:
        """Remove silence from an alert.

        Args:
            alert_name: Name of the alert to unsilence

        Raises:
            ExecutionError: If database update fails
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE sqlsentinel_state
                        SET
                            silenced_until = NULL,
                            updated_at = :updated_at
                        WHERE alert_name = :alert_name
                        """
                    ),
                    {
                        "alert_name": alert_name,
                        "updated_at": datetime.utcnow(),
                    },
                )
        except SQLAlchemyError as e:
            raise ExecutionError(f"Failed to unsilence alert: {e}") from e

    def record_notification_failure(self, alert_name: str) -> None:
        """Record a notification failure for an alert.

        Args:
            alert_name: Name of the alert

        Raises:
            ExecutionError: If database update fails
        """
        try:
            with self.engine.begin() as conn:
                state = self.get_state(alert_name)
                new_failure_count = state.notification_failures + 1

                logger.warning(
                    f"Notification failure for alert '{alert_name}' "
                    f"(total failures: {new_failure_count})"
                )

                conn.execute(
                    text(
                        """
                        UPDATE sqlsentinel_state
                        SET
                            notification_failures = :notification_failures,
                            updated_at = :updated_at
                        WHERE alert_name = :alert_name
                        """
                    ),
                    {
                        "alert_name": alert_name,
                        "notification_failures": new_failure_count,
                        "updated_at": datetime.utcnow(),
                    },
                )
        except SQLAlchemyError as e:
            logger.error(f"Failed to record notification failure for '{alert_name}': {e}")
            raise ExecutionError(f"Failed to record notification failure: {e}") from e

    def record_notification_success(self, alert_name: str) -> None:
        """Reset notification failure count after successful notification.

        Args:
            alert_name: Name of the alert

        Raises:
            ExecutionError: If database update fails
        """
        try:
            with self.engine.begin() as conn:
                logger.debug(f"Notification succeeded for alert '{alert_name}'")

                conn.execute(
                    text(
                        """
                        UPDATE sqlsentinel_state
                        SET
                            notification_failures = 0,
                            updated_at = :updated_at
                        WHERE alert_name = :alert_name
                        """
                    ),
                    {
                        "alert_name": alert_name,
                        "updated_at": datetime.utcnow(),
                    },
                )
        except SQLAlchemyError as e:
            logger.error(f"Failed to record notification success for '{alert_name}': {e}")
            raise ExecutionError(f"Failed to record notification success: {e}") from e

    def record_escalation(self, alert_name: str) -> None:
        """Increment escalation counter for an alert.

        Args:
            alert_name: Name of the alert

        Raises:
            ExecutionError: If database update fails
        """
        try:
            with self.engine.begin() as conn:
                state = self.get_state(alert_name)
                new_escalation_count = state.escalation_count + 1

                logger.info(
                    f"Alert '{alert_name}' escalated " f"(escalation count: {new_escalation_count})"
                )

                conn.execute(
                    text(
                        """
                        UPDATE sqlsentinel_state
                        SET
                            escalation_count = :escalation_count,
                            updated_at = :updated_at
                        WHERE alert_name = :alert_name
                        """
                    ),
                    {
                        "alert_name": alert_name,
                        "escalation_count": new_escalation_count,
                        "updated_at": datetime.utcnow(),
                    },
                )
        except SQLAlchemyError as e:
            logger.error(f"Failed to record escalation for '{alert_name}': {e}")
            raise ExecutionError(f"Failed to record escalation: {e}") from e

    def delete_state(self, alert_name: str) -> None:
        """Delete state for an alert.

        Args:
            alert_name: Name of the alert

        Raises:
            ExecutionError: If database delete fails
        """
        try:
            with self.engine.begin() as conn:
                logger.info(f"Deleting state for alert '{alert_name}'")
                conn.execute(
                    text(
                        """
                        DELETE FROM sqlsentinel_state
                        WHERE alert_name = :alert_name
                        """
                    ),
                    {"alert_name": alert_name},
                )
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete state for alert '{alert_name}': {e}")
            raise ExecutionError(f"Failed to delete alert state: {e}") from e
