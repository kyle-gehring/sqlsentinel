"""Tests for notification models."""

import pytest
from pydantic import ValidationError

from sqlsentinel.models.notification import (
    EmailConfig,
    NotificationChannel,
    NotificationConfig,
    SlackConfig,
    WebhookConfig,
)


class TestEmailConfig:
    """Tests for EmailConfig model."""

    def test_valid_email_config(self):
        """Test valid email configuration."""
        config = EmailConfig(recipients=["test@example.com", "user@test.com"])
        assert len(config.recipients) == 2
        assert config.subject is None

    def test_email_config_with_subject(self):
        """Test email config with subject."""
        config = EmailConfig(recipients=["test@example.com"], subject="Alert: {alert_name}")
        assert config.subject == "Alert: {alert_name}"

    def test_invalid_email_address(self):
        """Test invalid email address."""
        with pytest.raises(ValidationError) as exc_info:
            EmailConfig(recipients=["invalid-email"])
        assert "Invalid email address" in str(exc_info.value)

    def test_empty_recipients(self):
        """Test empty recipients list."""
        with pytest.raises(ValidationError):
            EmailConfig(recipients=[])


class TestSlackConfig:
    """Tests for SlackConfig model."""

    def test_valid_slack_config(self):
        """Test valid Slack configuration."""
        config = SlackConfig(webhook_url="https://hooks.slack.com/services/T/B/X")
        assert config.webhook_url.startswith("https://hooks.slack.com/")
        assert config.channel is None
        assert config.username is None

    def test_slack_config_with_overrides(self):
        """Test Slack config with channel and username overrides."""
        config = SlackConfig(
            webhook_url="https://hooks.slack.com/services/T/B/X",
            channel="#alerts",
            username="AlertBot",
        )
        assert config.channel == "#alerts"
        assert config.username == "AlertBot"

    def test_invalid_webhook_url(self):
        """Test invalid Slack webhook URL."""
        with pytest.raises(ValidationError) as exc_info:
            SlackConfig(webhook_url="https://example.com/webhook")
        assert "Invalid Slack webhook URL" in str(exc_info.value)


class TestWebhookConfig:
    """Tests for WebhookConfig model."""

    def test_valid_webhook_config(self):
        """Test valid webhook configuration."""
        config = WebhookConfig(url="https://example.com/webhook")
        assert config.url == "https://example.com/webhook"
        assert config.method == "POST"
        assert config.headers == {}

    def test_webhook_config_with_options(self):
        """Test webhook config with custom method and headers."""
        config = WebhookConfig(
            url="https://api.example.com/alerts",
            method="PUT",
            headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
        )
        assert config.method == "PUT"
        assert config.headers["Authorization"] == "Bearer token"

    def test_invalid_http_method(self):
        """Test invalid HTTP method."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookConfig(url="https://example.com", method="DELETE")
        assert "Invalid HTTP method" in str(exc_info.value)

    def test_method_normalization(self):
        """Test that method is normalized to uppercase."""
        config = WebhookConfig(url="https://example.com", method="post")
        assert config.method == "POST"


class TestNotificationConfig:
    """Tests for NotificationConfig model."""

    def test_email_notification(self, sample_email_notification):
        """Test email notification configuration."""
        config = NotificationConfig(**sample_email_notification)
        assert config.channel == NotificationChannel.EMAIL
        assert isinstance(config.config, EmailConfig)

    def test_slack_notification(self, sample_slack_notification):
        """Test Slack notification configuration."""
        config = NotificationConfig(**sample_slack_notification)
        assert config.channel == NotificationChannel.SLACK
        assert isinstance(config.config, SlackConfig)

    def test_webhook_notification(self, sample_webhook_notification):
        """Test webhook notification configuration."""
        config = NotificationConfig(**sample_webhook_notification)
        assert config.channel == NotificationChannel.WEBHOOK
        assert isinstance(config.config, WebhookConfig)

    def test_mismatched_channel_and_config(self):
        """Test validation fails when channel and config don't match."""
        with pytest.raises(ValidationError) as exc_info:
            NotificationConfig(
                channel=NotificationChannel.EMAIL,
                config=SlackConfig(webhook_url="https://hooks.slack.com/services/T/B/X"),
            )
        assert "Email channel requires EmailConfig" in str(exc_info.value)
