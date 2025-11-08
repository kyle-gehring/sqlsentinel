"""Metrics collection for SQL Sentinel using Prometheus client library."""

import logging
import time
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, generate_latest

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Centralized metrics collection using prometheus-client."""

    def __init__(self) -> None:
        """Initialize metrics collector with Prometheus metrics."""
        # Alert execution metrics
        self.alerts_total = Counter(
            "sqlsentinel_alerts_total",
            "Total number of alert executions",
            ["alert_name", "status"],
        )

        self.alert_duration_seconds = Histogram(
            "sqlsentinel_alert_duration_seconds",
            "Alert execution duration in seconds",
            ["alert_name"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        # Notification metrics
        self.notifications_total = Counter(
            "sqlsentinel_notifications_total",
            "Total notifications sent",
            ["channel", "status"],
        )

        self.notification_duration_seconds = Histogram(
            "sqlsentinel_notification_duration_seconds",
            "Notification delivery duration in seconds",
            ["channel"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0),
        )

        # Scheduler metrics
        self.scheduler_jobs = Gauge(
            "sqlsentinel_scheduler_jobs",
            "Current number of scheduled jobs",
        )

        self.scheduler_job_runs_total = Counter(
            "sqlsentinel_scheduler_job_runs_total",
            "Total number of scheduled job runs",
            ["alert_name"],
        )

        # System metrics
        self.uptime_seconds = Gauge(
            "sqlsentinel_uptime_seconds",
            "Application uptime in seconds",
        )

        self.start_time = time.time()

    def record_alert_execution(
        self,
        alert_name: str,
        status: str,
        duration_ms: float,
    ) -> None:
        """Record an alert execution.

        Args:
            alert_name: Name of the alert
            status: Execution status ('alert', 'ok', 'error')
            duration_ms: Execution duration in milliseconds
        """
        try:
            self.alerts_total.labels(alert_name=alert_name, status=status).inc()
            self.alert_duration_seconds.labels(alert_name=alert_name).observe(duration_ms / 1000)
        except Exception as e:
            logger.error(f"Failed to record alert execution metric: {e}")

    def record_notification(
        self,
        channel: str,
        status: str,
        duration_ms: float,
    ) -> None:
        """Record a notification attempt.

        Args:
            channel: Notification channel (email, slack, webhook)
            status: Send status ('success', 'failure')
            duration_ms: Delivery duration in milliseconds
        """
        try:
            self.notifications_total.labels(channel=channel, status=status).inc()
            if duration_ms > 0:
                self.notification_duration_seconds.labels(channel=channel).observe(
                    duration_ms / 1000
                )
        except Exception as e:
            logger.error(f"Failed to record notification metric: {e}")

    def set_scheduler_jobs(self, count: int) -> None:
        """Set the current number of scheduled jobs.

        Args:
            count: Number of currently scheduled jobs
        """
        try:
            self.scheduler_jobs.set(count)
        except Exception as e:
            logger.error(f"Failed to update scheduler jobs metric: {e}")

    def record_scheduler_job_run(self, alert_name: str) -> None:
        """Record a scheduler job run.

        Args:
            alert_name: Name of the alert that was triggered
        """
        try:
            self.scheduler_job_runs_total.labels(alert_name=alert_name).inc()
        except Exception as e:
            logger.error(f"Failed to record scheduler job run metric: {e}")

    def update_uptime(self) -> None:
        """Update uptime metric."""
        try:
            uptime = time.time() - self.start_time
            self.uptime_seconds.set(uptime)
        except Exception as e:
            logger.error(f"Failed to update uptime metric: {e}")

    def get_metrics_text(self) -> str:
        """Get all metrics in Prometheus text format.

        Returns:
            Prometheus format text representation of all metrics
        """
        self.update_uptime()
        return generate_latest().decode("utf-8")

    def get_metrics_dict(self) -> dict[str, Any]:
        """Get metrics as a dictionary (simplified view).

        Returns:
            Dictionary with metric names and values
        """
        return {
            "uptime_seconds": time.time() - self.start_time,
            "scheduler_jobs": self.scheduler_jobs._value.get(),  # type: ignore
        }


# Global metrics instance
_metrics_instance: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    """Get or create the global metrics collector instance.

    Returns:
        MetricsCollector instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance


def reset_metrics() -> None:
    """Reset the global metrics instance (for testing)."""
    global _metrics_instance
    _metrics_instance = None
