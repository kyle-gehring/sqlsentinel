"""Tests for QueryExecutor."""

import pytest
from sqlsentinel.database.adapter import DatabaseAdapter
from sqlsentinel.executor.query import QueryExecutor
from sqlsentinel.models.errors import ValidationError


class TestQueryExecutor:
    """Test suite for QueryExecutor."""

    @pytest.fixture
    def db_adapter(self):
        """Create a connected database adapter for testing."""
        adapter = DatabaseAdapter("sqlite:///:memory:")
        adapter.connect()
        yield adapter
        adapter.disconnect()

    @pytest.fixture
    def executor(self, db_adapter):
        """Create a QueryExecutor instance."""
        return QueryExecutor(db_adapter)

    def test_execute_valid_alert_query(self, executor):
        """Test executing a valid alert query."""
        query = "SELECT 'ALERT' as status, 100 as actual_value, 50 as threshold"
        result = executor.execute(query)

        assert result.status == "ALERT"
        assert result.actual_value == 100
        assert result.threshold == 50

    def test_execute_valid_ok_query(self, executor):
        """Test executing a valid OK query."""
        query = "SELECT 'OK' as status"
        result = executor.execute(query)

        assert result.status == "OK"
        assert result.actual_value is None
        assert result.threshold is None

    def test_execute_query_with_context(self, executor):
        """Test executing query with additional context columns."""
        query = """
            SELECT
                'ALERT' as status,
                100 as actual_value,
                50 as threshold,
                'urgent' as severity,
                'production' as environment
        """
        result = executor.execute(query)

        assert result.status == "ALERT"
        assert result.actual_value == 100
        assert result.threshold == 50
        assert result.context["severity"] == "urgent"
        assert result.context["environment"] == "production"

    def test_execute_query_no_results(self, executor, db_adapter):
        """Test executing query that returns no results raises error."""
        db_adapter.execute_query("CREATE TABLE empty_table (id INTEGER)")
        query = "SELECT * FROM empty_table WHERE 1=0"

        with pytest.raises(ValidationError, match="Query returned no results"):
            executor.execute(query)

    def test_execute_query_multiple_rows(self, executor):
        """Test executing query that returns multiple rows raises error."""
        query = "SELECT 'ALERT' as status UNION SELECT 'OK' as status"

        with pytest.raises(ValidationError, match="Query returned 2 rows"):
            executor.execute(query)

    def test_execute_query_missing_status_column(self, executor):
        """Test executing query without status column raises error."""
        query = "SELECT 100 as value, 50 as threshold"

        with pytest.raises(ValidationError, match="missing required 'status' column"):
            executor.execute(query)

    def test_execute_query_invalid_status_value(self, executor):
        """Test executing query with invalid status value raises error."""
        query = "SELECT 'INVALID' as status"

        with pytest.raises(ValidationError, match="Status must be 'ALERT' or 'OK'"):
            executor.execute(query)

    def test_execute_query_case_insensitive_status(self, executor):
        """Test status values are case-insensitive."""
        query = "SELECT 'alert' as status"
        result = executor.execute(query)
        assert result.status == "ALERT"

        query = "SELECT 'ok' as status"
        result = executor.execute(query)
        assert result.status == "OK"

    def test_execute_query_with_only_actual_value(self, executor):
        """Test query with status and actual_value but no threshold."""
        query = "SELECT 'ALERT' as status, 100 as actual_value"
        result = executor.execute(query)

        assert result.status == "ALERT"
        assert result.actual_value == 100
        assert result.threshold is None

    def test_execute_query_with_only_threshold(self, executor):
        """Test query with status and threshold but no actual_value."""
        query = "SELECT 'ALERT' as status, 50 as threshold"
        result = executor.execute(query)

        assert result.status == "ALERT"
        assert result.actual_value is None
        assert result.threshold == 50

    def test_execute_query_with_null_values(self, executor):
        """Test query with NULL values in optional columns."""
        query = "SELECT 'ALERT' as status, NULL as actual_value, NULL as threshold"
        result = executor.execute(query)

        assert result.status == "ALERT"
        assert result.actual_value is None
        assert result.threshold is None

    def test_validate_query_contract_valid(self, executor):
        """Test validating a query that follows the contract."""
        query = "SELECT 'OK' as status"
        is_valid, message = executor.validate_query_contract(query)

        assert is_valid is True
        assert "OK" in message

    def test_validate_query_contract_invalid_no_status(self, executor):
        """Test validating a query without status column."""
        query = "SELECT 1 as value"
        is_valid, message = executor.validate_query_contract(query)

        assert is_valid is False
        assert "missing required 'status' column" in message

    def test_validate_query_contract_invalid_multiple_rows(self, executor):
        """Test validating a query that returns multiple rows."""
        query = "SELECT 'ALERT' as status UNION SELECT 'OK' as status"
        is_valid, message = executor.validate_query_contract(query)

        assert is_valid is False
        assert "2 rows" in message

    def test_validate_query_contract_invalid_empty_result(self, executor, db_adapter):
        """Test validating a query that returns no results."""
        db_adapter.execute_query("CREATE TABLE empty_table (id INTEGER)")
        query = "SELECT 'OK' as status FROM empty_table WHERE 1=0"
        is_valid, message = executor.validate_query_contract(query)

        assert is_valid is False
        assert "no results" in message

    def test_execute_query_with_string_values(self, executor):
        """Test query with string values in actual_value and threshold."""
        query = """
            SELECT
                'ALERT' as status,
                'high' as actual_value,
                'medium' as threshold
        """
        result = executor.execute(query)

        assert result.status == "ALERT"
        assert result.actual_value == "high"
        assert result.threshold == "medium"

    def test_execute_query_with_float_values(self, executor):
        """Test query with float values."""
        query = "SELECT 'ALERT' as status, 99.5 as actual_value, 100.0 as threshold"
        result = executor.execute(query)

        assert result.status == "ALERT"
        assert result.actual_value == 99.5
        assert result.threshold == 100.0

    def test_execute_query_empty_context(self, executor):
        """Test query with only required fields has empty context."""
        query = "SELECT 'OK' as status"
        result = executor.execute(query)

        assert result.context == {}

    def test_validate_query_contract_with_execution_error(self, db_adapter):
        """Test validate_query_contract with SQL execution error."""
        from sqlsentinel.models.errors import ExecutionError

        executor = QueryExecutor(db_adapter)
        db_adapter.disconnect()  # Force disconnection to trigger error

        query = "SELECT 'OK' as status"
        with pytest.raises(ExecutionError, match="Query validation failed"):
            executor.validate_query_contract(query)
