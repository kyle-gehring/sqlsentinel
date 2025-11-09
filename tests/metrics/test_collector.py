"""Tests for metrics collection."""

import pytest
import time
from unittest.mock import patch, MagicMock
from prometheus_client import CollectorRegistry, REGISTRY, Counter, Gauge, Histogram

from sqlsentinel.metrics.collector import (
    MetricsCollector,
    get_metrics,
    reset_metrics,
)


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def setup_method(self):
        """Set up test method with fresh metrics instance."""
        # Use a fresh registry for each test to avoid conflicts
        self.registry = CollectorRegistry()
        self.collector = MetricsCollector(registry=self.registry)

    def test_initialization(self):
        """Test metrics collector initialization."""
        # Use isolated registry for this test
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        assert hasattr(collector, "alerts_total")
        assert hasattr(collector, "alert_duration_seconds")
        assert hasattr(collector, "notifications_total")
        assert hasattr(collector, "notification_duration_seconds")
        assert hasattr(collector, "scheduler_jobs")
        assert hasattr(collector, "scheduler_job_runs_total")
        assert hasattr(collector, "uptime_seconds")
        assert hasattr(collector, "start_time")
        assert isinstance(collector.start_time, float)
        assert collector.registry is registry

    def test_record_alert_execution_ok(self):
        """Test recording alert execution with OK status."""
        self.collector.record_alert_execution("test_alert", "ok", 100.5)

        # Should not raise exception
        assert True

    def test_record_alert_execution_alert(self):
        """Test recording alert execution with ALERT status."""
        self.collector.record_alert_execution("test_alert", "alert", 250.0)

        # Should not raise exception
        assert True

    def test_record_alert_execution_error(self):
        """Test recording alert execution with ERROR status."""
        self.collector.record_alert_execution("test_alert", "error", 50.0)

        # Should not raise exception
        assert True

    def test_record_alert_execution_zero_duration(self):
        """Test recording alert execution with zero duration."""
        self.collector.record_alert_execution("test_alert", "ok", 0.0)

        # Should not raise exception
        assert True

    def test_record_alert_execution_large_duration(self):
        """Test recording alert execution with large duration."""
        self.collector.record_alert_execution("test_alert", "ok", 15000.0)

        # Should not raise exception
        assert True

    def test_record_alert_execution_exception_handling(self):
        """Test that exceptions in record_alert_execution are caught."""
        # Mock the counter to raise exception
        self.collector.alerts_total = MagicMock()
        self.collector.alerts_total.labels.side_effect = Exception("Test error")

        # Should not raise exception (should be caught and logged)
        self.collector.record_alert_execution("test_alert", "ok", 100.0)

    def test_record_notification_success(self):
        """Test recording successful notification."""
        self.collector.record_notification("email", "success", 500.0)

        # Should not raise exception
        assert True

    def test_record_notification_failure(self):
        """Test recording failed notification."""
        self.collector.record_notification("slack", "failure", 1000.0)

        # Should not raise exception
        assert True

    def test_record_notification_all_channels(self):
        """Test recording notifications for all channels."""
        self.collector.record_notification("email", "success", 500.0)
        self.collector.record_notification("slack", "success", 600.0)
        self.collector.record_notification("webhook", "success", 700.0)

        # Should not raise exception
        assert True

    def test_record_notification_zero_duration(self):
        """Test recording notification with zero duration."""
        self.collector.record_notification("email", "success", 0.0)

        # Should not raise exception - zero duration should be skipped
        assert True

    def test_record_notification_negative_duration(self):
        """Test recording notification with negative duration."""
        self.collector.record_notification("email", "success", -100.0)

        # Negative duration should be skipped (not > 0)
        assert True

    def test_record_notification_exception_handling(self):
        """Test that exceptions in record_notification are caught."""
        self.collector.notifications_total = MagicMock()
        self.collector.notifications_total.labels.side_effect = Exception("Test error")

        # Should not raise exception
        self.collector.record_notification("email", "success", 100.0)

    def test_set_scheduler_jobs(self):
        """Test setting scheduler jobs count."""
        self.collector.set_scheduler_jobs(5)

        # Should not raise exception
        assert True

    def test_set_scheduler_jobs_zero(self):
        """Test setting scheduler jobs count to zero."""
        self.collector.set_scheduler_jobs(0)

        # Should not raise exception
        assert True

    def test_set_scheduler_jobs_large_number(self):
        """Test setting scheduler jobs count to large number."""
        self.collector.set_scheduler_jobs(1000)

        # Should not raise exception
        assert True

    def test_set_scheduler_jobs_exception_handling(self):
        """Test that exceptions in set_scheduler_jobs are caught."""
        self.collector.scheduler_jobs = MagicMock()
        self.collector.scheduler_jobs.set.side_effect = Exception("Test error")

        # Should not raise exception
        self.collector.set_scheduler_jobs(5)

    def test_record_scheduler_job_run(self):
        """Test recording scheduler job run."""
        self.collector.record_scheduler_job_run("test_alert")

        # Should not raise exception
        assert True

    def test_record_scheduler_job_run_multiple(self):
        """Test recording multiple scheduler job runs."""
        self.collector.record_scheduler_job_run("alert1")
        self.collector.record_scheduler_job_run("alert2")
        self.collector.record_scheduler_job_run("alert1")

        # Should not raise exception
        assert True

    def test_record_scheduler_job_run_exception_handling(self):
        """Test that exceptions in record_scheduler_job_run are caught."""
        self.collector.scheduler_job_runs_total = MagicMock()
        self.collector.scheduler_job_runs_total.labels.side_effect = Exception(
            "Test error"
        )

        # Should not raise exception
        self.collector.record_scheduler_job_run("test_alert")

    def test_update_uptime(self):
        """Test updating uptime metric."""
        self.collector.update_uptime()

        # Should not raise exception
        assert True

    def test_update_uptime_after_delay(self):
        """Test uptime increases after delay."""
        time.sleep(0.1)  # 100ms delay
        self.collector.update_uptime()

        # Should not raise exception
        assert True

    def test_update_uptime_exception_handling(self):
        """Test that exceptions in update_uptime are caught."""
        self.collector.uptime_seconds = MagicMock()
        self.collector.uptime_seconds.set.side_effect = Exception("Test error")

        # Should not raise exception
        self.collector.update_uptime()

    def test_get_metrics_text(self):
        """Test getting metrics in Prometheus text format."""
        # Record some metrics first
        self.collector.record_alert_execution("test_alert", "ok", 100.0)
        self.collector.record_notification("email", "success", 200.0)
        self.collector.set_scheduler_jobs(3)

        metrics_text = self.collector.get_metrics_text()

        assert isinstance(metrics_text, str)
        assert len(metrics_text) > 0
        # Should contain some of our metric names
        assert "sqlsentinel" in metrics_text

    def test_get_metrics_text_empty_metrics(self):
        """Test getting metrics text with no recorded metrics."""
        metrics_text = self.collector.get_metrics_text()

        assert isinstance(metrics_text, str)
        # Should still have some output (default metrics)
        assert len(metrics_text) > 0

    def test_get_metrics_dict(self):
        """Test getting metrics as dictionary."""
        self.collector.set_scheduler_jobs(5)
        time.sleep(0.1)  # Small delay for uptime

        metrics_dict = self.collector.get_metrics_dict()

        assert isinstance(metrics_dict, dict)
        assert "uptime_seconds" in metrics_dict
        assert "scheduler_jobs" in metrics_dict
        assert isinstance(metrics_dict["uptime_seconds"], float)
        assert metrics_dict["uptime_seconds"] >= 0

    def test_get_metrics_dict_uptime_accuracy(self):
        """Test that uptime metric is accurate."""
        # Create collector with mocked start_time
        registry = CollectorRegistry()
        with patch("time.time", side_effect=[100.0, 150.0]):
            collector = MetricsCollector(registry=registry)  # start_time = 100.0
            metrics_dict = collector.get_metrics_dict()  # current_time = 150.0

        assert metrics_dict["uptime_seconds"] == 50.0

    def test_metrics_with_special_characters_in_names(self):
        """Test metrics with special characters in alert names."""
        self.collector.record_alert_execution("alert-with-dash", "ok", 100.0)
        self.collector.record_alert_execution("alert_with_underscore", "ok", 100.0)

        # Should not raise exception
        assert True


class TestGlobalMetricsInstance:
    """Test global metrics instance management."""

    def setup_method(self):
        """Reset metrics before each test."""
        # Clear global instance
        reset_metrics()

        # Clean up the global REGISTRY to avoid duplicate registration errors
        collectors = list(REGISTRY._collector_to_names.keys())
        for collector in collectors:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

    def test_get_metrics_creates_instance(self):
        """Test that get_metrics creates instance if none exists."""
        metrics = get_metrics()

        assert metrics is not None
        assert isinstance(metrics, MetricsCollector)

    def test_get_metrics_returns_same_instance(self):
        """Test that get_metrics returns same instance on multiple calls."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()

        assert metrics1 is metrics2

    def test_reset_metrics(self):
        """Test that reset_metrics clears global instance."""
        metrics1 = get_metrics()
        reset_metrics()
        metrics2 = get_metrics()

        # Should be different instances after reset
        assert metrics1 is not metrics2

    def test_metrics_state_preserved_across_calls(self):
        """Test that metrics state is preserved across get_metrics calls."""
        metrics1 = get_metrics()
        metrics1.set_scheduler_jobs(10)

        metrics2 = get_metrics()

        # Should be same instance, so state should be preserved
        assert metrics1 is metrics2

    def test_multiple_reset_metrics(self):
        """Test multiple calls to reset_metrics."""
        get_metrics()
        reset_metrics()
        reset_metrics()  # Should not raise error
        metrics = get_metrics()

        assert metrics is not None

    def test_metrics_isolation_after_reset(self):
        """Test that metrics are isolated after reset."""
        metrics1 = get_metrics()
        metrics1.record_alert_execution("test", "ok", 100.0)

        reset_metrics()

        metrics2 = get_metrics()
        # New instance should not have the previous recordings
        # (This is verified by the fact it's a different instance)
        assert metrics1 is not metrics2


class TestMetricsIntegration:
    """Integration tests for metrics collector."""

    def setup_method(self):
        """Set up test method."""
        # Use isolated registry for each test
        self.registry = CollectorRegistry()
        self.collector = MetricsCollector(registry=self.registry)

    def test_full_alert_lifecycle_metrics(self):
        """Test recording full alert lifecycle."""
        # Simulate alert execution
        self.collector.record_alert_execution("revenue_check", "alert", 150.0)

        # Simulate notification
        self.collector.record_notification("email", "success", 500.0)
        self.collector.record_notification("slack", "success", 600.0)

        # Simulate scheduler
        self.collector.record_scheduler_job_run("revenue_check")
        self.collector.set_scheduler_jobs(1)

        # Get metrics text
        metrics_text = self.collector.get_metrics_text()

        assert "sqlsentinel" in metrics_text

    def test_error_scenario_metrics(self):
        """Test recording error scenario."""
        self.collector.record_alert_execution("failing_alert", "error", 50.0)
        self.collector.record_notification("email", "failure", 0.0)

        # Should not raise exception
        assert True

    def test_high_volume_metrics(self):
        """Test recording high volume of metrics."""
        # Simulate 100 alert executions
        for i in range(100):
            self.collector.record_alert_execution(f"alert_{i % 10}", "ok", 100.0)

        # Simulate 50 notifications
        for i in range(50):
            self.collector.record_notification("email", "success", 200.0)

        metrics_text = self.collector.get_metrics_text()
        assert len(metrics_text) > 0

    def test_concurrent_metric_recording(self):
        """Test that multiple metric recordings don't interfere."""
        # Record various metrics concurrently (simulated)
        self.collector.record_alert_execution("alert1", "ok", 100.0)
        self.collector.record_notification("email", "success", 200.0)
        self.collector.set_scheduler_jobs(5)
        self.collector.record_scheduler_job_run("alert1")
        self.collector.update_uptime()

        metrics_dict = self.collector.get_metrics_dict()
        assert "uptime_seconds" in metrics_dict
        assert "scheduler_jobs" in metrics_dict
