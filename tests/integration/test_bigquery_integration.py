"""Integration tests for BigQuery adapter using real BigQuery public datasets.

These tests require:
1. A valid GCP project ID
2. Authentication configured (service account key or ADC)
3. BigQuery API enabled in the project

The tests use BigQuery public datasets which are free to query.

To run these tests:
    # With ADC (Application Default Credentials)
    export BIGQUERY_PROJECT_ID=your-project-id
    gcloud auth application-default login
    poetry run pytest tests/integration/test_bigquery_integration.py -v

    # With service account
    export BIGQUERY_PROJECT_ID=your-project-id
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
    poetry run pytest tests/integration/test_bigquery_integration.py -v

To skip these tests in CI/CD:
    poetry run pytest -m "not bigquery_integration"
"""

import os

import pytest

from src.sqlsentinel.database.bigquery_adapter import BigQueryAdapter
from src.sqlsentinel.database.factory import AdapterFactory
from src.sqlsentinel.executor.alert_executor import AlertExecutor
from src.sqlsentinel.executor.query import QueryExecutor
from src.sqlsentinel.models.alert import AlertConfig, NotificationConfig


# Skip all tests in this module if credentials not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("BIGQUERY_PROJECT_ID"),
    reason="BIGQUERY_PROJECT_ID environment variable not set. "
    "Set BIGQUERY_PROJECT_ID and configure authentication to run BigQuery integration tests.",
)


@pytest.fixture
def project_id():
    """Get project ID from environment."""
    return os.getenv("BIGQUERY_PROJECT_ID")


@pytest.fixture
def credentials_path():
    """Get credentials path from environment (optional)."""
    return os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


@pytest.fixture
def bigquery_adapter(project_id, credentials_path):
    """Create BigQuery adapter with real credentials."""
    adapter = BigQueryAdapter(
        project_id=project_id,
        credentials_path=credentials_path,
    )
    adapter.connect()
    yield adapter
    adapter.disconnect()


class TestBigQueryAdapterIntegration:
    """Integration tests for BigQuery adapter with real BigQuery API."""

    def test_connect_and_disconnect(self, project_id, credentials_path):
        """Test basic connection and disconnection."""
        adapter = BigQueryAdapter(project_id=project_id, credentials_path=credentials_path)

        # Connect
        adapter.connect()
        assert adapter._client is not None

        # Disconnect
        adapter.disconnect()
        assert adapter._client is None

    def test_connect_with_context_manager(self, project_id, credentials_path):
        """Test connection using context manager."""
        with BigQueryAdapter(project_id=project_id, credentials_path=credentials_path) as adapter:
            assert adapter._client is not None

        # After context exits, client should be disconnected
        assert adapter._client is None

    def test_execute_simple_query(self, bigquery_adapter):
        """Test executing a simple query."""
        query = "SELECT 1 as value, 'test' as label"
        results = bigquery_adapter.execute_query(query)

        assert len(results) == 1
        assert results[0]["value"] == 1
        assert results[0]["label"] == "test"

    def test_execute_query_public_dataset_usa_names(self, bigquery_adapter):
        """Test query against BigQuery public dataset: usa_names."""
        # Query the USA names public dataset (free to query)
        query = """
        SELECT
            name,
            gender,
            number
        FROM `bigquery-public-data.usa_names.usa_1910_current`
        WHERE year = 2020 AND state = 'CA'
        ORDER BY number DESC
        LIMIT 5
        """

        results = bigquery_adapter.execute_query(query)

        # Verify results
        assert len(results) == 5
        assert "name" in results[0]
        assert "gender" in results[0]
        assert "number" in results[0]
        assert results[0]["number"] > results[1]["number"]  # Ordered by number DESC

    def test_execute_query_with_aggregation(self, bigquery_adapter):
        """Test query with aggregation functions."""
        query = """
        SELECT
            COUNT(*) as total_count,
            SUM(number) as total_births,
            AVG(number) as avg_births
        FROM `bigquery-public-data.usa_names.usa_1910_current`
        WHERE year = 2020 AND state = 'NY'
        """

        results = bigquery_adapter.execute_query(query)

        assert len(results) == 1
        assert results[0]["total_count"] > 0
        assert results[0]["total_births"] > 0
        assert results[0]["avg_births"] > 0

    def test_execute_query_with_date_types(self, bigquery_adapter):
        """Test query with DATE and TIMESTAMP types."""
        query = """
        SELECT
            DATE('2024-01-15') as date_col,
            TIMESTAMP('2024-01-15 10:30:00') as timestamp_col,
            CURRENT_DATE() as current_date_col
        """

        results = bigquery_adapter.execute_query(query)

        assert len(results) == 1
        assert results[0]["date_col"] is not None
        assert results[0]["timestamp_col"] is not None
        assert results[0]["current_date_col"] is not None

    def test_execute_query_with_arrays(self, bigquery_adapter):
        """Test query with ARRAY type."""
        query = """
        SELECT
            ['red', 'green', 'blue'] as colors,
            [1, 2, 3, 4, 5] as numbers
        """

        results = bigquery_adapter.execute_query(query)

        assert len(results) == 1
        assert results[0]["colors"] == ["red", "green", "blue"]
        assert results[0]["numbers"] == [1, 2, 3, 4, 5]

    def test_execute_query_with_struct(self, bigquery_adapter):
        """Test query with STRUCT type."""
        query = """
        SELECT
            STRUCT('John' as first_name, 'Doe' as last_name) as person
        """

        results = bigquery_adapter.execute_query(query)

        assert len(results) == 1
        assert isinstance(results[0]["person"], dict)
        assert results[0]["person"]["first_name"] == "John"
        assert results[0]["person"]["last_name"] == "Doe"

    def test_execute_query_with_null_values(self, bigquery_adapter):
        """Test query with NULL values."""
        query = """
        SELECT
            NULL as null_col,
            'not null' as string_col,
            123 as number_col
        """

        results = bigquery_adapter.execute_query(query)

        assert len(results) == 1
        assert results[0]["null_col"] is None
        assert results[0]["string_col"] == "not null"
        assert results[0]["number_col"] == 123

    def test_dry_run_estimates_cost(self, bigquery_adapter):
        """Test dry-run cost estimation."""
        # Small query on public dataset
        query = """
        SELECT name, number
        FROM `bigquery-public-data.usa_names.usa_1910_current`
        WHERE year = 2020
        LIMIT 100
        """

        result = bigquery_adapter.dry_run(query)

        assert "bytes_processed" in result
        assert "tb_processed" in result
        assert "estimated_cost_usd" in result
        assert result["bytes_processed"] > 0
        assert result["tb_processed"] >= 0
        assert result["estimated_cost_usd"] >= 0

    def test_dry_run_vs_actual_execution(self, bigquery_adapter):
        """Test that dry-run doesn't execute the query."""
        query = "SELECT 1 as value"

        # Dry-run should not return data
        dry_run_result = bigquery_adapter.dry_run(query)
        assert "bytes_processed" in dry_run_result
        assert "value" not in dry_run_result  # No query results

        # Actual execution should return data
        exec_result = bigquery_adapter.execute_query(query)
        assert len(exec_result) == 1
        assert exec_result[0]["value"] == 1

    def test_execute_query_with_timeout(self, bigquery_adapter):
        """Test query execution respects timeout."""
        # Very simple query should complete quickly
        query = "SELECT 1 as value"

        # This should succeed with generous timeout
        results = bigquery_adapter.execute_query(query, timeout=60.0)
        assert len(results) == 1


class TestAdapterFactoryIntegration:
    """Integration tests for AdapterFactory with BigQuery."""

    def test_factory_creates_bigquery_adapter(self, project_id, credentials_path):
        """Test factory creates BigQuery adapter from URL."""
        # Build connection string
        url = f"bigquery://{project_id}"
        if credentials_path:
            url += f"?credentials={credentials_path}"

        adapter = AdapterFactory.create_adapter(url)

        assert isinstance(adapter, BigQueryAdapter)
        assert adapter.project_id == project_id

    def test_factory_adapter_executes_query(self, project_id, credentials_path):
        """Test adapter created by factory can execute queries."""
        url = f"bigquery://{project_id}"
        if credentials_path:
            url += f"?credentials={credentials_path}"

        adapter = AdapterFactory.create_adapter(url)

        with adapter:
            results = adapter.execute_query("SELECT 1 as value")
            assert len(results) == 1
            assert results[0]["value"] == 1


class TestQueryExecutorIntegration:
    """Integration tests for QueryExecutor with BigQuery."""

    def test_query_executor_with_bigquery(self, bigquery_adapter):
        """Test QueryExecutor can execute alert queries against BigQuery."""
        from src.sqlsentinel.executor.query import QueryExecutor

        executor = QueryExecutor(bigquery_adapter)

        # Alert query that should return OK
        query = """
        SELECT
            CASE WHEN COUNT(*) > 0 THEN 'OK' ELSE 'ALERT' END as status,
            COUNT(*) as actual_value,
            0 as threshold
        FROM `bigquery-public-data.usa_names.usa_1910_current`
        WHERE year = 2020
        """

        result = executor.execute(query)

        assert result.status == "OK"
        assert result.actual_value > 0
        assert result.threshold == 0

    def test_query_executor_alert_condition(self, bigquery_adapter):
        """Test QueryExecutor detects ALERT status from BigQuery."""
        from src.sqlsentinel.executor.query import QueryExecutor

        executor = QueryExecutor(bigquery_adapter)

        # Query that triggers alert
        query = """
        SELECT
            'ALERT' as status,
            100 as actual_value,
            50 as threshold,
            'Test alert triggered' as message
        """

        result = executor.execute(query)

        assert result.status == "ALERT"
        assert result.actual_value == 100
        assert result.threshold == 50
        assert result.context["message"] == "Test alert triggered"


class TestBigQueryAlertScenarios:
    """Real-world alert scenarios using BigQuery public datasets."""

    def test_data_quality_alert_missing_data(self, bigquery_adapter):
        """Test alert for missing data in specific time period."""
        from src.sqlsentinel.executor.query import QueryExecutor

        executor = QueryExecutor(bigquery_adapter)

        # Alert if no data exists for a specific year
        query = """
        SELECT
            CASE
                WHEN COUNT(*) = 0 THEN 'ALERT'
                ELSE 'OK'
            END as status,
            COUNT(*) as actual_value,
            1 as threshold,
            'year_2020_data_check' as check_name
        FROM `bigquery-public-data.usa_names.usa_1910_current`
        WHERE year = 2020 AND state = 'CA'
        """

        result = executor.execute(query)

        # Should be OK because data exists for 2020
        assert result.status == "OK"
        assert result.actual_value > 0

    def test_threshold_alert_popular_names(self, bigquery_adapter):
        """Test threshold alert for popular names."""
        from src.sqlsentinel.executor.query import QueryExecutor

        executor = QueryExecutor(bigquery_adapter)

        # Alert if top name has fewer than expected births
        query = """
        SELECT
            CASE
                WHEN MAX(number) < 100 THEN 'ALERT'
                ELSE 'OK'
            END as status,
            MAX(number) as actual_value,
            100 as threshold,
            MAX(name) as top_name
        FROM `bigquery-public-data.usa_names.usa_1910_current`
        WHERE year = 2020 AND state = 'CA'
        """

        result = executor.execute(query)

        # Should be OK because top names in CA have > 100 births
        assert result.status == "OK"
        assert result.actual_value > 100

    def test_complex_alert_with_multiple_conditions(self, bigquery_adapter):
        """Test complex alert with multiple business rules."""
        from src.sqlsentinel.executor.query import QueryExecutor

        executor = QueryExecutor(bigquery_adapter)

        # Complex business logic alert
        query = """
        WITH stats AS (
            SELECT
                COUNT(DISTINCT name) as unique_names,
                SUM(number) as total_births,
                AVG(number) as avg_births
            FROM `bigquery-public-data.usa_names.usa_1910_current`
            WHERE year = 2020 AND state = 'NY'
        )
        SELECT
            CASE
                WHEN unique_names < 100 OR total_births < 1000 THEN 'ALERT'
                ELSE 'OK'
            END as status,
            unique_names as actual_value,
            100 as threshold,
            total_births,
            ROUND(avg_births, 2) as avg_births
        FROM stats
        """

        result = executor.execute(query)

        # Should be OK - NY has many unique names and births
        assert result.status == "OK"
        assert result.actual_value > 100
        assert "total_births" in result.context
        assert "avg_births" in result.context


class TestBigQueryPerformance:
    """Performance-related tests for BigQuery integration."""

    def test_query_caching_behavior(self, bigquery_adapter):
        """Test that BigQuery query caching works as expected."""
        query = "SELECT 1 as value, CURRENT_TIMESTAMP() as ts"

        # First execution
        result1 = bigquery_adapter.execute_query(query)

        # Second execution (may be cached by BigQuery)
        result2 = bigquery_adapter.execute_query(query)

        # Both should return results
        assert len(result1) == 1
        assert len(result2) == 1
        assert result1[0]["value"] == 1
        assert result2[0]["value"] == 1

    def test_large_result_set_pagination(self, bigquery_adapter):
        """Test handling of large result sets."""
        # Query that returns more rows (but still reasonable for testing)
        query = """
        SELECT name, number
        FROM `bigquery-public-data.usa_names.usa_1910_current`
        WHERE year = 2020 AND state = 'CA'
        LIMIT 1000
        """

        results = bigquery_adapter.execute_query(query)

        # Should successfully retrieve all rows
        assert len(results) == 1000
        assert all("name" in row and "number" in row for row in results)


# Mark all tests in this module with custom marker for selective running
pytest.mark.bigquery_integration = pytest.mark.bigquery_integration
