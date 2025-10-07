"""Base notification service interface."""

from abc import ABC, abstractmethod

from ..models.alert import AlertConfig, QueryResult
from ..models.notification import NotificationConfig


class NotificationService(ABC):
    """Abstract base class for notification services."""

    @abstractmethod
    def send(
        self,
        alert: AlertConfig,
        result: QueryResult,
        notification_config: NotificationConfig,
    ) -> None:
        """Send notification for an alert.

        Args:
            alert: Alert configuration
            result: Query result that triggered the alert
            notification_config: Notification configuration

        Raises:
            NotificationError: If notification fails to send
        """
        pass

    def format_message(self, alert: AlertConfig, result: QueryResult) -> tuple[str, str]:
        """Format notification message (subject and body).

        Args:
            alert: Alert configuration
            result: Query result

        Returns:
            Tuple of (subject, body)
        """
        subject = f"[SQL Sentinel] Alert: {alert.name}"

        body_parts = []
        body_parts.append(f"Alert: {alert.name}")

        if alert.description:
            body_parts.append(f"Description: {alert.description}")

        body_parts.append(f"Status: {result.status}")

        if result.actual_value is not None:
            body_parts.append(f"Actual Value: {result.actual_value}")

        if result.threshold is not None:
            body_parts.append(f"Threshold: {result.threshold}")

        # Add context fields
        if result.context:
            body_parts.append("\nAdditional Context:")
            for key, value in result.context.items():
                body_parts.append(f"  {key}: {value}")

        return subject, "\n".join(body_parts)
