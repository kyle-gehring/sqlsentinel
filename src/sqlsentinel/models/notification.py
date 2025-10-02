"""Notification configuration models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class NotificationChannel(str, Enum):
    """Supported notification channels."""

    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


class EmailConfig(BaseModel):
    """Email notification configuration."""

    recipients: list[str] = Field(..., min_length=1, description="Email recipients")
    subject: str | None = Field(None, description="Email subject template")

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, v: list[str]) -> list[str]:
        """Validate email addresses."""
        for email in v:
            if "@" not in email:
                raise ValueError(f"Invalid email address: {email}")
        return v


class SlackConfig(BaseModel):
    """Slack notification configuration."""

    webhook_url: str = Field(..., description="Slack webhook URL")
    channel: str | None = Field(None, description="Slack channel override")
    username: str | None = Field(None, description="Bot username override")

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        """Validate Slack webhook URL."""
        if not v.startswith("https://hooks.slack.com/"):
            raise ValueError("Invalid Slack webhook URL")
        return v


class WebhookConfig(BaseModel):
    """Generic webhook notification configuration."""

    url: str = Field(..., description="Webhook URL")
    method: str = Field("POST", description="HTTP method")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method."""
        if v.upper() not in ["GET", "POST", "PUT", "PATCH"]:
            raise ValueError(f"Invalid HTTP method: {v}")
        return v.upper()


class NotificationConfig(BaseModel):
    """Notification configuration for an alert."""

    channel: NotificationChannel = Field(..., description="Notification channel type")
    config: EmailConfig | SlackConfig | WebhookConfig = Field(
        ..., description="Channel-specific configuration"
    )

    @field_validator("config")
    @classmethod
    def validate_config(cls, v: Any, info: Any) -> Any:
        """Validate that config matches channel type."""
        channel = info.data.get("channel")
        if channel == NotificationChannel.EMAIL and not isinstance(v, EmailConfig):
            raise ValueError("Email channel requires EmailConfig")
        elif channel == NotificationChannel.SLACK and not isinstance(v, SlackConfig):
            raise ValueError("Slack channel requires SlackConfig")
        elif channel == NotificationChannel.WEBHOOK and not isinstance(v, WebhookConfig):
            raise ValueError("Webhook channel requires WebhookConfig")
        return v
