"""Database adapter factory for SQL Sentinel."""

from typing import Union
from urllib.parse import parse_qs, urlparse

from .adapter import DatabaseAdapter
from .bigquery_adapter import BigQueryAdapter


class AdapterFactory:
    """
    Factory for creating database adapters based on connection string.

    Supports:
    - bigquery://project-id/dataset?credentials=/path/to/key.json&location=US
    - postgresql://user:pass@host/db
    - mysql://user:pass@host/db
    - sqlite:///path/to/db.db
    - Any other SQLAlchemy-supported connection string
    """

    @staticmethod
    def create_adapter(connection_string: str) -> Union[DatabaseAdapter, BigQueryAdapter]:
        """
        Create appropriate adapter based on connection string scheme.

        Args:
            connection_string: Database connection string

        Returns:
            DatabaseAdapter for SQLAlchemy-supported databases
            BigQueryAdapter for BigQuery connections

        Raises:
            ValueError: If connection string is invalid or empty

        Examples:
            >>> adapter = AdapterFactory.create_adapter("bigquery://my-project")
            >>> isinstance(adapter, BigQueryAdapter)
            True

            >>> adapter = AdapterFactory.create_adapter("postgresql://localhost/db")
            >>> isinstance(adapter, DatabaseAdapter)
            True
        """
        if not connection_string or not connection_string.strip():
            raise ValueError("Connection string cannot be empty")

        connection_string = connection_string.strip()

        # Parse URL to detect scheme
        parsed = urlparse(connection_string)

        if parsed.scheme == "bigquery":
            return AdapterFactory._create_bigquery_adapter(connection_string)
        else:
            # All other schemes go to SQLAlchemy DatabaseAdapter
            return DatabaseAdapter(connection_string)

    @staticmethod
    def _create_bigquery_adapter(connection_string: str) -> BigQueryAdapter:
        """
        Parse BigQuery connection string and create adapter.

        Format: bigquery://project-id/dataset?credentials=/path/to/key.json&location=US

        Args:
            connection_string: BigQuery connection string

        Returns:
            Configured BigQueryAdapter instance

        Raises:
            ValueError: If connection string format is invalid
        """
        parsed = urlparse(connection_string)

        # Extract project ID from netloc (host part)
        project_id = parsed.netloc
        if not project_id:
            raise ValueError(
                "BigQuery connection string must include project ID: "
                "bigquery://project-id or bigquery://project-id/dataset"
            )

        # Extract default dataset from path (optional)
        default_dataset = None
        if parsed.path and parsed.path != "/":
            # Remove leading slash
            default_dataset = parsed.path.lstrip("/")

        # Parse query parameters
        query_params = parse_qs(parsed.query)

        # Extract credentials path (optional)
        credentials_path = None
        if "credentials" in query_params:
            credentials_path = query_params["credentials"][0]

        # Extract location (optional, default: US)
        location = "US"
        if "location" in query_params:
            location = query_params["location"][0]

        # Create and return BigQuery adapter
        return BigQueryAdapter(
            project_id=project_id,
            credentials_path=credentials_path,
            location=location,
            default_dataset=default_dataset,
        )
