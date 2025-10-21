"""Tests for SchedulerService."""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlsentinel.database.schema import SchemaManager
from sqlsentinel.models.errors import ConfigurationError
from sqlsentinel.scheduler.scheduler import SchedulerService


class TestSchedulerService:
    """Test SchedulerService class."""

    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration file."""
        config_content = """
alerts:
  - name: "test_alert_1"
    description: "Test alert 1"
    query: "SELECT 'OK' as status"
    schedule: "0 9 * * *"
    enabled: true
    notify:
      - channel: email
        recipients: ["test@example.com"]

  - name: "test_alert_2"
    description: "Test alert 2"
    query: "SELECT 'OK' as status"
    schedule: "*/15 * * * *"
    enabled: true
    notify: []

  - name: "test_alert_disabled"
    description: "Disabled alert"
    query: "SELECT 'OK' as status"
    schedule: "0 0 * * *"
    enabled: false
    notify: []
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def state_db_url(self):
        """Create in-memory state database."""
        url = "sqlite:///:memory:"
        engine = create_engine(url)
        schema_manager = SchemaManager(engine)
        schema_manager.create_schema()
        engine.dispose()
        return url

    @pytest.fixture
    def scheduler_service(self, temp_config, state_db_url):
        """Create SchedulerService instance."""
        service = SchedulerService(
            config_path=temp_config,
            state_db_url=state_db_url,
            database_url="sqlite:///:memory:",
            timezone="UTC",
        )
        yield service
        # Cleanup
        if service.scheduler.running:
            service.stop(wait=False)

    def test_init(self, temp_config, state_db_url):
        """Test SchedulerService initialization."""
        service = SchedulerService(
            config_path=temp_config,
            state_db_url=state_db_url,
            timezone="America/New_York",
        )

        assert service.config_path == Path(temp_config)
        assert service.state_db_url == state_db_url
        assert service.timezone == "America/New_York"
        assert isinstance(service.scheduler, BackgroundScheduler)
        assert len(service.alert_configs) == 0
        assert not service.scheduler.running

    def test_init_with_default_timezone(self, temp_config, state_db_url):
        """Test SchedulerService initialization with default timezone."""
        service = SchedulerService(
            config_path=temp_config,
            state_db_url=state_db_url,
        )

        assert service.timezone == "UTC"

    def test_state_engine_property(self, scheduler_service):
        """Test state_engine property creates engine lazily."""
        assert scheduler_service._state_engine is None

        engine1 = scheduler_service.state_engine
        assert engine1 is not None

        # Second access returns same engine
        engine2 = scheduler_service.state_engine
        assert engine1 is engine2

    def test_state_engine_invalid_url(self, temp_config):
        """Test state_engine with invalid database URL."""
        service = SchedulerService(
            config_path=temp_config,
            state_db_url="invalid://url",
        )

        with pytest.raises(ConfigurationError, match="Failed to create state database engine"):
            _ = service.state_engine

    def test_start_loads_config_and_starts_scheduler(self, scheduler_service):
        """Test start() loads configuration and starts scheduler."""
        assert not scheduler_service.scheduler.running
        assert len(scheduler_service.alert_configs) == 0

        scheduler_service.start()

        assert scheduler_service.scheduler.running
        assert len(scheduler_service.alert_configs) == 3  # 3 alerts in config
        # Only 2 enabled alerts should have jobs
        assert len(scheduler_service.scheduler.get_jobs()) == 2

        scheduler_service.stop(wait=False)

    def test_start_schedules_enabled_alerts_only(self, scheduler_service):
        """Test start() only schedules enabled alerts."""
        scheduler_service.start()

        jobs = scheduler_service.scheduler.get_jobs()
        job_ids = {job.id for job in jobs}

        assert "test_alert_1" in job_ids
        assert "test_alert_2" in job_ids
        assert "test_alert_disabled" not in job_ids

        scheduler_service.stop(wait=False)

    def test_stop_shuts_down_scheduler(self, scheduler_service):
        """Test stop() shuts down scheduler gracefully."""
        scheduler_service.start()
        assert scheduler_service.scheduler.running

        scheduler_service.stop(wait=False)
        assert not scheduler_service.scheduler.running

    def test_stop_when_not_running(self, scheduler_service):
        """Test stop() when scheduler is not running."""
        assert not scheduler_service.scheduler.running

        # Should not raise an error
        scheduler_service.stop(wait=False)

    def test_stop_closes_state_engine(self, scheduler_service):
        """Test stop() closes state engine if it was created."""
        # Access state engine to create it
        _ = scheduler_service.state_engine
        assert scheduler_service._state_engine is not None

        scheduler_service.stop(wait=False)
        assert scheduler_service._state_engine is None

    def test_add_alert_job_creates_job(self, scheduler_service):
        """Test add_alert_job() creates a scheduled job."""
        from sqlsentinel.models.alert import AlertConfig

        alert = AlertConfig(
            name="new_alert",
            query="SELECT 'OK' as status",
            schedule="0 12 * * *",
            enabled=True,
        )

        scheduler_service.add_alert_job(alert)

        job = scheduler_service.scheduler.get_job("new_alert")
        assert job is not None
        assert job.id == "new_alert"
        assert job.name == "Alert: new_alert"

    def test_add_alert_job_skips_disabled_alerts(self, scheduler_service):
        """Test add_alert_job() skips disabled alerts."""
        from sqlsentinel.models.alert import AlertConfig

        alert = AlertConfig(
            name="disabled_alert",
            query="SELECT 'OK' as status",
            schedule="0 12 * * *",
            enabled=False,
        )

        scheduler_service.add_alert_job(alert)

        job = scheduler_service.scheduler.get_job("disabled_alert")
        assert job is None

    def test_add_alert_job_replaces_existing(self, scheduler_service):
        """Test add_alert_job() replaces existing job."""
        from sqlsentinel.models.alert import AlertConfig

        alert1 = AlertConfig(
            name="test_alert",
            query="SELECT 'OK' as status",
            schedule="0 9 * * *",
            enabled=True,
        )

        alert2 = AlertConfig(
            name="test_alert",
            query="SELECT 'ALERT' as status",
            schedule="0 18 * * *",  # Different schedule
            enabled=True,
        )

        scheduler_service.add_alert_job(alert1)
        scheduler_service.add_alert_job(alert2)

        # Check that only one job exists with this ID
        job = scheduler_service.scheduler.get_job("test_alert")
        assert job is not None
        assert job.id == "test_alert"

    def test_add_alert_job_prevents_concurrent_executions(self, scheduler_service):
        """Test add_alert_job() sets max_instances=1 to prevent concurrent executions."""
        from sqlsentinel.models.alert import AlertConfig

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'OK' as status",
            schedule="* * * * *",
            enabled=True,
        )

        scheduler_service.add_alert_job(alert)

        job = scheduler_service.scheduler.get_job("test_alert")
        assert job.max_instances == 1

    def test_remove_alert_job_removes_job(self, scheduler_service):
        """Test remove_alert_job() removes a scheduled job."""
        from sqlsentinel.models.alert import AlertConfig

        alert = AlertConfig(
            name="test_alert",
            query="SELECT 'OK' as status",
            schedule="0 12 * * *",
            enabled=True,
        )

        scheduler_service.add_alert_job(alert)
        assert scheduler_service.scheduler.get_job("test_alert") is not None

        scheduler_service.remove_alert_job("test_alert")
        assert scheduler_service.scheduler.get_job("test_alert") is None

    def test_remove_alert_job_nonexistent(self, scheduler_service):
        """Test remove_alert_job() with nonexistent job (should not raise error)."""
        # Should not raise an error
        scheduler_service.remove_alert_job("nonexistent_alert")

    def test_get_job_status(self, scheduler_service):
        """Test get_job_status() returns job information."""
        scheduler_service.start()

        jobs = scheduler_service.get_job_status()

        assert len(jobs) == 2  # 2 enabled alerts
        assert all("alert_name" in job for job in jobs)
        assert all("next_run" in job for job in jobs)
        assert all("trigger" in job for job in jobs)

        # Check specific job
        test_job = next(j for j in jobs if j["alert_name"] == "test_alert_1")
        assert test_job["next_run"] is not None
        assert "cron" in test_job["trigger"].lower()

        scheduler_service.stop(wait=False)

    def test_reload_config_adds_new_alerts(self, scheduler_service, temp_config):
        """Test reload_config() adds new alerts."""
        scheduler_service.start()
        initial_job_count = len(scheduler_service.scheduler.get_jobs())

        # Modify config to add new alert
        new_config = """
alerts:
  - name: "test_alert_1"
    description: "Test alert 1"
    query: "SELECT 'OK' as status"
    schedule: "0 9 * * *"
    enabled: true
    notify: []

  - name: "test_alert_2"
    description: "Test alert 2"
    query: "SELECT 'OK' as status"
    schedule: "*/15 * * * *"
    enabled: true
    notify: []

  - name: "new_alert"
    description: "New alert"
    query: "SELECT 'OK' as status"
    schedule: "0 10 * * *"
    enabled: true
    notify: []
"""
        with open(temp_config, "w") as f:
            f.write(new_config)

        scheduler_service.reload_config()

        assert len(scheduler_service.scheduler.get_jobs()) == initial_job_count + 1
        assert scheduler_service.scheduler.get_job("new_alert") is not None

        scheduler_service.stop(wait=False)

    def test_reload_config_removes_deleted_alerts(self, scheduler_service, temp_config):
        """Test reload_config() removes deleted alerts."""
        scheduler_service.start()
        assert scheduler_service.scheduler.get_job("test_alert_2") is not None

        # Modify config to remove test_alert_2
        new_config = """
alerts:
  - name: "test_alert_1"
    description: "Test alert 1"
    query: "SELECT 'OK' as status"
    schedule: "0 9 * * *"
    enabled: true
    notify: []
"""
        with open(temp_config, "w") as f:
            f.write(new_config)

        scheduler_service.reload_config()

        assert len(scheduler_service.scheduler.get_jobs()) == 1
        assert scheduler_service.scheduler.get_job("test_alert_1") is not None
        assert scheduler_service.scheduler.get_job("test_alert_2") is None

        scheduler_service.stop(wait=False)

    def test_reload_config_updates_changed_alerts(self, scheduler_service, temp_config):
        """Test reload_config() updates alerts with changed schedules."""
        scheduler_service.start()

        # Modify config to change schedule
        new_config = """
alerts:
  - name: "test_alert_1"
    description: "Test alert 1"
    query: "SELECT 'OK' as status"
    schedule: "0 18 * * *"
    enabled: true
    notify: []

  - name: "test_alert_2"
    description: "Test alert 2"
    query: "SELECT 'OK' as status"
    schedule: "*/15 * * * *"
    enabled: true
    notify: []
"""
        with open(temp_config, "w") as f:
            f.write(new_config)

        scheduler_service.reload_config()

        # Job should be updated with new schedule
        job = scheduler_service.scheduler.get_job("test_alert_1")
        assert job is not None

        scheduler_service.stop(wait=False)

    def test_reload_config_handles_disabled_alerts(self, scheduler_service, temp_config):
        """Test reload_config() removes jobs for newly disabled alerts."""
        scheduler_service.start()
        assert scheduler_service.scheduler.get_job("test_alert_1") is not None

        # Disable test_alert_1
        new_config = """
alerts:
  - name: "test_alert_1"
    description: "Test alert 1"
    query: "SELECT 'OK' as status"
    schedule: "0 9 * * *"
    enabled: false
    notify: []

  - name: "test_alert_2"
    description: "Test alert 2"
    query: "SELECT 'OK' as status"
    schedule: "*/15 * * * *"
    enabled: true
    notify: []
"""
        with open(temp_config, "w") as f:
            f.write(new_config)

        scheduler_service.reload_config()

        assert scheduler_service.scheduler.get_job("test_alert_1") is None
        assert scheduler_service.scheduler.get_job("test_alert_2") is not None

        scheduler_service.stop(wait=False)

    def test_reload_config_invalid_config_raises_error(self, scheduler_service, temp_config):
        """Test reload_config() raises error for invalid configuration."""
        scheduler_service.start()

        # Write invalid config
        with open(temp_config, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError):
            scheduler_service.reload_config()

        scheduler_service.stop(wait=False)

    @pytest.mark.parametrize(
        "schedule",
        [
            "0 9 * * *",  # Daily at 9 AM
            "*/15 * * * *",  # Every 15 minutes
            "0 0 * * 0",  # Weekly on Sunday
            "0 0 1 * *",  # Monthly on 1st
            "0 0 1 1 *",  # Yearly on Jan 1st
        ],
    )
    def test_cron_schedule_parsing(self, scheduler_service, schedule):
        """Test various cron schedule formats are parsed correctly."""
        from sqlsentinel.models.alert import AlertConfig

        alert = AlertConfig(
            name="test_schedule",
            query="SELECT 'OK' as status",
            schedule=schedule,
            enabled=True,
        )

        # Should not raise an error
        scheduler_service.add_alert_job(alert)

        job = scheduler_service.scheduler.get_job("test_schedule")
        assert job is not None

    def test_execute_alert_job_with_missing_alert(self, scheduler_service):
        """Test _execute_alert_job() handles missing alert gracefully."""
        # Should not raise an error
        scheduler_service._execute_alert_job("nonexistent_alert")

    def test_execute_alert_job_with_no_database_url(self, temp_config, state_db_url):
        """Test _execute_alert_job() handles missing database URL."""
        service = SchedulerService(
            config_path=temp_config,
            state_db_url=state_db_url,
            database_url=None,  # No database URL
        )
        service._load_alerts_from_config()

        # Should log error but not raise
        service._execute_alert_job("test_alert_1")

    @patch("sqlsentinel.scheduler.scheduler.AlertExecutor")
    @patch("sqlsentinel.scheduler.scheduler.DatabaseAdapter")
    def test_execute_alert_job_success(
        self, mock_db_adapter_class, mock_executor_class, scheduler_service
    ):
        """Test _execute_alert_job() executes alert successfully."""
        # Setup mocks
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor

        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.duration_ms = 100.5
        mock_executor.execute_alert.return_value = mock_result

        scheduler_service._load_alerts_from_config()

        # Execute job
        scheduler_service._execute_alert_job("test_alert_1")

        # Verify executor was called
        mock_executor.execute_alert.assert_called_once()
        call_kwargs = mock_executor.execute_alert.call_args[1]
        assert call_kwargs["triggered_by"] == "CRON"
        assert call_kwargs["dry_run"] is False

    @patch("sqlsentinel.scheduler.scheduler.AlertExecutor")
    def test_execute_alert_job_handles_exceptions(self, mock_executor_class, scheduler_service):
        """Test _execute_alert_job() handles exceptions gracefully."""
        # Setup mock to raise exception
        mock_executor = MagicMock()
        mock_executor_class.return_value = mock_executor
        mock_executor.execute_alert.side_effect = Exception("Test error")

        scheduler_service._load_alerts_from_config()

        # Should not raise exception - should log it instead
        scheduler_service._execute_alert_job("test_alert_1")
