"""Tests for alert state management."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine

from sqlsentinel.database.schema import SchemaManager
from sqlsentinel.executor.state import AlertState, StateManager
from sqlsentinel.models.errors import ExecutionError


class TestAlertState:
    """Test AlertState class."""

    def test_init_defaults(self):
        """Test AlertState initialization with defaults."""
        state = AlertState(alert_name="test_alert")

        assert state.alert_name == "test_alert"
        assert state.last_executed_at is None
        assert state.last_alert_at is None
        assert state.last_ok_at is None
        assert state.consecutive_alerts == 0
        assert state.consecutive_oks == 0
        assert state.current_status is None
        assert state.silenced_until is None
        assert state.updated_at is not None

    def test_init_with_values(self):
        """Test AlertState initialization with values."""
        now = datetime.utcnow()
        state = AlertState(
            alert_name="test_alert",
            last_executed_at=now,
            last_alert_at=now,
            last_ok_at=None,
            consecutive_alerts=3,
            consecutive_oks=0,
            current_status="ALERT",
            silenced_until=None,
            updated_at=now,
        )

        assert state.alert_name == "test_alert"
        assert state.last_executed_at == now
        assert state.last_alert_at == now
        assert state.consecutive_alerts == 3
        assert state.current_status == "ALERT"

    def test_is_silenced_false(self):
        """Test is_silenced returns False when not silenced."""
        state = AlertState(alert_name="test_alert")
        assert state.is_silenced() is False

    def test_is_silenced_true(self):
        """Test is_silenced returns True when silenced."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        state = AlertState(alert_name="test_alert", silenced_until=future_time)
        assert state.is_silenced() is True

    def test_is_silenced_expired(self):
        """Test is_silenced returns False when silence period expired."""
        past_time = datetime.utcnow() - timedelta(hours=1)
        state = AlertState(alert_name="test_alert", silenced_until=past_time)
        assert state.is_silenced() is False

    def test_should_notify_first_alert(self):
        """Test should_notify returns True for first alert."""
        state = AlertState(alert_name="test_alert")
        assert state.should_notify("ALERT") is True

    def test_should_notify_status_change_ok_to_alert(self):
        """Test should_notify returns True when status changes from OK to ALERT."""
        state = AlertState(alert_name="test_alert", current_status="OK")
        assert state.should_notify("ALERT") is True

    def test_should_notify_consecutive_alerts(self):
        """Test should_notify returns False for consecutive alerts."""
        state = AlertState(
            alert_name="test_alert",
            current_status="ALERT",
            consecutive_alerts=2,
            last_alert_at=datetime.utcnow(),
        )
        assert state.should_notify("ALERT") is False

    def test_should_notify_ok_status(self):
        """Test should_notify returns False for OK status."""
        state = AlertState(alert_name="test_alert")
        assert state.should_notify("OK") is False

    def test_should_notify_error_status(self):
        """Test should_notify returns False for ERROR status."""
        state = AlertState(alert_name="test_alert")
        assert state.should_notify("ERROR") is False

    def test_should_notify_silenced(self):
        """Test should_notify returns False when silenced."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        state = AlertState(alert_name="test_alert", silenced_until=future_time)
        assert state.should_notify("ALERT") is False

    def test_should_notify_min_interval_not_met(self):
        """Test should_notify returns False when min interval not met."""
        recent_time = datetime.utcnow() - timedelta(seconds=30)
        state = AlertState(
            alert_name="test_alert",
            current_status="OK",
            last_alert_at=recent_time,
        )
        # Require 60 seconds between alerts
        assert state.should_notify("ALERT", min_interval_seconds=60) is False

    def test_should_notify_min_interval_met(self):
        """Test should_notify returns True when min interval met."""
        old_time = datetime.utcnow() - timedelta(seconds=120)
        state = AlertState(
            alert_name="test_alert",
            current_status="OK",
            last_alert_at=old_time,
        )
        # Require 60 seconds between alerts
        assert state.should_notify("ALERT", min_interval_seconds=60) is True


class TestStateManager:
    """Test StateManager class."""

    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing."""
        engine = create_engine("sqlite:///:memory:")
        schema_manager = SchemaManager(engine)
        schema_manager.create_schema()
        return engine

    @pytest.fixture
    def state_manager(self, engine):
        """Create StateManager instance."""
        return StateManager(engine)

    def test_init(self, state_manager, engine):
        """Test StateManager initialization."""
        assert state_manager.engine == engine

    def test_get_state_not_found(self, state_manager):
        """Test get_state returns new state when not found."""
        state = state_manager.get_state("nonexistent_alert")

        assert state.alert_name == "nonexistent_alert"
        assert state.last_executed_at is None
        assert state.current_status is None

    def test_update_state_creates_new_record(self, state_manager):
        """Test update_state creates new record when none exists."""
        state = AlertState(alert_name="new_alert")
        state_manager.update_state(state, "ALERT")

        # Verify state was created
        retrieved_state = state_manager.get_state("new_alert")
        assert retrieved_state.current_status == "ALERT"
        assert retrieved_state.consecutive_alerts == 1
        assert retrieved_state.consecutive_oks == 0
        assert retrieved_state.last_alert_at is not None

    def test_update_state_updates_existing_record(self, state_manager):
        """Test update_state updates existing record."""
        # Create initial state
        state = AlertState(alert_name="existing_alert")
        state_manager.update_state(state, "OK")

        # Update state
        state = state_manager.get_state("existing_alert")
        state_manager.update_state(state, "ALERT")

        # Verify update
        retrieved_state = state_manager.get_state("existing_alert")
        assert retrieved_state.current_status == "ALERT"
        assert retrieved_state.consecutive_alerts == 1
        assert retrieved_state.consecutive_oks == 0

    def test_update_state_alert_increments_consecutive(self, state_manager):
        """Test update_state increments consecutive_alerts."""
        state = AlertState(alert_name="test_alert")
        state_manager.update_state(state, "ALERT")

        state = state_manager.get_state("test_alert")
        state_manager.update_state(state, "ALERT")

        retrieved_state = state_manager.get_state("test_alert")
        assert retrieved_state.consecutive_alerts == 2
        assert retrieved_state.consecutive_oks == 0

    def test_update_state_ok_increments_consecutive(self, state_manager):
        """Test update_state increments consecutive_oks."""
        state = AlertState(alert_name="test_alert")
        state_manager.update_state(state, "OK")

        state = state_manager.get_state("test_alert")
        state_manager.update_state(state, "OK")

        retrieved_state = state_manager.get_state("test_alert")
        assert retrieved_state.consecutive_oks == 2
        assert retrieved_state.consecutive_alerts == 0

    def test_update_state_resets_consecutive_on_status_change(self, state_manager):
        """Test update_state resets consecutive counts on status change."""
        # Set to ALERT
        state = AlertState(alert_name="test_alert")
        state_manager.update_state(state, "ALERT")

        state = state_manager.get_state("test_alert")
        state_manager.update_state(state, "ALERT")

        # Change to OK
        state = state_manager.get_state("test_alert")
        state_manager.update_state(state, "OK")

        retrieved_state = state_manager.get_state("test_alert")
        assert retrieved_state.consecutive_alerts == 0
        assert retrieved_state.consecutive_oks == 1
        assert retrieved_state.current_status == "OK"

    def test_update_state_error_preserves_consecutive(self, state_manager):
        """Test update_state preserves consecutive counts for ERROR status."""
        state = AlertState(alert_name="test_alert")
        state_manager.update_state(state, "ALERT")

        state = state_manager.get_state("test_alert")
        state_manager.update_state(state, "ERROR")

        retrieved_state = state_manager.get_state("test_alert")
        assert retrieved_state.consecutive_alerts == 1
        assert retrieved_state.current_status == "ERROR"

    def test_silence_alert(self, state_manager):
        """Test silence_alert sets silenced_until."""
        state_manager.silence_alert("test_alert", duration_seconds=3600)

        state = state_manager.get_state("test_alert")
        assert state.silenced_until is not None
        assert state.is_silenced() is True

    def test_silence_alert_invalid_duration(self, state_manager):
        """Test silence_alert raises error for invalid duration."""
        with pytest.raises(ExecutionError, match="Silence duration must be positive"):
            state_manager.silence_alert("test_alert", duration_seconds=0)

        with pytest.raises(ExecutionError, match="Silence duration must be positive"):
            state_manager.silence_alert("test_alert", duration_seconds=-1)

    def test_unsilence_alert(self, state_manager):
        """Test unsilence_alert removes silenced_until."""
        # Silence first
        state_manager.silence_alert("test_alert", duration_seconds=3600)

        # Unsilence
        state_manager.unsilence_alert("test_alert")

        state = state_manager.get_state("test_alert")
        assert state.silenced_until is None
        assert state.is_silenced() is False

    def test_delete_state(self, state_manager):
        """Test delete_state removes state record."""
        # Create state
        state = AlertState(alert_name="test_alert")
        state_manager.update_state(state, "ALERT")

        # Delete state
        state_manager.delete_state("test_alert")

        # Verify deleted
        retrieved_state = state_manager.get_state("test_alert")
        assert retrieved_state.last_executed_at is None
        assert retrieved_state.current_status is None

    def test_delete_state_nonexistent(self, state_manager):
        """Test delete_state doesn't error for nonexistent alert."""
        # Should not raise error
        state_manager.delete_state("nonexistent_alert")
