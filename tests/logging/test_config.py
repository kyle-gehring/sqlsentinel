"""Tests for logging configuration."""

import logging
import os
import tempfile

from sqlsentinel.logging.config import (
    ContextFilter,
    clear_context,
    configure_from_env,
    configure_logging,
    get_logger,
    set_context,
)


class TestContextFilter:
    """Test ContextFilter class."""

    def setup_method(self):
        """Set up test method."""
        self.filter = ContextFilter()

    def test_initialization(self):
        """Test filter initialization."""
        assert isinstance(self.filter.context, dict)
        assert len(self.filter.context) == 0

    def test_filter_adds_context_to_record(self):
        """Test that filter adds context fields to log record."""
        # Set context
        self.filter.set_context(alert_name="test_alert", execution_id="123")

        # Create log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Apply filter
        result = self.filter.filter(record)

        assert result is True
        assert hasattr(record, "alert_name")
        assert record.alert_name == "test_alert"
        assert hasattr(record, "execution_id")
        assert record.execution_id == "123"

    def test_filter_returns_true(self):
        """Test that filter always returns True."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = self.filter.filter(record)
        assert result is True

    def test_set_context(self):
        """Test setting context fields."""
        self.filter.set_context(key1="value1", key2="value2")

        assert self.filter.context["key1"] == "value1"
        assert self.filter.context["key2"] == "value2"

    def test_set_context_updates_existing(self):
        """Test that set_context updates existing fields."""
        self.filter.set_context(key1="value1")
        self.filter.set_context(key1="updated", key2="value2")

        assert self.filter.context["key1"] == "updated"
        assert self.filter.context["key2"] == "value2"

    def test_clear_context(self):
        """Test clearing context fields."""
        self.filter.set_context(key1="value1", key2="value2")
        self.filter.clear_context()

        assert len(self.filter.context) == 0

    def test_filter_with_empty_context(self):
        """Test filter with empty context."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = self.filter.filter(record)
        assert result is True


class TestConfigureLogging:
    """Test configure_logging function."""

    def setup_method(self):
        """Set up test method."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def teardown_method(self):
        """Clean up after test."""
        # Reset logging configuration
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        clear_context()

    def test_configure_logging_default(self):
        """Test configure_logging with default parameters."""
        configure_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1  # Console handler only

    def test_configure_logging_debug_level(self):
        """Test configure_logging with DEBUG level."""
        configure_logging(log_level="DEBUG")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_logging_warning_level(self):
        """Test configure_logging with WARNING level."""
        configure_logging(log_level="WARNING")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_configure_logging_error_level(self):
        """Test configure_logging with ERROR level."""
        configure_logging(log_level="ERROR")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR

    def test_configure_logging_invalid_level(self):
        """Test configure_logging with invalid level defaults to INFO."""
        configure_logging(log_level="INVALID")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_configure_logging_json_format(self):
        """Test configure_logging with JSON format."""
        configure_logging(log_format="json")

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1
        # JSON formatter is set
        handler = root_logger.handlers[0]
        assert handler.formatter is not None

    def test_configure_logging_text_format(self):
        """Test configure_logging with text format."""
        configure_logging(log_format="text")

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert handler.formatter is not None
        assert isinstance(handler.formatter, logging.Formatter)

    def test_configure_logging_with_file(self):
        """Test configure_logging with log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            configure_logging(log_file=log_file)

            root_logger = logging.getLogger()
            # Should have console + file handler
            assert len(root_logger.handlers) == 2

            # Verify log file exists
            assert os.path.exists(log_file)

    def test_configure_logging_invalid_file_path(self):
        """Test configure_logging with invalid file path."""
        # Try to write to a directory that doesn't exist
        invalid_path = "/nonexistent/directory/test.log"

        # Should not raise exception, just log error
        configure_logging(log_file=invalid_path)

        root_logger = logging.getLogger()
        # Should only have console handler
        assert len(root_logger.handlers) == 1

    def test_configure_logging_removes_existing_handlers(self):
        """Test that configure_logging removes existing handlers."""
        # Add a handler first
        root_logger = logging.getLogger()
        existing_handler = logging.StreamHandler()
        root_logger.addHandler(existing_handler)

        # Configure logging
        configure_logging()

        # Old handler should be removed
        assert existing_handler not in root_logger.handlers
        assert len(root_logger.handlers) == 1

    def test_configure_logging_sets_apscheduler_level(self):
        """Test that configure_logging sets apscheduler log level."""
        configure_logging(log_level="DEBUG")

        apscheduler_logger = logging.getLogger("apscheduler")
        assert apscheduler_logger.level == logging.WARNING

    def test_configure_logging_sets_watchdog_level(self):
        """Test that configure_logging sets watchdog log level."""
        configure_logging(log_level="DEBUG")

        watchdog_logger = logging.getLogger("watchdog")
        assert watchdog_logger.level == logging.WARNING

    def test_configure_logging_lowercase_format(self):
        """Test configure_logging with lowercase format."""
        configure_logging(log_format="JSON")
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1

    def test_configure_logging_text_format_uppercase(self):
        """Test configure_logging with uppercase TEXT format."""
        configure_logging(log_format="TEXT")
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger(self):
        """Test get_logger returns logger instance."""
        logger = get_logger("test_logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_get_logger_different_names(self):
        """Test get_logger with different names."""
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")

        assert logger1.name == "logger1"
        assert logger2.name == "logger2"
        assert logger1 is not logger2

    def test_get_logger_same_name(self):
        """Test get_logger returns same instance for same name."""
        logger1 = get_logger("same_logger")
        logger2 = get_logger("same_logger")

        assert logger1 is logger2


class TestContextManagement:
    """Test context management functions."""

    def setup_method(self):
        """Set up test method."""
        clear_context()

    def teardown_method(self):
        """Clean up after test."""
        clear_context()

    def test_set_context(self):
        """Test set_context function."""
        set_context(alert_name="test_alert", status="ok")

        # Verify context is set (indirectly by using it)
        from sqlsentinel.logging.config import _context_filter

        assert _context_filter.context["alert_name"] == "test_alert"
        assert _context_filter.context["status"] == "ok"

    def test_set_context_multiple_calls(self):
        """Test multiple calls to set_context."""
        set_context(key1="value1")
        set_context(key2="value2")

        from sqlsentinel.logging.config import _context_filter

        assert _context_filter.context["key1"] == "value1"
        assert _context_filter.context["key2"] == "value2"

    def test_clear_context(self):
        """Test clear_context function."""
        set_context(key1="value1", key2="value2")
        clear_context()

        from sqlsentinel.logging.config import _context_filter

        assert len(_context_filter.context) == 0

    def test_set_context_with_special_characters(self):
        """Test set_context with special characters."""
        set_context(
            alert_name="test-alert_123",
            message="Test: message with special chars!",
        )

        from sqlsentinel.logging.config import _context_filter

        assert _context_filter.context["alert_name"] == "test-alert_123"
        assert "special chars" in _context_filter.context["message"]


class TestConfigureFromEnv:
    """Test configure_from_env function."""

    def setup_method(self):
        """Set up test method."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def teardown_method(self):
        """Clean up after test."""
        # Reset logging configuration
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Clean up environment variables
        for key in ["LOG_LEVEL", "LOG_FORMAT", "LOG_FILE"]:
            if key in os.environ:
                del os.environ[key]

    def test_configure_from_env_defaults(self):
        """Test configure_from_env with no environment variables."""
        configure_from_env()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1

    def test_configure_from_env_log_level(self):
        """Test configure_from_env with LOG_LEVEL set."""
        os.environ["LOG_LEVEL"] = "DEBUG"
        configure_from_env()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_from_env_log_format(self):
        """Test configure_from_env with LOG_FORMAT set."""
        os.environ["LOG_FORMAT"] = "text"
        configure_from_env()

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1

    def test_configure_from_env_log_file(self):
        """Test configure_from_env with LOG_FILE set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test_env.log")
            os.environ["LOG_FILE"] = log_file

            configure_from_env()

            root_logger = logging.getLogger()
            # Should have console + file handler
            assert len(root_logger.handlers) == 2
            assert os.path.exists(log_file)

    def test_configure_from_env_all_options(self):
        """Test configure_from_env with all environment variables set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test_all.log")
            os.environ["LOG_LEVEL"] = "WARNING"
            os.environ["LOG_FORMAT"] = "json"
            os.environ["LOG_FILE"] = log_file

            configure_from_env()

            root_logger = logging.getLogger()
            assert root_logger.level == logging.WARNING
            assert len(root_logger.handlers) == 2
            assert os.path.exists(log_file)


class TestLoggingIntegration:
    """Integration tests for logging configuration."""

    def setup_method(self):
        """Set up test method."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        clear_context()

    def teardown_method(self):
        """Clean up after test."""
        # Reset logging configuration
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        clear_context()

    def test_logging_with_context(self):
        """Test that context fields appear in log records."""
        configure_logging(log_format="text")
        set_context(alert_name="test_alert", execution_id="12345")

        logger = get_logger("test")

        # Create a custom handler to capture log records
        records = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        test_handler = TestHandler()
        logging.getLogger().addHandler(test_handler)

        logger.info("Test message")

        assert len(records) == 1
        assert hasattr(records[0], "alert_name")
        assert records[0].alert_name == "test_alert"
        assert records[0].execution_id == "12345"

    def test_logging_to_file(self):
        """Test logging to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test_integration.log")
            configure_logging(log_file=log_file, log_format="text")

            logger = get_logger("test")
            logger.info("Test message to file")

            # Verify log file has content
            assert os.path.exists(log_file)
            with open(log_file) as f:
                content = f.read()
                assert "Test message to file" in content

    def test_json_logging_format(self):
        """Test JSON logging format."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test_json.log")
            configure_logging(log_file=log_file, log_format="json")

            logger = get_logger("test")
            logger.info("Test JSON message")

            # Verify log file contains valid JSON
            assert os.path.exists(log_file)
            with open(log_file) as f:
                lines = f.readlines()
                assert len(lines) > 0
                # Each line should be valid JSON
                log_entry = json.loads(lines[0])
                assert "message" in log_entry
                assert "Test JSON message" in log_entry["message"]
