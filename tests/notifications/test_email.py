"""Tests for email notification service."""

from unittest.mock import MagicMock, patch

import pytest

from sqlsentinel.models.alert import AlertConfig, QueryResult
from sqlsentinel.models.errors import NotificationError
from sqlsentinel.models.notification import EmailConfig, NotificationChannel, NotificationConfig
from sqlsentinel.notifications.email import EmailNotificationService


class TestEmailNotificationService:
    """Test EmailNotificationService class."""

    def test_init_minimal(self):
        """Test initialization with minimal configuration."""
        service = EmailNotificationService(smtp_host="smtp.example.com")

        assert service.smtp_host == "smtp.example.com"
        assert service.smtp_port == 587
        assert service.use_tls is True
        assert service.max_retries == 3

    def test_init_full(self):
        """Test initialization with full configuration."""
        service = EmailNotificationService(
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_username="user@example.com",
            smtp_password="password123",
            use_tls=False,
            from_address="alerts@example.com",
            max_retries=5,
            retry_delay_seconds=3,
        )

        assert service.smtp_host == "smtp.example.com"
        assert service.smtp_port == 465
        assert service.smtp_username == "user@example.com"
        assert service.smtp_password == "password123"
        assert service.use_tls is False
        assert service.from_address == "alerts@example.com"
        assert service.max_retries == 5
        assert service.retry_delay_seconds == 3

    def test_init_from_address_defaults_to_username(self):
        """Test from_address defaults to username."""
        service = EmailNotificationService(
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
        )

        assert service.from_address == "user@example.com"

    def test_init_no_smtp_host(self):
        """Test initialization fails without SMTP host."""
        with pytest.raises(NotificationError, match="SMTP host is required"):
            EmailNotificationService(smtp_host="")

    @patch("sqlsentinel.notifications.email.smtplib.SMTP")
    def test_send_success(self, mock_smtp_class):
        """Test successful email send."""
        # Setup mock
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        service = EmailNotificationService(
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password="password123",
        )

        # Create test data
        alert = AlertConfig(
            name="test_alert",
            description="Test alert",
            query="SELECT 1",
            schedule="* * * * *",
        )

        result = QueryResult(
            status="ALERT",
            actual_value=95.5,
            threshold=90.0,
        )

        email_config = EmailConfig(recipients=["admin@example.com"])
        notification_config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config=email_config,
        )

        # Send notification
        service.send(alert, result, notification_config)

        # Verify SMTP calls
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=30)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user@example.com", "password123")
        mock_smtp.sendmail.assert_called_once()
        mock_smtp.quit.assert_called_once()

    @patch("sqlsentinel.notifications.email.smtplib.SMTP")
    def test_send_without_tls(self, mock_smtp_class):
        """Test email send without TLS."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        service = EmailNotificationService(
            smtp_host="smtp.example.com",
            use_tls=False,
        )

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 1",
            schedule="* * * * *",
        )
        result = QueryResult(status="ALERT")
        email_config = EmailConfig(recipients=["admin@example.com"])
        notification_config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config=email_config,
        )

        service.send(alert, result, notification_config)

        # Verify TLS was not called
        mock_smtp.starttls.assert_not_called()

    @patch("sqlsentinel.notifications.email.smtplib.SMTP")
    def test_send_without_authentication(self, mock_smtp_class):
        """Test email send without authentication."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        service = EmailNotificationService(smtp_host="smtp.example.com")

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 1",
            schedule="* * * * *",
        )
        result = QueryResult(status="ALERT")
        email_config = EmailConfig(recipients=["admin@example.com"])
        notification_config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config=email_config,
        )

        service.send(alert, result, notification_config)

        # Verify login was not called
        mock_smtp.login.assert_not_called()

    @patch("sqlsentinel.notifications.email.smtplib.SMTP")
    def test_send_custom_subject(self, mock_smtp_class):
        """Test email with custom subject template."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        service = EmailNotificationService(smtp_host="smtp.example.com")

        alert = AlertConfig(
            name="revenue_alert",
            query="SELECT 1",
            schedule="* * * * *",
        )
        result = QueryResult(status="ALERT", actual_value=95.5)

        email_config = EmailConfig(
            recipients=["admin@example.com"],
            subject="URGENT: {alert_name} - Status: {status}",
        )
        notification_config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config=email_config,
        )

        service.send(alert, result, notification_config)

        # Verify sendmail was called (subject is in the message)
        mock_smtp.sendmail.assert_called_once()
        call_args = mock_smtp.sendmail.call_args[0]
        message = call_args[2]
        assert "URGENT: revenue_alert - Status: ALERT" in message

    @patch("sqlsentinel.notifications.email.smtplib.SMTP")
    @patch("sqlsentinel.notifications.email.time.sleep")
    def test_send_with_retry(self, mock_sleep, mock_smtp_class):
        """Test email send with retry on failure."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        # Fail first attempt, succeed on second
        mock_smtp.sendmail.side_effect = [
            Exception("Connection failed"),
            None,  # Success
        ]

        service = EmailNotificationService(
            smtp_host="smtp.example.com",
            max_retries=3,
            retry_delay_seconds=1,
        )

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 1",
            schedule="* * * * *",
        )
        result = QueryResult(status="ALERT")
        email_config = EmailConfig(recipients=["admin@example.com"])
        notification_config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config=email_config,
        )

        service.send(alert, result, notification_config)

        # Verify retry happened
        assert mock_smtp.sendmail.call_count == 2
        mock_sleep.assert_called_once()  # Called once between retries

    @patch("sqlsentinel.notifications.email.smtplib.SMTP")
    @patch("sqlsentinel.notifications.email.time.sleep")
    def test_send_fails_after_max_retries(self, mock_sleep, mock_smtp_class):
        """Test email send fails after max retries."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        # Fail all attempts
        mock_smtp.sendmail.side_effect = Exception("Connection failed")

        service = EmailNotificationService(
            smtp_host="smtp.example.com",
            max_retries=3,
            retry_delay_seconds=1,
        )

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 1",
            schedule="* * * * *",
        )
        result = QueryResult(status="ALERT")
        email_config = EmailConfig(recipients=["admin@example.com"])
        notification_config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config=email_config,
        )

        with pytest.raises(NotificationError, match="Failed to send email after 3 attempts"):
            service.send(alert, result, notification_config)

        # Verify all retries were attempted
        assert mock_smtp.sendmail.call_count == 3

    def test_send_invalid_notification_config(self):
        """Test send with invalid notification config."""
        service = EmailNotificationService(smtp_host="smtp.example.com")

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 1",
            schedule="* * * * *",
        )
        result = QueryResult(status="ALERT")

        # Create notification config with wrong type
        from sqlsentinel.models.notification import SlackConfig

        slack_config = SlackConfig(webhook_url="https://hooks.slack.com/test")
        notification_config = NotificationConfig(
            channel=NotificationChannel.SLACK,
            config=slack_config,
        )

        with pytest.raises(NotificationError, match="Expected EmailConfig"):
            service.send(alert, result, notification_config)

    def test_format_message(self):
        """Test message formatting."""
        service = EmailNotificationService(smtp_host="smtp.example.com")

        alert = AlertConfig(
            name="test_alert",
            description="This is a test alert",
            query="SELECT 1",
            schedule="* * * * *",
        )

        result = QueryResult(
            status="ALERT",
            actual_value=95.5,
            threshold=90.0,
            context={"order_count": 42},
        )

        subject, body = service.format_message(alert, result)

        assert subject == "[SQL Sentinel] Alert: test_alert"
        assert "test_alert" in body
        assert "This is a test alert" in body
        assert "ALERT" in body
        assert "95.5" in body
        assert "90.0" in body
        assert "order_count" in body
        assert "42" in body
