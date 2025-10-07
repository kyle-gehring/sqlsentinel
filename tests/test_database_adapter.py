"""Tests for DatabaseAdapter."""

import pytest
from sqlsentinel.database.adapter import DatabaseAdapter
from sqlsentinel.models.errors import ExecutionError


class TestDatabaseAdapter:
    """Test suite for DatabaseAdapter."""

    def test_init_with_valid_connection_string(self):
        """Test initialization with valid connection string."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        assert adapter.connection_string == "sqlite:///:memory:"
        assert adapter._engine is None

    def test_init_with_empty_connection_string(self):
        """Test initialization with empty connection string raises error."""
        with pytest.raises(ExecutionError, match="Connection string cannot be empty"):
            DatabaseAdapter("")

    def test_init_with_whitespace_connection_string(self):
        """Test initialization with whitespace connection string raises error."""
        with pytest.raises(ExecutionError, match="Connection string cannot be empty"):
            DatabaseAdapter("   ")

    def test_connect_success(self):
        """Test successful database connection."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        assert adapter._engine is not None
        adapter.disconnect()

    def test_connect_invalid_connection_string(self):
        """Test connection with invalid connection string raises error."""
        adapter = DatabaseAdapter("invalid://connection")
        with pytest.raises(ExecutionError, match="Failed to connect to database"):
            adapter.connect()

    def test_disconnect(self):
        """Test disconnection closes the engine."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        assert adapter._engine is not None
        adapter.disconnect()
        assert adapter._engine is None

    def test_disconnect_without_connect(self):
        """Test disconnect works when not connected."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.disconnect()  # Should not raise error
        assert adapter._engine is None

    def test_execute_query_simple_select(self):
        """Test executing a simple SELECT query."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        results = adapter.execute_query("SELECT 1 as value")
        assert len(results) == 1
        assert results[0]["value"] == 1
        adapter.disconnect()

    def test_execute_query_with_multiple_columns(self):
        """Test executing query with multiple columns."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        results = adapter.execute_query(
            "SELECT 'ALERT' as status, 100 as actual_value, 50 as threshold"
        )
        assert len(results) == 1
        assert results[0]["status"] == "ALERT"
        assert results[0]["actual_value"] == 100
        assert results[0]["threshold"] == 50
        adapter.disconnect()

    def test_execute_query_multiple_rows(self):
        """Test executing query that returns multiple rows."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        results = adapter.execute_query("SELECT 1 as id UNION SELECT 2 UNION SELECT 3")
        assert len(results) == 3
        assert results[0]["id"] == 1
        assert results[1]["id"] == 2
        assert results[2]["id"] == 3
        adapter.disconnect()

    def test_execute_query_empty_result(self):
        """Test executing query that returns no rows."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        adapter.execute_query("CREATE TABLE test (id INTEGER)")
        results = adapter.execute_query("SELECT * FROM test")
        assert len(results) == 0
        adapter.disconnect()

    def test_execute_query_without_connect(self):
        """Test executing query without connection raises error."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        with pytest.raises(ExecutionError, match="Database connection not established"):
            adapter.execute_query("SELECT 1")

    def test_execute_query_empty_query(self):
        """Test executing empty query raises error."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        with pytest.raises(ExecutionError, match="Query cannot be empty"):
            adapter.execute_query("")
        adapter.disconnect()

    def test_execute_query_whitespace_query(self):
        """Test executing whitespace query raises error."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        with pytest.raises(ExecutionError, match="Query cannot be empty"):
            adapter.execute_query("   ")
        adapter.disconnect()

    def test_execute_query_invalid_sql(self):
        """Test executing invalid SQL raises error."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        with pytest.raises(ExecutionError, match="Query execution failed"):
            adapter.execute_query("INVALID SQL SYNTAX")
        adapter.disconnect()

    def test_context_manager_success(self):
        """Test using DatabaseAdapter as context manager."""
        with DatabaseAdapter("sqlite:///:memory:") as adapter:
            assert adapter._engine is not None
            results = adapter.execute_query("SELECT 1 as value")
            assert results[0]["value"] == 1
        # After exiting context, connection should be closed
        assert adapter._engine is None

    def test_context_manager_with_exception(self):
        """Test context manager properly disconnects on exception."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        try:
            with adapter:
                assert adapter._engine is not None
                raise ValueError("Test exception")
        except ValueError:
            pass
        # Connection should be closed even after exception
        assert adapter._engine is None

    def test_execute_query_with_special_characters(self):
        """Test executing query with special characters in results."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        results = adapter.execute_query(
            "SELECT 'Value with ''quotes'' and \"double quotes\"' as text"
        )
        assert len(results) == 1
        assert "quotes" in results[0]["text"]
        adapter.disconnect()

    def test_execute_query_with_null_values(self):
        """Test executing query with NULL values."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        results = adapter.execute_query("SELECT NULL as null_value, 1 as value")
        assert len(results) == 1
        assert results[0]["null_value"] is None
        assert results[0]["value"] == 1
        adapter.disconnect()
