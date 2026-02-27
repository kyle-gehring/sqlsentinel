"""CLI integration tests.

These tests invoke the CLI via subprocess to catch issues that unit tests
cannot detect: import errors, wrong defaults, end-to-end command failures.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_CONFIG = Path(__file__).parent / "fixtures" / "integration_config.yaml"
CLI = [sys.executable, "-m", "sqlsentinel.cli"]


def run_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    """Run the CLI with the given arguments and return the result."""
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        [*CLI, *args],
        capture_output=True,
        text=True,
        env=merged_env,
    )


class TestCLIStartup:
    """Tests that catch import errors and startup failures."""

    def test_version(self):
        """CLI starts and reports version — catches any module-level import errors."""
        result = run_cli("--version")
        assert result.returncode == 0, result.stderr
        assert "sqlsentinel" in result.stdout

    def test_help(self):
        """CLI help works without error."""
        result = run_cli("--help")
        assert result.returncode == 0, result.stderr


class TestValidateCommand:
    def test_validate_valid_config(self):
        """Validate passes on a well-formed config."""
        result = run_cli("validate", str(FIXTURE_CONFIG))
        assert result.returncode == 0, result.stderr
        assert "valid" in result.stdout.lower()

    def test_validate_invalid_config(self, tmp_path):
        """Validate fails on a bad config."""
        bad_config = tmp_path / "bad.yaml"
        bad_config.write_text("not: valid: yaml:\n  - oops")
        result = run_cli("validate", str(bad_config))
        assert result.returncode != 0


class TestInitCommand:
    def test_init_creates_state_db(self, tmp_path):
        """Init creates the state database file."""
        state_db = tmp_path / "state.db"
        result = run_cli("init", "--state-db", f"sqlite:///{state_db}")
        assert result.returncode == 0, result.stderr
        assert state_db.exists()

    def test_init_reads_state_db_url_env(self, tmp_path):
        """Init uses STATE_DB_URL env var when --state-db is not provided."""
        state_db = tmp_path / "state.db"
        result = run_cli("init", env={"STATE_DB_URL": f"sqlite:///{state_db}"})
        assert result.returncode == 0, result.stderr
        assert state_db.exists()


class TestRunCommand:
    @pytest.fixture()
    def state_db(self, tmp_path):
        """Initialised state DB ready for use."""
        db = tmp_path / "state.db"
        run_cli("init", "--state-db", f"sqlite:///{db}")
        return db

    def test_dry_run_all_alerts(self, state_db):
        """Run --dry-run executes all alerts without sending notifications.

        One alert fires (exit code 1 is correct) — we verify both ran without
        crashing (no 'error' status, only 'success'/'failure').
        """
        result = run_cli(
            "run",
            str(FIXTURE_CONFIG),
            "--state-db",
            f"sqlite:///{state_db}",
            "--dry-run",
        )
        assert result.returncode in (0, 1), result.stdout  # 1 = alert fired, not a crash
        assert "DRY RUN" in result.stdout
        assert "Always OK" in result.stdout
        assert "Always Alert" in result.stdout
        assert "error" not in result.stdout.lower().split("execution summary")[1]

    def test_dry_run_single_alert(self, state_db):
        """Run --dry-run with --alert only runs the named alert."""
        result = run_cli(
            "run",
            str(FIXTURE_CONFIG),
            "--alert",
            "Always OK",
            "--state-db",
            f"sqlite:///{state_db}",
            "--dry-run",
        )
        assert result.returncode == 0, result.stdout
        assert "Always OK" in result.stdout

    def test_run_uses_state_db_url_env(self, tmp_path):
        """Run uses STATE_DB_URL env var when --state-db is not provided."""
        state_db = tmp_path / "state.db"
        state_db_url = f"sqlite:///{state_db}"
        run_cli("init", "--state-db", state_db_url)
        result = run_cli(
            "run",
            str(FIXTURE_CONFIG),
            "--alert",
            "Always OK",  # single OK alert → exit code 0
            "--dry-run",
            env={"STATE_DB_URL": state_db_url},
        )
        assert result.returncode == 0, result.stdout

    def test_run_missing_alert_name(self, state_db):
        """Run fails with a helpful message when alert name doesn't exist."""
        result = run_cli(
            "run",
            str(FIXTURE_CONFIG),
            "--alert",
            "Nonexistent Alert",
            "--state-db",
            f"sqlite:///{state_db}",
            "--dry-run",
        )
        assert result.returncode != 0
        assert "not found" in result.stdout.lower()


class TestStateDatabaseErrors:
    def test_bare_file_path_gives_helpful_error(self, tmp_path):
        """Passing a bare file path to --state-db prints a clear, actionable error."""
        result = run_cli(
            "run",
            str(FIXTURE_CONFIG),
            "--state-db",
            str(tmp_path / "state.db"),  # missing sqlite:/// scheme
            "--dry-run",
        )
        assert result.returncode != 0
        assert "sqlite://" in result.stdout


class TestStatusCommand:
    def test_status_before_any_runs(self, tmp_path):
        """Status works even when no alerts have run yet."""
        state_db = tmp_path / "state.db"
        run_cli("init", "--state-db", f"sqlite:///{state_db}")
        result = run_cli(
            "status",
            str(FIXTURE_CONFIG),
            "--state-db",
            f"sqlite:///{state_db}",
        )
        assert result.returncode == 0, result.stderr
