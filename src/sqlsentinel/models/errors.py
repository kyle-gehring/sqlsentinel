"""Error hierarchy for SQL Sentinel."""


class SQLSentinelError(Exception):
    """Base exception for all SQL Sentinel errors."""

    pass


class ConfigurationError(SQLSentinelError):
    """Raised when there is an error in configuration."""

    pass


class ValidationError(SQLSentinelError):
    """Raised when data validation fails."""

    pass


class ExecutionError(SQLSentinelError):
    """Raised when alert execution fails."""

    pass


class NotificationError(SQLSentinelError):
    """Raised when notification delivery fails."""

    pass
