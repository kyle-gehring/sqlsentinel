"""Tests for Slack notification service."""

from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError, URLError

import pytest
from sqlsentinel.models.alert import AlertConfig, QueryResult
from sqlsentinel.models.errors import NotificationError
from sqlsentinel.models.notification import (
    NotificationChannel,
    NotificationConfig,
    SlackConfig,
)
from sqlsentinel.notifications.slack import SlackNotificationService


class TestSlackNotificationServiceInit:
    """Tests for SlackNotificationService initialization."""

    def test_init_with_valid_webhook_url(self):
        """Test initialization with valid webhook URL."""
        service = SlackNotificationService(
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        )
        assert (
            service.webhook_url
            == "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        )
        assert service.max_retries == 3
        assert service.retry_delay_seconds == 1
        assert service.timeout_seconds == 30

    def test_init_with_custom_retry_settings(self):
        """Test initialization with custom retry settings."""
        service = SlackNotificationService(
            webhook_url="https://hooks.slack.com/services/T00/B00/XXX",
            max_retries=5,
            retry_delay_seconds=2,
            timeout_seconds=60,
        )
        assert service.max_retries == 5
        assert service.retry_delay_seconds == 2
        assert service.timeout_seconds == 60

    def test_init_with_empty_webhook_url(self):
        """Test initialization with empty webhook URL."""
        with pytest.raises(NotificationError, match="Slack webhook URL is required"):
            SlackNotificationService(webhook_url="")

    def test_init_with_invalid_webhook_url(self):
        """Test initialization with invalid webhook URL."""
        with pytest.raises(NotificationError, match="Invalid Slack webhook URL"):
            SlackNotificationService(webhook_url="https://invalid.com/webhook")

    def test_init_with_http_webhook_url(self):
        """Test initialization with HTTP (not HTTPS) webhook URL."""
        with pytest.raises(NotificationError, match="Invalid Slack webhook URL"):
            SlackNotificationService(webhook_url="http://hooks.slack.com/services/T00/B00/XXX")


class TestSlackNotificationServiceBuildPayload:
    """Tests for Slack payload building."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = SlackNotificationService(
            webhook_url="https://hooks.slack.com/services/T00/B00/XXX"
        )

    def test_build_payload_alert_status(self):
        """Test payload building for ALERT status."""
        alert = AlertConfig(
            name="test_alert",
            description="Test alert description",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
        )
        result = QueryResult(
            status="ALERT",
            actual_value=100.0,
            threshold=50.0,
        )
        slack_config = SlackConfig(webhook_url="https://hooks.slack.com/services/T00/B00/XXX")

        payload = self.service._build_payload(alert, result, slack_config)

        assert "blocks" in payload
        assert "attachments" in payload
        assert len(payload["blocks"]) >= 2  # Header + section
        assert payload["attachments"][0]["color"] == "#d00000"  # Red for ALERT

    def test_build_payload_ok_status(self):
        """Test payload building for OK status."""
        alert = AlertConfig(
            name="test_alert",
            description="Test alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
        )
        result = QueryResult(
            status="OK",
            actual_value=30.0,
            threshold=50.0,
        )
        slack_config = SlackConfig(webhook_url="https://hooks.slack.com/services/T00/B00/XXX")

        payload = self.service._build_payload(alert, result, slack_config)

        assert payload["attachments"][0]["color"] == "#36a64f"  # Green for OK

    def test_build_payload_with_context(self):
        """Test payload building with additional context."""
        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
        )
        result = QueryResult(
            status="ALERT",
            actual_value=100.0,
            threshold=50.0,
            context={"region": "us-east-1", "environment": "production"},
        )
        slack_config = SlackConfig(webhook_url="https://hooks.slack.com/services/T00/B00/XXX")

        payload = self.service._build_payload(alert, result, slack_config)

        # Check that context is included in blocks
        assert len(payload["blocks"]) >= 3  # Header + fields + context
        context_block = payload["blocks"][-1]
        assert "region" in context_block["text"]["text"]
        assert "environment" in context_block["text"]["text"]

    def test_build_payload_with_channel_override(self):
        """Test payload building with channel override."""
        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
        )
        result = QueryResult(status="ALERT")
        slack_config = SlackConfig(
            webhook_url="https://hooks.slack.com/services/T00/B00/XXX",
            channel="#custom-alerts",
        )

        payload = self.service._build_payload(alert, result, slack_config)

        assert payload["channel"] == "#custom-alerts"

    def test_build_payload_with_username_override(self):
        """Test payload building with username override."""
        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
        )
        result = QueryResult(status="ALERT")
        slack_config = SlackConfig(
            webhook_url="https://hooks.slack.com/services/T00/B00/XXX",
            username="SQL Sentinel Bot",
        )

        payload = self.service._build_payload(alert, result, slack_config)

        assert payload["username"] == "SQL Sentinel Bot"

    def test_build_payload_minimal(self):
        """Test payload building with minimal data."""
        alert = AlertConfig(
            name="minimal_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
        )
        result = QueryResult(status="ALERT")
        slack_config = SlackConfig(webhook_url="https://hooks.slack.com/services/T00/B00/XXX")

        payload = self.service._build_payload(alert, result, slack_config)

        assert "blocks" in payload
        assert "attachments" in payload
        assert payload["blocks"][0]["type"] == "header"


class TestSlackNotificationServiceSend:
    """Tests for Slack notification sending."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = SlackNotificationService(
            webhook_url="https://hooks.slack.com/services/T00/B00/XXX"
        )
        self.alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
        )
        self.result = QueryResult(status="ALERT", actual_value=100.0)
        self.slack_config = SlackConfig(webhook_url="https://hooks.slack.com/services/T00/B00/XXX")
        self.notification_config = NotificationConfig(
            channel=NotificationChannel.SLACK,
            config=self.slack_config,
        )

    @patch("urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        """Test successful notification send."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.read.return_value = b"ok"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Should not raise
        self.service.send(self.alert, self.result, self.notification_config)

        # Verify webhook was called
        assert mock_urlopen.call_count == 1

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_send_with_retries(self, mock_sleep, mock_urlopen):
        """Test notification send with retries on failure."""
        # First two attempts fail, third succeeds
        mock_response_success = MagicMock()
        mock_response_success.read.return_value = b"ok"

        mock_urlopen.side_effect = [
            URLError("Network error"),
            URLError("Network error"),
            MagicMock(__enter__=lambda self: mock_response_success, __exit__=lambda *args: None),
        ]

        # Should eventually succeed
        self.service.send(self.alert, self.result, self.notification_config)

        # Verify retries occurred
        assert mock_urlopen.call_count == 3

    @patch("urllib.request.urlopen")
    def test_send_all_retries_fail(self, mock_urlopen):
        """Test notification send when all retries fail."""
        # All attempts fail
        mock_urlopen.side_effect = URLError("Network error")

        # Should raise NotificationError after max retries
        with pytest.raises(
            NotificationError, match="Failed to send Slack notification after 3 attempts"
        ):
            self.service.send(self.alert, self.result, self.notification_config)

        # Verify all retries were attempted
        assert mock_urlopen.call_count == 3

    @patch("urllib.request.urlopen")
    def test_send_http_error(self, mock_urlopen):
        """Test notification send with HTTP error."""
        # Mock HTTP error
        mock_fp = Mock()
        mock_fp.read.return_value = b"Invalid payload"
        mock_urlopen.side_effect = HTTPError(
            "https://hooks.slack.com/services/T00/B00/XXX",
            400,
            "Bad Request",
            {},
            mock_fp,
        )

        with pytest.raises(NotificationError, match="Slack webhook HTTP error 400"):
            self.service.send(self.alert, self.result, self.notification_config)

    @patch("urllib.request.urlopen")
    def test_send_invalid_config_type(self, mock_urlopen):
        """Test send with wrong config type."""
        from sqlsentinel.models.notification import EmailConfig

        # Use email config instead of Slack config
        invalid_config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config=EmailConfig(recipients=["test@example.com"]),
        )

        with pytest.raises(NotificationError, match="Expected SlackConfig"):
            self.service.send(self.alert, self.result, invalid_config)

        # Should not call webhook
        assert mock_urlopen.call_count == 0

    @patch("urllib.request.urlopen")
    def test_send_unexpected_response(self, mock_urlopen):
        """Test send with unexpected response from Slack."""
        # Mock unexpected response
        mock_response = MagicMock()
        mock_response.read.return_value = b"unexpected"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(NotificationError, match="Slack webhook returned unexpected response"):
            self.service.send(self.alert, self.result, self.notification_config)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_send_exponential_backoff(self, mock_sleep, mock_urlopen):
        """Test that retries use exponential backoff."""
        # All attempts fail
        mock_urlopen.side_effect = URLError("Network error")

        with pytest.raises(NotificationError):
            self.service.send(self.alert, self.result, self.notification_config)

        # Verify exponential backoff delays: 1s, 2s (2^0=1, 2^1=2)
        # Note: no sleep after last attempt
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # First retry: 1 * 2^0
        mock_sleep.assert_any_call(2)  # Second retry: 1 * 2^1
