# Sprint 1.1: Project Setup & Core Models

**Duration:** Days 1-3
**Sprint Goal:** Establish foundational project structure with core data models and testing framework
**Status:** Not Started

## Objectives

Set up a production-ready Python project structure with core domain models, containerization, and automated testing infrastructure that will serve as the foundation for SQL Sentinel.

## Success Criteria

- [ ] All tests pass with >80% code coverage
- [ ] Docker container builds and runs successfully locally
- [ ] Code passes all linting checks (black, mypy, ruff)
- [ ] Pre-commit hooks configured and working
- [ ] Core models are fully type-hinted and validated

## Work Items

### 1. Project Structure Setup
- [ ] Create Python package structure (`src/sqlsentinel/`)
- [ ] Initialize Poetry project with core dependencies
- [ ] Configure pyproject.toml with project metadata
- [ ] Set up directory structure (models, services, utils, tests)
- [ ] Create .gitignore for Python projects
- [ ] Add LICENSE file (Apache 2.0 or MIT)

### 2. Development Environment Configuration
- [ ] Configure Poetry virtual environment
- [ ] Add development dependencies (pytest, black, mypy, ruff)
- [ ] Set up pre-commit hooks for code quality
- [ ] Configure VSCode/IDE settings for project
- [ ] Create .editorconfig for consistent formatting
- [ ] Document development setup in contributing guide

### 3. Docker Containerization
- [ ] Create Dockerfile with multi-stage build
- [ ] Optimize image layers for minimal size
- [ ] Add health check endpoint configuration
- [ ] Create .dockerignore file
- [ ] Test local Docker build and run
- [ ] Document Docker usage

### 4. Core Data Models Implementation
- [ ] Create `AlertConfig` dataclass with Pydantic validation
  - name, description, query, schedule fields
  - notification configuration
  - validation rules
- [ ] Create `ExecutionResult` model
  - execution timestamp
  - status (success, failure, error)
  - execution duration
  - error details
- [ ] Create `QueryResult` model
  - status field (ALERT, OK)
  - actual_value (optional)
  - threshold (optional)
  - additional context fields
- [ ] Create `NotificationConfig` models
  - channel type (email, slack, webhook)
  - channel-specific configuration
  - recipient information
- [ ] Create error handling hierarchy
  - ConfigurationError
  - ValidationError
  - ExecutionError
  - NotificationError

### 5. Basic Testing Framework
- [ ] Set up pytest configuration (pytest.ini)
- [ ] Create test directory structure mirroring src/
- [ ] Implement mock data fixtures for testing
- [ ] Create test database setup/teardown utilities
- [ ] Write unit tests for all core models (>80% coverage)
- [ ] Add pytest plugins (pytest-cov, pytest-mock)
- [ ] Document testing approach and patterns

## Technical Decisions

- **Package Manager:** Poetry (for dependency management and packaging)
- **Type Checking:** mypy (strict mode)
- **Linting:** ruff (fast Python linter)
- **Formatting:** black (opinionated code formatter)
- **Testing:** pytest (with coverage plugin)
- **Validation:** Pydantic v2 (data validation and settings)
- **Container Base:** python:3.11-slim (balance of size and compatibility)

## Dependencies

**Core:**
- Python 3.11+
- Pydantic v2
- SQLAlchemy 2.0+

**Development:**
- pytest
- pytest-cov
- pytest-mock
- black
- mypy
- ruff
- pre-commit

## Risks & Mitigations

| Risk                  | Impact | Mitigation                                                    |
|-----------------------|--------|---------------------------------------------------------------|
| Poetry setup issues   | Low    | Provide detailed setup documentation and troubleshooting      |
| Docker build failures | Medium | Test on multiple platforms, document platform-specific issues |
| Type hint complexity  | Low    | Use gradual typing, allow `Any` where needed initially        |

## Deliverables

1. Working Python package in `src/sqlsentinel/`
2. Core models with comprehensive type hints
3. Test suite with >80% coverage
4. Docker container that builds successfully
5. Pre-commit hooks configured for code quality
6. Development setup documentation

## Definition of Done

- [ ] All work items completed
- [ ] All tests passing
- [ ] Code coverage >80%
- [ ] Docker image builds without errors
- [ ] Pre-commit hooks pass locally
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Sprint retrospective completed

## Notes

This sprint establishes the foundation for the entire project. Quality and completeness here will pay dividends throughout development. Focus on getting the structure right rather than rushing to add features.