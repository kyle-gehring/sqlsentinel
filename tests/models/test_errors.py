"""Tests for error hierarchy."""

from sqlsentinel.models.errors import (
    ConfigurationError,
    ExecutionError,
    NotificationError,
    SQLSentinelError,
    ValidationError,
)


def test_base_exception():
    """Test base exception."""
    error = SQLSentinelError("test error")
    assert str(error) == "test error"
    assert isinstance(error, Exception)


def test_configuration_error():
    """Test configuration error."""
    error = ConfigurationError("config error")
    assert str(error) == "config error"
    assert isinstance(error, SQLSentinelError)


def test_validation_error():
    """Test validation error."""
    error = ValidationError("validation error")
    assert str(error) == "validation error"
    assert isinstance(error, SQLSentinelError)


def test_execution_error():
    """Test execution error."""
    error = ExecutionError("execution error")
    assert str(error) == "execution error"
    assert isinstance(error, SQLSentinelError)


def test_notification_error():
    """Test notification error."""
    error = NotificationError("notification error")
    assert str(error) == "notification error"
    assert isinstance(error, SQLSentinelError)
