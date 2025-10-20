"""Tests for CLI module."""

import argparse
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine

from sqlsentinel.cli import (
    AppConfig,
    DatabaseConfig,
    init_database,
    load_config,
    main,
    run_alert,
    run_all_alerts,
    show_history,
    silence_alert,
    show_status,
    unsilence_alert,
    validate_config,
)
from sqlsentinel.models.alert import AlertConfig, QueryResult
from sqlsentinel.models.notification import EmailConfig, NotificationConfig


class TestDatabaseConfig:
    """Tests for DatabaseConfig model."""

    def test_create_database_config(self):
        """Test creating a DatabaseConfig."""
        config = DatabaseConfig(url="sqlite:///test.db")
        assert config.url == "sqlite:///test.db"


class TestAppConfig:
    """Tests for AppConfig model."""

    def test_create_app_config(self):
        """Test creating an AppConfig."""
        db_config = DatabaseConfig(url="sqlite:///test.db")
        alert = AlertConfig(
            name="test_alert",
            description="Test alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
        )
        config = AppConfig(database=db_config, alerts=[alert])

        assert config.database.url == "sqlite:///test.db"
        assert len(config.alerts) == 1
        assert config.alerts[0].name == "test_alert"


class TestLoadConfig:
    """Tests for load_config function."""

    @patch("sqlsentinel.cli.ConfigLoader")
    @patch("sqlsentinel.cli.ConfigValidator")
    def test_load_config_success(self, mock_validator_class, mock_loader_class):
        """Test successful configuration loading."""
        # Mock loader
        mock_loader = Mock()
        mock_loader.load.return_value = {
            "database": {"url": "sqlite:///test.db"},
            "alerts": [],
        }
        mock_loader_class.return_value = mock_loader

        # Mock validator
        mock_validator = Mock()
        mock_validator.validate.return_value = []
        mock_validator_class.return_value = mock_validator

        # Load config
        config = load_config("test.yaml")

        # Assertions
        assert config.database.url == "sqlite:///test.db"
        assert config.alerts == []
        mock_loader_class.assert_called_once_with("test.yaml")
        mock_loader.load.assert_called_once()
        mock_validator.validate.assert_called_once()


class TestInitDatabase:
    """Tests for init_database function."""

    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.cli.SchemaManager")
    def test_init_database_success(self, mock_schema_class, mock_create_engine, capsys):
        """Test successful database initialization."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_schema = Mock()
        mock_schema_class.return_value = mock_schema

        # Initialize database
        init_database("sqlite:///test.db")

        # Assertions
        mock_create_engine.assert_called_once_with("sqlite:///test.db")
        mock_schema_class.assert_called_once_with(mock_engine)
        mock_schema.initialize_schema.assert_called_once()

        # Check output
        captured = capsys.readouterr()
        assert "Initializing SQL Sentinel schema" in captured.out
        assert "Schema initialized successfully" in captured.out


class TestRunAlert:
    """Tests for run_alert function."""

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.cli.NotificationFactory")
    @patch("sqlsentinel.cli.AlertExecutor")
    @patch("sqlsentinel.cli.DatabaseAdapter")
    def test_run_alert_success(
        self,
        mock_adapter_class,
        mock_executor_class,
        mock_factory_class,
        mock_create_engine,
        mock_load_config,
        capsys,
    ):
        """Test successful alert execution."""
        # Mock config
        alert = AlertConfig(
            name="test_alert",
            description="Test alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
        )
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=[alert],
        )
        mock_load_config.return_value = config

        # Mock engine
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Mock adapter
        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter

        # Mock executor
        mock_executor = Mock()
        mock_result = Mock()
        mock_result.alert_name = "test_alert"
        mock_result.status = "success"
        mock_result.duration_ms = 123.45
        mock_result.query_result = QueryResult(
            status="OK",
            actual_value=10,
            threshold=5,
            context={"foo": "bar"},
        )
        mock_result.error = None
        mock_executor.execute_alert.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        # Run alert
        exit_code = run_alert("test.yaml", "test_alert", "sqlite:///state.db")

        # Assertions
        assert exit_code == 0
        mock_load_config.assert_called_once_with("test.yaml")
        mock_adapter.connect.assert_called_once()
        mock_adapter.disconnect.assert_called_once()
        mock_executor.execute_alert.assert_called_once()

        # Check output
        captured = capsys.readouterr()
        assert "Loading configuration" in captured.out
        assert "Found alert: test_alert" in captured.out
        assert "Executing alert" in captured.out
        assert "Alert Execution Result" in captured.out

    @patch("sqlsentinel.cli.load_config")
    def test_run_alert_not_found(self, mock_load_config, capsys):
        """Test running alert that doesn't exist."""
        alert = AlertConfig(
            name="other_alert",
            description="Other alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
        )
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=[alert],
        )
        mock_load_config.return_value = config

        # Run non-existent alert
        exit_code = run_alert("test.yaml", "test_alert", "sqlite:///state.db")

        # Assertions
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Alert 'test_alert' not found" in captured.out
        assert "Available alerts: other_alert" in captured.out

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.cli.NotificationFactory")
    @patch("sqlsentinel.cli.AlertExecutor")
    @patch("sqlsentinel.cli.DatabaseAdapter")
    def test_run_alert_error_status(
        self,
        mock_adapter_class,
        mock_executor_class,
        mock_factory_class,
        mock_create_engine,
        mock_load_config,
    ):
        """Test alert execution that results in error."""
        alert = AlertConfig(
            name="test_alert",
            description="Test alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
        )
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=[alert],
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter

        mock_executor = Mock()
        mock_result = Mock()
        mock_result.status = "error"
        mock_result.alert_name = "test_alert"
        mock_result.duration_ms = 100.0
        mock_result.query_result = None
        mock_result.error = "Query failed"
        mock_executor.execute_alert.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        exit_code = run_alert("test.yaml", "test_alert", "sqlite:///state.db")

        assert exit_code == 1

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.cli.NotificationFactory")
    @patch("sqlsentinel.cli.AlertExecutor")
    @patch("sqlsentinel.cli.DatabaseAdapter")
    def test_run_alert_dry_run(
        self,
        mock_adapter_class,
        mock_executor_class,
        mock_factory_class,
        mock_create_engine,
        mock_load_config,
        capsys,
    ):
        """Test alert execution in dry-run mode."""
        alert = AlertConfig(
            name="test_alert",
            description="Test alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
        )
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=[alert],
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter

        mock_executor = Mock()
        mock_result = Mock()
        mock_result.status = "success"
        mock_result.alert_name = "test_alert"
        mock_result.duration_ms = 100.0
        mock_result.query_result = None
        mock_result.error = None
        mock_executor.execute_alert.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        exit_code = run_alert("test.yaml", "test_alert", "sqlite:///state.db", dry_run=True)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "DRY RUN MODE" in captured.out

        # Verify dry_run was passed to executor
        call_args = mock_executor.execute_alert.call_args
        assert call_args.kwargs["dry_run"] is True

    @patch("sqlsentinel.cli.load_config")
    def test_run_alert_exception(self, mock_load_config, capsys):
        """Test alert execution with exception."""
        mock_load_config.side_effect = Exception("Config error")

        exit_code = run_alert("test.yaml", "test_alert", "sqlite:///state.db")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error executing alert" in captured.out


class TestRunAllAlerts:
    """Tests for run_all_alerts function."""

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.cli.NotificationFactory")
    @patch("sqlsentinel.cli.AlertExecutor")
    @patch("sqlsentinel.cli.DatabaseAdapter")
    def test_run_all_alerts_success(
        self,
        mock_adapter_class,
        mock_executor_class,
        mock_factory_class,
        mock_create_engine,
        mock_load_config,
        capsys,
    ):
        """Test successful execution of all alerts."""
        alerts = [
            AlertConfig(
                name="alert1",
                description="First alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
                enabled=True,
            ),
            AlertConfig(
                name="alert2",
                description="Second alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
                enabled=True,
            ),
        ]
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=alerts,
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter

        mock_executor = Mock()
        mock_result = Mock()
        mock_result.status = "success"
        mock_result.duration_ms = 100.0
        mock_result.query_result = Mock(status="OK")
        mock_executor.execute_alert.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        exit_code = run_all_alerts("test.yaml", "sqlite:///state.db")

        assert exit_code == 0
        assert mock_executor.execute_alert.call_count == 2
        captured = capsys.readouterr()
        assert "Found 2 alert(s)" in captured.out
        assert "Execution Summary" in captured.out

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.cli.NotificationFactory")
    @patch("sqlsentinel.cli.AlertExecutor")
    @patch("sqlsentinel.cli.DatabaseAdapter")
    def test_run_all_alerts_with_disabled(
        self,
        mock_adapter_class,
        mock_executor_class,
        mock_factory_class,
        mock_create_engine,
        mock_load_config,
        capsys,
    ):
        """Test running all alerts with some disabled."""
        alerts = [
            AlertConfig(
                name="alert1",
                description="Enabled alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
                enabled=True,
            ),
            AlertConfig(
                name="alert2",
                description="Disabled alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
                enabled=False,
            ),
        ]
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=alerts,
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter

        mock_executor = Mock()
        mock_result = Mock()
        mock_result.status = "success"
        mock_result.duration_ms = 100.0
        mock_result.query_result = Mock(status="OK")
        mock_executor.execute_alert.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        exit_code = run_all_alerts("test.yaml", "sqlite:///state.db")

        assert exit_code == 0
        # Only one alert should be executed
        assert mock_executor.execute_alert.call_count == 1
        captured = capsys.readouterr()
        assert "Skipping disabled alert: alert2" in captured.out

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.cli.NotificationFactory")
    @patch("sqlsentinel.cli.AlertExecutor")
    @patch("sqlsentinel.cli.DatabaseAdapter")
    def test_run_all_alerts_with_failures(
        self,
        mock_adapter_class,
        mock_executor_class,
        mock_factory_class,
        mock_create_engine,
        mock_load_config,
    ):
        """Test running all alerts with some failures."""
        alerts = [
            AlertConfig(
                name="alert1",
                description="Success alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
            ),
            AlertConfig(
                name="alert2",
                description="Failed alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
            ),
        ]
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=alerts,
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter

        mock_executor = Mock()

        # First alert succeeds, second fails
        def execute_side_effect(*args, **kwargs):
            alert = kwargs.get("alert") or args[0]
            result = Mock()
            if alert.name == "alert1":
                result.status = "success"
            else:
                result.status = "error"
            result.duration_ms = 100.0
            result.query_result = Mock(status="OK") if alert.name == "alert1" else None
            return result

        mock_executor.execute_alert.side_effect = execute_side_effect
        mock_executor_class.return_value = mock_executor

        exit_code = run_all_alerts("test.yaml", "sqlite:///state.db")

        assert exit_code == 1  # Should return 1 if any alerts failed

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.cli.NotificationFactory")
    @patch("sqlsentinel.cli.AlertExecutor")
    @patch("sqlsentinel.cli.DatabaseAdapter")
    def test_run_all_alerts_dry_run(
        self,
        mock_adapter_class,
        mock_executor_class,
        mock_factory_class,
        mock_create_engine,
        mock_load_config,
        capsys,
    ):
        """Test running all alerts in dry-run mode."""
        alerts = [
            AlertConfig(
                name="alert1",
                description="Test alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
            )
        ]
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=alerts,
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter

        mock_executor = Mock()
        mock_result = Mock()
        mock_result.status = "success"
        mock_result.duration_ms = 100.0
        mock_result.query_result = Mock(status="OK")
        mock_executor.execute_alert.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        exit_code = run_all_alerts("test.yaml", "sqlite:///state.db", dry_run=True)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "DRY RUN MODE" in captured.out

    @patch("sqlsentinel.cli.load_config")
    def test_run_all_alerts_exception(self, mock_load_config, capsys):
        """Test running all alerts with exception."""
        mock_load_config.side_effect = Exception("Config error")

        exit_code = run_all_alerts("test.yaml", "sqlite:///state.db")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error running alerts" in captured.out


class TestValidateConfig:
    """Tests for validate_config function."""

    @patch("sqlsentinel.cli.load_config")
    def test_validate_config_success(self, mock_load_config, capsys):
        """Test successful configuration validation."""
        alerts = [
            AlertConfig(
                name="alert1",
                description="Test alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
                enabled=True,
            )
        ]
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=alerts,
        )
        mock_load_config.return_value = config

        exit_code = validate_config("test.yaml")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Configuration is valid" in captured.out
        assert "Database: sqlite:///test.db" in captured.out
        assert "Alerts: 1" in captured.out
        assert "alert1 (enabled)" in captured.out

    @patch("sqlsentinel.cli.load_config")
    def test_validate_config_disabled_alert(self, mock_load_config, capsys):
        """Test validation with disabled alert."""
        alerts = [
            AlertConfig(
                name="alert1",
                description="Disabled alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"])
                )
            ],
                enabled=False,
            )
        ]
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=alerts,
        )
        mock_load_config.return_value = config

        exit_code = validate_config("test.yaml")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "alert1 (disabled)" in captured.out

    @patch("sqlsentinel.cli.load_config")
    def test_validate_config_failure(self, mock_load_config, capsys):
        """Test configuration validation failure."""
        mock_load_config.side_effect = Exception("Invalid config")

        exit_code = validate_config("test.yaml")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Configuration validation failed" in captured.out


class TestShowHistory:
    """Tests for show_history function."""

    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.executor.history.ExecutionHistory")
    def test_show_history_success(self, mock_history_class, mock_create_engine, capsys):
        """Test showing execution history."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_history = Mock()
        mock_record = Mock()
        mock_record.executed_at = "2024-01-01 12:00:00"
        mock_record.alert_name = "test_alert"
        mock_record.status = "success"
        mock_record.execution_duration_ms = 123.45
        mock_record.triggered_by = "MANUAL"
        mock_record.actual_value = 10
        mock_record.threshold = 5
        mock_record.error_message = None
        mock_record.notification_sent = True
        mock_history.get_executions.return_value = [mock_record]
        mock_history_class.return_value = mock_history

        exit_code = show_history("test.yaml", "sqlite:///state.db")

        assert exit_code == 0
        mock_history.get_executions.assert_called_once_with(alert_name=None, limit=10)
        captured = capsys.readouterr()
        assert "Execution History" in captured.out
        assert "test_alert" in captured.out
        assert "Notification sent" in captured.out

    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.executor.history.ExecutionHistory")
    def test_show_history_filtered(self, mock_history_class, mock_create_engine):
        """Test showing filtered execution history."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_history = Mock()
        mock_history.get_executions.return_value = []
        mock_history_class.return_value = mock_history

        exit_code = show_history("test.yaml", "sqlite:///state.db", alert_name="test_alert")

        assert exit_code == 0
        mock_history.get_executions.assert_called_once_with(
            alert_name="test_alert", limit=10
        )

    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.executor.history.ExecutionHistory")
    def test_show_history_empty(self, mock_history_class, mock_create_engine, capsys):
        """Test showing empty history."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_history = Mock()
        mock_history.get_executions.return_value = []
        mock_history_class.return_value = mock_history

        exit_code = show_history("test.yaml", "sqlite:///state.db")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No execution history found" in captured.out

    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.executor.history.ExecutionHistory")
    def test_show_history_with_error(self, mock_history_class, mock_create_engine, capsys):
        """Test showing history with error record."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_history = Mock()
        mock_record = Mock()
        mock_record.executed_at = "2024-01-01 12:00:00"
        mock_record.alert_name = "test_alert"
        mock_record.status = "error"
        mock_record.execution_duration_ms = 50.0
        mock_record.triggered_by = "MANUAL"
        mock_record.actual_value = None
        mock_record.threshold = None
        mock_record.error_message = "Query failed"
        mock_record.notification_sent = False
        mock_history.get_executions.return_value = [mock_record]
        mock_history_class.return_value = mock_history

        exit_code = show_history("test.yaml", "sqlite:///state.db")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Error: Query failed" in captured.out

    @patch("sqlsentinel.cli.create_engine")
    def test_show_history_exception(self, mock_create_engine, capsys):
        """Test show history with exception."""
        mock_create_engine.side_effect = Exception("Database error")

        exit_code = show_history("test.yaml", "sqlite:///state.db")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error retrieving history" in captured.out


class TestMain:
    """Tests for main CLI function."""

    @patch("sys.argv", ["sqlsentinel"])
    def test_main_no_command(self, capsys):
        """Test main with no command."""
        exit_code = main()
        assert exit_code == 1

    @patch("sys.argv", ["sqlsentinel", "init"])
    @patch("sqlsentinel.cli.init_database")
    def test_main_init_command(self, mock_init):
        """Test main with init command."""
        mock_init.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_init.assert_called_once_with("sqlite:///sqlsentinel.db")

    @patch("sys.argv", ["sqlsentinel", "init", "--state-db", "sqlite:///custom.db"])
    @patch("sqlsentinel.cli.init_database")
    def test_main_init_command_custom_db(self, mock_init):
        """Test main with init command and custom database."""
        mock_init.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_init.assert_called_once_with("sqlite:///custom.db")

    @patch("sys.argv", ["sqlsentinel", "validate", "test.yaml"])
    @patch("sqlsentinel.cli.validate_config")
    def test_main_validate_command(self, mock_validate):
        """Test main with validate command."""
        mock_validate.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_validate.assert_called_once_with("test.yaml")

    @patch("sys.argv", ["sqlsentinel", "run", "test.yaml"])
    @patch("sqlsentinel.cli.run_all_alerts")
    def test_main_run_all_command(self, mock_run_all):
        """Test main with run command for all alerts."""
        mock_run_all.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_run_all.assert_called_once_with(
            "test.yaml", "sqlite:///sqlsentinel.db", False
        )

    @patch("sys.argv", ["sqlsentinel", "run", "test.yaml", "--alert", "my_alert"])
    @patch("sqlsentinel.cli.run_alert")
    def test_main_run_single_alert_command(self, mock_run_alert):
        """Test main with run command for single alert."""
        mock_run_alert.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_run_alert.assert_called_once_with(
            "test.yaml", "my_alert", "sqlite:///sqlsentinel.db", False
        )

    @patch("sys.argv", ["sqlsentinel", "run", "test.yaml", "--dry-run"])
    @patch("sqlsentinel.cli.run_all_alerts")
    def test_main_run_dry_run(self, mock_run_all):
        """Test main with run command in dry-run mode."""
        mock_run_all.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_run_all.assert_called_once_with(
            "test.yaml", "sqlite:///sqlsentinel.db", True
        )

    @patch("sys.argv", ["sqlsentinel", "history", "test.yaml"])
    @patch("sqlsentinel.cli.show_history")
    def test_main_history_command(self, mock_history):
        """Test main with history command."""
        mock_history.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_history.assert_called_once_with(
            "test.yaml", "sqlite:///sqlsentinel.db", None, 10
        )

    @patch(
        "sys.argv",
        ["sqlsentinel", "history", "test.yaml", "--alert", "my_alert", "--limit", "20"],
    )
    @patch("sqlsentinel.cli.show_history")
    def test_main_history_filtered(self, mock_history):
        """Test main with filtered history command."""
        mock_history.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_history.assert_called_once_with(
            "test.yaml", "sqlite:///sqlsentinel.db", "my_alert", 20
        )

    @patch("sys.argv", ["sqlsentinel", "silence", "test.yaml", "--alert", "my_alert"])
    @patch("sqlsentinel.cli.silence_alert")
    def test_main_silence_command(self, mock_silence):
        """Test main with silence command."""
        mock_silence.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_silence.assert_called_once_with(
            "test.yaml", "sqlite:///sqlsentinel.db", "my_alert", 1
        )

    @patch(
        "sys.argv",
        ["sqlsentinel", "silence", "test.yaml", "--alert", "my_alert", "--duration", "4"],
    )
    @patch("sqlsentinel.cli.silence_alert")
    def test_main_silence_command_custom_duration(self, mock_silence):
        """Test main with silence command and custom duration."""
        mock_silence.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_silence.assert_called_once_with(
            "test.yaml", "sqlite:///sqlsentinel.db", "my_alert", 4
        )

    @patch("sys.argv", ["sqlsentinel", "unsilence", "test.yaml", "--alert", "my_alert"])
    @patch("sqlsentinel.cli.unsilence_alert")
    def test_main_unsilence_command(self, mock_unsilence):
        """Test main with unsilence command."""
        mock_unsilence.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_unsilence.assert_called_once_with(
            "test.yaml", "sqlite:///sqlsentinel.db", "my_alert"
        )

    @patch("sys.argv", ["sqlsentinel", "status", "test.yaml"])
    @patch("sqlsentinel.cli.show_status")
    def test_main_status_command(self, mock_status):
        """Test main with status command."""
        mock_status.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_status.assert_called_once_with(
            "test.yaml", "sqlite:///sqlsentinel.db", None
        )

    @patch("sys.argv", ["sqlsentinel", "status", "test.yaml", "--alert", "my_alert"])
    @patch("sqlsentinel.cli.show_status")
    def test_main_status_filtered(self, mock_status):
        """Test main with filtered status command."""
        mock_status.return_value = 0
        exit_code = main()
        assert exit_code == 0
        mock_status.assert_called_once_with(
            "test.yaml", "sqlite:///sqlsentinel.db", "my_alert"
        )


class TestSilenceAlert:
    """Tests for silence_alert function."""

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.executor.state.StateManager")
    def test_silence_alert_success(
        self, mock_state_class, mock_create_engine, mock_load_config, capsys
    ):
        """Test successful alert silencing."""
        # Mock config
        alert = AlertConfig(
            name="test_alert",
            description="Test alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"]),
                )
            ],
        )
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=[alert],
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_state_manager = Mock()
        mock_state_class.return_value = mock_state_manager

        exit_code = silence_alert("test.yaml", "sqlite:///state.db", "test_alert", 2)

        assert exit_code == 0
        mock_state_manager.silence_alert.assert_called_once_with("test_alert", 7200)
        captured = capsys.readouterr()
        assert "silenced until" in captured.out
        assert "Duration: 2 hour(s)" in captured.out

    @patch("sqlsentinel.cli.load_config")
    def test_silence_alert_not_found(self, mock_load_config, capsys):
        """Test silencing alert that doesn't exist."""
        alert = AlertConfig(
            name="other_alert",
            description="Other alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"]),
                )
            ],
        )
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=[alert],
        )
        mock_load_config.return_value = config

        exit_code = silence_alert("test.yaml", "sqlite:///state.db", "test_alert", 1)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Alert 'test_alert' not found" in captured.out
        assert "Available alerts: other_alert" in captured.out

    @patch("sqlsentinel.cli.load_config")
    def test_silence_alert_exception(self, mock_load_config, capsys):
        """Test silence alert with exception."""
        mock_load_config.side_effect = Exception("Config error")

        exit_code = silence_alert("test.yaml", "sqlite:///state.db", "test_alert", 1)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error silencing alert" in captured.out


class TestUnsilenceAlert:
    """Tests for unsilence_alert function."""

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.executor.state.StateManager")
    def test_unsilence_alert_success(
        self, mock_state_class, mock_create_engine, mock_load_config, capsys
    ):
        """Test successful alert unsilencing."""
        # Mock config
        alert = AlertConfig(
            name="test_alert",
            description="Test alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"]),
                )
            ],
        )
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=[alert],
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_state_manager = Mock()
        mock_state_class.return_value = mock_state_manager

        exit_code = unsilence_alert("test.yaml", "sqlite:///state.db", "test_alert")

        assert exit_code == 0
        mock_state_manager.unsilence_alert.assert_called_once_with("test_alert")
        captured = capsys.readouterr()
        assert "unsilenced successfully" in captured.out

    @patch("sqlsentinel.cli.load_config")
    def test_unsilence_alert_not_found(self, mock_load_config, capsys):
        """Test unsilencing alert that doesn't exist."""
        alert = AlertConfig(
            name="other_alert",
            description="Other alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"]),
                )
            ],
        )
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=[alert],
        )
        mock_load_config.return_value = config

        exit_code = unsilence_alert("test.yaml", "sqlite:///state.db", "test_alert")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Alert 'test_alert' not found" in captured.out

    @patch("sqlsentinel.cli.load_config")
    def test_unsilence_alert_exception(self, mock_load_config, capsys):
        """Test unsilence alert with exception."""
        mock_load_config.side_effect = Exception("Config error")

        exit_code = unsilence_alert("test.yaml", "sqlite:///state.db", "test_alert")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error unsilencing alert" in captured.out


class TestShowStatus:
    """Tests for show_status function."""

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.executor.state.StateManager")
    def test_show_status_success(
        self, mock_state_class, mock_create_engine, mock_load_config, capsys
    ):
        """Test successful status display."""
        from datetime import datetime

        # Mock config
        alerts = [
            AlertConfig(
                name="alert1",
                description="First alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                    NotificationConfig(
                        channel="email",
                        config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"]),
                    )
                ],
            ),
            AlertConfig(
                name="alert2",
                description="Second alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                    NotificationConfig(
                        channel="email",
                        config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"]),
                    )
                ],
            ),
        ]
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=alerts,
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_state_manager = Mock()

        # Mock state for alert1 with execution history
        mock_state1 = Mock()
        mock_state1.current_status = "OK"
        mock_state1.last_executed_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_state1.silenced_until = None

        # Mock state for alert2 with no execution history
        mock_state2 = Mock()
        mock_state2.current_status = None
        mock_state2.last_executed_at = None
        mock_state2.silenced_until = None

        def get_state_side_effect(alert_name):
            if alert_name == "alert1":
                return mock_state1
            return mock_state2

        mock_state_manager.get_state.side_effect = get_state_side_effect
        mock_state_class.return_value = mock_state_manager

        exit_code = show_status("test.yaml", "sqlite:///state.db")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Alert Status Report" in captured.out
        assert "alert1" in captured.out
        assert "alert2" in captured.out
        assert "OK" in captured.out

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.executor.state.StateManager")
    def test_show_status_with_silenced(
        self, mock_state_class, mock_create_engine, mock_load_config, capsys
    ):
        """Test status display with silenced alert."""
        from datetime import datetime, timedelta

        alert = AlertConfig(
            name="test_alert",
            description="Test alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"]),
                )
            ],
        )
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=[alert],
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_state_manager = Mock()
        mock_state = Mock()
        mock_state.current_status = "ALERT"
        mock_state.last_executed_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_state.silenced_until = datetime.utcnow() + timedelta(hours=2)
        mock_state_manager.get_state.return_value = mock_state
        mock_state_class.return_value = mock_state_manager

        exit_code = show_status("test.yaml", "sqlite:///state.db")

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Alert Status Report" in captured.out
        assert "Yes (until" in captured.out

    @patch("sqlsentinel.cli.load_config")
    @patch("sqlsentinel.cli.create_engine")
    @patch("sqlsentinel.executor.state.StateManager")
    def test_show_status_filtered(
        self, mock_state_class, mock_create_engine, mock_load_config
    ):
        """Test status display filtered by alert name."""
        from datetime import datetime

        alerts = [
            AlertConfig(
                name="alert1",
                description="First alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                    NotificationConfig(
                        channel="email",
                        config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"]),
                    )
                ],
            ),
            AlertConfig(
                name="alert2",
                description="Second alert",
                query="SELECT 'OK' as status",
                schedule="* * * * *",
                notify=[
                    NotificationConfig(
                        channel="email",
                        config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"]),
                    )
                ],
            ),
        ]
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=alerts,
        )
        mock_load_config.return_value = config

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_state_manager = Mock()
        mock_state = Mock()
        mock_state.current_status = "OK"
        mock_state.last_executed_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_state.silenced_until = None
        mock_state_manager.get_state.return_value = mock_state
        mock_state_class.return_value = mock_state_manager

        exit_code = show_status("test.yaml", "sqlite:///state.db", alert_name="alert1")

        assert exit_code == 0
        # Should only call get_state once for alert1
        assert mock_state_manager.get_state.call_count == 1

    @patch("sqlsentinel.cli.load_config")
    def test_show_status_alert_not_found(self, mock_load_config, capsys):
        """Test status display for non-existent alert."""
        alert = AlertConfig(
            name="other_alert",
            description="Other alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            notify=[
                NotificationConfig(
                    channel="email",
                    config=EmailConfig(recipients=["sqlsentinel@kylegehring.com"]),
                )
            ],
        )
        config = AppConfig(
            database=DatabaseConfig(url="sqlite:///test.db"),
            alerts=[alert],
        )
        mock_load_config.return_value = config

        exit_code = show_status("test.yaml", "sqlite:///state.db", alert_name="test_alert")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Alert 'test_alert' not found" in captured.out

    @patch("sqlsentinel.cli.load_config")
    def test_show_status_exception(self, mock_load_config, capsys):
        """Test status display with exception."""
        mock_load_config.side_effect = Exception("Config error")

        exit_code = show_status("test.yaml", "sqlite:///state.db")

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error showing status" in captured.out
