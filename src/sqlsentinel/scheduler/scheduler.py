"""Scheduler service for automated alert execution."""

import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ..config.loader import ConfigLoader
from ..config.validator import ConfigValidator
from ..database.factory import AdapterFactory
from ..executor.alert_executor import AlertExecutor
from ..models.alert import AlertConfig
from ..models.errors import ConfigurationError
from ..notifications.factory import NotificationFactory

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled execution of SQL Sentinel alerts using APScheduler.

    This service wraps APScheduler to provide automated execution of alerts
    based on their cron schedules. It handles configuration loading, job
    management, and graceful shutdown.

    Responsibilities:
    - Load alert configurations from YAML
    - Create scheduled jobs from alert configs
    - Execute alerts via AlertExecutor
    - Handle configuration reloading
    - Graceful shutdown

    Example:
        >>> scheduler = SchedulerService(
        ...     config_path="/config/alerts.yaml",
        ...     state_db_url="sqlite:///state.db",
        ...     timezone="UTC"
        ... )
        >>> scheduler.start()
        >>> # Scheduler runs in background...
        >>> scheduler.stop()
    """

    def __init__(
        self,
        config_path: str | Path,
        state_db_url: str,
        database_url: str | None = None,
        timezone: str = "UTC",
        min_alert_interval_seconds: int = 0,
    ):
        """Initialize the scheduler service.

        Args:
            config_path: Path to the YAML configuration file
            state_db_url: Database URL for state and history storage
            database_url: Optional default database URL for alert queries
            timezone: Timezone for scheduling (default: UTC)
            min_alert_interval_seconds: Minimum seconds between alert notifications
        """
        self.config_path = Path(config_path)
        self.state_db_url = state_db_url
        self.database_url = database_url
        self.timezone = timezone
        self.min_alert_interval_seconds = min_alert_interval_seconds

        # Initialize APScheduler
        self.scheduler = BackgroundScheduler(timezone=timezone)

        # Initialize storage for alert configs
        self.alert_configs: dict[str, AlertConfig] = {}

        # Initialize state/history engine
        self._state_engine: Engine | None = None

        # Initialize notification factory
        self.notification_factory = NotificationFactory()

        logger.info(
            f"Initialized SchedulerService: config={config_path}, "
            f"state_db={state_db_url}, timezone={timezone}"
        )

    @property
    def state_engine(self) -> Engine:
        """Get or create the state/history database engine.

        Returns:
            SQLAlchemy engine for state database

        Raises:
            ConfigurationError: If state_db_url is invalid
        """
        if self._state_engine is None:
            try:
                self._state_engine = create_engine(self.state_db_url)
                logger.debug(f"Created state engine: {self.state_db_url}")
            except Exception as e:
                raise ConfigurationError(f"Failed to create state database engine: {e}") from e
        return self._state_engine

    def start(self) -> None:
        """Load configuration and start scheduler.

        This method:
        1. Loads and validates configuration
        2. Creates jobs for all enabled alerts
        3. Starts the APScheduler background scheduler

        Raises:
            ConfigurationError: If configuration is invalid
        """
        logger.info("Starting scheduler service...")

        # Load and validate configuration
        self._load_alerts_from_config()

        # Start the scheduler
        self.scheduler.start()

        # Log scheduler status
        job_count = len(self.scheduler.get_jobs())
        logger.info(f"Scheduler started with {job_count} jobs")

    def stop(self, wait: bool = True) -> None:
        """Gracefully shutdown scheduler.

        Args:
            wait: If True, wait for all currently executing jobs to finish
        """
        logger.info("Stopping scheduler service...")

        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scheduler stopped")
        else:
            logger.warning("Scheduler was not running")

        # Close state engine if it was created
        if self._state_engine is not None:
            self._state_engine.dispose()
            self._state_engine = None
            logger.debug("Closed state engine")

    def reload_config(self) -> None:
        """Reload configuration and update jobs.

        This method:
        1. Loads the latest configuration from disk
        2. Removes jobs for alerts that no longer exist or are disabled
        3. Updates jobs for alerts that have changed
        4. Adds jobs for new alerts

        Raises:
            ConfigurationError: If the new configuration is invalid
        """
        logger.info("Reloading configuration...")

        # Load new configuration
        try:
            old_alert_names = set(self.alert_configs.keys())
            self._load_alerts_from_config()
            new_alert_names = set(self.alert_configs.keys())
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            raise

        # Determine which alerts were added, removed, or updated
        removed_alerts = old_alert_names - new_alert_names
        added_alerts = new_alert_names - old_alert_names
        potential_updates = old_alert_names & new_alert_names

        # Remove jobs for removed alerts
        for alert_name in removed_alerts:
            self.remove_alert_job(alert_name)
            logger.info(f"Removed job for deleted alert: {alert_name}")

        # Add jobs for new alerts
        for alert_name in added_alerts:
            alert = self.alert_configs[alert_name]
            if alert.enabled:
                self.add_alert_job(alert)
                logger.info(f"Added job for new alert: {alert_name}")

        # Update jobs for potentially changed alerts
        # (Always recreate to ensure schedule changes are applied)
        for alert_name in potential_updates:
            alert = self.alert_configs[alert_name]
            self.remove_alert_job(alert_name)
            if alert.enabled:
                self.add_alert_job(alert)
                logger.debug(f"Updated job for alert: {alert_name}")
            else:
                logger.info(f"Disabled alert: {alert_name}")

        job_count = len(self.scheduler.get_jobs())
        logger.info(f"Configuration reloaded. Active jobs: {job_count}")

    def add_alert_job(self, alert: AlertConfig) -> None:
        """Add or update a scheduled job for an alert.

        Args:
            alert: Alert configuration to schedule

        Raises:
            ValueError: If alert schedule is invalid
        """
        if not alert.enabled:
            logger.debug(f"Skipping disabled alert: {alert.name}")
            return

        try:
            # Create cron trigger from alert schedule
            trigger = CronTrigger.from_crontab(alert.schedule, timezone=self.timezone)

            # Add job to scheduler
            self.scheduler.add_job(
                func=self._execute_alert_job,
                trigger=trigger,
                id=alert.name,
                name=f"Alert: {alert.name}",
                args=[alert.name],
                replace_existing=True,
                max_instances=1,  # Prevent concurrent executions of same alert
            )

            logger.info(f"Scheduled job for alert '{alert.name}' with schedule: {alert.schedule}")
        except Exception as e:
            logger.error(f"Failed to add job for alert '{alert.name}': {e}")
            raise ValueError(f"Failed to schedule alert '{alert.name}': {e}") from e

    def remove_alert_job(self, alert_name: str) -> None:
        """Remove a scheduled job.

        Args:
            alert_name: Name of the alert whose job should be removed
        """
        try:
            self.scheduler.remove_job(alert_name)
            logger.debug(f"Removed job for alert: {alert_name}")
        except Exception:
            # Job doesn't exist - this is fine
            pass

    def get_job_status(self) -> list[dict[str, str]]:
        """Get status of all scheduled jobs.

        Returns:
            List of dictionaries with job information
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time.isoformat() if job.next_run_time else None
            jobs.append(
                {
                    "alert_name": job.id,
                    "next_run": next_run,
                    "trigger": str(job.trigger),
                }
            )
        return jobs

    def _load_alerts_from_config(self) -> None:
        """Load and validate alerts from configuration file.

        This method loads the YAML configuration, validates it, and stores
        the alert configs. It also schedules jobs for enabled alerts.

        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        logger.debug(f"Loading configuration from: {self.config_path}")

        # Load raw configuration
        loader = ConfigLoader(self.config_path)
        raw_config = loader.load()

        # Validate and parse alerts
        validator = ConfigValidator()
        alerts = validator.validate(raw_config)

        # Store alerts in dictionary for quick lookup
        self.alert_configs = {alert.name: alert for alert in alerts}

        logger.info(f"Loaded {len(alerts)} alerts from configuration")

        # Schedule jobs for enabled alerts (only when first starting)
        # Reload calls add_alert_job separately
        if not self.scheduler.running:
            for alert in alerts:
                if alert.enabled:
                    self.add_alert_job(alert)

    def _execute_alert_job(self, alert_name: str) -> None:
        """Execute an alert job (called by APScheduler).

        This is the callback function that APScheduler calls when a job
        is triggered. It:
        1. Retrieves the alert configuration
        2. Creates a database adapter
        3. Executes the alert via AlertExecutor
        4. Handles and logs any errors

        Args:
            alert_name: Name of the alert to execute
        """
        logger.info(f"Executing scheduled alert: {alert_name}")

        try:
            # Get alert configuration
            alert = self.alert_configs.get(alert_name)
            if alert is None:
                logger.error(f"Alert not found in configuration: {alert_name}")
                return

            # Create database adapter
            # Use alert's database URL if specified, otherwise use default
            db_url = self.database_url
            if db_url is None:
                logger.error(
                    f"No database URL configured for alert '{alert_name}'. "
                    "Set DATABASE_URL environment variable or pass database_url to scheduler."
                )
                return

            db_adapter = AdapterFactory.create_adapter(db_url)

            # Create alert executor
            executor = AlertExecutor(
                engine=self.state_engine,
                notification_factory=self.notification_factory,
                min_alert_interval_seconds=self.min_alert_interval_seconds,
            )

            # Execute alert
            result = executor.execute_alert(
                alert=alert,
                db_adapter=db_adapter,
                triggered_by="CRON",
                dry_run=False,
            )

            logger.info(
                f"Alert '{alert_name}' executed successfully: "
                f"status={result.status}, duration={result.duration_ms:.2f}ms"
            )

        except Exception as e:
            logger.error(f"Error executing alert '{alert_name}': {e}", exc_info=True)
            # Don't re-raise - we don't want to crash the scheduler
