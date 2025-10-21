"""Configuration file watcher for automatic reloading."""

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from .scheduler import SchedulerService

logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """Handler for configuration file changes."""

    def __init__(
        self,
        config_path: Path,
        scheduler: "SchedulerService",
        debounce_seconds: float,
    ):
        """Initialize the config file handler.

        Args:
            config_path: Path to the configuration file to watch
            scheduler: SchedulerService instance to reload
            debounce_seconds: Minimum seconds between reload attempts
        """
        self.config_path = config_path
        self.scheduler = scheduler
        self.debounce_seconds = debounce_seconds
        self.last_reload_time = 0.0

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        # Check if the modified file is our config file
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")
        if Path(src_path).resolve() == self.config_path.resolve():
            self._trigger_reload()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        # Check if the created file is our config file
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")
        if Path(src_path).resolve() == self.config_path.resolve():
            self._trigger_reload()

    def _trigger_reload(self) -> None:
        """Trigger a configuration reload with debouncing."""
        current_time = time.time()
        time_since_last_reload = current_time - self.last_reload_time

        # Debounce: ignore if last reload was too recent
        if time_since_last_reload < self.debounce_seconds:
            logger.debug(
                f"Ignoring config change (debounced): "
                f"{time_since_last_reload:.2f}s since last reload"
            )
            return

        logger.info("Configuration file changed, reloading...")
        self.last_reload_time = current_time

        try:
            self.scheduler.reload_config()
            logger.info("Configuration reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            # Don't crash - just log the error


class ConfigWatcher:
    """Watches configuration file for changes and triggers reloads."""

    def __init__(
        self,
        config_path: str | Path,
        scheduler: "SchedulerService",
        debounce_seconds: float = 2.0,
    ):
        """Initialize the config watcher.

        Args:
            config_path: Path to the configuration file to watch
            scheduler: SchedulerService instance to reload when config changes
            debounce_seconds: Minimum seconds between reload attempts (default: 2.0)
        """
        self.config_path = Path(config_path).resolve()
        self.scheduler = scheduler
        self.debounce_seconds = debounce_seconds

        # Validate config file exists
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        # Create file system observer
        self.observer = Observer()
        self.event_handler = ConfigFileHandler(
            config_path=self.config_path,
            scheduler=scheduler,
            debounce_seconds=debounce_seconds,
        )

        # Watch the directory containing the config file
        self.watch_directory = self.config_path.parent
        logger.debug(f"Will watch directory: {self.watch_directory}")

    def start(self) -> None:
        """Start watching the configuration file."""
        logger.info(f"Starting config file watcher for: {self.config_path}")

        # Schedule the observer to watch the directory
        self.observer.schedule(
            self.event_handler,
            str(self.watch_directory),
            recursive=False,
        )

        # Start the observer thread
        self.observer.start()
        logger.debug("Config file watcher started")

    def stop(self) -> None:
        """Stop watching the configuration file."""
        logger.debug("Stopping config file watcher...")

        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5.0)

            if self.observer.is_alive():
                logger.warning("Config file watcher did not stop cleanly")
            else:
                logger.debug("Config file watcher stopped")
        else:
            logger.debug("Config file watcher was not running")

    def is_alive(self) -> bool:
        """Check if the watcher is running.

        Returns:
            True if the watcher thread is alive
        """
        return self.observer.is_alive()
