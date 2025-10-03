"""Database adapter for SQL Sentinel."""

from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..models.errors import ExecutionError


class DatabaseAdapter:
    """Database adapter using SQLAlchemy for multi-database support."""

    def __init__(self, connection_string: str):
        """Initialize database adapter.

        Args:
            connection_string: SQLAlchemy connection string

        Raises:
            ExecutionError: If connection string is invalid or connection fails
        """
        if not connection_string or not connection_string.strip():
            raise ExecutionError("Connection string cannot be empty")

        self.connection_string = connection_string
        self._engine: Engine | None = None

    def connect(self) -> None:
        """Establish database connection.

        Raises:
            ExecutionError: If connection fails
        """
        try:
            self._engine = create_engine(self.connection_string)
            # Test connection
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except SQLAlchemyError as e:
            raise ExecutionError(f"Failed to connect to database: {e}") from e
        except Exception as e:
            raise ExecutionError(f"Unexpected error connecting to database: {e}") from e

    def disconnect(self) -> None:
        """Close database connection."""
        if self._engine:
            self._engine.dispose()
            self._engine = None

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute SQL query and return results.

        Args:
            query: SQL query to execute

        Returns:
            List of dictionaries representing query results

        Raises:
            ExecutionError: If query execution fails or connection not established
        """
        if not self._engine:
            raise ExecutionError("Database connection not established. Call connect() first.")

        if not query or not query.strip():
            raise ExecutionError("Query cannot be empty")

        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(query))
                # Convert result to list of dictionaries
                rows = []
                if result.returns_rows:
                    for row in result:
                        rows.append(dict(row._mapping))
                return rows
        except SQLAlchemyError as e:
            raise ExecutionError(f"Query execution failed: {e}") from e
        except Exception as e:
            raise ExecutionError(f"Unexpected error executing query: {e}") from e

    def __enter__(self) -> "DatabaseAdapter":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.disconnect()
