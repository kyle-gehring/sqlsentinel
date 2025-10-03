"""Configuration validator for SQL Sentinel."""

from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ..models.alert import AlertConfig
from ..models.errors import ValidationError
from ..models.notification import (
    EmailConfig,
    NotificationChannel,
    NotificationConfig,
    SlackConfig,
    WebhookConfig,
)


class ConfigValidator:
    """Validates alert configurations against the schema."""

    def validate(self, config: dict[str, Any]) -> list[AlertConfig]:
        """Validate configuration and return list of AlertConfig objects.

        Args:
            config: Raw configuration dictionary from YAML

        Returns:
            List of validated AlertConfig objects

        Raises:
            ValidationError: If configuration is invalid
        """
        if "alerts" not in config:
            raise ValidationError("Configuration must contain 'alerts' key")

        alerts = config["alerts"]
        if not isinstance(alerts, list):
            raise ValidationError("'alerts' must be a list")

        if len(alerts) == 0:
            raise ValidationError("'alerts' list cannot be empty")

        validated_alerts = []
        for idx, alert_dict in enumerate(alerts):
            try:
                # Transform notification configs before validation
                if "notify" in alert_dict:
                    alert_dict["notify"] = self._transform_notifications(alert_dict["notify"])

                validated_alert = AlertConfig(**alert_dict)
                validated_alerts.append(validated_alert)
            except PydanticValidationError as e:
                raise ValidationError(f"Alert at index {idx} is invalid: {e}") from e
            except Exception as e:
                raise ValidationError(f"Alert at index {idx} failed validation: {e}") from e

        # Validate unique alert names
        alert_names = [alert.name for alert in validated_alerts]
        if len(alert_names) != len(set(alert_names)):
            duplicates = [name for name in alert_names if alert_names.count(name) > 1]
            raise ValidationError(f"Duplicate alert names found: {set(duplicates)}")

        return validated_alerts

    def _transform_notifications(
        self, notify_list: list[dict[str, Any]]
    ) -> list[NotificationConfig]:
        """Transform notification dictionaries to NotificationConfig objects.

        Args:
            notify_list: List of notification configuration dictionaries

        Returns:
            List of NotificationConfig objects

        Raises:
            ValidationError: If notification configuration is invalid
        """
        notifications = []
        for notify_dict in notify_list:
            if "channel" not in notify_dict:
                raise ValidationError("Notification must have 'channel' field")

            channel_str = notify_dict["channel"]
            try:
                channel = NotificationChannel(channel_str)
            except ValueError as e:
                valid_channels = [c.value for c in NotificationChannel]
                raise ValidationError(
                    f"Invalid notification channel '{channel_str}'. "
                    f"Valid channels: {valid_channels}"
                ) from e

            # Extract channel-specific config
            config_data = {k: v for k, v in notify_dict.items() if k != "channel"}

            # Create appropriate config object based on channel type
            try:
                config: EmailConfig | SlackConfig | WebhookConfig
                if channel == NotificationChannel.EMAIL:
                    config = EmailConfig(**config_data)
                elif channel == NotificationChannel.SLACK:
                    config = SlackConfig(**config_data)
                elif channel == NotificationChannel.WEBHOOK:
                    config = WebhookConfig(**config_data)
                else:
                    raise ValidationError(f"Unsupported channel: {channel}")

                notifications.append(NotificationConfig(channel=channel, config=config))
            except PydanticValidationError as e:
                raise ValidationError(
                    f"Invalid configuration for {channel_str} notification: {e}"
                ) from e

        return notifications
