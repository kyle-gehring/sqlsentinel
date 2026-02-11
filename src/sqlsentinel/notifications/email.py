"""Email notification service."""

import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..models.alert import AlertConfig, QueryResult
from ..models.errors import NotificationError
from ..models.notification import EmailConfig, NotificationConfig
from .base import NotificationService


class EmailNotificationService(NotificationService):
    """Email notification service using SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        smtp_username: str | None = None,
        smtp_password: str | None = None,
        use_tls: bool = True,
        from_address: str | None = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 2,
    ):
        """Initialize email notification service.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port (default: 587 for TLS)
            smtp_username: SMTP username (optional)
            smtp_password: SMTP password (optional)
            use_tls: Whether to use TLS encryption (default: True)
            from_address: From email address (defaults to username)
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay_seconds: Delay between retries in seconds (default: 2)

        Raises:
            NotificationError: If configuration is invalid
        """
        if not smtp_host:
            raise NotificationError("SMTP host is required")

        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.from_address = from_address or smtp_username or "sqlsentinel@localhost"
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def send(
        self,
        alert: AlertConfig,
        result: QueryResult,
        notification_config: NotificationConfig,
    ) -> None:
        """Send email notification.

        Args:
            alert: Alert configuration
            result: Query result
            notification_config: Notification configuration

        Raises:
            NotificationError: If email fails to send after retries
        """
        # Extract email config
        if not isinstance(notification_config.config, EmailConfig):
            raise NotificationError(f"Expected EmailConfig, got {type(notification_config.config)}")

        email_config = notification_config.config

        # Format message
        subject, body = self.format_message(alert, result)

        # Override subject if specified in config
        if email_config.subject:
            subject = email_config.subject.format(
                alert_name=alert.name,
                status=result.status,
                actual_value=result.actual_value,
                threshold=result.threshold,
            )

        # Send with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self._send_email(
                    recipients=email_config.recipients,
                    subject=subject,
                    body=body,
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
            f"Failed to send email after {self.max_retries} attempts: {last_error}"
        ) from last_error

    def _send_email(
        self,
        recipients: list[str],
        subject: str,
        body: str,
    ) -> None:
        """Send email via SMTP.

        Args:
            recipients: List of recipient email addresses
            subject: Email subject
            body: Email body (plain text)

        Raises:
            Exception: If SMTP operation fails
        """
        # Create message
        msg = MIMEMultipart("alternative")
        msg["From"] = self.from_address
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        # Add plain text body
        msg.attach(MIMEText(body, "plain"))

        # Connect to SMTP server and send
        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)

            # Login if credentials provided
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            # Send email
            server.sendmail(self.from_address, recipients, msg.as_string())
            server.quit()

        except smtplib.SMTPException as e:
            raise NotificationError(f"SMTP error: {e}") from e
        except Exception as e:
            raise NotificationError(f"Failed to send email: {e}") from e
