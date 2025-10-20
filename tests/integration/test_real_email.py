"""Integration tests with real email delivery.

These tests send actual emails using the configured SMTP server.
They are only run when ENABLE_REAL_EMAIL_TESTS=true in .env
"""

import pytest
from sqlalchemy.engine import Engine

from sqlsentinel.database.adapter import DatabaseAdapter
from sqlsentinel.executor.alert_executor import AlertExecutor
from sqlsentinel.models.alert import AlertConfig
from sqlsentinel.models.notification import NotificationChannel, NotificationConfig
from sqlsentinel.notifications.factory import NotificationFactory
from tests.helpers import (
    assert_execution_result,
    get_alert_state,
    get_execution_count,
    verify_execution_recorded,
    verify_state_updated,
)
from tests.test_config import get_test_email_recipient, should_run_real_email_tests

# Skip all tests in this module if real email tests are disabled
pytestmark = pytest.mark.skipif(
    not should_run_real_email_tests(),
    reason="Real email tests disabled. Set ENABLE_REAL_EMAIL_TESTS=true in .env to enable",
)


class TestRealEmailIntegration:
    """Integration tests that send real emails."""

    def test_send_alert_email(
        self,
        temp_state_db: Engine,
        db_adapter: DatabaseAdapter,
        configured_notification_factory: NotificationFactory,
    ):
        """Test sending a real alert email through SMTP.

        This test sends an actual email to the configured TEST_EMAIL_RECIPIENT.
        """
        # Get test recipient
        recipient = get_test_email_recipient()
        assert recipient, "TEST_EMAIL_RECIPIENT must be set in .env"

        # Create alert with email notification
        alert = AlertConfig(
            name="integration_test_alert",
            description="Integration test - real email delivery",
            query="SELECT 'ALERT' as status, 100 as actual_value, 50 as threshold",
            schedule="0 9 * * *",
            enabled=True,
            notify=[
                NotificationConfig(
                    channel=NotificationChannel.EMAIL,
                    config={
                        "recipients": [recipient],
                        "subject": "[SQL Sentinel Test] Alert Triggered",
                    },
                )
            ],
        )

        # Create executor
        executor = AlertExecutor(temp_state_db, configured_notification_factory)

        # Execute alert - this will send a real email
        result = executor.execute_alert(alert, db_adapter, triggered_by="MANUAL")

        # Verify execution succeeded
        assert_execution_result(result, expected_status="failure")  # ALERT = failure
        assert result.query_result.status == "ALERT"
        assert result.query_result.actual_value == 100
        assert result.query_result.threshold == 50

        # Verify state was updated
        assert verify_state_updated(
            temp_state_db,
            "integration_test_alert",
            expected_status="ALERT",
            expected_consecutive_alerts=1,
        )

        # Verify execution was recorded with notification sent
        assert verify_execution_recorded(
            temp_state_db,
            "integration_test_alert",
            expected_status="ALERT",
            expected_notification_sent=True,
        )

        print(f"\n✉️  Test email sent to {recipient}")
        print("Check your inbox to verify email delivery!")

    def test_send_ok_status_email(
        self,
        temp_state_db: Engine,
        db_adapter: DatabaseAdapter,
        configured_notification_factory: NotificationFactory,
    ):
        """Test that OK status doesn't send email (by design).

        Verifies the notification logic works correctly for non-alert states.
        """
        recipient = get_test_email_recipient()
        assert recipient, "TEST_EMAIL_RECIPIENT must be set in .env"

        # Create alert that returns OK
        alert = AlertConfig(
            name="ok_status_test",
            description="Integration test - OK status (no email expected)",
            query="SELECT 'OK' as status, 30 as actual_value, 50 as threshold",
            schedule="0 9 * * *",
            enabled=True,
            notify=[
                NotificationConfig(
                    channel=NotificationChannel.EMAIL,
                    config={
                        "recipients": [recipient],
                        "subject": "[SQL Sentinel Test] OK Status",
                    },
                )
            ],
        )

        # Create executor
        executor = AlertExecutor(temp_state_db, configured_notification_factory)

        # Execute alert
        result = executor.execute_alert(alert, db_adapter, triggered_by="MANUAL")

        # Verify execution succeeded
        assert_execution_result(result, expected_status="success")  # OK = success
        assert result.query_result.status == "OK"

        # Verify state was updated
        assert verify_state_updated(
            temp_state_db, "ok_status_test", expected_status="OK", expected_consecutive_oks=1
        )

        # Verify execution recorded but NO notification sent (OK status)
        assert verify_execution_recorded(
            temp_state_db,
            "ok_status_test",
            expected_status="OK",
            expected_notification_sent=False,
        )

        print("\n✅ OK status correctly did not send email")

    def test_alert_deduplication_prevents_spam(
        self,
        temp_state_db: Engine,
        db_adapter: DatabaseAdapter,
        configured_notification_factory: NotificationFactory,
    ):
        """Test that consecutive alerts only send one email.

        This verifies deduplication works with real SMTP to prevent spam.
        """
        recipient = get_test_email_recipient()
        assert recipient, "TEST_EMAIL_RECIPIENT must be set in .env"

        alert = AlertConfig(
            name="dedup_test",
            description="Deduplication test - only first alert sends email",
            query="SELECT 'ALERT' as status, 100 as actual_value, 50 as threshold",
            schedule="0 9 * * *",
            enabled=True,
            notify=[
                NotificationConfig(
                    channel=NotificationChannel.EMAIL,
                    config={
                        "recipients": [recipient],
                        "subject": "[SQL Sentinel Test] Deduplication Test",
                    },
                )
            ],
        )

        executor = AlertExecutor(temp_state_db, configured_notification_factory)

        # First execution - should send email
        result1 = executor.execute_alert(alert, db_adapter, triggered_by="MANUAL")
        assert_execution_result(result1, expected_status="failure")

        # Verify first execution sent notification
        exec1 = get_execution_count(temp_state_db, "dedup_test")
        assert exec1 == 1

        # Second execution - should NOT send email (deduplicated)
        result2 = executor.execute_alert(alert, db_adapter, triggered_by="MANUAL")
        assert_execution_result(result2, expected_status="failure")

        # Verify second execution did NOT send notification
        exec_count = get_execution_count(temp_state_db, "dedup_test")
        assert exec_count == 2

        # Verify state shows 2 consecutive alerts
        state = get_alert_state(temp_state_db, "dedup_test")
        assert state["consecutive_alerts"] == 2

        print("\n✅ Deduplication working - only 1 email sent for 2 consecutive alerts")
        print(f"   Check {recipient} - you should only see ONE email")
