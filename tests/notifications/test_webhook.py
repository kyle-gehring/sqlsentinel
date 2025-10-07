"""Tests for webhook notification service."""

from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError, URLError

import pytest
from sqlsentinel.models.alert import AlertConfig, QueryResult
from sqlsentinel.models.errors import NotificationError
from sqlsentinel.models.notification import (
    NotificationChannel,
    NotificationConfig,
    WebhookConfig,
)
from sqlsentinel.notifications.webhook import WebhookNotificationService


class TestWebhookNotificationServiceInit:
    """Tests for WebhookNotificationService initialization."""

    def test_init_with_valid_url(self):
        """Test initialization with valid URL."""
        service = WebhookNotificationService(url="https://example.com/webhook")
        assert service.url == "https://example.com/webhook"
        assert service.method == "POST"
        assert service.headers == {}
        assert service.max_retries == 3
        assert service.retry_delay_seconds == 1
        assert service.timeout_seconds == 30
        assert service.verify_ssl is True

    def test_init_with_http_url(self):
        """Test initialization with HTTP URL."""
        service = WebhookNotificationService(url="http://example.com/webhook")
        assert service.url == "http://example.com/webhook"

    def test_init_with_custom_method(self):
        """Test initialization with custom HTTP method."""
        service = WebhookNotificationService(
            url="https://example.com/webhook",
            method="PUT",
        )
        assert service.method == "PUT"

    def test_init_with_lowercase_method(self):
        """Test initialization with lowercase HTTP method."""
        service = WebhookNotificationService(
            url="https://example.com/webhook",
            method="post",
        )
        assert service.method == "POST"

    def test_init_with_custom_headers(self):
        """Test initialization with custom headers."""
        headers = {"Authorization": "Bearer token123", "X-Custom": "value"}
        service = WebhookNotificationService(
            url="https://example.com/webhook",
            headers=headers,
        )
        assert service.headers == headers

    def test_init_with_custom_retry_settings(self):
        """Test initialization with custom retry settings."""
        service = WebhookNotificationService(
            url="https://example.com/webhook",
            max_retries=5,
            retry_delay_seconds=2,
            timeout_seconds=60,
        )
        assert service.max_retries == 5
        assert service.retry_delay_seconds == 2
        assert service.timeout_seconds == 60

    def test_init_with_ssl_verification_disabled(self):
        """Test initialization with SSL verification disabled."""
        service = WebhookNotificationService(
            url="https://example.com/webhook",
            verify_ssl=False,
        )
        assert service.verify_ssl is False

    def test_init_with_empty_url(self):
        """Test initialization with empty URL."""
        with pytest.raises(NotificationError, match="Webhook URL is required"):
            WebhookNotificationService(url="")

    def test_init_with_invalid_url_scheme(self):
        """Test initialization with invalid URL scheme."""
        with pytest.raises(NotificationError, match="Webhook URL must start with"):
            WebhookNotificationService(url="ftp://example.com/webhook")

    def test_init_with_invalid_method(self):
        """Test initialization with invalid HTTP method."""
        with pytest.raises(NotificationError, match="Invalid HTTP method"):
            WebhookNotificationService(
                url="https://example.com/webhook",
                method="DELETE",
            )


class TestWebhookNotificationServiceBuildPayload:
    """Tests for webhook payload building."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = WebhookNotificationService(url="https://example.com/webhook")

    def test_build_payload_minimal(self):
        """Test payload building with minimal data."""
        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
        )
        result = QueryResult(status="ALERT")

        payload = self.service._build_payload(alert, result)

        assert payload["alert_name"] == "test_alert"
        assert payload["status"] == "ALERT"
        assert payload["description"] is None
        assert payload["actual_value"] is None
        assert payload["threshold"] is None
        assert "context" not in payload

    def test_build_payload_full(self):
        """Test payload building with full data."""
        alert = AlertConfig(
            name="revenue_alert",
            description="Revenue below threshold",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
        )
        result = QueryResult(
            status="ALERT",
            actual_value=45000.0,
            threshold=50000.0,
        )

        payload = self.service._build_payload(alert, result)

        assert payload["alert_name"] == "revenue_alert"
        assert payload["status"] == "ALERT"
        assert payload["description"] == "Revenue below threshold"
        assert payload["actual_value"] == 45000.0
        assert payload["threshold"] == 50000.0

    def test_build_payload_with_context(self):
        """Test payload building with additional context."""
        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
        )
        result = QueryResult(
            status="ALERT",
            context={"region": "us-west-2", "service": "api"},
        )

        payload = self.service._build_payload(alert, result)

        assert "context" in payload
        assert payload["context"]["region"] == "us-west-2"
        assert payload["context"]["service"] == "api"


class TestWebhookNotificationServiceSend:
    """Tests for webhook notification sending."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = WebhookNotificationService(url="https://example.com/webhook")
        self.alert = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="* * * * *",
        )
        self.result = QueryResult(status="ALERT", actual_value=100.0)
        self.webhook_config = WebhookConfig(url="https://example.com/webhook")
        self.notification_config = NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            config=self.webhook_config,
        )

    @patch("urllib.request.urlopen")
    def test_send_success_post(self, mock_urlopen):
        """Test successful POST request."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Should not raise
        self.service.send(self.alert, self.result, self.notification_config)

        # Verify webhook was called
        assert mock_urlopen.call_count == 1

    @patch("urllib.request.urlopen")
    def test_send_success_put(self, mock_urlopen):
        """Test successful PUT request."""
        service = WebhookNotificationService(
            url="https://example.com/webhook",
            method="PUT",
        )
        webhook_config = WebhookConfig(
            url="https://example.com/webhook",
            method="PUT",
        )
        notification_config = NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            config=webhook_config,
        )

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        service.send(self.alert, self.result, notification_config)

        assert mock_urlopen.call_count == 1

    @patch("urllib.request.urlopen")
    def test_send_success_get(self, mock_urlopen):
        """Test successful GET request."""
        webhook_config = WebhookConfig(
            url="https://example.com/webhook",
            method="GET",
        )
        notification_config = NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            config=webhook_config,
        )

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        self.service.send(self.alert, self.result, notification_config)

        assert mock_urlopen.call_count == 1

    @patch("urllib.request.urlopen")
    def test_send_with_custom_headers(self, mock_urlopen):
        """Test sending with custom headers."""
        webhook_config = WebhookConfig(
            url="https://example.com/webhook",
            headers={
                "Authorization": "Bearer token123",
                "X-API-Key": "secret",
            },
        )
        notification_config = NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            config=webhook_config,
        )

        mock_response = MagicMock()
        mock_response.getcode.return_value = 201
        mock_urlopen.return_value.__enter__.return_value = mock_response

        self.service.send(self.alert, self.result, notification_config)

        # Verify request was made
        assert mock_urlopen.call_count == 1

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_send_with_retries(self, mock_sleep, mock_urlopen):
        """Test sending with retries on failure."""
        # First two attempts fail, third succeeds
        mock_response_success = MagicMock()
        mock_response_success.getcode.return_value = 200

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
        """Test sending when all retries fail."""
        # All attempts fail
        mock_urlopen.side_effect = URLError("Network error")

        # Should raise NotificationError after max retries
        with pytest.raises(
            NotificationError, match="Failed to send webhook notification after 3 attempts"
        ):
            self.service.send(self.alert, self.result, self.notification_config)

        # Verify all retries were attempted
        assert mock_urlopen.call_count == 3

    @patch("urllib.request.urlopen")
    def test_send_http_error_400(self, mock_urlopen):
        """Test sending with 400 HTTP error."""
        mock_fp = Mock()
        mock_fp.read.return_value = b"Bad request"
        mock_urlopen.side_effect = HTTPError(
            "https://example.com/webhook",
            400,
            "Bad Request",
            {},
            mock_fp,
        )

        with pytest.raises(NotificationError, match="Webhook HTTP error 400"):
            self.service.send(self.alert, self.result, self.notification_config)

    @patch("urllib.request.urlopen")
    def test_send_http_error_500(self, mock_urlopen):
        """Test sending with 500 HTTP error."""
        mock_fp = Mock()
        mock_fp.read.return_value = b"Internal server error"
        mock_urlopen.side_effect = HTTPError(
            "https://example.com/webhook",
            500,
            "Internal Server Error",
            {},
            mock_fp,
        )

        with pytest.raises(NotificationError, match="Webhook HTTP error 500"):
            self.service.send(self.alert, self.result, self.notification_config)

    @patch("urllib.request.urlopen")
    def test_send_invalid_config_type(self, mock_urlopen):
        """Test send with wrong config type."""
        from sqlsentinel.models.notification import EmailConfig

        # Use email config instead of webhook config
        invalid_config = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            config=EmailConfig(recipients=["test@example.com"]),
        )

        with pytest.raises(NotificationError, match="Expected WebhookConfig"):
            self.service.send(self.alert, self.result, invalid_config)

        # Should not call webhook
        assert mock_urlopen.call_count == 0

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_send_exponential_backoff(self, mock_sleep, mock_urlopen):
        """Test that retries use exponential backoff."""
        # All attempts fail
        mock_urlopen.side_effect = URLError("Network error")

        with pytest.raises(NotificationError):
            self.service.send(self.alert, self.result, self.notification_config)

        # Verify exponential backoff delays: 1s, 2s
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # First retry: 1 * 2^0
        mock_sleep.assert_any_call(2)  # Second retry: 1 * 2^1

    @patch("urllib.request.urlopen")
    def test_send_non_2xx_status_code(self, mock_urlopen):
        """Test sending when response is not 2xx."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 404
        mock_response.read.return_value = b"Not found"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(NotificationError, match="Webhook returned non-2xx status code 404"):
            self.service.send(self.alert, self.result, self.notification_config)

    @patch("urllib.request.urlopen")
    def test_send_with_ssl_verification_disabled(self, mock_urlopen):
        """Test sending with SSL verification disabled."""
        service = WebhookNotificationService(
            url="https://example.com/webhook",
            verify_ssl=False,
        )

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        service.send(self.alert, self.result, self.notification_config)

        # Verify request was made
        assert mock_urlopen.call_count == 1
        # Verify context was passed (SSL context)
        call_args = mock_urlopen.call_args
        assert "context" in call_args.kwargs

    @patch("urllib.request.urlopen")
    def test_send_merges_headers(self, mock_urlopen):
        """Test that instance headers are merged with config headers."""
        service = WebhookNotificationService(
            url="https://example.com/webhook",
            headers={"X-Instance": "value1"},
        )
        webhook_config = WebhookConfig(
            url="https://example.com/webhook",
            headers={"X-Config": "value2"},
        )
        notification_config = NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            config=webhook_config,
        )

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        service.send(self.alert, self.result, notification_config)

        # Both headers should be present in the request
        assert mock_urlopen.call_count == 1
