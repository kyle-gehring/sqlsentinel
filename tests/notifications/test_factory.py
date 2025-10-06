"""Tests for notification factory."""

import os
from unittest.mock import patch

import pytest

from sqlsentinel.models.errors import NotificationError
from sqlsentinel.models.notification import NotificationChannel
from sqlsentinel.notifications.email import EmailNotificationService
from sqlsentinel.notifications.factory import NotificationFactory


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

    def test_create_slack_service_not_implemented(self):
        """Test creating Slack service raises not implemented error."""
        factory = NotificationFactory(smtp_host="smtp.example.com")

        with pytest.raises(NotificationError, match="Slack notifications not yet implemented"):
            factory.create_service(NotificationChannel.SLACK)

    def test_create_webhook_service_not_implemented(self):
        """Test creating webhook service raises not implemented error."""
        factory = NotificationFactory(smtp_host="smtp.example.com")

        with pytest.raises(NotificationError, match="Webhook notifications not yet implemented"):
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
