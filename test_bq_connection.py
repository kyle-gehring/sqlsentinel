#!/usr/bin/env python3
"""Quick BigQuery connection test with timeout and error handling."""

import os
import sys
import signal
from contextlib import contextmanager

# Set up environment if not already set
if not os.getenv("BIGQUERY_PROJECT_ID"):
    os.environ["BIGQUERY_PROJECT_ID"] = "ai-text-rpg"

if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/workspace/.bigquery_credentials.json"

print(f"Project ID: {os.environ['BIGQUERY_PROJECT_ID']}")
print(f"Credentials: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")
print()


class TimeoutError(Exception):
    pass


@contextmanager
def timeout(seconds):
    """Context manager for timeout."""
    def signal_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # Set the signal handler
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def test_connection():
    """Test BigQuery connection with timeout."""
    print("Testing BigQuery connection...")

    try:
        from src.sqlsentinel.database.bigquery_adapter import BigQueryAdapter

        print("1. Creating adapter...")
        adapter = BigQueryAdapter(
            project_id=os.environ["BIGQUERY_PROJECT_ID"],
            credentials_path=os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        )

        print("2. Attempting connection (with 30s timeout)...")
        with timeout(30):
            adapter.connect()

        print("✓ Connection successful!")

        print("3. Testing simple query...")
        with timeout(30):
            results = adapter.execute_query("SELECT 1 as value")

        print(f"✓ Query successful! Result: {results}")

        print("4. Disconnecting...")
        adapter.disconnect()

        print("\n✓ All tests passed!")
        return True

    except TimeoutError as e:
        print(f"\n✗ TIMEOUT: {e}")
        print("\nPossible causes:")
        print("  - Network/firewall blocking BigQuery API access")
        print("  - BigQuery API not enabled in project")
        print("  - Service account permissions issue")
        return False

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
