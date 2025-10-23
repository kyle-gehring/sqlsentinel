"""Tests for database adapter factory."""

import pytest

from src.sqlsentinel.database.adapter import DatabaseAdapter
from src.sqlsentinel.database.bigquery_adapter import BigQueryAdapter
from src.sqlsentinel.database.factory import AdapterFactory


class TestAdapterFactory:
    """Tests for AdapterFactory class."""

    def test_create_adapter_empty_string(self):
        """Test factory raises error for empty connection string."""
        with pytest.raises(ValueError, match="Connection string cannot be empty"):
            AdapterFactory.create_adapter("")

    def test_create_adapter_whitespace(self):
        """Test factory raises error for whitespace connection string."""
        with pytest.raises(ValueError, match="Connection string cannot be empty"):
            AdapterFactory.create_adapter("   ")

    def test_create_adapter_postgresql(self):
        """Test factory creates DatabaseAdapter for PostgreSQL."""
        adapter = AdapterFactory.create_adapter("postgresql://localhost/testdb")

        assert isinstance(adapter, DatabaseAdapter)
        assert not isinstance(adapter, BigQueryAdapter)
        assert adapter.connection_string == "postgresql://localhost/testdb"

    def test_create_adapter_mysql(self):
        """Test factory creates DatabaseAdapter for MySQL."""
        adapter = AdapterFactory.create_adapter("mysql://localhost/testdb")

        assert isinstance(adapter, DatabaseAdapter)
        assert adapter.connection_string == "mysql://localhost/testdb"

    def test_create_adapter_sqlite(self):
        """Test factory creates DatabaseAdapter for SQLite."""
        adapter = AdapterFactory.create_adapter("sqlite:///test.db")

        assert isinstance(adapter, DatabaseAdapter)
        assert adapter.connection_string == "sqlite:///test.db"

    def test_create_adapter_sqlite_memory(self):
        """Test factory creates DatabaseAdapter for in-memory SQLite."""
        adapter = AdapterFactory.create_adapter("sqlite:///:memory:")

        assert isinstance(adapter, DatabaseAdapter)
        assert adapter.connection_string == "sqlite:///:memory:"

    def test_create_adapter_bigquery_minimal(self):
        """Test factory creates BigQueryAdapter for minimal BigQuery URL."""
        adapter = AdapterFactory.create_adapter("bigquery://my-project")

        assert isinstance(adapter, BigQueryAdapter)
        assert adapter.project_id == "my-project"
        assert adapter.credentials_path is None
        assert adapter.location == "US"
        assert adapter.default_dataset is None

    def test_create_adapter_bigquery_with_dataset(self):
        """Test factory creates BigQueryAdapter with dataset."""
        adapter = AdapterFactory.create_adapter("bigquery://my-project/my_dataset")

        assert isinstance(adapter, BigQueryAdapter)
        assert adapter.project_id == "my-project"
        assert adapter.default_dataset == "my_dataset"

    def test_create_adapter_bigquery_with_credentials(self):
        """Test factory creates BigQueryAdapter with credentials path."""
        adapter = AdapterFactory.create_adapter(
            "bigquery://my-project?credentials=/path/to/key.json"
        )

        assert isinstance(adapter, BigQueryAdapter)
        assert adapter.project_id == "my-project"
        assert adapter.credentials_path == "/path/to/key.json"

    def test_create_adapter_bigquery_with_location(self):
        """Test factory creates BigQueryAdapter with custom location."""
        adapter = AdapterFactory.create_adapter("bigquery://my-project?location=EU")

        assert isinstance(adapter, BigQueryAdapter)
        assert adapter.project_id == "my-project"
        assert adapter.location == "EU"

    def test_create_adapter_bigquery_full(self):
        """Test factory creates BigQueryAdapter with all parameters."""
        adapter = AdapterFactory.create_adapter(
            "bigquery://my-project/analytics?credentials=/keys/service.json&location=EU"
        )

        assert isinstance(adapter, BigQueryAdapter)
        assert adapter.project_id == "my-project"
        assert adapter.default_dataset == "analytics"
        assert adapter.credentials_path == "/keys/service.json"
        assert adapter.location == "EU"

    def test_create_adapter_bigquery_no_project(self):
        """Test factory fails for BigQuery URL without project ID."""
        with pytest.raises(ValueError, match="must include project ID"):
            AdapterFactory.create_adapter("bigquery://")

    def test_create_adapter_bigquery_only_scheme(self):
        """Test factory fails for BigQuery URL with only scheme."""
        with pytest.raises(ValueError, match="must include project ID"):
            AdapterFactory.create_adapter("bigquery:")

    def test_create_adapter_strips_whitespace(self):
        """Test factory strips whitespace from connection string."""
        adapter = AdapterFactory.create_adapter("  bigquery://my-project  ")

        assert isinstance(adapter, BigQueryAdapter)
        assert adapter.project_id == "my-project"

    @pytest.mark.parametrize(
        "connection_string,expected_type",
        [
            ("bigquery://project", BigQueryAdapter),
            ("postgresql://localhost/db", DatabaseAdapter),
            ("mysql://localhost/db", DatabaseAdapter),
            ("sqlite:///test.db", DatabaseAdapter),
            ("oracle://localhost/db", DatabaseAdapter),  # Other SQLAlchemy dialects
            ("mssql://localhost/db", DatabaseAdapter),
        ],
    )
    def test_create_adapter_type_detection(self, connection_string, expected_type):
        """Test factory creates correct adapter type for various connection strings."""
        adapter = AdapterFactory.create_adapter(connection_string)
        assert type(adapter) == expected_type

    def test_create_adapter_bigquery_complex_project_id(self):
        """Test factory handles complex project IDs (with dashes, numbers)."""
        adapter = AdapterFactory.create_adapter("bigquery://my-project-123")

        assert adapter.project_id == "my-project-123"

    def test_create_adapter_bigquery_dataset_with_underscores(self):
        """Test factory handles dataset names with underscores."""
        adapter = AdapterFactory.create_adapter("bigquery://project/my_data_set")

        assert adapter.default_dataset == "my_data_set"

    def test_create_adapter_bigquery_multiple_query_params(self):
        """Test factory handles multiple query parameters."""
        adapter = AdapterFactory.create_adapter(
            "bigquery://project?credentials=/path/key.json&location=EU&foo=bar"
        )

        # Should extract known params
        assert adapter.credentials_path == "/path/key.json"
        assert adapter.location == "EU"
        # Unknown params should be ignored (foo=bar)

    def test_create_adapter_bigquery_location_default(self):
        """Test BigQuery adapter defaults to US location."""
        adapter = AdapterFactory.create_adapter("bigquery://project")

        assert adapter.location == "US"

    def test_create_adapter_real_world_examples(self):
        """Test factory with real-world connection strings."""
        # PostgreSQL on Heroku
        adapter1 = AdapterFactory.create_adapter(
            "postgresql://user:password@ec2-host.amazonaws.com:5432/dbname"
        )
        assert isinstance(adapter1, DatabaseAdapter)

        # BigQuery with service account
        adapter2 = AdapterFactory.create_adapter(
            "bigquery://my-gcp-project-prod/analytics?credentials=/app/config/sa.json"
        )
        assert isinstance(adapter2, BigQueryAdapter)
        assert adapter2.project_id == "my-gcp-project-prod"
        assert adapter2.default_dataset == "analytics"

        # SQLite for local dev
        adapter3 = AdapterFactory.create_adapter("sqlite:///./data/local.db")
        assert isinstance(adapter3, DatabaseAdapter)
