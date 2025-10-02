"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_alert_config():
    """Sample alert configuration for testing."""
    return {
        "name": "test_alert",
        "description": "Test alert description",
        "query": "SELECT 'ALERT' as status, 100 as actual_value, 50 as threshold",
        "schedule": "0 9 * * *",
        "enabled": True,
    }


@pytest.fixture
def sample_email_notification():
    """Sample email notification config for testing."""
    return {
        "channel": "email",
        "config": {"recipients": ["test@example.com"], "subject": "Test Alert"},
    }


@pytest.fixture
def sample_slack_notification():
    """Sample Slack notification config for testing."""
    return {
        "channel": "slack",
        "config": {
            "webhook_url": "https://hooks.slack.com/services/TEST/TEST/TEST",
            "channel": "#alerts",
        },
    }


@pytest.fixture
def sample_webhook_notification():
    """Sample webhook notification config for testing."""
    return {
        "channel": "webhook",
        "config": {"url": "https://example.com/webhook", "method": "POST"},
    }
