"""Slack notification service."""

import json
import time
import urllib.request
from typing import Any
from urllib.error import HTTPError, URLError

from ..models.alert import AlertConfig, QueryResult
from ..models.errors import NotificationError
from ..models.notification import NotificationConfig, SlackConfig
from .base import NotificationService


class SlackNotificationService(NotificationService):
    """Slack notification service using webhooks."""

    def __init__(
        self,
        webhook_url: str,
        max_retries: int = 3,
        retry_delay_seconds: int = 1,
        timeout_seconds: int = 30,
    ):
        """Initialize Slack notification service.

        Args:
            webhook_url: Slack webhook URL
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay_seconds: Initial delay between retries in seconds (default: 1)
            timeout_seconds: Request timeout in seconds (default: 30)

        Raises:
            NotificationError: If webhook_url is invalid
        """
        if not webhook_url:
            raise NotificationError("Slack webhook URL is required")

        if not webhook_url.startswith("https://hooks.slack.com/"):
            raise NotificationError(
                "Invalid Slack webhook URL. Must start with 'https://hooks.slack.com/'"
            )

        self.webhook_url = webhook_url
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.timeout_seconds = timeout_seconds

    def send(
        self,
        alert: AlertConfig,
        result: QueryResult,
        notification_config: NotificationConfig,
    ) -> None:
        """Send Slack notification.

        Args:
            alert: Alert configuration
            result: Query result
            notification_config: Notification configuration

        Raises:
            NotificationError: If message fails to send after retries
        """
        # Extract Slack config
        if not isinstance(notification_config.config, SlackConfig):
            raise NotificationError(f"Expected SlackConfig, got {type(notification_config.config)}")

        slack_config = notification_config.config

        # Build Slack message payload
        payload = self._build_payload(alert, result, slack_config)

        # Send with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self._send_webhook(payload)
                return  # Success
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay_seconds * (2**attempt)
                    time.sleep(delay)

        # All retries failed
        raise NotificationError(
            f"Failed to send Slack notification after {self.max_retries} attempts: {last_error}"
        ) from last_error

    def _build_payload(
        self,
        alert: AlertConfig,
        result: QueryResult,
        slack_config: SlackConfig,
    ) -> dict[str, Any]:
        """Build Slack Block Kit payload.

        Args:
            alert: Alert configuration
            result: Query result
            slack_config: Slack-specific configuration

        Returns:
            Slack message payload as dict
        """
        # Determine color based on status
        color = "#d00000" if result.status == "ALERT" else "#36a64f"  # Red or Green

        # Build blocks for rich formatting
        blocks = []

        # Header block
        blocks.append(
            {"type": "header", "text": {"type": "plain_text", "text": alert.name, "emoji": True}}
        )

        # Main content section
        fields = []

        # Status field
        status_emoji = ":red_circle:" if result.status == "ALERT" else ":large_green_circle:"
        fields.append({"type": "mrkdwn", "text": f"*Status:*\n{status_emoji} {result.status}"})

        # Description field
        if alert.description:
            fields.append({"type": "mrkdwn", "text": f"*Description:*\n{alert.description}"})

        # Actual value and threshold
        if result.actual_value is not None:
            fields.append({"type": "mrkdwn", "text": f"*Actual Value:*\n{result.actual_value}"})

        if result.threshold is not None:
            fields.append({"type": "mrkdwn", "text": f"*Threshold:*\n{result.threshold}"})

        if fields:
            blocks.append({"type": "section", "fields": fields})  # type: ignore[dict-item]

        # Add context fields if present
        if result.context:
            context_text = []
            for key, value in result.context.items():
                context_text.append(f"*{key}:* {value}")

            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(context_text)}}
            )

        # Build final payload
        payload: dict[str, Any] = {
            "blocks": blocks,
            "attachments": [
                {"color": color, "fallback": f"Alert: {alert.name} - Status: {result.status}"}
            ],
        }

        # Add optional overrides
        if slack_config.channel:
            payload["channel"] = slack_config.channel

        if slack_config.username:
            payload["username"] = slack_config.username

        return payload

    def _send_webhook(self, payload: dict[str, Any]) -> None:
        """Send webhook POST request to Slack.

        Args:
            payload: JSON payload to send

        Raises:
            NotificationError: If webhook request fails
        """
        try:
            # Prepare request
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            # Send request
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")

                # Slack responds with "ok" on success
                if response_body != "ok":
                    raise NotificationError(
                        f"Slack webhook returned unexpected response: {response_body}"
                    )

        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else "No error details"
            raise NotificationError(f"Slack webhook HTTP error {e.code}: {error_body}") from e
        except URLError as e:
            raise NotificationError(f"Slack webhook network error: {e.reason}") from e
        except TimeoutError as e:
            raise NotificationError(f"Slack webhook timeout after {self.timeout_seconds}s") from e
        except Exception as e:
            raise NotificationError(f"Failed to send Slack webhook: {e}") from e
