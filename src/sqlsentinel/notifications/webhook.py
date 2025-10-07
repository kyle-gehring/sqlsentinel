"""Generic webhook notification service."""

import json
import time
import urllib.request
from typing import Any, Optional
from urllib.error import HTTPError, URLError

from ..models.alert import AlertConfig, QueryResult
from ..models.errors import NotificationError
from ..models.notification import NotificationConfig, WebhookConfig
from .base import NotificationService


class WebhookNotificationService(NotificationService):
    """Generic webhook notification service."""

    def __init__(
        self,
        url: str,
        method: str = "POST",
        headers: Optional[dict[str, str]] = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 1,
        timeout_seconds: int = 30,
        verify_ssl: bool = True,
    ):
        """Initialize webhook notification service.

        Args:
            url: Webhook URL
            method: HTTP method (GET, POST, PUT, PATCH)
            headers: Optional HTTP headers
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay_seconds: Initial delay between retries in seconds (default: 1)
            timeout_seconds: Request timeout in seconds (default: 30)
            verify_ssl: Whether to verify SSL certificates (default: True)

        Raises:
            NotificationError: If configuration is invalid
        """
        if not url:
            raise NotificationError("Webhook URL is required")

        if not url.startswith(("http://", "https://")):
            raise NotificationError("Webhook URL must start with http:// or https://")

        valid_methods = ["GET", "POST", "PUT", "PATCH"]
        method_upper = method.upper()
        if method_upper not in valid_methods:
            raise NotificationError(
                f"Invalid HTTP method: {method}. Must be one of {valid_methods}"
            )

        self.url = url
        self.method = method_upper
        self.headers = headers or {}
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.timeout_seconds = timeout_seconds
        self.verify_ssl = verify_ssl

    def send(
        self,
        alert: AlertConfig,
        result: QueryResult,
        notification_config: NotificationConfig,
    ) -> None:
        """Send webhook notification.

        Args:
            alert: Alert configuration
            result: Query result
            notification_config: Notification configuration

        Raises:
            NotificationError: If webhook fails to send after retries
        """
        # Extract webhook config
        if not isinstance(notification_config.config, WebhookConfig):
            raise NotificationError(
                f"Expected WebhookConfig, got {type(notification_config.config)}"
            )

        webhook_config = notification_config.config

        # Build payload with template variable substitution
        payload = self._build_payload(alert, result)

        # Merge headers from config and instance
        merged_headers = {**self.headers, **webhook_config.headers}

        # Send with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self._send_request(
                    url=webhook_config.url,
                    method=webhook_config.method,
                    payload=payload,
                    headers=merged_headers,
                )
                return  # Success
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay_seconds * (2**attempt)
                    time.sleep(delay)

        # All retries failed
        raise NotificationError(
            f"Failed to send webhook notification after {self.max_retries} attempts: {last_error}"
        ) from last_error

    def _build_payload(
        self,
        alert: AlertConfig,
        result: QueryResult,
    ) -> dict[str, Any]:
        """Build webhook payload with alert data.

        Args:
            alert: Alert configuration
            result: Query result

        Returns:
            Payload dictionary
        """
        payload: dict[str, Any] = {
            "alert_name": alert.name,
            "status": result.status,
            "description": alert.description,
            "actual_value": result.actual_value,
            "threshold": result.threshold,
        }

        # Add context fields
        if result.context:
            payload["context"] = result.context

        return payload

    def _send_request(
        self,
        url: str,
        method: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        """Send HTTP request to webhook.

        Args:
            url: Webhook URL
            method: HTTP method
            payload: Request payload
            headers: HTTP headers

        Raises:
            NotificationError: If request fails
        """
        try:
            # Prepare request data
            data = None
            request_headers = headers.copy()

            # For POST, PUT, PATCH, send JSON body
            if method in ["POST", "PUT", "PATCH"]:
                data = json.dumps(payload).encode("utf-8")
                # Set Content-Type if not already specified
                if "Content-Type" not in request_headers:
                    request_headers["Content-Type"] = "application/json"

            # Create request
            req = urllib.request.Request(
                url,
                data=data,
                headers=request_headers,
                method=method,
            )

            # Handle SSL verification
            context = None
            if not self.verify_ssl:
                import ssl

                context = ssl._create_unverified_context()

            # Send request
            with urllib.request.urlopen(
                req, timeout=self.timeout_seconds, context=context
            ) as response:
                status_code = response.getcode()

                # Check for successful status codes (2xx)
                if status_code < 200 or status_code >= 300:
                    response_body = response.read().decode("utf-8")
                    raise NotificationError(
                        f"Webhook returned non-2xx status code {status_code}: {response_body}"
                    )

        except HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else "No error details"
            raise NotificationError(f"Webhook HTTP error {e.code}: {error_body}") from e
        except URLError as e:
            raise NotificationError(f"Webhook network error: {e.reason}") from e
        except TimeoutError as e:
            raise NotificationError(f"Webhook timeout after {self.timeout_seconds}s") from e
        except Exception as e:
            raise NotificationError(f"Failed to send webhook: {e}") from e
