# SQL Sentinel v0.1.0 Public Alpha - 3 Day Plan

**Version:** 0.1.0
**Target Date:** 2025-02-08 (3 days from now)
**Status:** In Planning

---

## Executive Summary

Ship a **production-ready public alpha** in 3 days focused on:
- ✅ PyPI package (`pip install sqlsentinel`)
- ✅ Docker Hub images (`docker pull sqlsentinel/sqlsentinel`)
- ✅ GitHub repository with CI/CD
- ✅ Excellent documentation enabling AI-assisted workflows
- ✅ Optional: Minimal MCP server for installation/setup only

**Strategic Decision**: Focus on **excellent docs** that enable Claude Code to work WITH the existing CLI, rather than building complex NL→SQL conversion. Let analysts use their SQL skills naturally.

---

## Package Name Confirmed ✅

**PyPI Check Results:**
- Package name: `sqlsentinel`
- Status: **AVAILABLE** ✅
- Verified: 2025-02-05

---

## Day 1: Repository & CI/CD Setup

### Morning (4 hours)

#### 1.1 Create GitHub Repository
- [ ] Create repository: `github.com/kyle-gehring/sql-sentinel`
- [ ] Set visibility to **Public**
- [ ] Add description: "SQL-first alerting system for data analysts"
- [ ] Add topics: `sql`, `alerting`, `monitoring`, `data-quality`, `python`, `ai-first`
- [ ] Initialize with existing code (push from local)

#### 1.2 Essential Documentation Files
- [ ] **CONTRIBUTING.md**
  - How to set up development environment
  - How to run tests
  - Code style guidelines
  - PR process
  - Code of Conduct (Contributor Covenant)

- [ ] **CHANGELOG.md**
  - v0.1.0 initial release entry
  - Format: Keep a Changelog standard

- [ ] **.github/ISSUE_TEMPLATE/**
  - `bug_report.md`
  - `feature_request.md`

- [ ] **.github/PULL_REQUEST_TEMPLATE.md**
  - Checklist for PRs
  - Testing requirements
  - Documentation updates

#### 1.3 Update Repository URLs
- [ ] Update `pyproject.toml`:
  - `homepage = "https://github.com/kyle-gehring/sql-sentinel"`
  - `repository = "https://github.com/kyle-gehring/sql-sentinel"`
  - `documentation = "https://github.com/kyle-gehring/sql-sentinel/tree/main/docs"`

### Afternoon (4 hours)

#### 1.4 GitHub Actions CI/CD Pipeline

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install Poetry
      run: |
        curl -sSL https://install.python-poetry.org | python3 -
        echo "$HOME/.local/bin" >> $GITHUB_PATH

    - name: Install dependencies
      run: poetry install

    - name: Run tests with coverage
      run: poetry run pytest --cov=src --cov-report=xml --cov-report=term

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        fail_ci_if_error: false

  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install Poetry
      run: |
        curl -sSL https://install.python-poetry.org | python3 -
        echo "$HOME/.local/bin" >> $GITHUB_PATH

    - name: Install dependencies
      run: poetry install

    - name: Run Black
      run: poetry run black --check src/ tests/

    - name: Run Ruff
      run: poetry run ruff check src/ tests/

    - name: Run mypy
      run: poetry run mypy src/

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install Poetry
      run: |
        curl -sSL https://install.python-poetry.org | python3 -
        echo "$HOME/.local/bin" >> $GITHUB_PATH

    - name: Install dependencies
      run: poetry install

    - name: Run pip-audit
      run: poetry run pip-audit --skip-editable
      continue-on-error: true

    - name: Run Bandit
      run: poetry run bandit -r src/ -ll
      continue-on-error: true
```

#### 1.5 Pre-commit Configuration

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
```

### Day 1 Deliverables Checklist

- [ ] GitHub repository created and public
- [ ] CONTRIBUTING.md complete
- [ ] CHANGELOG.md initialized
- [ ] GitHub Actions CI/CD working
- [ ] Pre-commit hooks configured
- [ ] Issue/PR templates created
- [ ] All URLs updated in pyproject.toml
- [ ] Initial commit pushed with all changes
- [ ] CI pipeline passes (tests, lint, security)

---

## Day 2: PyPI & Docker Publishing

### Morning (4 hours)

#### 2.1 Package Testing (Local)

**Critical**: Test package locally BEFORE publishing to PyPI

```bash
# Step 1: Build the package
cd /workspace
poetry build

# Step 2: Install in a fresh virtualenv
python -m venv /tmp/test-sqlsentinel
source /tmp/test-sqlsentinel/bin/activate
pip install dist/sqlsentinel-*.whl

# Step 3: Verify installation
sqlsentinel --version
sqlsentinel --help

# Step 4: Test with example
cp examples/alerts.yaml /tmp/test-alerts.yaml
sqlsentinel validate /tmp/test-alerts.yaml

# Step 5: Cleanup
deactivate
rm -rf /tmp/test-sqlsentinel
```

**Checklist:**
- [ ] Package builds without errors
- [ ] Package installs in fresh venv
- [ ] CLI command available (`sqlsentinel`)
- [ ] All subcommands work (`validate`, `run`, etc.)
- [ ] Example configs validate successfully
- [ ] No import errors or missing dependencies

#### 2.2 PyPI Publishing

**Prerequisites:**
- [ ] Create PyPI account at https://pypi.org/account/register/
- [ ] Generate API token at https://pypi.org/manage/account/token/
- [ ] Add token to GitHub Secrets: `PYPI_TOKEN`

**Test on TestPyPI first:**

```bash
# Step 1: Publish to TestPyPI
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi <YOUR_TESTPYPI_TOKEN>
poetry publish --repository testpypi

# Step 2: Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ sqlsentinel

# Step 3: Verify it works
sqlsentinel --version
```

**Publish to PyPI (production):**

```bash
# Step 1: Configure PyPI token
poetry config pypi-token.pypi <YOUR_PYPI_TOKEN>

# Step 2: Publish
poetry build
poetry publish

# Step 3: Verify
pip install sqlsentinel
sqlsentinel --version
```

**Checklist:**
- [ ] PyPI account created
- [ ] API token generated
- [ ] Published to TestPyPI successfully
- [ ] Tested installation from TestPyPI
- [ ] Published to PyPI successfully
- [ ] Verified `pip install sqlsentinel` works
- [ ] Package page looks good on pypi.org/project/sqlsentinel

### Afternoon (4 hours)

#### 2.3 Docker Hub Publishing

**Prerequisites:**
- [ ] Create Docker Hub account at https://hub.docker.com/
- [ ] Create repository: `sqlsentinel/sqlsentinel`
- [ ] Generate access token
- [ ] Add token to GitHub Secrets: `DOCKERHUB_TOKEN`

**Create `.github/workflows/docker-publish.yml`:**

```yaml
name: Docker

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: sqlsentinel/sqlsentinel
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Manual Docker build and test:**

```bash
# Step 1: Build locally
docker build -t sqlsentinel/sqlsentinel:test .

# Step 2: Test the image
docker run --rm sqlsentinel/sqlsentinel:test sqlsentinel --version
docker run --rm sqlsentinel/sqlsentinel:test sqlsentinel --help

# Step 3: Test with example config
docker run --rm \
  -v $(pwd)/examples/alerts.yaml:/app/alerts.yaml \
  sqlsentinel/sqlsentinel:test \
  sqlsentinel validate /app/alerts.yaml

# Step 4: Tag and push
docker tag sqlsentinel/sqlsentinel:test sqlsentinel/sqlsentinel:latest
docker tag sqlsentinel/sqlsentinel:test sqlsentinel/sqlsentinel:0.1.0
docker push sqlsentinel/sqlsentinel:latest
docker push sqlsentinel/sqlsentinel:0.1.0
```

**Checklist:**
- [ ] Docker Hub account created
- [ ] Repository created on Docker Hub
- [ ] GitHub Actions workflow for Docker created
- [ ] Multi-platform images built (amd64, arm64)
- [ ] Images pushed to Docker Hub
- [ ] `docker pull sqlsentinel/sqlsentinel` works
- [ ] Docker image tested with example config
- [ ] README updated with Docker instructions

### Day 2 Deliverables Checklist

- [ ] Package published to PyPI
- [ ] `pip install sqlsentinel` works globally
- [ ] Docker images on Docker Hub
- [ ] `docker pull sqlsentinel/sqlsentinel` works
- [ ] Both installation methods tested on clean system
- [ ] README updated with installation instructions

---

## Day 3: Documentation & Launch

### Morning (4 hours)

#### 3.1 Enhanced README

Update README.md with:

**New Sections:**
- [ ] **Badges** (CI status, PyPI version, Docker pulls, coverage, license)
- [ ] **Quick Demo** (animated GIF showing CLI workflow)
- [ ] **Installation** (both pip and Docker, tested)
- [ ] **5-Minute Quickstart** (simplified, works out-of-the-box)
- [ ] **AI-First Positioning** (new section on Claude Code usage)

**Example AI-First Section:**

```markdown
## AI-First Design

SQL Sentinel is designed to work naturally with AI coding assistants like Claude Code.

### Creating Alerts with Claude Code

Instead of writing YAML by hand, just describe what you want:

**You:** "I need an alert that checks if yesterday's revenue is below $10,000. Send me an email at john@company.com every morning at 9 AM."

**Claude Code will:**
1. Generate the SQL query for your database
2. Create the YAML configuration
3. Set up the schedule
4. Test the database connection
5. Validate the alert

### Example Conversation

> **You:** "Create a data quality alert for missing email addresses in the customers table"
>
> **Claude:** "I'll create an alert that checks for NULL emails. What threshold percentage should trigger the alert?"
>
> **You:** "Alert if more than 5% are missing"
>
> **Claude:** [Generates complete YAML config with SQL query]

### Common AI Tasks

- "Show me all my configured alerts"
- "Test the daily_revenue alert without sending notifications"
- "Silence the inventory_low alert for 2 hours"
- "What was the last execution result for my data quality alerts?"
- "Create an alert for [business metric]"

All of these work naturally with Claude Code - no MCP server required!
```

#### 3.2 Demo GIF Creation

**Tool:** Use `asciinema` + `agg` for terminal recording

```bash
# Install tools
pip install asciinema
cargo install --git https://github.com/asciinema/agg

# Record demo
asciinema rec demo.cast

# Convert to GIF
agg demo.cast demo.gif --speed 1.5 --theme monokai

# Or use https://terminalizer.com/
```

**Demo Script (30-60 seconds):**
1. Show: `pip install sqlsentinel` (or skip, assume installed)
2. Show: Create simple `alerts.yaml` file
3. Run: `sqlsentinel validate alerts.yaml` ✅
4. Run: `sqlsentinel run alerts.yaml "Daily Revenue" --dry-run`
5. Show: Alert triggered with notification preview
6. Run: `sqlsentinel daemon alerts.yaml` (show it starting)

**Checklist:**
- [ ] Terminal recording created
- [ ] GIF exported (< 5MB)
- [ ] GIF added to README
- [ ] Demo is clear and compelling

#### 3.3 AI-Optimized Documentation

Create `docs/ai-workflows.md`:

**Content:**
- How Claude Code can help with SQL Sentinel
- Common prompt patterns
- Example conversations
- Troubleshooting with AI
- Best practices for AI-assisted alert management

**Key Sections:**
- Getting Started with Claude Code
- Creating Alerts via Conversation
- Managing Existing Alerts
- Debugging and Troubleshooting
- Advanced Patterns

### Afternoon (4 hours)

#### 3.4 Additional Documentation

**Create/Enhance:**

- [ ] **FAQ.md** - Common questions
  - Why SQL Sentinel vs [alternative]?
  - What databases are supported?
  - How do I configure notifications?
  - How does state management work?
  - Is there a Web UI?

- [ ] **ARCHITECTURE.md** - System design
  - Component diagram
  - Data flow
  - State management
  - Deployment models

- [ ] **SECURITY.md** - Security considerations
  - Credential management
  - SQL injection prevention
  - Network security
  - Audit logging

- [ ] **examples/README.md** - Example walkthrough
  - Explain each example
  - How to customize
  - Common patterns

#### 3.5 Create GitHub Release

**Prepare v0.1.0 Release:**

```bash
# Create git tag
git tag -a v0.1.0 -m "Initial public alpha release"
git push origin v0.1.0
```

**Release Notes Template:**

```markdown
# SQL Sentinel v0.1.0 - Public Alpha 🎉

First public release of SQL Sentinel, an AI-first SQL alerting system for data analysts.

## What's New

- ✅ Complete SQL-first alerting engine
- ✅ Multi-database support (PostgreSQL, MySQL, SQLite, BigQuery, etc.)
- ✅ Email, Slack, and Webhook notifications
- ✅ Cron-based scheduling with daemon mode
- ✅ State management and alert deduplication
- ✅ Health checks and Prometheus metrics
- ✅ 92.9% test coverage (530 passing tests)
- ✅ Docker deployment ready
- ✅ AI-friendly CLI design

## Installation

### PyPI
```bash
pip install sqlsentinel
```

### Docker
```bash
docker pull sqlsentinel/sqlsentinel:latest
```

## Quick Start

[Link to README quickstart section]

## AI-First Design

SQL Sentinel works naturally with AI coding assistants like Claude Code. [Learn more](docs/ai-workflows.md)

## Known Limitations

- Web UI not included (use CLI or AI assistants)
- Advanced multi-cloud features coming in v0.2.0

## Security

- 1 low-severity CVE in dev dependency (Black) - no production impact
- All security scans documented in [security report](docs/security/)

## Contributors

- Kyle Gehring (@kyle-gehring)

## What's Next (v0.2.0)

- MCP server for enhanced Claude Code integration
- Additional notification channels
- Performance optimizations
- Community-requested features

---

**Full Changelog**: https://github.com/kyle-gehring/sql-sentinel/blob/main/CHANGELOG.md
```

#### 3.6 Launch Checklist

**Pre-Launch:**
- [ ] All tests passing in CI
- [ ] PyPI package works
- [ ] Docker images work
- [ ] Documentation complete
- [ ] Demo GIF in README
- [ ] GitHub release created
- [ ] LICENSE file present
- [ ] Code of Conduct included

**Launch:**
- [ ] Tweet/LinkedIn post announcing launch
- [ ] Share in relevant communities (optional):
  - r/dataengineering
  - r/python
  - Hacker News
  - Dev.to
  - LinkedIn

**Post-Launch:**
- [ ] Monitor GitHub issues
- [ ] Respond to questions
- [ ] Fix any critical bugs
- [ ] Plan v0.2.0 features

### Day 3 Deliverables Checklist

- [ ] README enhanced with badges, demo GIF, AI-first section
- [ ] Demo GIF created and compelling
- [ ] AI workflows documentation complete
- [ ] FAQ, Architecture, Security docs created
- [ ] GitHub release v0.1.0 published
- [ ] Launch announcement posted
- [ ] All links working
- [ ] Repository looks professional

---

## Optional: Minimal MCP Server (Post Day 3)

**Scope**: Handle installation/setup ONLY (not NL→SQL conversion)

**Purpose**: Help analysts get started without wrestling with Python environments

### MCP Server Capabilities (Minimal)

**Tool 1: Install SQL Sentinel**
```json
{
  "name": "install_sqlsentinel",
  "description": "Install SQL Sentinel and dependencies",
  "input": {
    "method": "pip|docker"
  }
}
```

**Tool 2: Initialize Project**
```json
{
  "name": "init_project",
  "description": "Create initial config files and directory structure",
  "input": {
    "project_path": "/path/to/project",
    "database_type": "postgresql|mysql|bigquery"
  }
}
```

**Tool 3: Validate Setup**
```json
{
  "name": "validate_setup",
  "description": "Check that SQL Sentinel is installed and configured correctly",
  "input": {}
}
```

### Why This Is Useful

**Problem**: Analysts get stuck on:
- Python environment setup
- Installing dependencies
- Creating initial config structure
- Database connection strings

**Solution**: MCP server handles these setup tasks, then analysts use:
- Claude Code for SQL query generation (natural language → SQL)
- SQL Sentinel CLI for execution
- Their existing SQL skills for alert logic

### Implementation Time

**Estimate**: 4-6 hours (optional Day 4)

**Tech Stack**: Python MCP SDK

**Deliverables**:
- [ ] MCP server for setup tasks
- [ ] Installation guide
- [ ] Basic tests

---

## Success Criteria

### v0.1.0 Public Alpha Must-Haves

**Technical:**
- [x] Package name available on PyPI ✅
- [ ] `pip install sqlsentinel` works
- [ ] `docker pull sqlsentinel/sqlsentinel` works
- [ ] All tests passing in CI (92.9% coverage maintained)
- [ ] Security scans documented (acceptable risk profile)

**Documentation:**
- [ ] Professional README with demo
- [ ] Clear installation instructions
- [ ] Quick start guide (< 10 minutes)
- [ ] AI workflows documented
- [ ] Contributing guidelines

**Repository:**
- [ ] GitHub repository public
- [ ] CI/CD pipeline working
- [ ] Issue/PR templates
- [ ] License file (MIT)
- [ ] Code of Conduct

**Launch:**
- [ ] v0.1.0 release published
- [ ] Announcement posted
- [ ] Links all working

### Success Metrics (Week 1)

**Realistic Goals:**
- [ ] 5+ GitHub stars
- [ ] 10+ PyPI downloads
- [ ] 3+ Docker pulls
- [ ] 1+ quality issue/question from external user
- [ ] 0 critical bugs reported

**Stretch Goals:**
- 10+ GitHub stars
- 50+ PyPI downloads
- 1+ external contributor
- Featured on Python Weekly / Data Engineering newsletter

---

## Timeline

| Day | Morning (4h) | Afternoon (4h) | Evening (optional) |
|-----|--------------|----------------|-------------------|
| **Day 1** | GitHub setup, CONTRIBUTING.md, CHANGELOG.md | GitHub Actions CI/CD, pre-commit hooks | Review CI results |
| **Day 2** | Package testing, TestPyPI, PyPI publish | Docker Hub setup, multi-platform builds | Test installations |
| **Day 3** | README enhancements, demo GIF, AI docs | FAQ/Architecture/Security docs, GitHub release | Launch announcements |

**Total: 24 hours active work over 3 days**

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| PyPI publishing fails | Test with TestPyPI first |
| Docker build fails | Test multi-platform locally before pushing |
| CI pipeline breaks | Set up on feature branch first |
| Package has missing dependencies | Test in fresh virtualenv |
| Demo GIF unclear | Get feedback before publishing |
| Documentation gaps | Use AI workflows doc as template |

---

## Day 4+ (Optional - MCP Server)

If time permits after successful v0.1.0 launch:

**Focus**: Minimal MCP server for installation/setup

**Deliverables**:
- [ ] Python MCP server implementation
- [ ] 3 tools: install, init, validate
- [ ] Installation guide
- [ ] Update AI workflows docs
- [ ] Test with Claude Code

**Timeline**: 4-6 hours

---

## Checklist: Ready to Start?

**Prerequisites:**
- [ ] GitHub account ready
- [ ] PyPI account created (or will create on Day 2)
- [ ] Docker Hub account created (or will create on Day 2)
- [ ] Local development environment working
- [ ] All 530 tests passing locally
- [ ] Code committed and clean working directory

**Day 1 Ready:**
- [ ] Plan reviewed and approved
- [ ] Time allocated (8 hours)
- [ ] Coffee/energy drinks stocked ☕

---

**Prepared by:** Claude Code
**Date:** 2025-02-05
**Status:** Ready to Execute

**Next Step:** Begin Day 1 - Create GitHub repository and CI/CD pipeline

---

## Quick Reference Commands

```bash
# Check package name availability
pip index versions sqlsentinel

# Build package locally
poetry build

# Test package in fresh venv
python -m venv /tmp/test && source /tmp/test/bin/activate
pip install dist/sqlsentinel-*.whl
sqlsentinel --version

# Publish to TestPyPI
poetry publish --repository testpypi

# Publish to PyPI
poetry publish

# Build Docker image
docker build -t sqlsentinel/sqlsentinel:latest .

# Test Docker image
docker run --rm sqlsentinel/sqlsentinel:latest sqlsentinel --version

# Create git tag
git tag -a v0.1.0 -m "Initial public alpha release"
git push origin v0.1.0
```
