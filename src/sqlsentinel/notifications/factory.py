"""Notification factory for creating notification services."""

import os
from typing import Optional

from ..models.errors import NotificationError
from ..models.notification import NotificationChannel
from .base import NotificationService
from .email import EmailNotificationService
from .slack import SlackNotificationService
from .webhook import WebhookNotificationService


class NotificationFactory:
    """Factory for creating notification services."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_use_tls: bool = True,
        smtp_from_address: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ):
        """Initialize notification factory.

        Args:
            smtp_host: SMTP server hostname (can be env var or direct value)
            smtp_port: SMTP server port
            smtp_username: SMTP username
            smtp_password: SMTP password
            smtp_use_tls: Whether to use TLS
            smtp_from_address: From email address
            slack_webhook_url: Default Slack webhook URL
            webhook_url: Default webhook URL

        Note:
            All parameters support environment variable substitution.
            If a value is None, it will be read from environment variables:
            - smtp_host: SMTP_HOST
            - smtp_port: SMTP_PORT
            - smtp_username: SMTP_USERNAME
            - smtp_password: SMTP_PASSWORD
            - smtp_use_tls: SMTP_USE_TLS
            - smtp_from_address: SMTP_FROM_ADDRESS
            - slack_webhook_url: SLACK_WEBHOOK_URL
            - webhook_url: WEBHOOK_URL
        """
        # Email configuration
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")

        # Handle smtp_port: use parameter if provided, otherwise check env var, otherwise default to 587
        if smtp_port is not None and smtp_port != 587:
            self.smtp_port = smtp_port
        else:
            self.smtp_port = int(os.getenv("SMTP_PORT", "587"))

        self.smtp_username = smtp_username or os.getenv("SMTP_USERNAME")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")

        # Handle smtp_use_tls: only check env var if not explicitly set in parameter
        # Note: default parameter value is True, so we need to check if it was explicitly set
        env_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        # If the default wasn't changed, use env var; otherwise use the explicit value
        # Since we can't tell if True was explicitly set or is default, we'll always prefer env var when present
        if os.getenv("SMTP_USE_TLS"):
            self.smtp_use_tls = env_tls
        else:
            self.smtp_use_tls = smtp_use_tls

        self.smtp_from_address = smtp_from_address or os.getenv("SMTP_FROM_ADDRESS")

        # Slack configuration
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")

        # Webhook configuration
        self.webhook_url = webhook_url or os.getenv("WEBHOOK_URL")

    def create_service(self, channel: NotificationChannel) -> NotificationService:
        """Create notification service for the specified channel.

        Args:
            channel: Notification channel type

        Returns:
            NotificationService instance

        Raises:
            NotificationError: If channel is not supported or configuration is missing
        """
        if channel == NotificationChannel.EMAIL:
            return self._create_email_service()
        elif channel == NotificationChannel.SLACK:
            return self._create_slack_service()
        elif channel == NotificationChannel.WEBHOOK:
            return self._create_webhook_service()
        else:
            raise NotificationError(f"Unsupported notification channel: {channel}")

    def _create_email_service(self) -> EmailNotificationService:
        """Create email notification service.

        Returns:
            EmailNotificationService instance

        Raises:
            NotificationError: If SMTP configuration is missing
        """
        if not self.smtp_host:
            raise NotificationError(
                "SMTP host not configured. Set smtp_host parameter or SMTP_HOST environment variable."
            )

        return EmailNotificationService(
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
            smtp_username=self.smtp_username,
            smtp_password=self.smtp_password,
            use_tls=self.smtp_use_tls,
            from_address=self.smtp_from_address,
        )

    def _create_slack_service(self) -> SlackNotificationService:
        """Create Slack notification service.

        Returns:
            SlackNotificationService instance

        Raises:
            NotificationError: If Slack webhook URL is not configured
        """
        if not self.slack_webhook_url:
            raise NotificationError(
                "Slack webhook URL not configured. Set slack_webhook_url parameter or SLACK_WEBHOOK_URL environment variable."
            )

        return SlackNotificationService(webhook_url=self.slack_webhook_url)

    def _create_webhook_service(self) -> WebhookNotificationService:
        """Create generic webhook notification service.

        Returns:
            WebhookNotificationService instance

        Raises:
            NotificationError: If webhook URL is not configured
        """
        if not self.webhook_url:
            raise NotificationError(
                "Webhook URL not configured. Set webhook_url parameter or WEBHOOK_URL environment variable."
            )

        return WebhookNotificationService(url=self.webhook_url)
