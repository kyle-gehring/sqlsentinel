"""Command-line interface for SQL Sentinel."""

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import create_engine

from .config.loader import ConfigLoader
from .config.validator import ConfigValidator
from .logging import configure_logging, configure_from_env
from .metrics import get_metrics
from .database.factory import AdapterFactory
from .database.schema import SchemaManager
from .executor.alert_executor import AlertExecutor
from .health.checks import (
    aggregate_health_status,
    check_database,
    check_notifications,
    check_scheduler,
)
from .models.alert import AlertConfig
from .notifications.factory import NotificationFactory
from .scheduler.config_watcher import ConfigWatcher
from .scheduler.scheduler import SchedulerService


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str


class AppConfig(BaseModel):
    """Application configuration."""

    database: DatabaseConfig
    alerts: list[AlertConfig]


def load_config(config_file: str) -> AppConfig:
    """Load and validate configuration file.

    Args:
        config_file: Path to YAML configuration file

    Returns:
        Validated AppConfig object
    """
    loader = ConfigLoader(config_file)
    raw_config = loader.load()

    validator = ConfigValidator()
    alerts = validator.validate(raw_config)

    database_config = DatabaseConfig(**raw_config["database"])

    return AppConfig(database=database_config, alerts=alerts)


def init_database(state_db_url: str) -> None:
    """Initialize SQL Sentinel database schema.

    Args:
        state_db_url: Connection string for state/history database
    """
    print(f"Initializing SQL Sentinel schema at: {state_db_url}")
    engine = create_engine(state_db_url)
    schema_manager = SchemaManager(engine)
    schema_manager.initialize_schema()
    print("✓ Schema initialized successfully")


def run_alert(
    config_file: str,
    alert_name: str,
    state_db_url: str,
    dry_run: bool = False,
) -> int:
    """Run a single alert manually.

    Args:
        config_file: Path to YAML configuration file
        alert_name: Name of alert to execute
        state_db_url: Connection string for state/history database
        dry_run: If True, don't send notifications or update state

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Load configuration
        print(f"Loading configuration from: {config_file}")
        config = load_config(config_file)

        # Find the alert
        alert = None
        for a in config.alerts:
            if a.name == alert_name:
                alert = a
                break

        if not alert:
            print(f"✗ Alert '{alert_name}' not found in configuration")
            available = [a.name for a in config.alerts]
            print(f"Available alerts: {', '.join(available)}")
            return 1

        print(f"Found alert: {alert.name}")
        if alert.description:
            print(f"Description: {alert.description}")

        # Initialize components
        engine = create_engine(state_db_url)
        notification_factory = NotificationFactory()
        executor = AlertExecutor(engine, notification_factory)

        # Create database adapter for alert query (auto-detects BigQuery vs SQLAlchemy)
        db_adapter = AdapterFactory.create_adapter(config.database.url)
        db_adapter.connect()

        # Execute alert
        if dry_run:
            print("\n[DRY RUN MODE - No notifications will be sent, state won't be updated]")

        print(f"\nExecuting alert: {alert.name}...")
        result = executor.execute_alert(
            alert=alert,
            db_adapter=db_adapter,
            triggered_by="MANUAL",
            dry_run=dry_run,
        )

        # Display results
        print(f"\n{'='*60}")
        print("Alert Execution Result")
        print(f"{'='*60}")
        print(f"Alert Name: {result.alert_name}")
        print(f"Status: {result.status}")
        print(f"Duration: {result.duration_ms:.2f}ms")

        if result.query_result:
            print(f"Query Status: {result.query_result.status}")
            if result.query_result.actual_value is not None:
                print(f"Actual Value: {result.query_result.actual_value}")
            if result.query_result.threshold is not None:
                print(f"Threshold: {result.query_result.threshold}")
            if result.query_result.context:
                print(f"Context: {result.query_result.context}")

        if result.error:
            print(f"Error: {result.error}")

        print(f"{'='*60}\n")

        # Cleanup
        db_adapter.disconnect()

        # Return appropriate exit code
        if result.status == "error":
            return 1
        return 0

    except Exception as e:
        print(f"✗ Error executing alert: {e}")
        return 1


def run_all_alerts(
    config_file: str,
    state_db_url: str,
    dry_run: bool = False,
) -> int:
    """Run all alerts in configuration file.

    Args:
        config_file: Path to YAML configuration file
        state_db_url: Connection string for state/history database
        dry_run: If True, don't send notifications or update state

    Returns:
        Exit code (0 for success, 1 if any alerts failed)
    """
    try:
        # Load configuration
        print(f"Loading configuration from: {config_file}")
        config = load_config(config_file)

        print(f"Found {len(config.alerts)} alert(s)")

        # Initialize components
        engine = create_engine(state_db_url)
        notification_factory = NotificationFactory()
        executor = AlertExecutor(engine, notification_factory)

        # Create database adapter (auto-detects BigQuery vs SQLAlchemy)
        db_adapter = AdapterFactory.create_adapter(config.database.url)
        db_adapter.connect()

        if dry_run:
            print("\n[DRY RUN MODE - No notifications will be sent, state won't be updated]\n")

        # Execute all enabled alerts
        results = []
        for alert in config.alerts:
            if not alert.enabled:
                print(f"⊘ Skipping disabled alert: {alert.name}")
                continue

            print(f"\nExecuting: {alert.name}...")
            result = executor.execute_alert(
                alert=alert,
                db_adapter=db_adapter,
                triggered_by="MANUAL",
                dry_run=dry_run,
            )

            status_symbol = "✓" if result.status == "success" else "✗"
            print(f"{status_symbol} {alert.name}: {result.status} ({result.duration_ms:.2f}ms)")

            if result.query_result:
                print(f"  Query Status: {result.query_result.status}")

            results.append(result)

        # Cleanup
        db_adapter.disconnect()

        # Summary
        print(f"\n{'='*60}")
        print("Execution Summary")
        print(f"{'='*60}")
        total = len(results)
        successful = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status in ["failure", "error"])
        print(f"Total: {total} | Success: {successful} | Failed: {failed}")
        print(f"{'='*60}\n")

        return 1 if failed > 0 else 0

    except Exception as e:
        print(f"✗ Error running alerts: {e}")
        import traceback

        traceback.print_exc()
        return 1


def validate_config(config_file: str) -> int:
    """Validate configuration file.

    Args:
        config_file: Path to YAML configuration file

    Returns:
        Exit code (0 for valid, 1 for invalid)
    """
    try:
        print(f"Validating configuration: {config_file}")
        config = load_config(config_file)

        print("✓ Configuration is valid")
        print(f"  Database: {config.database.url}")
        print(f"  Alerts: {len(config.alerts)}")

        for alert in config.alerts:
            enabled_status = "enabled" if alert.enabled else "disabled"
            print(f"    - {alert.name} ({enabled_status})")

        return 0

    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")
        return 1


def show_history(
    config_file: str,
    state_db_url: str,
    alert_name: str = None,
    limit: int = 10,
) -> int:
    """Show execution history for alerts.

    Args:
        config_file: Path to YAML configuration file
        state_db_url: Connection string for state/history database
        alert_name: Optional alert name to filter by
        limit: Maximum number of records to show

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        from .executor.history import ExecutionHistory

        engine = create_engine(state_db_url)
        history = ExecutionHistory(engine)

        print(f"Execution History (last {limit} records)")
        if alert_name:
            print(f"Alert: {alert_name}")
        print(f"{'='*80}")

        records = history.get_executions(alert_name=alert_name, limit=limit)

        if not records:
            print("No execution history found")
            return 0

        for record in records:
            print(f"\n{record.executed_at} | {record.alert_name}")
            print(f"  Status: {record.status} | Duration: {record.execution_duration_ms:.2f}ms")
            print(f"  Triggered by: {record.triggered_by}")
            if record.actual_value is not None:
                print(f"  Actual: {record.actual_value} | Threshold: {record.threshold}")
            if record.error_message:
                print(f"  Error: {record.error_message}")
            if record.notification_sent:
                print("  ✓ Notification sent")

        print(f"\n{'='*80}\n")
        return 0

    except Exception as e:
        print(f"✗ Error retrieving history: {e}")
        return 1


def silence_alert(
    config_file: str,
    state_db_url: str,
    alert_name: str,
    duration_hours: int = 1,
) -> int:
    """Silence an alert for a specified duration.

    Args:
        config_file: Path to YAML configuration file
        state_db_url: Connection string for state/history database
        alert_name: Name of alert to silence
        duration_hours: Hours to silence alert (default: 1)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        from datetime import datetime, timedelta

        from .executor.state import StateManager

        # Load config to verify alert exists
        print(f"Loading configuration from: {config_file}")
        config = load_config(config_file)

        # Find the alert
        alert_found = False
        for alert in config.alerts:
            if alert.name == alert_name:
                alert_found = True
                break

        if not alert_found:
            print(f"✗ Alert '{alert_name}' not found in configuration")
            available = [a.name for a in config.alerts]
            print(f"Available alerts: {', '.join(available)}")
            return 1

        # Initialize state manager
        engine = create_engine(state_db_url)
        state_manager = StateManager(engine)

        # Convert hours to seconds
        duration_seconds = duration_hours * 3600

        # Silence the alert
        state_manager.silence_alert(alert_name, duration_seconds)

        # Calculate silence end time for display
        silence_until = datetime.utcnow() + timedelta(hours=duration_hours)

        print(f"✓ Alert '{alert_name}' silenced until {silence_until.isoformat()}")
        print(f"  Duration: {duration_hours} hour(s)")
        return 0

    except Exception as e:
        print(f"✗ Error silencing alert: {e}")
        return 1


def unsilence_alert(
    config_file: str,
    state_db_url: str,
    alert_name: str,
) -> int:
    """Clear silence on an alert.

    Args:
        config_file: Path to YAML configuration file
        state_db_url: Connection string for state/history database
        alert_name: Name of alert to unsilence

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        from .executor.state import StateManager

        # Load config to verify alert exists
        print(f"Loading configuration from: {config_file}")
        config = load_config(config_file)

        # Find the alert
        alert_found = False
        for alert in config.alerts:
            if alert.name == alert_name:
                alert_found = True
                break

        if not alert_found:
            print(f"✗ Alert '{alert_name}' not found in configuration")
            available = [a.name for a in config.alerts]
            print(f"Available alerts: {', '.join(available)}")
            return 1

        # Initialize state manager
        engine = create_engine(state_db_url)
        state_manager = StateManager(engine)

        # Unsilence the alert
        state_manager.unsilence_alert(alert_name)

        print(f"✓ Alert '{alert_name}' unsilenced successfully")
        return 0

    except Exception as e:
        print(f"✗ Error unsilencing alert: {e}")
        return 1


def show_status(
    config_file: str,
    state_db_url: str,
    alert_name: str = None,
) -> int:
    """Show current status of alerts.

    Args:
        config_file: Path to YAML configuration file
        state_db_url: Connection string for state/history database
        alert_name: Optional alert name to filter by

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        from datetime import datetime

        from .executor.state import StateManager

        # Load config
        print(f"Loading configuration from: {config_file}")
        config = load_config(config_file)

        # Filter alerts if specific name provided
        alerts_to_show = config.alerts
        if alert_name:
            alerts_to_show = [a for a in config.alerts if a.name == alert_name]
            if not alerts_to_show:
                print(f"✗ Alert '{alert_name}' not found in configuration")
                return 1

        # Initialize state manager
        engine = create_engine(state_db_url)
        state_manager = StateManager(engine)

        print("\nAlert Status Report")
        print("=" * 80)
        print(f"{'Alert Name':<30} {'Status':<15} {'Silenced':<10} {'Last Check':<20}")
        print("-" * 80)

        for alert in alerts_to_show:
            state = state_manager.get_state(alert.name)

            if state and state.last_executed_at:
                status = state.current_status or "Unknown"
                last_check = (
                    state.last_executed_at.strftime("%Y-%m-%d %H:%M:%S")
                    if state.last_executed_at
                    else "Never"
                )

                # Check if silenced
                is_silenced = False
                silence_info = ""
                if state.silenced_until:
                    if state.silenced_until > datetime.utcnow():
                        is_silenced = True
                        silence_info = f" (until {state.silenced_until.strftime('%Y-%m-%d %H:%M')})"

                silenced_str = ("Yes" + silence_info) if is_silenced else "No"
            else:
                status = "Never Run"
                last_check = "Never"
                silenced_str = "No"

            print(f"{alert.name:<30} {status:<15} {silenced_str:<10} {last_check:<20}")

        print(f"{'='*80}\n")
        return 0

    except Exception as e:
        print(f"✗ Error showing status: {e}")
        import traceback

        traceback.print_exc()
        return 1


def show_metrics(output_format: str = "text") -> int:
    """Display collected metrics.

    Args:
        output_format: Output format ('text' or 'json')

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        metrics = get_metrics()

        if output_format == "json":
            # Return Prometheus format as text (which is line-based)
            metrics_text = metrics.get_metrics_text()
            print(metrics_text)
        else:
            # Text format - pretty print metrics
            print("\n" + "=" * 60)
            print("SQL Sentinel Metrics")
            print("=" * 60)
            print("\nPrometheus Format Output:")
            print("-" * 60)
            metrics_text = metrics.get_metrics_text()
            # Print only non-comment lines for readability
            for line in metrics_text.split("\n"):
                if line and not line.startswith("#"):
                    print(line)
            print("=" * 60 + "\n")

        return 0

    except Exception as e:
        print(f"✗ Failed to retrieve metrics: {e}")
        return 1


def healthcheck(
    config_file: str,
    state_db_url: str,
    database_url: str | None = None,
    output_format: str = "text",
) -> int:
    """Check health of SQL Sentinel and dependencies.

    Args:
        config_file: Path to YAML configuration file
        state_db_url: Connection string for state/history database
        database_url: Connection string for alert queries database (optional)
        output_format: Output format ('text' or 'json')

    Returns:
        Exit code (0 for healthy, 1 for unhealthy)
    """
    try:
        # Get database URL from environment if not provided
        if database_url is None:
            database_url = os.environ.get("DATABASE_URL")

        # Load configuration
        config = load_config(config_file)

        # Initialize components for checking
        state_engine = create_engine(state_db_url)
        notification_factory = NotificationFactory()

        # Perform health checks
        checks: dict[str, object] = {}

        # Check state database
        checks["state_database"] = check_database(state_engine)

        # Check alert database if provided
        if database_url:
            try:
                alert_engine = create_engine(database_url)
                checks["alert_database"] = check_database(alert_engine)
            except Exception as e:
                checks["alert_database"] = {
                    "status": "unhealthy",
                    "message": f"Failed to connect: {str(e)}",
                }
        else:
            checks["alert_database"] = {
                "status": "not_configured",
                "message": "DATABASE_URL not set",
            }

        # Check notifications
        checks["notifications"] = check_notifications(notification_factory)

        # Aggregate status
        overall_status = aggregate_health_status(checks)

        # Output results
        if output_format == "json":
            output = {
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "checks": checks,
            }
            print(json.dumps(output, indent=2, default=str))
        else:
            # Text format
            print("\n" + "=" * 60)
            print("SQL Sentinel Health Check")
            print("=" * 60)

            for check_name, check_result in checks.items():
                check_result_dict = check_result if isinstance(check_result, dict) else {}
                status = check_result_dict.get("status", "unknown")
                status_symbol = (
                    "✓"
                    if status == "healthy"
                    else "⚠" if status == "degraded" else "⊘" if status == "not_configured" else "✗"
                )
                print(f"\n{status_symbol} {check_name.replace('_', ' ').title()}")
                print(f"  Status: {status}")

                if "latency_ms" in check_result_dict and check_result_dict["latency_ms"]:
                    print(f"  Latency: {check_result_dict['latency_ms']}ms")

                if "jobs_count" in check_result_dict:
                    print(f"  Jobs: {check_result_dict['jobs_count']}")

                if "message" in check_result_dict:
                    print(f"  Message: {check_result_dict['message']}")

                if "channels" in check_result_dict:
                    print("  Channels:")
                    for channel_name, channel_status in check_result_dict["channels"].items():
                        chan_status = channel_status.get("status", "unknown") if isinstance(
                            channel_status, dict
                        ) else "unknown"
                        chan_symbol = "✓" if chan_status == "healthy" else "⊘"
                        print(f"    {chan_symbol} {channel_name}: {chan_status}")

            print(f"\n{'='*60}")
            print(f"Overall Status: {overall_status.upper()}")
            print(f"{'='*60}\n")

        # Return appropriate exit code
        if overall_status == "unhealthy":
            return 1
        elif overall_status == "degraded":
            return 0  # Degraded but not completely unhealthy
        return 0

    except Exception as e:
        print(f"✗ Healthcheck failed: {e}")
        if output_format == "json":
            output = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            print(json.dumps(output, indent=2))
        return 1


def run_daemon(
    config_file: str,
    state_db_url: str,
    database_url: str | None = None,
    reload_config: bool = False,
    log_level: str = "INFO",
    timezone: str = "UTC",
    port: int | None = None,
) -> int:
    """Run SQL Sentinel as a daemon with scheduled alert execution.

    Args:
        config_file: Path to YAML configuration file
        state_db_url: Connection string for state/history database
        database_url: Connection string for alert queries database
        reload_config: If True, watch config file for changes and reload
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        timezone: Timezone for scheduling (default: UTC)
        port: HTTP port for health/metrics endpoints (default: $PORT or 8080)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Configure logging
    configure_logging(log_level=log_level, log_format="json")
    logger = logging.getLogger(__name__)

    # Get database URL from environment if not provided
    if database_url is None:
        database_url = os.environ.get("DATABASE_URL")
        if database_url is None:
            print(
                "✗ No database URL provided. Set DATABASE_URL environment variable "
                "or pass --database-url"
            )
            return 1

    logger.info("Starting SQL Sentinel daemon...")
    logger.info(f"Configuration file: {config_file}")
    logger.info(f"State database: {state_db_url}")
    logger.info(f"Alert database: {database_url}")
    logger.info(f"Timezone: {timezone}")
    logger.info(f"Config reload: {'enabled' if reload_config else 'disabled'}")

    # Create scheduler service
    try:
        scheduler = SchedulerService(
            config_path=config_file,
            state_db_url=state_db_url,
            database_url=database_url,
            timezone=timezone,
        )
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}")
        return 1

    # Setup signal handlers for graceful shutdown
    shutdown_requested = {"value": False}

    def signal_handler(signum: int, frame: object) -> None:
        """Handle shutdown signals."""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name} signal, initiating graceful shutdown...")
        shutdown_requested["value"] = True

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Setup config file watcher if requested
    watcher = None
    if reload_config:
        try:
            watcher = ConfigWatcher(
                config_path=config_file,
                scheduler=scheduler,
                debounce_seconds=2.0,
            )
            watcher.start()
            logger.info("Configuration file watcher started")
        except Exception as e:
            logger.error(f"Failed to start config watcher: {e}")
            # Continue without watcher

    # Start scheduler
    try:
        scheduler.start()
        logger.info("Scheduler started successfully")

        # Log scheduled jobs
        jobs = scheduler.get_job_status()
        logger.info(f"Scheduled {len(jobs)} jobs:")
        for job in jobs:
            logger.info(f"  - {job['alert_name']}: next run at {job['next_run']}")

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        if watcher:
            watcher.stop()
        return 1

    # Start HTTP health/metrics server
    http_port = port if port is not None else int(os.environ.get("PORT", "8080"))
    http_server = None
    try:
        from .server import start_health_server

        http_server = start_health_server(
            port=http_port,
            scheduler_service=scheduler,
            state_engine=create_engine(state_db_url),
        )
    except Exception as e:
        logger.warning(f"Failed to start health server on port {http_port}: {e}")
        # Continue without HTTP server — daemon still works for local use

    # Main loop - wait for shutdown signal
    logger.info("SQL Sentinel daemon running. Press Ctrl+C to stop.")
    try:
        while not shutdown_requested["value"]:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")

    # Graceful shutdown
    if http_server:
        logger.info("Stopping health server...")
        http_server.shutdown()

    logger.info("Shutting down scheduler...")
    scheduler.stop(wait=True)

    if watcher:
        logger.info("Stopping config watcher...")
        watcher.stop()

    logger.info("SQL Sentinel daemon stopped")
    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SQL Sentinel - SQL-first alerting system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    from . import __version__

    parser.add_argument(
        "--version",
        action="version",
        version=f"sqlsentinel {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize SQL Sentinel database schema")
    init_parser.add_argument(
        "--state-db",
        default="sqlite:///sqlsentinel.db",
        help="State database URL (default: sqlite:///sqlsentinel.db)",
    )

    # Run command
    run_parser = subparsers.add_parser("run", help="Run alerts")
    run_parser.add_argument("config", help="Path to configuration file")
    run_parser.add_argument(
        "--alert",
        help="Run specific alert by name (omit to run all alerts)",
    )
    run_parser.add_argument(
        "--state-db",
        default="sqlite:///sqlsentinel.db",
        help="State database URL (default: sqlite:///sqlsentinel.db)",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't send notifications or update state",
    )

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration file")
    validate_parser.add_argument("config", help="Path to configuration file")

    # History command
    history_parser = subparsers.add_parser("history", help="Show execution history")
    history_parser.add_argument("config", help="Path to configuration file")
    history_parser.add_argument(
        "--alert",
        help="Filter by alert name",
    )
    history_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of records to show (default: 10)",
    )
    history_parser.add_argument(
        "--state-db",
        default="sqlite:///sqlsentinel.db",
        help="State database URL (default: sqlite:///sqlsentinel.db)",
    )

    # Silence command
    silence_parser = subparsers.add_parser("silence", help="Silence an alert")
    silence_parser.add_argument("config", help="Path to configuration file")
    silence_parser.add_argument("--alert", required=True, help="Alert name to silence")
    silence_parser.add_argument(
        "--duration",
        type=int,
        default=1,
        help="Hours to silence alert (default: 1)",
    )
    silence_parser.add_argument(
        "--state-db",
        default="sqlite:///sqlsentinel.db",
        help="State database URL (default: sqlite:///sqlsentinel.db)",
    )

    # Unsilence command
    unsilence_parser = subparsers.add_parser("unsilence", help="Unsilence an alert")
    unsilence_parser.add_argument("config", help="Path to configuration file")
    unsilence_parser.add_argument("--alert", required=True, help="Alert name to unsilence")
    unsilence_parser.add_argument(
        "--state-db",
        default="sqlite:///sqlsentinel.db",
        help="State database URL (default: sqlite:///sqlsentinel.db)",
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show alert status")
    status_parser.add_argument("config", help="Path to configuration file")
    status_parser.add_argument(
        "--alert",
        help="Filter by alert name",
    )
    status_parser.add_argument(
        "--state-db",
        default="sqlite:///sqlsentinel.db",
        help="State database URL (default: sqlite:///sqlsentinel.db)",
    )

    # Healthcheck command
    healthcheck_parser = subparsers.add_parser("healthcheck", help="Check system health")
    healthcheck_parser.add_argument("config", help="Path to configuration file")
    healthcheck_parser.add_argument(
        "--state-db",
        default="sqlite:///sqlsentinel.db",
        help="State database URL (default: sqlite:///sqlsentinel.db)",
    )
    healthcheck_parser.add_argument(
        "--database-url",
        help="Database URL for alert queries (default: from DATABASE_URL env var)",
    )
    healthcheck_parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Show collected metrics")
    metrics_parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Run SQL Sentinel as a background daemon")
    daemon_parser.add_argument("config", help="Path to configuration file")
    daemon_parser.add_argument(
        "--state-db",
        default="sqlite:///sqlsentinel.db",
        help="State database URL (default: sqlite:///sqlsentinel.db)",
    )
    daemon_parser.add_argument(
        "--database-url",
        help="Database URL for alert queries (default: from DATABASE_URL env var)",
    )
    daemon_parser.add_argument(
        "--reload",
        action="store_true",
        help="Watch config file for changes and reload automatically",
    )
    daemon_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    daemon_parser.add_argument(
        "--timezone",
        default="UTC",
        help="Timezone for scheduling (default: UTC)",
    )
    daemon_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP port for health/metrics endpoints (default: $PORT or 8080)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "init":
        return init_database(args.state_db)
    elif args.command == "run":
        if args.alert:
            return run_alert(args.config, args.alert, args.state_db, args.dry_run)
        else:
            return run_all_alerts(args.config, args.state_db, args.dry_run)
    elif args.command == "validate":
        return validate_config(args.config)
    elif args.command == "history":
        return show_history(args.config, args.state_db, args.alert, args.limit)
    elif args.command == "silence":
        return silence_alert(args.config, args.state_db, args.alert, args.duration)
    elif args.command == "unsilence":
        return unsilence_alert(args.config, args.state_db, args.alert)
    elif args.command == "status":
        return show_status(args.config, args.state_db, args.alert)
    elif args.command == "healthcheck":
        return healthcheck(
            config_file=args.config,
            state_db_url=args.state_db,
            database_url=args.database_url,
            output_format=args.output,
        )
    elif args.command == "metrics":
        return show_metrics(output_format=args.output)
    elif args.command == "daemon":
        return run_daemon(
            config_file=args.config,
            state_db_url=args.state_db,
            database_url=args.database_url,
            reload_config=args.reload,
            log_level=args.log_level,
            timezone=args.timezone,
            port=args.port,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
