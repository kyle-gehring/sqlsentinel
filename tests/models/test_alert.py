"""Tests for alert models."""

import pytest
from pydantic import ValidationError

from sqlsentinel.models.alert import AlertConfig, ExecutionResult, QueryResult
from sqlsentinel.models.notification import NotificationConfig


class TestAlertConfig:
    """Tests for AlertConfig model."""

    def test_valid_alert_config(self, sample_alert_config):
        """Test valid alert configuration."""
        config = AlertConfig(**sample_alert_config)
        assert config.name == "test_alert"
        assert config.description == "Test alert description"
        assert config.enabled is True
        assert len(config.notify) == 0

    def test_alert_config_with_notifications(self, sample_alert_config, sample_email_notification):
        """Test alert config with notifications."""
        sample_alert_config["notify"] = [sample_email_notification]
        config = AlertConfig(**sample_alert_config)
        assert len(config.notify) == 1
        assert isinstance(config.notify[0], NotificationConfig)

    def test_query_validation(self, sample_alert_config):
        """Test query validation strips whitespace."""
        sample_alert_config["query"] = "  SELECT 'ALERT' as status  "
        config = AlertConfig(**sample_alert_config)
        assert config.query == "SELECT 'ALERT' as status"

    def test_empty_query(self, sample_alert_config):
        """Test empty query fails validation."""
        sample_alert_config["query"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            AlertConfig(**sample_alert_config)
        assert "Query cannot be empty" in str(exc_info.value)

    def test_invalid_cron_schedule(self, sample_alert_config):
        """Test invalid cron schedule fails validation."""
        sample_alert_config["schedule"] = "invalid cron"
        with pytest.raises(ValidationError) as exc_info:
            AlertConfig(**sample_alert_config)
        assert "Invalid cron schedule" in str(exc_info.value)

    def test_valid_cron_schedules(self, sample_alert_config):
        """Test various valid cron schedules."""
        valid_schedules = [
            "0 9 * * *",  # Daily at 9am
            "*/15 * * * *",  # Every 15 minutes
            "0 0 * * 0",  # Weekly on Sunday at midnight
            "0 0 1 * *",  # Monthly on the 1st at midnight
        ]
        for schedule in valid_schedules:
            sample_alert_config["schedule"] = schedule
            config = AlertConfig(**sample_alert_config)
            assert config.schedule == schedule

    def test_disabled_alert(self, sample_alert_config):
        """Test disabled alert."""
        sample_alert_config["enabled"] = False
        config = AlertConfig(**sample_alert_config)
        assert config.enabled is False


class TestQueryResult:
    """Tests for QueryResult model."""

    def test_alert_status(self):
        """Test query result with ALERT status."""
        result = QueryResult(
            status="ALERT", actual_value=100, threshold=50, context={"metric": "revenue"}
        )
        assert result.status == "ALERT"
        assert result.actual_value == 100
        assert result.threshold == 50
        assert result.context["metric"] == "revenue"

    def test_ok_status(self):
        """Test query result with OK status."""
        result = QueryResult(status="OK")
        assert result.status == "OK"
        assert result.actual_value is None
        assert result.threshold is None

    def test_status_normalization(self):
        """Test that status is normalized to uppercase."""
        result = QueryResult(status="alert")
        assert result.status == "ALERT"

    def test_invalid_status(self):
        """Test invalid status fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            QueryResult(status="INVALID")
        assert "Status must be 'ALERT' or 'OK'" in str(exc_info.value)

    def test_query_result_with_context(self):
        """Test query result with additional context."""
        result = QueryResult(
            status="ALERT",
            actual_value=500,
            threshold=1000,
            context={"region": "US", "product": "Widget", "percentage": 50.0},
        )
        assert result.context["region"] == "US"
        assert result.context["product"] == "Widget"
        assert result.context["percentage"] == 50.0


class TestExecutionResult:
    """Tests for ExecutionResult model."""

    def test_successful_execution(self):
        """Test successful execution result."""
        query_result = QueryResult(status="ALERT", actual_value=100, threshold=50)
        result = ExecutionResult(
            alert_name="test_alert",
            timestamp="2025-01-01T09:00:00Z",
            status="success",
            query_result=query_result,
            duration_ms=125.5,
        )
        assert result.alert_name == "test_alert"
        assert result.status == "success"
        assert result.query_result is not None
        assert result.duration_ms == 125.5
        assert result.error is None

    def test_failed_execution(self):
        """Test failed execution result."""
        result = ExecutionResult(
            alert_name="test_alert",
            timestamp="2025-01-01T09:00:00Z",
            status="failure",
            query_result=None,
            duration_ms=50.0,
            error="Connection timeout",
        )
        assert result.status == "failure"
        assert result.query_result is None
        assert result.error == "Connection timeout"

    def test_error_execution(self):
        """Test execution with error."""
        result = ExecutionResult(
            alert_name="test_alert",
            timestamp="2025-01-01T09:00:00Z",
            status="error",
            query_result=None,
            duration_ms=10.0,
            error="Invalid SQL syntax",
        )
        assert result.status == "error"
        assert result.error == "Invalid SQL syntax"

    def test_status_normalization(self):
        """Test that status is normalized to lowercase."""
        result = ExecutionResult(
            alert_name="test_alert",
            timestamp="2025-01-01T09:00:00Z",
            status="SUCCESS",
            duration_ms=100.0,
        )
        assert result.status == "success"

    def test_invalid_status(self):
        """Test invalid status fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ExecutionResult(
                alert_name="test_alert",
                timestamp="2025-01-01T09:00:00Z",
                status="invalid",
                duration_ms=100.0,
            )
        assert "Status must be 'success', 'failure', or 'error'" in str(exc_info.value)
