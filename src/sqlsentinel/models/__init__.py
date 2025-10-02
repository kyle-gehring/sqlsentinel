"""Core data models for SQL Sentinel."""

from .alert import AlertConfig, ExecutionResult, QueryResult
from .errors import (
    ConfigurationError,
    ExecutionError,
    NotificationError,
    SQLSentinelError,
    ValidationError,
)
from .notification import (
    EmailConfig,
    NotificationChannel,
    NotificationConfig,
    SlackConfig,
    WebhookConfig,
)

__all__ = [
    # Alert models
    "AlertConfig",
    "ExecutionResult",
    "QueryResult",
    # Error models
    "SQLSentinelError",
    "ConfigurationError",
    "ValidationError",
    "ExecutionError",
    "NotificationError",
    # Notification models
    "NotificationChannel",
    "NotificationConfig",
    "EmailConfig",
    "SlackConfig",
    "WebhookConfig",
]
