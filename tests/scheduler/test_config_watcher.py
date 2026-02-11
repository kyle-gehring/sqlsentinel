"""Tests for configuration file watcher."""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlsentinel.scheduler.config_watcher import ConfigFileHandler, ConfigWatcher


class TestConfigFileHandler:
    """Test ConfigFileHandler class."""

    def setup_method(self):
        """Set up test method."""
        self.config_path = Path("/tmp/test_config.yaml")
        self.scheduler = Mock()
        self.handler = ConfigFileHandler(
            config_path=self.config_path,
            scheduler=self.scheduler,
            debounce_seconds=1.0,
        )

    def test_initialization(self):
        """Test handler initialization."""
        assert self.handler.config_path == self.config_path
        assert self.handler.scheduler is self.scheduler
        assert self.handler.debounce_seconds == 1.0
        assert self.handler.last_reload_time == 0.0

    def test_on_modified_ignores_directory(self):
        """Test that on_modified ignores directory events."""
        event = Mock()
        event.is_directory = True
        event.src_path = "/tmp/some_dir"

        self.handler.on_modified(event)

        # Should not trigger reload
        self.scheduler.reload_config.assert_not_called()

    def test_on_modified_ignores_other_files(self):
        """Test that on_modified ignores other files."""
        event = Mock()
        event.is_directory = False
        event.src_path = "/tmp/other_file.yaml"

        self.handler.on_modified(event)

        # Should not trigger reload
        self.scheduler.reload_config.assert_not_called()

    def test_on_modified_triggers_reload_for_config_file(self):
        """Test that on_modified triggers reload for config file."""
        event = Mock()
        event.is_directory = False
        event.src_path = str(self.config_path)

        with patch("time.time", return_value=100.0):
            self.handler.on_modified(event)

        # Should trigger reload
        self.scheduler.reload_config.assert_called_once()

    def test_on_modified_with_bytes_path(self):
        """Test on_modified with bytes path."""
        event = Mock()
        event.is_directory = False
        event.src_path = str(self.config_path).encode("utf-8")

        with patch("time.time", return_value=100.0):
            self.handler.on_modified(event)

        # Should trigger reload
        self.scheduler.reload_config.assert_called_once()

    def test_on_created_ignores_directory(self):
        """Test that on_created ignores directory events."""
        event = Mock()
        event.is_directory = True
        event.src_path = "/tmp/some_dir"

        self.handler.on_created(event)

        # Should not trigger reload
        self.scheduler.reload_config.assert_not_called()

    def test_on_created_ignores_other_files(self):
        """Test that on_created ignores other files."""
        event = Mock()
        event.is_directory = False
        event.src_path = "/tmp/other_file.yaml"

        self.handler.on_created(event)

        # Should not trigger reload
        self.scheduler.reload_config.assert_not_called()

    def test_on_created_triggers_reload_for_config_file(self):
        """Test that on_created triggers reload for config file."""
        event = Mock()
        event.is_directory = False
        event.src_path = str(self.config_path)

        with patch("time.time", return_value=100.0):
            self.handler.on_created(event)

        # Should trigger reload
        self.scheduler.reload_config.assert_called_once()

    def test_on_created_with_bytes_path(self):
        """Test on_created with bytes path."""
        event = Mock()
        event.is_directory = False
        event.src_path = str(self.config_path).encode("utf-8")

        with patch("time.time", return_value=100.0):
            self.handler.on_created(event)

        # Should trigger reload
        self.scheduler.reload_config.assert_called_once()

    def test_trigger_reload_debouncing(self):
        """Test that trigger_reload debounces rapid changes."""
        event = Mock()
        event.is_directory = False
        event.src_path = str(self.config_path)

        # First reload at time 100
        with patch("time.time", return_value=100.0):
            self.handler.on_modified(event)

        # Second reload at time 100.5 (within debounce period of 1.0s)
        with patch("time.time", return_value=100.5):
            self.handler.on_modified(event)

        # Should only reload once (debounced)
        assert self.scheduler.reload_config.call_count == 1

    def test_trigger_reload_after_debounce_period(self):
        """Test that trigger_reload works after debounce period."""
        event = Mock()
        event.is_directory = False
        event.src_path = str(self.config_path)

        # First reload at time 100
        with patch("time.time", return_value=100.0):
            self.handler.on_modified(event)

        # Second reload at time 102 (after debounce period of 1.0s)
        with patch("time.time", return_value=102.0):
            self.handler.on_modified(event)

        # Should reload twice
        assert self.scheduler.reload_config.call_count == 2

    def test_trigger_reload_handles_exception(self):
        """Test that trigger_reload handles exceptions gracefully."""
        event = Mock()
        event.is_directory = False
        event.src_path = str(self.config_path)

        # Make reload_config raise an exception
        self.scheduler.reload_config.side_effect = Exception("Reload failed")

        # Should not raise exception
        with patch("time.time", return_value=100.0):
            self.handler.on_modified(event)

        # Should have attempted reload
        self.scheduler.reload_config.assert_called_once()

    def test_trigger_reload_updates_last_reload_time(self):
        """Test that trigger_reload updates last_reload_time."""
        event = Mock()
        event.is_directory = False
        event.src_path = str(self.config_path)

        with patch("time.time", return_value=123.45):
            self.handler.on_modified(event)

        assert self.handler.last_reload_time == 123.45


class TestConfigWatcher:
    """Test ConfigWatcher class."""

    def test_initialization_with_existing_file(self):
        """Test watcher initialization with existing file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("alerts: []")
            config_path = f.name

        try:
            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=config_path,
                scheduler=scheduler,
                debounce_seconds=1.0,
            )

            assert watcher.config_path == Path(config_path).resolve()
            assert watcher.scheduler is scheduler
            assert watcher.debounce_seconds == 1.0
            assert watcher.watch_directory == Path(config_path).parent
            assert isinstance(watcher.observer, object)
            assert isinstance(watcher.event_handler, ConfigFileHandler)
        finally:
            Path(config_path).unlink()

    def test_initialization_with_nonexistent_file(self):
        """Test watcher initialization with nonexistent file."""
        scheduler = Mock()

        with pytest.raises(FileNotFoundError):
            ConfigWatcher(
                config_path="/nonexistent/config.yaml",
                scheduler=scheduler,
            )

    def test_initialization_with_string_path(self):
        """Test watcher initialization with string path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("alerts: []")
            config_path = f.name

        try:
            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=config_path,  # String path
                scheduler=scheduler,
            )

            assert watcher.config_path == Path(config_path).resolve()
        finally:
            Path(config_path).unlink()

    def test_initialization_with_path_object(self):
        """Test watcher initialization with Path object."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("alerts: []")
            config_path = Path(f.name)

        try:
            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=config_path,  # Path object
                scheduler=scheduler,
            )

            assert watcher.config_path == config_path.resolve()
        finally:
            config_path.unlink()

    def test_initialization_default_debounce_seconds(self):
        """Test watcher initialization with default debounce_seconds."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("alerts: []")
            config_path = f.name

        try:
            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=config_path,
                scheduler=scheduler,
            )

            assert watcher.debounce_seconds == 2.0  # Default value
        finally:
            Path(config_path).unlink()

    def test_start(self):
        """Test starting the watcher."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("alerts: []")
            config_path = f.name

        try:
            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=config_path,
                scheduler=scheduler,
            )

            watcher.start()

            # Watcher should be running
            assert watcher.is_alive()

            # Clean up
            watcher.stop()
        finally:
            Path(config_path).unlink()

    def test_stop(self):
        """Test stopping the watcher."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("alerts: []")
            config_path = f.name

        try:
            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=config_path,
                scheduler=scheduler,
            )

            watcher.start()
            assert watcher.is_alive()

            watcher.stop()

            # Watcher should be stopped
            assert not watcher.is_alive()
        finally:
            Path(config_path).unlink()

    def test_stop_when_not_running(self):
        """Test stopping the watcher when it's not running."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("alerts: []")
            config_path = f.name

        try:
            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=config_path,
                scheduler=scheduler,
            )

            # Don't start, just stop
            watcher.stop()

            # Should not raise exception
            assert not watcher.is_alive()
        finally:
            Path(config_path).unlink()

    def test_stop_timeout_handling(self):
        """Test stop handles timeout gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("alerts: []")
            config_path = f.name

        try:
            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=config_path,
                scheduler=scheduler,
            )

            # Mock observer to simulate timeout
            mock_observer = Mock()
            mock_observer.is_alive.side_effect = [True, True]  # Still alive after join
            mock_observer.stop = Mock()
            mock_observer.join = Mock()

            watcher.observer = mock_observer

            watcher.stop()

            # Should call stop and join
            mock_observer.stop.assert_called_once()
            mock_observer.join.assert_called_once_with(timeout=5.0)
        finally:
            Path(config_path).unlink()

    def test_is_alive_when_running(self):
        """Test is_alive returns True when watcher is running."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("alerts: []")
            config_path = f.name

        try:
            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=config_path,
                scheduler=scheduler,
            )

            watcher.start()
            assert watcher.is_alive() is True

            watcher.stop()
        finally:
            Path(config_path).unlink()

    def test_is_alive_when_not_running(self):
        """Test is_alive returns False when watcher is not running."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("alerts: []")
            config_path = f.name

        try:
            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=config_path,
                scheduler=scheduler,
            )

            assert watcher.is_alive() is False
        finally:
            Path(config_path).unlink()


class TestConfigWatcherIntegration:
    """Integration tests for ConfigWatcher."""

    def test_file_modification_triggers_reload(self):
        """Test that file modification triggers reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"
            config_path.write_text("alerts: []")

            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=str(config_path),
                scheduler=scheduler,
                debounce_seconds=0.1,  # Short debounce for testing
            )

            try:
                watcher.start()

                # Give watcher time to start
                time.sleep(0.2)

                # Modify the file
                config_path.write_text("alerts:\n  - name: test")

                # Give watcher time to detect change
                time.sleep(0.3)

                # Should have triggered reload
                scheduler.reload_config.assert_called()
            finally:
                watcher.stop()

    def test_file_creation_triggers_reload(self):
        """Test that file creation triggers reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"
            config_path.write_text("alerts: []")

            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=str(config_path),
                scheduler=scheduler,
                debounce_seconds=0.1,
            )

            try:
                watcher.start()
                time.sleep(0.2)

                # Remove and recreate the file (simulates some editors' save behavior)
                config_path.unlink()
                time.sleep(0.1)
                config_path.write_text("alerts:\n  - name: new_alert")

                # Give watcher time to detect change
                time.sleep(0.3)

                # Should have triggered reload
                scheduler.reload_config.assert_called()
            finally:
                watcher.stop()

    def test_debouncing_prevents_multiple_reloads(self):
        """Test that debouncing prevents multiple rapid reloads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"
            config_path.write_text("alerts: []")

            scheduler = Mock()
            watcher = ConfigWatcher(
                config_path=str(config_path),
                scheduler=scheduler,
                debounce_seconds=1.0,  # Longer debounce
            )

            try:
                watcher.start()
                time.sleep(0.2)

                # Make multiple rapid changes
                config_path.write_text("alerts:\n  - name: test1")
                time.sleep(0.1)
                config_path.write_text("alerts:\n  - name: test2")
                time.sleep(0.1)
                config_path.write_text("alerts:\n  - name: test3")

                # Give watcher time to process
                time.sleep(0.5)

                # Should only reload once (or at most twice due to debouncing)
                call_count = scheduler.reload_config.call_count
                assert call_count <= 2  # Debouncing should prevent all 3 from triggering
            finally:
                watcher.stop()
