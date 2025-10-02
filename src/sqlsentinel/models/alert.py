"""Alert configuration models."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .notification import NotificationConfig


class AlertConfig(BaseModel):
    """Alert configuration from YAML."""

    name: str = Field(..., min_length=1, description="Alert name")
    description: str | None = Field(None, description="Alert description")
    query: str = Field(..., min_length=1, description="SQL query to execute")
    schedule: str = Field(..., description="Cron schedule expression")
    notify: list[NotificationConfig] = Field(
        default_factory=list, description="Notification configurations"
    )
    enabled: bool = Field(True, description="Whether alert is enabled")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate SQL query."""
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v: str) -> str:
        """Validate cron schedule expression."""
        from croniter import croniter

        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron schedule: {v}")
        return v


class QueryResult(BaseModel):
    """Result from executing an alert query."""

    status: str = Field(..., description="Alert status: ALERT or OK")
    actual_value: Any = Field(None, description="The metric value that triggered the alert")
    threshold: Any = Field(None, description="The threshold that was exceeded")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context fields")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status field."""
        v = v.upper()
        if v not in ["ALERT", "OK"]:
            raise ValueError(f"Status must be 'ALERT' or 'OK', got '{v}'")
        return v


class ExecutionResult(BaseModel):
    """Result from executing an alert."""

    alert_name: str = Field(..., description="Name of the alert that was executed")
    timestamp: str = Field(..., description="Execution timestamp (ISO format)")
    status: str = Field(..., description="Execution status: success, failure, error")
    query_result: QueryResult | None = Field(None, description="Query result if successful")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    error: str | None = Field(None, description="Error message if execution failed")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate execution status."""
        v = v.lower()
        if v not in ["success", "failure", "error"]:
            raise ValueError(f"Status must be 'success', 'failure', or 'error', got '{v}'")
        return v
