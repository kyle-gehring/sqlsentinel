"""Test configuration and environment setup."""

import os
from pathlib import Path


def load_test_env() -> None:
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return

    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def should_run_real_email_tests() -> bool:
    """Check if real email integration tests should run.

    Returns:
        True if ENABLE_REAL_EMAIL_TESTS is set to 'true', False otherwise
    """
    load_test_env()
    return os.getenv("ENABLE_REAL_EMAIL_TESTS", "false").lower() == "true"


def get_test_email_recipient() -> str | None:
    """Get the test email recipient address.

    Returns:
        Email address for test messages, or None if not configured
    """
    load_test_env()
    return os.getenv("TEST_EMAIL_RECIPIENT")


def get_smtp_config() -> dict:
    """Get SMTP configuration from environment.

    Returns:
        Dictionary with SMTP configuration
    """
    load_test_env()
    return {
        "smtp_host": os.getenv("SMTP_HOST"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_username": os.getenv("SMTP_USERNAME"),
        "smtp_password": os.getenv("SMTP_PASSWORD"),
        "smtp_use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        "smtp_from_address": os.getenv("SMTP_FROM_ADDRESS"),
    }
