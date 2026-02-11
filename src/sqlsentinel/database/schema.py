"""Database schema management for SQL Sentinel internal tables."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..models.errors import ExecutionError


class SchemaManager:
    """Manages SQL Sentinel internal database schema."""

    def __init__(self, engine: Engine):
        """Initialize schema manager.

        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine
        self.metadata = MetaData()
        self._define_tables()

    def _define_tables(self) -> None:
        """Define SQL Sentinel internal tables."""
        # Execution history table
        self.executions_table = Table(
            "sqlsentinel_executions",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("alert_name", String(255), nullable=False, index=True),
            Column("executed_at", DateTime, nullable=False, index=True),
            Column("execution_duration_ms", Float, nullable=False),
            Column("status", String(50), nullable=False),  # ALERT, OK, ERROR
            Column("actual_value", Float, nullable=True),
            Column("threshold", Float, nullable=True),
            Column("query", Text, nullable=False),
            Column("error_message", Text, nullable=True),
            Column("triggered_by", String(50), nullable=False),  # CRON, MANUAL, API
            Column("notification_sent", Boolean, nullable=False, default=False),
            Column("notification_error", Text, nullable=True),
            Column("context_data", Text, nullable=True),  # JSON string of additional context
        )

        # Alert state table
        self.state_table = Table(
            "sqlsentinel_state",
            self.metadata,
            Column("alert_name", String(255), primary_key=True),
            Column("last_executed_at", DateTime, nullable=True),
            Column("last_alert_at", DateTime, nullable=True),
            Column("last_ok_at", DateTime, nullable=True),
            Column("consecutive_alerts", Integer, nullable=False, default=0),
            Column("consecutive_oks", Integer, nullable=False, default=0),
            Column("current_status", String(50), nullable=True),  # ALERT, OK, ERROR
            Column("silenced_until", DateTime, nullable=True),
            Column("escalation_count", Integer, nullable=False, default=0),
            Column("notification_failures", Integer, nullable=False, default=0),
            Column("last_notification_channel", String(50), nullable=True),
            Column("updated_at", DateTime, nullable=False),
        )

        # Configuration tracking table (optional, for audit trail)
        self.configs_table = Table(
            "sqlsentinel_configs",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("alert_name", String(255), nullable=False, index=True),
            Column("config_hash", String(64), nullable=False),
            Column("config_yaml", Text, nullable=False),
            Column("loaded_at", DateTime, nullable=False),
            Column("active", Boolean, nullable=False, default=True),
        )

    def create_schema(self) -> None:
        """Create all SQL Sentinel internal tables.

        Raises:
            ExecutionError: If schema creation fails
        """
        try:
            self.metadata.create_all(self.engine)
        except SQLAlchemyError as e:
            raise ExecutionError(f"Failed to create schema: {e}") from e

    def drop_schema(self) -> None:
        """Drop all SQL Sentinel internal tables.

        WARNING: This will delete all execution history and state data.

        Raises:
            ExecutionError: If schema drop fails
        """
        try:
            self.metadata.drop_all(self.engine)
        except SQLAlchemyError as e:
            raise ExecutionError(f"Failed to drop schema: {e}") from e

    def schema_exists(self) -> bool:
        """Check if SQL Sentinel schema exists.

        Returns:
            True if at least one SQL Sentinel table exists, False otherwise
        """
        try:
            # Check if executions table exists
            return self.engine.dialect.has_table(self.engine.connect(), "sqlsentinel_executions")
        except SQLAlchemyError:
            return False

    def initialize_schema(self, drop_existing: bool = False) -> None:
        """Initialize SQL Sentinel schema.

        Args:
            drop_existing: If True, drop existing schema before creating

        Raises:
            ExecutionError: If initialization fails
        """
        if drop_existing:
            self.drop_schema()
        self.create_schema()


def create_schema_from_connection_string(
    connection_string: str, drop_existing: bool = False
) -> None:
    """Create SQL Sentinel schema from connection string.

    Convenience function for creating schema without manually creating engine.

    Args:
        connection_string: SQLAlchemy connection string
        drop_existing: If True, drop existing schema before creating

    Raises:
        ExecutionError: If schema creation fails
    """
    try:
        engine = create_engine(connection_string)
        manager = SchemaManager(engine)
        manager.initialize_schema(drop_existing=drop_existing)
    except SQLAlchemyError as e:
        raise ExecutionError(f"Failed to create schema: {e}") from e
