"""Command-line interface for SQL Sentinel."""

import argparse
import sys

from pydantic import BaseModel
from sqlalchemy import create_engine

from .config.loader import ConfigLoader
from .config.validator import ConfigValidator
from .database.adapter import DatabaseAdapter
from .database.schema import SchemaManager
from .executor.alert_executor import AlertExecutor
from .models.alert import AlertConfig
from .notifications.factory import NotificationFactory


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

        # Create database adapter for alert query
        db_adapter = DatabaseAdapter(config.database.url)
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

        # Create database adapter
        db_adapter = DatabaseAdapter(config.database.url)
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

        # Calculate silence end time
        silence_until = datetime.utcnow() + timedelta(hours=duration_hours)

        # Silence the alert
        state_manager.silence_alert(alert_name, silence_until)

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

        print(f"\nAlert Status Report")
        print(f"{'='*80}")
        print(f"{'Alert Name':<30} {'Status':<15} {'Silenced':<10} {'Last Check':<20}")
        print(f"{'-'*80}")

        for alert in alerts_to_show:
            state = state_manager.get_alert_state(alert.name)

            if state:
                status = state.current_status or "Unknown"
                last_check = (
                    state.last_checked.strftime("%Y-%m-%d %H:%M:%S")
                    if state.last_checked
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


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SQL Sentinel - SQL-first alerting system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

    return 0


if __name__ == "__main__":
    sys.exit(main())
