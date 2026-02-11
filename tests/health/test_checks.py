"""Tests for health check functions."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from sqlsentinel.health.checks import (
    HealthCheckError,
    check_database,
    check_scheduler,
    check_notifications,
    aggregate_health_status,
)
from sqlsentinel.models.notification import NotificationChannel


class TestHealthCheckError:
    """Test HealthCheckError exception."""

    def test_raise_health_check_error(self):
        """Test raising HealthCheckError."""
        with pytest.raises(HealthCheckError, match="Test error"):
            raise HealthCheckError("Test error")


class TestCheckDatabase:
    """Test check_database function."""

    def test_check_database_healthy(self):
        """Test database health check when database is healthy."""
        # Mock engine and connection
        mock_engine = Mock(spec=Engine)
        mock_conn = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_conn
        mock_context.__exit__.return_value = None
        mock_engine.connect.return_value = mock_context

        result = check_database(mock_engine)

        assert result["status"] == "healthy"
        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], (int, float))
        assert result["latency_ms"] >= 0
        assert result["message"] == "Database connection OK"
        mock_conn.execute.assert_called_once()

    def test_check_database_unhealthy_connection_error(self):
        """Test database health check when connection fails."""
        mock_engine = Mock(spec=Engine)
        mock_engine.connect.side_effect = OperationalError("Connection failed", None, None)

        result = check_database(mock_engine)

        assert result["status"] == "unhealthy"
        assert result["latency_ms"] is None
        assert "Connection failed" in result["message"]

    def test_check_database_unhealthy_execution_error(self):
        """Test database health check when query execution fails."""
        mock_engine = Mock(spec=Engine)
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Query execution failed")
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_conn
        mock_context.__exit__.return_value = None
        mock_engine.connect.return_value = mock_context

        result = check_database(mock_engine)

        assert result["status"] == "unhealthy"
        assert result["latency_ms"] is None
        assert "Query execution failed" in result["message"]

    def test_check_database_measures_latency(self):
        """Test that database check measures latency."""
        mock_engine = Mock(spec=Engine)
        mock_conn = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_conn
        mock_context.__exit__.return_value = None
        mock_engine.connect.return_value = mock_context

        with patch("time.time", side_effect=[0.0, 0.150]):  # 150ms
            result = check_database(mock_engine)

        assert result["status"] == "healthy"
        assert result["latency_ms"] == 150.0


class TestCheckScheduler:
    """Test check_scheduler function."""

    def test_check_scheduler_healthy_with_jobs(self):
        """Test scheduler health check when scheduler is running with jobs."""
        mock_scheduler_service = Mock()
        mock_scheduler_service.scheduler.running = True
        mock_job1 = Mock()
        mock_job2 = Mock()
        mock_scheduler_service.scheduler.get_jobs.return_value = [mock_job1, mock_job2]

        result = check_scheduler(mock_scheduler_service)

        assert result["status"] == "healthy"
        assert result["jobs_count"] == 2
        assert result["message"] == "2 jobs scheduled"

    def test_check_scheduler_healthy_no_jobs(self):
        """Test scheduler health check when scheduler is running but no jobs."""
        mock_scheduler_service = Mock()
        mock_scheduler_service.scheduler.running = True
        mock_scheduler_service.scheduler.get_jobs.return_value = []

        result = check_scheduler(mock_scheduler_service)

        assert result["status"] == "healthy"
        assert result["jobs_count"] == 0
        assert result["message"] == "0 jobs scheduled"

    def test_check_scheduler_not_initialized(self):
        """Test scheduler health check when scheduler is None."""
        result = check_scheduler(None)

        assert result["status"] == "unhealthy"
        assert result["jobs_count"] == 0
        assert result["message"] == "Scheduler not initialized"

    def test_check_scheduler_not_running(self):
        """Test scheduler health check when scheduler is not running."""
        mock_scheduler_service = Mock()
        mock_scheduler_service.scheduler.running = False

        result = check_scheduler(mock_scheduler_service)

        assert result["status"] == "degraded"
        assert result["jobs_count"] == 0
        assert result["message"] == "Scheduler is not running"

    def test_check_scheduler_exception(self):
        """Test scheduler health check when exception occurs."""
        mock_scheduler_service = Mock()
        mock_scheduler_service.scheduler.running = True
        mock_scheduler_service.scheduler.get_jobs.side_effect = Exception("Scheduler error")

        result = check_scheduler(mock_scheduler_service)

        assert result["status"] == "degraded"
        assert result["jobs_count"] == 0
        assert "Scheduler check failed" in result["message"]
        assert "Scheduler error" in result["message"]


class TestCheckNotifications:
    """Test check_notifications function."""

    def test_check_notifications_all_healthy(self):
        """Test notification health check when all channels are configured."""
        mock_factory = Mock()
        mock_email = Mock()
        mock_slack = Mock()
        mock_webhook = Mock()

        def create_service(channel):
            if channel == NotificationChannel.EMAIL:
                return mock_email
            elif channel == NotificationChannel.SLACK:
                return mock_slack
            elif channel == NotificationChannel.WEBHOOK:
                return mock_webhook

        mock_factory.create_service.side_effect = create_service

        result = check_notifications(mock_factory)

        assert result["status"] == "healthy"
        assert result["channels"]["email"]["status"] == "healthy"
        assert result["channels"]["slack"]["status"] == "healthy"
        assert result["channels"]["webhook"]["status"] == "healthy"

    def test_check_notifications_email_not_configured(self):
        """Test notification health check when email is not configured."""
        mock_factory = Mock()

        def create_service(channel):
            if channel == NotificationChannel.EMAIL:
                raise ValueError("Email not configured")
            elif channel == NotificationChannel.SLACK:
                return Mock()
            elif channel == NotificationChannel.WEBHOOK:
                return Mock()

        mock_factory.create_service.side_effect = create_service

        result = check_notifications(mock_factory)

        assert result["status"] == "healthy"
        assert result["channels"]["email"]["status"] == "not_configured"
        assert result["channels"]["slack"]["status"] == "healthy"
        assert result["channels"]["webhook"]["status"] == "healthy"

    def test_check_notifications_slack_not_configured(self):
        """Test notification health check when slack is not configured."""
        mock_factory = Mock()

        def create_service(channel):
            if channel == NotificationChannel.EMAIL:
                return Mock()
            elif channel == NotificationChannel.SLACK:
                raise ValueError("Slack not configured")
            elif channel == NotificationChannel.WEBHOOK:
                return Mock()

        mock_factory.create_service.side_effect = create_service

        result = check_notifications(mock_factory)

        assert result["status"] == "healthy"
        assert result["channels"]["email"]["status"] == "healthy"
        assert result["channels"]["slack"]["status"] == "not_configured"
        assert result["channels"]["webhook"]["status"] == "healthy"

    def test_check_notifications_webhook_not_configured(self):
        """Test notification health check when webhook is not configured."""
        mock_factory = Mock()

        def create_service(channel):
            if channel == NotificationChannel.EMAIL:
                return Mock()
            elif channel == NotificationChannel.SLACK:
                return Mock()
            elif channel == NotificationChannel.WEBHOOK:
                raise ValueError("Webhook not configured")

        mock_factory.create_service.side_effect = create_service

        result = check_notifications(mock_factory)

        assert result["status"] == "healthy"
        assert result["channels"]["email"]["status"] == "healthy"
        assert result["channels"]["slack"]["status"] == "healthy"
        assert result["channels"]["webhook"]["status"] == "not_configured"

    def test_check_notifications_all_not_configured(self):
        """Test notification health check when all channels are not configured."""
        mock_factory = Mock()
        mock_factory.create_service.side_effect = ValueError("Not configured")

        result = check_notifications(mock_factory)

        assert result["status"] == "healthy"
        assert result["channels"]["email"]["status"] == "not_configured"
        assert result["channels"]["slack"]["status"] == "not_configured"
        assert result["channels"]["webhook"]["status"] == "not_configured"

    def test_check_notifications_email_error(self):
        """Test notification health check when email has error."""
        mock_factory = Mock()

        def create_service(channel):
            if channel == NotificationChannel.EMAIL:
                raise RuntimeError("Email service error")
            elif channel == NotificationChannel.SLACK:
                return Mock()
            elif channel == NotificationChannel.WEBHOOK:
                return Mock()

        mock_factory.create_service.side_effect = create_service

        result = check_notifications(mock_factory)

        assert result["status"] == "healthy"
        assert result["channels"]["email"]["status"] == "unhealthy"
        assert "Email service error" in result["channels"]["email"]["message"]
        assert result["channels"]["slack"]["status"] == "healthy"
        assert result["channels"]["webhook"]["status"] == "healthy"

    def test_check_notifications_slack_error(self):
        """Test notification health check when slack has error."""
        mock_factory = Mock()

        def create_service(channel):
            if channel == NotificationChannel.EMAIL:
                return Mock()
            elif channel == NotificationChannel.SLACK:
                raise RuntimeError("Slack service error")
            elif channel == NotificationChannel.WEBHOOK:
                return Mock()

        mock_factory.create_service.side_effect = create_service

        result = check_notifications(mock_factory)

        assert result["status"] == "healthy"
        assert result["channels"]["email"]["status"] == "healthy"
        assert result["channels"]["slack"]["status"] == "unhealthy"
        assert "Slack service error" in result["channels"]["slack"]["message"]
        assert result["channels"]["webhook"]["status"] == "healthy"

    def test_check_notifications_webhook_error(self):
        """Test notification health check when webhook has error."""
        mock_factory = Mock()

        def create_service(channel):
            if channel == NotificationChannel.EMAIL:
                return Mock()
            elif channel == NotificationChannel.SLACK:
                return Mock()
            elif channel == NotificationChannel.WEBHOOK:
                raise RuntimeError("Webhook service error")

        mock_factory.create_service.side_effect = create_service

        result = check_notifications(mock_factory)

        assert result["status"] == "healthy"
        assert result["channels"]["email"]["status"] == "healthy"
        assert result["channels"]["slack"]["status"] == "healthy"
        assert result["channels"]["webhook"]["status"] == "unhealthy"
        assert "Webhook service error" in result["channels"]["webhook"]["message"]

    def test_check_notifications_factory_exception(self):
        """Test notification health check when factory itself fails."""
        mock_factory = Mock()
        mock_factory.create_service.side_effect = Exception("Factory error")

        result = check_notifications(mock_factory)

        # The function should handle the exception gracefully
        assert result["status"] in ["healthy", "degraded"]
        assert "channels" in result

    def test_check_notifications_returns_none_for_unconfigured(self):
        """Test notification health check when factory returns None."""
        mock_factory = Mock()

        def create_service(channel):
            return None  # Returns None when not configured

        mock_factory.create_service.side_effect = create_service

        result = check_notifications(mock_factory)

        assert result["status"] == "healthy"
        assert result["channels"]["email"]["status"] == "not_configured"
        assert result["channels"]["slack"]["status"] == "not_configured"
        assert result["channels"]["webhook"]["status"] == "not_configured"


class TestAggregateHealthStatus:
    """Test aggregate_health_status function."""

    def test_aggregate_all_healthy(self):
        """Test aggregation when all checks are healthy."""
        checks = {
            "database": {"status": "healthy"},
            "scheduler": {"status": "healthy"},
            "notifications": {"status": "healthy"},
        }

        result = aggregate_health_status(checks)

        assert result == "healthy"

    def test_aggregate_one_unhealthy(self):
        """Test aggregation when one check is unhealthy."""
        checks = {
            "database": {"status": "unhealthy"},
            "scheduler": {"status": "healthy"},
            "notifications": {"status": "healthy"},
        }

        result = aggregate_health_status(checks)

        assert result == "unhealthy"

    def test_aggregate_multiple_unhealthy(self):
        """Test aggregation when multiple checks are unhealthy."""
        checks = {
            "database": {"status": "unhealthy"},
            "scheduler": {"status": "unhealthy"},
            "notifications": {"status": "healthy"},
        }

        result = aggregate_health_status(checks)

        assert result == "unhealthy"

    def test_aggregate_one_degraded(self):
        """Test aggregation when one check is degraded."""
        checks = {
            "database": {"status": "healthy"},
            "scheduler": {"status": "degraded"},
            "notifications": {"status": "healthy"},
        }

        result = aggregate_health_status(checks)

        assert result == "degraded"

    def test_aggregate_unhealthy_takes_priority_over_degraded(self):
        """Test that unhealthy takes priority over degraded."""
        checks = {
            "database": {"status": "unhealthy"},
            "scheduler": {"status": "degraded"},
            "notifications": {"status": "healthy"},
        }

        result = aggregate_health_status(checks)

        assert result == "unhealthy"

    def test_aggregate_empty_checks(self):
        """Test aggregation with empty checks dictionary."""
        checks = {}

        result = aggregate_health_status(checks)

        assert result == "healthy"

    def test_aggregate_mixed_statuses(self):
        """Test aggregation with mixed statuses."""
        checks = {
            "database": {"status": "healthy"},
            "scheduler": {"status": "degraded"},
            "notifications": {"status": "healthy"},
            "cache": {"status": "healthy"},
        }

        result = aggregate_health_status(checks)

        assert result == "degraded"
