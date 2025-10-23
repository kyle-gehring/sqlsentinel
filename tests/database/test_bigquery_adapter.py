"""Tests for BigQuery database adapter."""

import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.sqlsentinel.database.bigquery_adapter import BigQueryAdapter
from src.sqlsentinel.models.errors import ExecutionError


class TestBigQueryAdapter:
    """Tests for BigQueryAdapter class."""

    def test_initialization_success(self):
        """Test adapter initializes with valid project ID."""
        adapter = BigQueryAdapter(project_id="test-project")

        assert adapter.project_id == "test-project"
        assert adapter.credentials_path is None
        assert adapter.location == "US"
        assert adapter.default_dataset is None
        assert adapter._client is None

    def test_initialization_with_all_params(self):
        """Test adapter initializes with all parameters."""
        adapter = BigQueryAdapter(
            project_id="test-project",
            credentials_path="/path/to/key.json",
            location="EU",
            default_dataset="my_dataset",
        )

        assert adapter.project_id == "test-project"
        assert adapter.credentials_path == "/path/to/key.json"
        assert adapter.location == "EU"
        assert adapter.default_dataset == "my_dataset"

    def test_initialization_empty_project_id(self):
        """Test initialization fails with empty project ID."""
        with pytest.raises(ExecutionError, match="project_id cannot be empty"):
            BigQueryAdapter(project_id="")

    def test_initialization_whitespace_project_id(self):
        """Test initialization fails with whitespace project ID."""
        with pytest.raises(ExecutionError, match="project_id cannot be empty"):
            BigQueryAdapter(project_id="   ")

    def test_initialization_strips_whitespace(self):
        """Test project ID whitespace is stripped."""
        adapter = BigQueryAdapter(project_id="  test-project  ")
        assert adapter.project_id == "test-project"

    @patch("src.sqlsentinel.database.bigquery_adapter.default")
    @patch("src.sqlsentinel.database.bigquery_adapter.bigquery.Client")
    def test_connect_with_adc(self, mock_client_class, mock_default):
        """Test connection with Application Default Credentials."""
        # Setup mocks
        mock_credentials = Mock()
        mock_default.return_value = (mock_credentials, "test-project")

        mock_client = Mock()
        mock_client.list_datasets.return_value = iter([])
        mock_client_class.return_value = mock_client

        # Test connection
        adapter = BigQueryAdapter(project_id="test-project")
        adapter.connect()

        # Verify ADC was used
        mock_default.assert_called_once()
        assert "bigquery" in str(mock_default.call_args)

        # Verify client was created
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args.kwargs
        assert call_kwargs["project"] == "test-project"
        assert call_kwargs["credentials"] == mock_credentials
        assert call_kwargs["location"] == "US"

        # Verify connection test
        mock_client.list_datasets.assert_called_once_with(max_results=1)

        assert adapter._client == mock_client

    @patch("src.sqlsentinel.database.bigquery_adapter.service_account")
    @patch("src.sqlsentinel.database.bigquery_adapter.bigquery.Client")
    @patch("os.path.exists")
    def test_connect_with_service_account(self, mock_exists, mock_client_class, mock_service_account):
        """Test connection with service account credentials."""
        # Setup mocks
        mock_exists.return_value = True

        mock_credentials = Mock()
        mock_service_account.Credentials.from_service_account_file.return_value = (
            mock_credentials
        )

        mock_client = Mock()
        mock_client.list_datasets.return_value = iter([])
        mock_client_class.return_value = mock_client

        # Test connection
        adapter = BigQueryAdapter(
            project_id="test-project", credentials_path="/path/to/key.json"
        )
        adapter.connect()

        # Verify service account was loaded
        mock_service_account.Credentials.from_service_account_file.assert_called_once_with(
            "/path/to/key.json",
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )

        # Verify client was created with service account credentials
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args.kwargs
        assert call_kwargs["project"] == "test-project"
        assert call_kwargs["credentials"] == mock_credentials

        assert adapter._client == mock_client

    @patch("os.path.exists")
    def test_connect_service_account_file_not_found(self, mock_exists):
        """Test connection fails when service account file doesn't exist."""
        mock_exists.return_value = False

        adapter = BigQueryAdapter(
            project_id="test-project", credentials_path="/path/to/missing.json"
        )

        with pytest.raises(ExecutionError, match="Service account key file not found"):
            adapter.connect()

    @patch("src.sqlsentinel.database.bigquery_adapter.default")
    @patch("src.sqlsentinel.database.bigquery_adapter.bigquery.Client")
    def test_connect_adc_not_configured(self, mock_client_class, mock_default):
        """Test connection fails with helpful message when ADC not configured."""
        # Simulate ADC failure
        mock_default.side_effect = Exception("Could not automatically determine credentials")

        adapter = BigQueryAdapter(project_id="test-project")

        with pytest.raises(ExecutionError, match="Failed to connect to BigQuery"):
            adapter.connect()

    def test_disconnect(self):
        """Test disconnect closes client."""
        adapter = BigQueryAdapter(project_id="test-project")
        mock_client = Mock()
        adapter._client = mock_client

        adapter.disconnect()

        mock_client.close.assert_called_once()
        assert adapter._client is None

    def test_disconnect_no_client(self):
        """Test disconnect works when client is None."""
        adapter = BigQueryAdapter(project_id="test-project")
        adapter.disconnect()  # Should not raise

    def test_execute_query_not_connected(self):
        """Test execute_query fails when not connected."""
        adapter = BigQueryAdapter(project_id="test-project")

        with pytest.raises(ExecutionError, match="connection not established"):
            adapter.execute_query("SELECT 1")

    def test_execute_query_empty_query(self):
        """Test execute_query fails with empty query."""
        adapter = BigQueryAdapter(project_id="test-project")
        adapter._client = Mock()

        with pytest.raises(ExecutionError, match="Query cannot be empty"):
            adapter.execute_query("")

    def test_execute_query_whitespace_query(self):
        """Test execute_query fails with whitespace query."""
        adapter = BigQueryAdapter(project_id="test-project")
        adapter._client = Mock()

        with pytest.raises(ExecutionError, match="Query cannot be empty"):
            adapter.execute_query("   ")

    def test_execute_query_success(self):
        """Test successful query execution."""
        adapter = BigQueryAdapter(project_id="test-project")

        # Mock client and query results
        mock_client = Mock()
        mock_query_job = Mock()

        # Create mock result rows
        mock_row1 = Mock()
        mock_row1.items.return_value = [("status", "OK"), ("count", 100)]

        mock_row2 = Mock()
        mock_row2.items.return_value = [("status", "ALERT"), ("count", 50)]

        mock_results = [mock_row1, mock_row2]
        mock_query_job.result.return_value = mock_results

        mock_client.query.return_value = mock_query_job
        adapter._client = mock_client

        # Execute query
        results = adapter.execute_query("SELECT status, count FROM test_table")

        # Verify query was executed
        mock_client.query.assert_called_once()
        call_args = mock_client.query.call_args
        assert call_args.args[0] == "SELECT status, count FROM test_table"

        # Verify timeout was passed
        assert call_args.kwargs["timeout"] == 300.0

        # Verify results
        assert len(results) == 2
        assert results[0] == {"status": "OK", "count": 100}
        assert results[1] == {"status": "ALERT", "count": 50}

    def test_execute_query_with_custom_timeout(self):
        """Test query execution with custom timeout."""
        adapter = BigQueryAdapter(project_id="test-project")

        mock_client = Mock()
        mock_query_job = Mock()
        mock_query_job.result.return_value = []
        mock_client.query.return_value = mock_query_job
        adapter._client = mock_client

        adapter.execute_query("SELECT 1", timeout=60.0)

        # Verify custom timeout was used
        call_args = mock_client.query.call_args
        assert call_args.kwargs["timeout"] == 60.0

    def test_execute_query_with_default_dataset(self):
        """Test query execution with default dataset configured."""
        adapter = BigQueryAdapter(project_id="test-project", default_dataset="my_dataset")

        mock_client = Mock()
        mock_query_job = Mock()
        mock_query_job.result.return_value = []
        mock_client.query.return_value = mock_query_job
        adapter._client = mock_client

        adapter.execute_query("SELECT 1")

        # Verify default dataset was configured
        call_args = mock_client.query.call_args
        job_config = call_args.kwargs["job_config"]
        # The default_dataset is set as a DatasetReference object or string
        dataset_str = str(job_config.default_dataset)
        assert "my_dataset" in dataset_str
        assert "test-project" in dataset_str

    def test_execute_query_timeout_error(self):
        """Test query execution handles timeout."""
        adapter = BigQueryAdapter(project_id="test-project")

        mock_client = Mock()
        mock_query_job = Mock()
        mock_query_job.result.side_effect = TimeoutError("Query timed out")
        mock_client.query.return_value = mock_query_job
        adapter._client = mock_client

        with pytest.raises(ExecutionError, match="timed out after 300.0 seconds"):
            adapter.execute_query("SELECT 1")

    def test_execute_query_general_error(self):
        """Test query execution handles general errors."""
        adapter = BigQueryAdapter(project_id="test-project")

        mock_client = Mock()
        mock_client.query.side_effect = Exception("Bad request")
        adapter._client = mock_client

        with pytest.raises(ExecutionError, match="Query execution failed"):
            adapter.execute_query("SELECT 1")

    def test_dry_run_not_connected(self):
        """Test dry_run fails when not connected."""
        adapter = BigQueryAdapter(project_id="test-project")

        with pytest.raises(ExecutionError, match="connection not established"):
            adapter.dry_run("SELECT 1")

    def test_dry_run_empty_query(self):
        """Test dry_run fails with empty query."""
        adapter = BigQueryAdapter(project_id="test-project")
        adapter._client = Mock()

        with pytest.raises(ExecutionError, match="Query cannot be empty"):
            adapter.dry_run("")

    def test_dry_run_success(self):
        """Test successful dry-run."""
        adapter = BigQueryAdapter(project_id="test-project")

        mock_client = Mock()
        mock_query_job = Mock()
        mock_query_job.total_bytes_processed = 1024 * 1024 * 1024 * 500  # 500 GB
        mock_client.query.return_value = mock_query_job
        adapter._client = mock_client

        result = adapter.dry_run("SELECT * FROM large_table")

        # Verify dry_run was configured
        call_args = mock_client.query.call_args
        job_config = call_args.kwargs["job_config"]
        assert job_config.dry_run is True
        assert job_config.use_query_cache is False

        # Verify results
        assert result["bytes_processed"] == 1024 * 1024 * 1024 * 500
        assert result["tb_processed"] == pytest.approx(500 / 1024)  # ~0.488 TB
        # First 1 TB is free, so cost should be 0
        assert result["estimated_cost_usd"] == 0

    def test_dry_run_with_cost(self):
        """Test dry-run cost estimation for large query."""
        adapter = BigQueryAdapter(project_id="test-project")

        mock_client = Mock()
        mock_query_job = Mock()
        # 3 TB processed = $10 ($5 per TB after first free TB)
        mock_query_job.total_bytes_processed = 1024**4 * 3  # 3 TB
        mock_client.query.return_value = mock_query_job
        adapter._client = mock_client

        result = adapter.dry_run("SELECT * FROM huge_table")

        assert result["tb_processed"] == 3.0
        # (3 TB - 1 TB free) * $5/TB = $10
        assert result["estimated_cost_usd"] == pytest.approx(10.0)

    def test_dry_run_error(self):
        """Test dry-run handles errors."""
        adapter = BigQueryAdapter(project_id="test-project")

        mock_client = Mock()
        mock_client.query.side_effect = Exception("Invalid syntax")
        adapter._client = mock_client

        with pytest.raises(ExecutionError, match="Query dry-run failed"):
            adapter.dry_run("SELECT invalid syntax")

    def test_convert_bigquery_types_datetime(self):
        """Test datetime conversion."""
        adapter = BigQueryAdapter(project_id="test-project")

        dt = datetime.datetime(2024, 1, 15, 10, 30, 0)
        row_dict = {"timestamp_col": dt}

        result = adapter._convert_bigquery_types(row_dict)

        assert result["timestamp_col"] == dt  # Should keep as datetime

    def test_convert_bigquery_types_date(self):
        """Test date to datetime conversion."""
        adapter = BigQueryAdapter(project_id="test-project")

        date = datetime.date(2024, 1, 15)
        row_dict = {"date_col": date}

        result = adapter._convert_bigquery_types(row_dict)

        # Date should be converted to datetime
        expected = datetime.datetime(2024, 1, 15, 0, 0, 0)
        assert result["date_col"] == expected

    def test_convert_bigquery_types_array(self):
        """Test ARRAY type handling."""
        adapter = BigQueryAdapter(project_id="test-project")

        row_dict = {"tags": ("tag1", "tag2", "tag3")}

        result = adapter._convert_bigquery_types(row_dict)

        assert result["tags"] == ["tag1", "tag2", "tag3"]  # Converted to list

    def test_convert_bigquery_types_struct(self):
        """Test STRUCT type handling."""
        adapter = BigQueryAdapter(project_id="test-project")

        row_dict = {"address": {"street": "123 Main", "city": "NYC"}}

        result = adapter._convert_bigquery_types(row_dict)

        assert result["address"] == {"street": "123 Main", "city": "NYC"}  # Kept as dict

    def test_convert_bigquery_types_null(self):
        """Test NULL value handling."""
        adapter = BigQueryAdapter(project_id="test-project")

        row_dict = {"nullable_col": None}

        result = adapter._convert_bigquery_types(row_dict)

        assert result["nullable_col"] is None

    def test_convert_bigquery_types_primitives(self):
        """Test primitive types are unchanged."""
        adapter = BigQueryAdapter(project_id="test-project")

        row_dict = {
            "int_col": 42,
            "float_col": 3.14,
            "str_col": "hello",
            "bool_col": True,
        }

        result = adapter._convert_bigquery_types(row_dict)

        assert result == row_dict  # All primitives should be unchanged

    def test_context_manager_success(self):
        """Test context manager connects and disconnects."""
        adapter = BigQueryAdapter(project_id="test-project")

        # Mock connect and disconnect
        adapter.connect = Mock()
        adapter.disconnect = Mock()

        with adapter:
            adapter.connect.assert_called_once()
            assert adapter.disconnect.call_count == 0

        adapter.disconnect.assert_called_once()

    def test_context_manager_with_exception(self):
        """Test context manager disconnects even on exception."""
        adapter = BigQueryAdapter(project_id="test-project")

        adapter.connect = Mock()
        adapter.disconnect = Mock()

        with pytest.raises(ValueError):
            with adapter:
                raise ValueError("Test error")

        # Disconnect should still be called
        adapter.disconnect.assert_called_once()
