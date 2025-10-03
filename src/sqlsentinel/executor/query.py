"""Query executor for SQL Sentinel."""

from ..database.adapter import DatabaseAdapter
from ..models.alert import QueryResult
from ..models.errors import ExecutionError, ValidationError


class QueryExecutor:
    """Executes alert queries and validates results."""

    def __init__(self, db_adapter: DatabaseAdapter):
        """Initialize query executor.

        Args:
            db_adapter: Database adapter instance
        """
        self.db_adapter = db_adapter

    def execute(self, query: str) -> QueryResult:
        """Execute alert query and return validated result.

        Args:
            query: SQL query to execute

        Returns:
            QueryResult object with status and optional metrics

        Raises:
            ExecutionError: If query execution fails
            ValidationError: If query result doesn't match expected schema
        """
        # Execute the query
        rows = self.db_adapter.execute_query(query)

        # Validate result set
        if not rows:
            raise ValidationError(
                "Query returned no results. Alert queries must return at least one row "
                "with a 'status' column containing 'ALERT' or 'OK'."
            )

        if len(rows) > 1:
            raise ValidationError(
                f"Query returned {len(rows)} rows. Alert queries must return exactly one row."
            )

        row = rows[0]

        # Validate required 'status' column
        if "status" not in row:
            available_columns = ", ".join(row.keys())
            raise ValidationError(
                f"Query result missing required 'status' column. "
                f"Available columns: {available_columns}"
            )

        # Extract fields for QueryResult
        status = row["status"]
        actual_value = row.get("actual_value")
        threshold = row.get("threshold")

        # Extract additional context (all columns except the known ones)
        context = {k: v for k, v in row.items() if k not in ["status", "actual_value", "threshold"]}

        try:
            return QueryResult(
                status=status,
                actual_value=actual_value,
                threshold=threshold,
                context=context,
            )
        except Exception as e:
            raise ValidationError(f"Failed to create QueryResult: {e}") from e

    def validate_query_contract(self, query: str) -> tuple[bool, str]:
        """Validate that a query follows the alert query contract.

        This method executes the query and checks if it returns the expected format.

        Args:
            query: SQL query to validate

        Returns:
            Tuple of (is_valid, message) where message explains any issues

        Raises:
            ExecutionError: If query execution fails
        """
        try:
            result = self.execute(query)
            return True, f"Query is valid. Status: {result.status}"
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            raise ExecutionError(f"Query validation failed: {e}") from e
