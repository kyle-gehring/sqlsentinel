# Contributing to SQL Sentinel

Thank you for your interest in contributing to SQL Sentinel! This guide will help you get started.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.11 or 3.12
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management
- Git

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/sql-sentinel.git
   cd sql-sentinel
   ```

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Install pre-commit hooks:**
   ```bash
   poetry run pre-commit install
   ```

4. **Verify your setup:**
   ```bash
   poetry run pytest
   ```

### Using the DevContainer

If you use VS Code, you can open this project in a DevContainer which has all dependencies pre-configured. Just open the project and select "Reopen in Container" when prompted.

## Development Workflow

### Running Commands

All Python commands must be run with the `poetry run` prefix:

```bash
poetry run pytest                    # Run tests
poetry run pytest tests/test_cli.py  # Run specific test file
poetry run black src/ tests/         # Format code
poetry run ruff check src/ tests/    # Lint code
poetry run mypy src/                 # Type check
```

### Code Style

- **Formatter:** [Black](https://black.readthedocs.io/) with 100 character line length
- **Linter:** [Ruff](https://docs.astral.sh/ruff/) with pycodestyle, pyflakes, isort, bugbear, and pyupgrade rules
- **Type Checking:** [mypy](https://mypy.readthedocs.io/) in strict mode

Pre-commit hooks will automatically check formatting and linting on each commit.

### Running Tests

```bash
# Run all tests with coverage
poetry run pytest

# Run a specific test file
poetry run pytest tests/test_cli.py

# Run tests matching a pattern
poetry run pytest -k "test_validate"

# Run with verbose output
poetry run pytest -v
```

Tests require 80% minimum coverage. The test suite uses SQLite for all database tests, so no external database is needed.

## Making Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring

### Commit Messages

Write clear, concise commit messages that explain the **why**, not just the **what**:

```
Add silence duration option to CLI

Previously, silencing an alert required specifying an exact end time.
This adds a --duration flag accepting values like "2h" or "30m" for
convenience.
```

### Pull Request Process

1. **Create a feature branch** from `master`
2. **Make your changes** with tests
3. **Ensure all checks pass:**
   ```bash
   poetry run pytest
   poetry run black --check src/ tests/
   poetry run ruff check src/ tests/
   poetry run mypy src/
   ```
4. **Push and open a pull request** against `master`
5. **Fill out the PR template** with a description and test plan
6. **Address review feedback**

### What Makes a Good PR

- Focused on a single change
- Includes tests for new functionality
- Updates documentation if behavior changes
- Passes all CI checks
- Has a clear description of what and why

## Project Structure

```
sql-sentinel/
├── src/sqlsentinel/       # Main package
│   ├── cli.py             # CLI entry point
│   ├── config.py          # YAML configuration parsing
│   ├── executor.py        # Alert query execution
│   ├── scheduler.py       # Cron scheduling
│   ├── notifications/     # Notification channels
│   └── state.py           # State management
├── tests/                 # Test suite
├── examples/              # Example configurations
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

## Reporting Issues

- Use the [bug report template](https://github.com/kyle-gehring/sql-sentinel/issues/new?template=bug_report.md) for bugs
- Use the [feature request template](https://github.com/kyle-gehring/sql-sentinel/issues/new?template=feature_request.md) for ideas

Include as much detail as possible: steps to reproduce, expected vs actual behavior, and your environment (Python version, OS, database type).

## Questions?

Open a [discussion](https://github.com/kyle-gehring/sql-sentinel/discussions) or file an issue. We're happy to help!
