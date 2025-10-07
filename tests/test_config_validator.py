"""Tests for ConfigValidator."""

import pytest
from sqlsentinel.config.validator import ConfigValidator
from sqlsentinel.models.alert import AlertConfig
from sqlsentinel.models.errors import ValidationError
from sqlsentinel.models.notification import NotificationChannel


class TestConfigValidator:
    """Test suite for ConfigValidator."""

    def test_validate_valid_config(self):
        """Test validating a valid configuration."""
        config = {
            "alerts": [
                {
                    "name": "Test Alert",
                    "query": "SELECT 'OK' as status",
                    "schedule": "0 9 * * *",
                    "notify": [
                        {
                            "channel": "email",
                            "recipients": ["test@example.com"],
                        }
                    ],
                }
            ]
        }
        validator = ConfigValidator()
        alerts = validator.validate(config)

        assert len(alerts) == 1
        assert isinstance(alerts[0], AlertConfig)
        assert alerts[0].name == "Test Alert"
        assert alerts[0].enabled is True

    def test_validate_multi_alert_config(self):
        """Test validating configuration with multiple alerts."""
        config = {
            "alerts": [
                {
                    "name": "Alert 1",
                    "query": "SELECT 'OK' as status",
                    "schedule": "0 9 * * *",
                },
                {
                    "name": "Alert 2",
                    "query": "SELECT 'ALERT' as status",
                    "schedule": "0 10 * * *",
                },
            ]
        }
        validator = ConfigValidator()
        alerts = validator.validate(config)

        assert len(alerts) == 2
        assert alerts[0].name == "Alert 1"
        assert alerts[1].name == "Alert 2"

    def test_validate_missing_alerts_key(self):
        """Test validation fails when 'alerts' key is missing."""
        config = {"other_key": "value"}
        validator = ConfigValidator()
        with pytest.raises(ValidationError, match="must contain 'alerts' key"):
            validator.validate(config)

    def test_validate_alerts_not_list(self):
        """Test validation fails when 'alerts' is not a list."""
        config = {"alerts": "not a list"}
        validator = ConfigValidator()
        with pytest.raises(ValidationError, match="'alerts' must be a list"):
            validator.validate(config)

    def test_validate_empty_alerts_list(self):
        """Test validation fails when 'alerts' list is empty."""
        config = {"alerts": []}
        validator = ConfigValidator()
        with pytest.raises(ValidationError, match="'alerts' list cannot be empty"):
            validator.validate(config)

    def test_validate_invalid_alert(self):
        """Test validation fails for invalid alert configuration."""
        config = {
            "alerts": [
                {
                    "name": "",  # Empty name is invalid
                    "query": "SELECT 1",
                    "schedule": "0 9 * * *",
                }
            ]
        }
        validator = ConfigValidator()
        with pytest.raises(ValidationError, match="Alert at index 0 is invalid"):
            validator.validate(config)

    def test_validate_duplicate_alert_names(self):
        """Test validation fails for duplicate alert names."""
        config = {
            "alerts": [
                {
                    "name": "Duplicate",
                    "query": "SELECT 'OK' as status",
                    "schedule": "0 9 * * *",
                },
                {
                    "name": "Duplicate",
                    "query": "SELECT 'ALERT' as status",
                    "schedule": "0 10 * * *",
                },
            ]
        }
        validator = ConfigValidator()
        with pytest.raises(ValidationError, match="Duplicate alert names"):
            validator.validate(config)

    def test_validate_email_notification(self):
        """Test validation of email notification configuration."""
        config = {
            "alerts": [
                {
                    "name": "Email Alert",
                    "query": "SELECT 'OK' as status",
                    "schedule": "0 9 * * *",
                    "notify": [
                        {
                            "channel": "email",
                            "recipients": ["user1@example.com", "user2@example.com"],
                            "subject": "Alert Triggered",
                        }
                    ],
                }
            ]
        }
        validator = ConfigValidator()
        alerts = validator.validate(config)

        assert len(alerts[0].notify) == 1
        assert alerts[0].notify[0].channel == NotificationChannel.EMAIL

    def test_validate_slack_notification(self):
        """Test validation of Slack notification configuration."""
        config = {
            "alerts": [
                {
                    "name": "Slack Alert",
                    "query": "SELECT 'OK' as status",
                    "schedule": "0 9 * * *",
                    "notify": [
                        {
                            "channel": "slack",
                            "webhook_url": "https://hooks.slack.com/services/TEST/WEBHOOK",
                        }
                    ],
                }
            ]
        }
        validator = ConfigValidator()
        alerts = validator.validate(config)

        assert len(alerts[0].notify) == 1
        assert alerts[0].notify[0].channel == NotificationChannel.SLACK

    def test_validate_webhook_notification(self):
        """Test validation of webhook notification configuration."""
        config = {
            "alerts": [
                {
                    "name": "Webhook Alert",
                    "query": "SELECT 'OK' as status",
                    "schedule": "0 9 * * *",
                    "notify": [
                        {
                            "channel": "webhook",
                            "url": "https://api.example.com/webhook",
                            "method": "POST",
                            "headers": {"Authorization": "Bearer token123"},
                        }
                    ],
                }
            ]
        }
        validator = ConfigValidator()
        alerts = validator.validate(config)

        assert len(alerts[0].notify) == 1
        assert alerts[0].notify[0].channel == NotificationChannel.WEBHOOK

    def test_validate_invalid_notification_channel(self):
        """Test validation fails for invalid notification channel."""
        config = {
            "alerts": [
                {
                    "name": "Invalid Channel Alert",
                    "query": "SELECT 'OK' as status",
                    "schedule": "0 9 * * *",
                    "notify": [
                        {
                            "channel": "invalid_channel",
                            "some_config": "value",
                        }
                    ],
                }
            ]
        }
        validator = ConfigValidator()
        with pytest.raises(ValidationError, match="Invalid notification channel"):
            validator.validate(config)

    def test_validate_notification_missing_channel(self):
        """Test validation fails when notification lacks channel field."""
        config = {
            "alerts": [
                {
                    "name": "No Channel Alert",
                    "query": "SELECT 'OK' as status",
                    "schedule": "0 9 * * *",
                    "notify": [
                        {
                            "recipients": ["test@example.com"],
                        }
                    ],
                }
            ]
        }
        validator = ConfigValidator()
        with pytest.raises(ValidationError, match="must have 'channel' field"):
            validator.validate(config)

    def test_validate_invalid_email_config(self):
        """Test validation fails for invalid email configuration."""
        config = {
            "alerts": [
                {
                    "name": "Invalid Email Alert",
                    "query": "SELECT 'OK' as status",
                    "schedule": "0 9 * * *",
                    "notify": [
                        {
                            "channel": "email",
                            "recipients": [],  # Empty recipients list is invalid
                        }
                    ],
                }
            ]
        }
        validator = ConfigValidator()
        with pytest.raises(ValidationError, match="Invalid configuration for email"):
            validator.validate(config)
