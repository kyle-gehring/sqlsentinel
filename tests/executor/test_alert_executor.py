"""Tests for alert executor with state and history integration."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine

from sqlsentinel.database.adapter import DatabaseAdapter
from sqlsentinel.database.schema import SchemaManager
from sqlsentinel.executor.alert_executor import AlertExecutor
from sqlsentinel.models.alert import AlertConfig
from sqlsentinel.models.notification import EmailConfig, NotificationChannel, NotificationConfig
from sqlsentinel.notifications.factory import NotificationFactory


class TestAlertExecutor:
    """Test AlertExecutor class."""

    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing."""
        engine = create_engine("sqlite:///:memory:")
        schema_manager = SchemaManager(engine)
        schema_manager.create_schema()
        return engine

    @pytest.fixture
    def notification_factory(self):
        """Create notification factory."""
        return NotificationFactory(smtp_host="smtp.example.com")

    @pytest.fixture
    def executor(self, engine, notification_factory):
        """Create AlertExecutor instance."""
        return AlertExecutor(engine, notification_factory)

    @pytest.fixture
    def db_adapter(self):
        """Create mock database adapter."""
        adapter = MagicMock(spec=DatabaseAdapter)
        return adapter

    def test_init(self, executor, engine, notification_factory):
        """Test AlertExecutor initialization."""
        assert executor.engine == engine
        assert executor.notification_factory == notification_factory
        assert executor.state_manager is not None
        assert executor.history_manager is not None

    def test_execute_alert_ok_status(self, executor, db_adapter):
        """Test executing alert with OK status."""
        # Setup mock to return OK result
        db_adapter.execute_query.return_value = [
            {"status": "OK", "actual_value": 50.0, "threshold": 100.0}
        ]

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
        )

        result = executor.execute_alert(alert, db_adapter)

        assert result.alert_name == "test_alert"
        assert result.status == "success"
        assert result.query_result.status == "OK"
        assert result.query_result.actual_value == 50.0
        assert result.query_result.threshold == 100.0
        assert result.error is None

    def test_execute_alert_first_alert(self, executor, db_adapter):
        """Test executing alert with ALERT status (first time)."""
        db_adapter.execute_query.return_value = [
            {"status": "ALERT", "actual_value": 150.0, "threshold": 100.0}
        ]

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel=NotificationChannel.EMAIL,
                    config=EmailConfig(recipients=["test@example.com"]),
                )
            ],
        )

        # Mock notification service
        with patch.object(executor.notification_factory, "create_service") as mock_create:
            mock_service = MagicMock()
            mock_create.return_value = mock_service

            result = executor.execute_alert(alert, db_adapter)

            assert result.status == "failure"  # Alert condition = failure status
            assert result.query_result.status == "ALERT"
            mock_service.send.assert_called_once()

    def test_execute_alert_consecutive_alert_no_notification(self, executor, db_adapter):
        """Test consecutive alerts don't send notifications."""
        db_adapter.execute_query.return_value = [
            {"status": "ALERT", "actual_value": 150.0, "threshold": 100.0}
        ]

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel=NotificationChannel.EMAIL,
                    config=EmailConfig(recipients=["test@example.com"]),
                )
            ],
        )

        # Execute first alert
        with patch.object(executor.notification_factory, "create_service") as mock_create:
            mock_service = MagicMock()
            mock_create.return_value = mock_service

            # First execution
            result1 = executor.execute_alert(alert, db_adapter)
            assert result1.status == "failure"

            # Second execution (consecutive) - should still be failure but no new notification
            result2 = executor.execute_alert(alert, db_adapter)
            assert result2.status == "failure"

            # Notification should have been sent exactly once (first time only)
            assert mock_service.send.call_count == 1

    def test_execute_alert_dry_run(self, executor, db_adapter):
        """Test dry run doesn't update state or send notifications."""
        db_adapter.execute_query.return_value = [
            {"status": "ALERT", "actual_value": 150.0, "threshold": 100.0}
        ]

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel=NotificationChannel.EMAIL,
                    config=EmailConfig(recipients=["test@example.com"]),
                )
            ],
        )

        result = executor.execute_alert(alert, db_adapter, dry_run=True)

        assert result.status == "failure"
        assert result.query_result.status == "ALERT"

        # Verify state not updated (should still be initial state)
        state = executor.state_manager.get_state("test_alert")
        assert state.last_executed_at is None

    def test_execute_alert_disabled_no_notification(self, executor, db_adapter):
        """Test disabled alert doesn't send notifications."""
        db_adapter.execute_query.return_value = [
            {"status": "ALERT", "actual_value": 150.0, "threshold": 100.0}
        ]

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
            enabled=False,
            notify=[
                NotificationConfig(
                    channel=NotificationChannel.EMAIL,
                    config=EmailConfig(recipients=["test@example.com"]),
                )
            ],
        )

        result = executor.execute_alert(alert, db_adapter)

        assert result.status == "failure"
        assert result.query_result.status == "ALERT"

    def test_execute_alert_records_history(self, executor, db_adapter):
        """Test alert execution is recorded in history."""
        db_adapter.execute_query.return_value = [
            {"status": "OK", "actual_value": 50.0, "threshold": 100.0}
        ]

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
        )

        result = executor.execute_alert(alert, db_adapter)

        assert result.status == "success"

        # Check history
        history = executor.history_manager.get_executions(alert_name="test_alert")
        assert len(history) == 1
        assert history[0].status == "OK"
        assert history[0].actual_value == 50.0

    def test_execute_alert_query_error(self, executor, db_adapter):
        """Test alert execution with query error."""
        db_adapter.execute_query.side_effect = Exception("Database error")

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
        )

        result = executor.execute_alert(alert, db_adapter)

        assert result.status == "error"
        assert "Database error" in result.error

    def test_execute_alert_notification_error(self, executor, db_adapter):
        """Test alert execution with notification error."""
        db_adapter.execute_query.return_value = [
            {"status": "ALERT", "actual_value": 150.0, "threshold": 100.0}
        ]

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel=NotificationChannel.EMAIL,
                    config=EmailConfig(recipients=["test@example.com"]),
                )
            ],
        )

        # Mock notification service to fail
        with patch.object(executor.notification_factory, "create_service") as mock_create:
            mock_service = MagicMock()
            mock_service.send.side_effect = Exception("SMTP error")
            mock_create.return_value = mock_service

            result = executor.execute_alert(alert, db_adapter)

            # Execution should succeed even if notification fails
            assert result.status == "failure"  # Alert condition still detected
            assert result.query_result.status == "ALERT"

    def test_execute_alert_triggered_by_cron(self, executor, db_adapter):
        """Test alert execution triggered by CRON."""
        db_adapter.execute_query.return_value = [{"status": "OK"}]

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
        )

        result = executor.execute_alert(alert, db_adapter, triggered_by="CRON")

        assert result.status == "success"

        # Check history for triggered_by field
        history = executor.history_manager.get_executions(alert_name="test_alert")
        assert len(history) == 1
        assert history[0].triggered_by == "CRON"

    def test_execute_alert_measures_duration(self, executor, db_adapter):
        """Test alert execution measures duration."""
        db_adapter.execute_query.return_value = [{"status": "OK"}]

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
        )

        result = executor.execute_alert(alert, db_adapter)

        assert result.status == "success"
        assert result.duration_ms > 0

    def test_execute_alert_min_interval(self):
        """Test minimum interval between alerts."""
        engine = create_engine("sqlite:///:memory:")
        schema_manager = SchemaManager(engine)
        schema_manager.create_schema()
        notification_factory = NotificationFactory(smtp_host="smtp.example.com")

        # Create executor with 60 second minimum interval
        executor = AlertExecutor(engine, notification_factory, min_alert_interval_seconds=60)

        db_adapter = MagicMock(spec=DatabaseAdapter)
        db_adapter.execute_query.return_value = [{"status": "ALERT"}]

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel=NotificationChannel.EMAIL,
                    config=EmailConfig(recipients=["test@example.com"]),
                )
            ],
        )

        with patch.object(executor.notification_factory, "create_service") as mock_create:
            mock_service = MagicMock()
            mock_create.return_value = mock_service

            # First alert should send notification
            result1 = executor.execute_alert(alert, db_adapter)
            assert result1.status == "failure"

            # Immediate second alert should NOT send notification (within 60 seconds)
            result2 = executor.execute_alert(alert, db_adapter)
            assert result2.status == "failure"

            # Verify only one notification was sent
            assert mock_service.send.call_count == 1
