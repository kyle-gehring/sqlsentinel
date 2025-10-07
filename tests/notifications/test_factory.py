"""Tests for notification factory."""

import os
from unittest.mock import patch

import pytest
from sqlsentinel.models.errors import NotificationError
from sqlsentinel.models.notification import NotificationChannel
from sqlsentinel.notifications.email import EmailNotificationService
from sqlsentinel.notifications.factory import NotificationFactory
from sqlsentinel.notifications.slack import SlackNotificationService
from sqlsentinel.notifications.webhook import WebhookNotificationService


class TestNotificationFactory:
    """Test NotificationFactory class."""

    def test_init_with_direct_values(self):
        """Test initialization with direct values."""
        factory = NotificationFactory(
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_username="user@example.com",
            smtp_password="password123",
            smtp_use_tls=False,
            smtp_from_address="alerts@example.com",
        )

        assert factory.smtp_host == "smtp.example.com"
        assert factory.smtp_port == 465
        assert factory.smtp_username == "user@example.com"
        assert factory.smtp_password == "password123"
        assert factory.smtp_use_tls is False
        assert factory.smtp_from_address == "alerts@example.com"

    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "2525",
            "SMTP_USERNAME": "testuser",
            "SMTP_PASSWORD": "testpass",
            "SMTP_USE_TLS": "false",
            "SMTP_FROM_ADDRESS": "test@test.com",
        }

        with patch.dict(os.environ, env_vars):
            factory = NotificationFactory()

            assert factory.smtp_host == "smtp.test.com"
            assert factory.smtp_port == 2525
            assert factory.smtp_username == "testuser"
            assert factory.smtp_password == "testpass"
            assert factory.smtp_use_tls is False
            assert factory.smtp_from_address == "test@test.com"

    def test_init_direct_values_override_env(self):
        """Test direct values override environment variables."""
        env_vars = {
            "SMTP_HOST": "smtp.env.com",
            "SMTP_PORT": "2525",
        }

        with patch.dict(os.environ, env_vars):
            factory = NotificationFactory(
                smtp_host="smtp.direct.com",
                smtp_port=465,
            )

            assert factory.smtp_host == "smtp.direct.com"
            assert factory.smtp_port == 465

    def test_create_email_service(self):
        """Test creating email notification service."""
        factory = NotificationFactory(smtp_host="smtp.example.com")

        service = factory.create_service(NotificationChannel.EMAIL)

        assert isinstance(service, EmailNotificationService)
        assert service.smtp_host == "smtp.example.com"

    def test_create_email_service_no_smtp_host(self):
        """Test creating email service without SMTP host fails."""
        factory = NotificationFactory()

        with pytest.raises(NotificationError, match="SMTP host not configured"):
            factory.create_service(NotificationChannel.EMAIL)

    def test_create_slack_service(self):
        """Test creating Slack notification service."""
        factory = NotificationFactory(
            slack_webhook_url="https://hooks.slack.com/services/T00/B00/XXX"
        )

        service = factory.create_service(NotificationChannel.SLACK)

        assert isinstance(service, SlackNotificationService)
        assert service.webhook_url == "https://hooks.slack.com/services/T00/B00/XXX"

    def test_create_slack_service_with_env_var(self):
        """Test creating Slack service with environment variable."""
        with patch.dict(
            os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T11/B11/YYY"}
        ):
            factory = NotificationFactory()

            service = factory.create_service(NotificationChannel.SLACK)

            assert isinstance(service, SlackNotificationService)
            assert service.webhook_url == "https://hooks.slack.com/services/T11/B11/YYY"

    def test_create_slack_service_no_webhook_url(self):
        """Test creating Slack service without webhook URL fails."""
        factory = NotificationFactory()

        with pytest.raises(NotificationError, match="Slack webhook URL not configured"):
            factory.create_service(NotificationChannel.SLACK)

    def test_create_webhook_service(self):
        """Test creating webhook notification service."""
        factory = NotificationFactory(webhook_url="https://example.com/webhook")

        service = factory.create_service(NotificationChannel.WEBHOOK)

        assert isinstance(service, WebhookNotificationService)
        assert service.url == "https://example.com/webhook"

    def test_create_webhook_service_with_env_var(self):
        """Test creating webhook service with environment variable."""
        with patch.dict(os.environ, {"WEBHOOK_URL": "https://api.example.com/alerts"}):
            factory = NotificationFactory()

            service = factory.create_service(NotificationChannel.WEBHOOK)

            assert isinstance(service, WebhookNotificationService)
            assert service.url == "https://api.example.com/alerts"

    def test_create_webhook_service_no_url(self):
        """Test creating webhook service without URL fails."""
        factory = NotificationFactory()

        with pytest.raises(NotificationError, match="Webhook URL not configured"):
            factory.create_service(NotificationChannel.WEBHOOK)

    def test_smtp_use_tls_default_true(self):
        """Test SMTP_USE_TLS defaults to true."""
        factory = NotificationFactory(smtp_host="smtp.example.com")
        assert factory.smtp_use_tls is True

    def test_smtp_use_tls_env_var_false(self):
        """Test SMTP_USE_TLS from environment variable."""
        with patch.dict(os.environ, {"SMTP_USE_TLS": "false"}):
            factory = NotificationFactory(smtp_host="smtp.example.com")
            assert factory.smtp_use_tls is False

    def test_smtp_port_default(self):
        """Test SMTP port defaults to 587."""
        factory = NotificationFactory(smtp_host="smtp.example.com")
        assert factory.smtp_port == 587

    def test_init_with_all_channels(self):
        """Test initialization with all channel configurations."""
        factory = NotificationFactory(
            smtp_host="smtp.example.com",
            slack_webhook_url="https://hooks.slack.com/services/T00/B00/XXX",
            webhook_url="https://example.com/webhook",
        )

        assert factory.smtp_host == "smtp.example.com"
        assert factory.slack_webhook_url == "https://hooks.slack.com/services/T00/B00/XXX"
        assert factory.webhook_url == "https://example.com/webhook"

    def test_init_with_all_env_vars(self):
        """Test initialization with all environment variables."""
        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
            "WEBHOOK_URL": "https://api.test.com/alerts",
        }

        with patch.dict(os.environ, env_vars):
            factory = NotificationFactory()

            assert factory.smtp_host == "smtp.test.com"
            assert factory.slack_webhook_url == "https://hooks.slack.com/services/T00/B00/XXX"
            assert factory.webhook_url == "https://api.test.com/alerts"

    def test_create_all_channel_types(self):
        """Test creating all three notification channel types."""
        factory = NotificationFactory(
            smtp_host="smtp.example.com",
            slack_webhook_url="https://hooks.slack.com/services/T00/B00/XXX",
            webhook_url="https://example.com/webhook",
        )

        email_service = factory.create_service(NotificationChannel.EMAIL)
        slack_service = factory.create_service(NotificationChannel.SLACK)
        webhook_service = factory.create_service(NotificationChannel.WEBHOOK)

        assert isinstance(email_service, EmailNotificationService)
        assert isinstance(slack_service, SlackNotificationService)
        assert isinstance(webhook_service, WebhookNotificationService)
