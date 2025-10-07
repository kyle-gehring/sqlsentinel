"""Tests for database schema management."""

import pytest
from sqlalchemy import create_engine, inspect
from sqlsentinel.database.schema import SchemaManager, create_schema_from_connection_string
from sqlsentinel.models.errors import ExecutionError


class TestSchemaManager:
    """Test SchemaManager class."""

    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing."""
        return create_engine("sqlite:///:memory:")

    @pytest.fixture
    def schema_manager(self, engine):
        """Create SchemaManager instance."""
        return SchemaManager(engine)

    def test_init(self, schema_manager, engine):
        """Test SchemaManager initialization."""
        assert schema_manager.engine == engine
        assert schema_manager.metadata is not None
        assert schema_manager.executions_table is not None
        assert schema_manager.state_table is not None
        assert schema_manager.configs_table is not None

    def test_create_schema(self, schema_manager, engine):
        """Test schema creation."""
        schema_manager.create_schema()

        # Verify tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "sqlsentinel_executions" in tables
        assert "sqlsentinel_state" in tables
        assert "sqlsentinel_configs" in tables

    def test_executions_table_columns(self, schema_manager, engine):
        """Test executions table has correct columns."""
        schema_manager.create_schema()

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("sqlsentinel_executions")}

        expected_columns = {
            "id",
            "alert_name",
            "executed_at",
            "execution_duration_ms",
            "status",
            "actual_value",
            "threshold",
            "query",
            "error_message",
            "triggered_by",
            "notification_sent",
            "notification_error",
            "context_data",
        }

        assert columns == expected_columns

    def test_state_table_columns(self, schema_manager, engine):
        """Test state table has correct columns."""
        schema_manager.create_schema()

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("sqlsentinel_state")}

        expected_columns = {
            "alert_name",
            "last_executed_at",
            "last_alert_at",
            "last_ok_at",
            "consecutive_alerts",
            "consecutive_oks",
            "current_status",
            "silenced_until",
            "escalation_count",
            "notification_failures",
            "last_notification_channel",
            "updated_at",
        }

        assert columns == expected_columns

    def test_configs_table_columns(self, schema_manager, engine):
        """Test configs table has correct columns."""
        schema_manager.create_schema()

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("sqlsentinel_configs")}

        expected_columns = {
            "id",
            "alert_name",
            "config_hash",
            "config_yaml",
            "loaded_at",
            "active",
        }

        assert columns == expected_columns

    def test_drop_schema(self, schema_manager, engine):
        """Test schema drop."""
        schema_manager.create_schema()
        schema_manager.drop_schema()

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "sqlsentinel_executions" not in tables
        assert "sqlsentinel_state" not in tables
        assert "sqlsentinel_configs" not in tables

    def test_schema_exists_when_created(self, schema_manager):
        """Test schema_exists returns True when schema exists."""
        schema_manager.create_schema()
        assert schema_manager.schema_exists() is True

    def test_schema_exists_when_not_created(self, schema_manager):
        """Test schema_exists returns False when schema doesn't exist."""
        assert schema_manager.schema_exists() is False

    def test_initialize_schema(self, schema_manager, engine):
        """Test initialize_schema creates tables."""
        schema_manager.initialize_schema()

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "sqlsentinel_executions" in tables
        assert "sqlsentinel_state" in tables
        assert "sqlsentinel_configs" in tables

    def test_initialize_schema_drop_existing(self, schema_manager, engine):
        """Test initialize_schema with drop_existing=True."""
        # Create schema first
        schema_manager.create_schema()

        # Reinitialize with drop
        schema_manager.initialize_schema(drop_existing=True)

        # Tables should still exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "sqlsentinel_executions" in tables
        assert "sqlsentinel_state" in tables
        assert "sqlsentinel_configs" in tables


class TestCreateSchemaFromConnectionString:
    """Test create_schema_from_connection_string function."""

    def test_create_schema_from_connection_string(self):
        """Test creating schema from connection string."""
        connection_string = "sqlite:///:memory:"
        create_schema_from_connection_string(connection_string)

        # Verify by creating new connection and checking tables
        engine = create_engine(connection_string)
        inspector = inspect(engine)
        # Note: in-memory databases are not shared, so we can't verify this way
        # This test mainly ensures no exceptions are raised

    def test_create_schema_from_connection_string_with_drop(self):
        """Test creating schema with drop_existing=True."""
        connection_string = "sqlite:///:memory:"
        create_schema_from_connection_string(connection_string, drop_existing=True)

    def test_create_schema_from_invalid_connection_string(self):
        """Test creating schema with invalid connection string."""
        with pytest.raises(ExecutionError, match="Failed to create schema"):
            create_schema_from_connection_string("invalid://connection")
