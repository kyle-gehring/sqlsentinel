"""BigQuery database adapter for SQL Sentinel."""

import os
from typing import TYPE_CHECKING, Any

from ..models.errors import ExecutionError

if TYPE_CHECKING:
    from google.cloud.bigquery import Client


class BigQueryAdapter:
    """
    BigQuery-specific database adapter.

    Supports both service account authentication and Application Default Credentials (ADC).
    Provides query execution, dry-run cost estimation, and proper result conversion.
    """

    def __init__(
        self,
        project_id: str,
        credentials_path: str | None = None,
        location: str = "US",
        default_dataset: str | None = None,
    ):
        """
        Initialize BigQuery adapter.

        Args:
            project_id: GCP project ID
            credentials_path: Path to service account JSON key file (optional)
                            If not provided, uses Application Default Credentials
            location: BigQuery dataset location (default: US)
            default_dataset: Default dataset name for queries (optional)

        Raises:
            ExecutionError: If project_id is empty or invalid
        """
        if not project_id or not project_id.strip():
            raise ExecutionError("BigQuery project_id cannot be empty")

        self.project_id = project_id.strip()
        self.credentials_path = credentials_path
        self.location = location
        self.default_dataset = default_dataset
        self._client: "Client | None" = None

    def connect(self) -> None:
        """
        Establish BigQuery connection.

        Uses service account credentials if credentials_path is provided,
        otherwise uses Application Default Credentials (ADC).

        Raises:
            ExecutionError: If connection fails or credentials are invalid
        """
        try:
            from google.auth import default
            from google.cloud import bigquery
            from google.oauth2 import service_account

            # Load credentials
            credentials = None
            if self.credentials_path:
                # Service account authentication
                if not os.path.exists(self.credentials_path):
                    raise ExecutionError(
                        f"Service account key file not found: {self.credentials_path}"
                    )
                credentials = service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
                    self.credentials_path,
                    scopes=["https://www.googleapis.com/auth/bigquery"],
                )
            else:
                # Application Default Credentials (ADC)
                credentials, _ = default(scopes=["https://www.googleapis.com/auth/bigquery"])  # type: ignore[no-untyped-call]

            # Create BigQuery client
            self._client = bigquery.Client(
                project=self.project_id,
                credentials=credentials,
                location=self.location,
            )

            # Test connection by listing datasets (minimal API call)
            # This validates both credentials and project access
            list(self._client.list_datasets(max_results=1))

        except FileNotFoundError as e:
            raise ExecutionError(f"Credentials file not found: {e}") from e
        except Exception as e:
            error_msg = str(e)
            if "ADC" in error_msg or "default credentials" in error_msg.lower():
                raise ExecutionError(
                    "Failed to load Application Default Credentials. "
                    "Run 'gcloud auth application-default login' or provide credentials_path."
                ) from e
            raise ExecutionError(f"Failed to connect to BigQuery: {e}") from e

    def disconnect(self) -> None:
        """Close BigQuery connection."""
        if self._client:
            self._client.close()  # type: ignore[no-untyped-call]
            self._client = None

    def execute_query(self, query: str, timeout: float = 300.0) -> list[dict[str, Any]]:
        """
        Execute BigQuery query and return results.

        Args:
            query: SQL query to execute
            timeout: Query timeout in seconds (default: 300)

        Returns:
            List of dictionaries representing query results
            (same format as DatabaseAdapter for compatibility)

        Raises:
            ExecutionError: If query execution fails or connection not established
        """
        if not self._client:
            raise ExecutionError("BigQuery connection not established. Call connect() first.")

        if not query or not query.strip():
            raise ExecutionError("Query cannot be empty")

        try:
            from google.cloud.bigquery import QueryJobConfig

            # Configure query job
            job_config = QueryJobConfig()
            if self.default_dataset:
                job_config.default_dataset = f"{self.project_id}.{self.default_dataset}"

            # Execute query
            query_job = self._client.query(query, job_config=job_config, timeout=timeout)

            # Wait for query to complete
            results = query_job.result(timeout=timeout)

            # Convert results to list of dictionaries
            rows = []
            for row in results:
                # Convert BigQuery Row to dict
                row_dict = dict(row.items())
                # Convert BigQuery-specific types to Python types
                row_dict = self._convert_bigquery_types(row_dict)
                rows.append(row_dict)

            return rows

        except TimeoutError as e:
            raise ExecutionError(f"Query execution timed out after {timeout} seconds") from e
        except Exception as e:
            raise ExecutionError(f"Query execution failed: {e}") from e

    def dry_run(self, query: str) -> dict[str, Any]:
        """
        Perform query dry-run to estimate cost.

        Args:
            query: SQL query to estimate

        Returns:
            Dictionary with:
                - bytes_processed: Estimated bytes that will be processed
                - estimated_cost_usd: Estimated cost in USD ($5 per TB)

        Raises:
            ExecutionError: If dry-run fails or connection not established
        """
        if not self._client:
            raise ExecutionError("BigQuery connection not established. Call connect() first.")

        if not query or not query.strip():
            raise ExecutionError("Query cannot be empty")

        try:
            from google.cloud.bigquery import QueryJobConfig

            # Configure dry-run job
            job_config = QueryJobConfig(dry_run=True, use_query_cache=False)
            if self.default_dataset:
                job_config.default_dataset = f"{self.project_id}.{self.default_dataset}"

            # Execute dry-run
            query_job = self._client.query(query, job_config=job_config)

            # Get bytes processed
            bytes_processed = query_job.total_bytes_processed or 0

            # Calculate estimated cost ($5 per TB, first 1 TB free per month)
            # Note: This is a simplified estimate - actual costs may vary
            tb_processed = bytes_processed / (1024**4)  # Convert bytes to TB
            estimated_cost = max(0, (tb_processed - 1) * 5)  # First 1 TB free

            return {
                "bytes_processed": bytes_processed,
                "tb_processed": tb_processed,
                "estimated_cost_usd": estimated_cost,
            }

        except Exception as e:
            raise ExecutionError(f"Query dry-run failed: {e}") from e

    def _convert_bigquery_types(self, row_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Convert BigQuery-specific types to standard Python types.

        Args:
            row_dict: Dictionary with BigQuery types

        Returns:
            Dictionary with converted types
        """
        import datetime

        converted: dict[str, Any] = {}
        for key, value in row_dict.items():
            if value is None:
                converted[key] = None
            elif isinstance(value, datetime.datetime):
                # Keep datetime as is (compatible with Python)
                converted[key] = value
            elif isinstance(value, datetime.date):
                # Convert date to datetime for consistency
                converted[key] = datetime.datetime.combine(value, datetime.time.min)
            elif isinstance(value, list | tuple):
                # Handle ARRAY types (keep as list)
                converted[key] = list(value)
            elif isinstance(value, dict):
                # Handle STRUCT types (keep as dict)
                converted[key] = value
            else:
                # Keep all other types as is (int, float, str, bool, etc.)
                converted[key] = value

        return converted

    def __enter__(self) -> "BigQueryAdapter":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.disconnect()
