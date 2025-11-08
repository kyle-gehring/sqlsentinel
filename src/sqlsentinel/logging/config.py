"""Logging configuration for SQL Sentinel."""

import logging
import os
from typing import Any

from pythonjsonlogger import jsonlogger


class ContextFilter(logging.Filter):
    """Filter to add contextual information to log records."""

    def __init__(self) -> None:
        """Initialize context filter."""
        super().__init__()
        self.context: dict[str, Any] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context fields to the log record.

        Args:
            record: Log record to filter

        Returns:
            True to allow the record to be logged
        """
        # Add context fields to record
        for key, value in self.context.items():
            setattr(record, key, value)
        return True

    def set_context(self, **kwargs: Any) -> None:
        """Set context fields to be added to all log records.

        Args:
            **kwargs: Key-value pairs to add to context
        """
        self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context fields."""
        self.context.clear()


# Global context filter instance
_context_filter = ContextFilter()


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: str | None = None,
) -> None:
    """Configure SQL Sentinel logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Log format ('json' or 'text')
        log_file: Optional file path for logging output
    """
    # Get log level
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter based on format choice
    if log_format.lower() == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            timestamp=True,
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        # Text format
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_context_filter)
    root_logger.addHandler(console_handler)

    # Create file handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            file_handler.addFilter(_context_filter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.error(f"Failed to create log file handler: {e}")

    # Silence some verbose loggers
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("watchdog").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_context(**kwargs: Any) -> None:
    """Set contextual fields to be added to all log records.

    Args:
        **kwargs: Key-value pairs to add to log context
    """
    _context_filter.set_context(**kwargs)


def clear_context() -> None:
    """Clear all contextual fields from log records."""
    _context_filter.clear_context()


def configure_from_env() -> None:
    """Configure logging from environment variables.

    Environment variables:
    - LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR; default: INFO)
    - LOG_FORMAT: Log format (json or text; default: json)
    - LOG_FILE: Optional log file path
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    log_format = os.environ.get("LOG_FORMAT", "json")
    log_file = os.environ.get("LOG_FILE")

    configure_logging(
        log_level=log_level,
        log_format=log_format,
        log_file=log_file,
    )
