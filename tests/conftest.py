"""Pytest configuration and fixtures."""

from collections.abc import Generator
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlsentinel.database.adapter import DatabaseAdapter
from sqlsentinel.database.schema import SchemaManager
from sqlsentinel.models.alert import AlertConfig
from sqlsentinel.models.notification import NotificationConfig
from sqlsentinel.notifications.factory import NotificationFactory

from tests.test_config import get_smtp_config, load_test_env

# Load environment variables at test session start
load_test_env()


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


# Integration test fixtures


@pytest.fixture
def temp_state_db() -> Generator[Engine, None, None]:
    """Create a temporary in-memory SQLite database for state/history tracking.

    This fixture creates a fresh database for each test and ensures proper cleanup.
    """
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Initialize state and history tables using SchemaManager
    schema_manager = SchemaManager(engine)
    schema_manager.create_schema()

    yield engine

    # Cleanup
    engine.dispose()


@pytest.fixture
def temp_query_db() -> Generator[str, None, None]:
    """Create a temporary in-memory SQLite database for alert queries.

    This database simulates the user's data warehouse with sample business data.
    Returns the connection string.
    """
    import os
    import tempfile

    from sqlalchemy import text

    # Create a temporary file for SQLite database to allow sharing across connections
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    connection_string = f"sqlite:///{db_path}"
    engine = create_engine(connection_string, echo=False)

    # Create sample tables with business data
    with engine.connect() as conn:
        # Orders table for revenue alerts
        conn.execute(
            text(
                """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                amount DECIMAL(10, 2),
                created_at TIMESTAMP,
                status TEXT
            )
        """
            )
        )

        # Metrics table for monitoring alerts
        conn.execute(
            text(
                """
            CREATE TABLE metrics (
                id INTEGER PRIMARY KEY,
                metric_name TEXT,
                value DECIMAL(10, 2),
                recorded_at TIMESTAMP
            )
        """
            )
        )

        conn.commit()

    engine.dispose()

    yield connection_string

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def db_adapter(temp_query_db: str) -> DatabaseAdapter:
    """Create a DatabaseAdapter connected to the temporary query database."""
    adapter = DatabaseAdapter(temp_query_db)
    adapter.connect()
    yield adapter
    adapter.disconnect()


@pytest.fixture
def mock_smtp_server():
    """Mock SMTP server for email notification testing."""
    mock_server = MagicMock()
    mock_server.sendmail = Mock()
    mock_server.quit = Mock()
    return mock_server


@pytest.fixture
def mock_http_responses():
    """Mock HTTP responses for webhook and Slack testing.

    Returns a dictionary that can be used to configure mock responses.
    """
    return {
        "slack": Mock(status_code=200, json=lambda: {"ok": True}),
        "webhook": Mock(status_code=200, json=lambda: {"success": True}),
    }


@pytest.fixture
def notification_factory_with_mocks(mock_smtp_server, mock_http_responses) -> NotificationFactory:
    """Create a NotificationFactory with mocked external services.

    This factory can be used in integration tests without actually sending
    emails or HTTP requests.
    """
    return NotificationFactory(
        smtp_host="localhost",
        smtp_port=587,
        smtp_username="test@example.com",
        smtp_password="password",
        smtp_from_address="noreply@example.com",
    )


@pytest.fixture
def configured_notification_factory() -> NotificationFactory:
    """Create a NotificationFactory with test configuration from environment.

    This factory uses real SMTP configuration from .env file if available,
    allowing integration tests to send real emails for verification.
    """
    smtp_config = get_smtp_config()
    return NotificationFactory(**smtp_config)


@pytest.fixture
def sample_alert_config_model() -> AlertConfig:
    """Create a sample AlertConfig model instance."""
    return AlertConfig(
        name="test_alert",
        description="Test alert for integration testing",
        query="SELECT 'ALERT' as status, 100 as actual_value, 50 as threshold",
        schedule="0 9 * * *",
        enabled=True,
        notify=[],
    )


@pytest.fixture
def alert_with_email_notification() -> AlertConfig:
    """Create an AlertConfig with email notification."""
    return AlertConfig(
        name="email_alert",
        description="Alert with email notification",
        query="SELECT 'ALERT' as status, 100 as actual_value, 50 as threshold",
        schedule="0 9 * * *",
        enabled=True,
        notify=[
            NotificationConfig(
                channel="email",
                config={"recipients": ["test@example.com"], "subject": "Test Alert"},
            )
        ],
    )


@pytest.fixture
def alert_with_slack_notification() -> AlertConfig:
    """Create an AlertConfig with Slack notification."""
    return AlertConfig(
        name="slack_alert",
        description="Alert with Slack notification",
        query="SELECT 'ALERT' as status, 100 as actual_value, 50 as threshold",
        schedule="0 9 * * *",
        enabled=True,
        notify=[
            NotificationConfig(
                channel="slack",
                config={
                    "webhook_url": "https://hooks.slack.com/services/TEST/TEST/TEST",
                },
            )
        ],
    )


@pytest.fixture
def alert_with_webhook_notification() -> AlertConfig:
    """Create an AlertConfig with webhook notification."""
    return AlertConfig(
        name="webhook_alert",
        description="Alert with webhook notification",
        query="SELECT 'ALERT' as status, 100 as actual_value, 50 as threshold",
        schedule="0 9 * * *",
        enabled=True,
        notify=[
            NotificationConfig(
                channel="webhook",
                config={
                    "url": "https://example.com/webhook",
                    "method": "POST",
                },
            )
        ],
    )


@pytest.fixture
def alert_with_multi_channel() -> AlertConfig:
    """Create an AlertConfig with multiple notification channels."""
    return AlertConfig(
        name="multi_channel_alert",
        description="Alert with multiple notification channels",
        query="SELECT 'ALERT' as status, 100 as actual_value, 50 as threshold",
        schedule="0 9 * * *",
        enabled=True,
        notify=[
            NotificationConfig(
                channel="email",
                config={"recipients": ["test@example.com"], "subject": "Multi-Channel Alert"},
            ),
            NotificationConfig(
                channel="slack",
                config={
                    "webhook_url": "https://hooks.slack.com/services/TEST/TEST/TEST",
                },
            ),
            NotificationConfig(
                channel="webhook",
                config={
                    "url": "https://example.com/webhook",
                    "method": "POST",
                },
            ),
        ],
    )
