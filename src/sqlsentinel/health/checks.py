"""Health check functions for SQL Sentinel."""

import logging
import time
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class HealthCheckError(Exception):
    """Exception raised during health checks."""

    pass


def check_database(engine: Engine) -> dict[str, Any]:
    """
    Check database connectivity and responsiveness.

    Args:
        engine: SQLAlchemy engine instance

    Returns:
        Dictionary with status, latency, and message
    """
    try:
        start_time = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "message": "Database connection OK",
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "latency_ms": None,
            "message": f"Database connection failed: {str(e)}",
        }


def check_scheduler(scheduler_service: Any) -> dict[str, Any]:
    """
    Check scheduler status and job count.

    Args:
        scheduler_service: SchedulerService instance

    Returns:
        Dictionary with status, job count, and next run time
    """
    try:
        if not scheduler_service:
            return {
                "status": "unhealthy",
                "jobs_count": 0,
                "message": "Scheduler not initialized",
            }

        # Check if scheduler is running
        if not scheduler_service.scheduler.running:
            return {
                "status": "degraded",
                "jobs_count": 0,
                "message": "Scheduler is not running",
            }

        # Get job count
        jobs_count = len(scheduler_service.scheduler.get_jobs())

        return {
            "status": "healthy",
            "jobs_count": jobs_count,
            "message": f"{jobs_count} jobs scheduled",
        }
    except Exception as e:
        logger.error(f"Scheduler health check failed: {e}")
        return {
            "status": "degraded",
            "jobs_count": 0,
            "message": f"Scheduler check failed: {str(e)}",
        }


def check_notifications(notification_factory: Any) -> dict[str, Any]:
    """
    Check notification service connectivity.

    Args:
        notification_factory: NotificationFactory instance

    Returns:
        Dictionary with per-channel health status
    """
    from ..models.notification import NotificationChannel

    channels = {}

    try:
        # Check Email
        try:
            email_notifier = notification_factory.create_service(NotificationChannel.EMAIL)
            if email_notifier:
                channels["email"] = {"status": "healthy"}
            else:
                channels["email"] = {"status": "not_configured"}
        except Exception as e:
            # Not configured is expected if SMTP settings aren't set
            if "not configured" in str(e).lower():
                channels["email"] = {"status": "not_configured"}
            else:
                logger.warning(f"Email notification check failed: {e}")
                channels["email"] = {"status": "unhealthy", "message": str(e)}

        # Check Slack
        try:
            slack_notifier = notification_factory.create_service(NotificationChannel.SLACK)
            if slack_notifier:
                channels["slack"] = {"status": "healthy"}
            else:
                channels["slack"] = {"status": "not_configured"}
        except Exception as e:
            # Not configured is expected if Slack webhook isn't set
            if "not configured" in str(e).lower():
                channels["slack"] = {"status": "not_configured"}
            else:
                logger.warning(f"Slack notification check failed: {e}")
                channels["slack"] = {"status": "unhealthy", "message": str(e)}

        # Check Webhook
        try:
            webhook_notifier = notification_factory.create_service(NotificationChannel.WEBHOOK)
            if webhook_notifier:
                channels["webhook"] = {"status": "healthy"}
            else:
                channels["webhook"] = {"status": "not_configured"}
        except Exception as e:
            # Not configured is expected if webhook URL isn't set
            if "not configured" in str(e).lower():
                channels["webhook"] = {"status": "not_configured"}
            else:
                logger.warning(f"Webhook notification check failed: {e}")
                channels["webhook"] = {"status": "unhealthy", "message": str(e)}

        return {
            "status": "healthy",
            "channels": channels,
        }
    except Exception as e:
        logger.error(f"Notification health check failed: {e}")
        return {
            "status": "degraded",
            "channels": channels,
            "message": f"Notification check failed: {str(e)}",
        }


def aggregate_health_status(checks: dict[str, Any]) -> str:
    """
    Aggregate individual check statuses into overall health status.

    Args:
        checks: Dictionary of individual health check results

    Returns:
        Overall status: 'healthy', 'degraded', or 'unhealthy'
    """
    statuses = [check.get("status") for check in checks.values()]

    if "unhealthy" in statuses:
        return "unhealthy"
    elif "degraded" in statuses:
        return "degraded"
    else:
        return "healthy"
