# SQL Sentinel v0.1.0 Public Alpha Plan

**Version:** 0.1.0
**Status:** All automation and documentation complete. Manual steps remaining below.

---

## Remaining Manual Steps

Everything below requires human action — accounts, credentials, UI clicks, or external tooling. Steps are in dependency order.

---

### Step 1: Configure GitHub Repository

**Time:** 5 minutes

The repo exists at `github.com/kyle-gehring/sql-sentinel`. Configure it for public release:

1. Go to **Settings > General**
   - Set visibility to **Public**
   - Add description: `SQL-first alerting system for data analysts`
2. Go to the repo main page, click the gear icon next to "About"
   - Add topics: `sql`, `alerting`, `monitoring`, `data-quality`, `python`, `ai-first`
3. Merge `sprint-4.2` branch to `master` (or your main branch)

**Verify:** CI pipeline runs on push to master. Check the Actions tab — the `ci.yml` workflow should run test, lint, and security jobs.

---

### Step 2: Create PyPI Account and Publish

**Time:** 20 minutes

#### 2a. Create account and token

1. Register at https://pypi.org/account/register/
2. Go to https://pypi.org/manage/account/token/ and create an API token (scope: entire account for first publish)
3. In the GitHub repo, go to **Settings > Secrets and variables > Actions**
   - Add secret: `PYPI_TOKEN` with your token value

#### 2b. Test on TestPyPI first (recommended)

```bash
# Configure TestPyPI
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi <YOUR_TESTPYPI_TOKEN>

# Build and publish
poetry build
poetry publish --repository testpypi

# Test installation
pip install --index-url https://test.pypi.org/simple/ sqlsentinel
sqlsentinel --version
```

#### 2c. Publish to production PyPI

```bash
poetry config pypi-token.pypi <YOUR_PYPI_TOKEN>
poetry build
poetry publish
```

#### 2d. Verify

```bash
pip install sqlsentinel
sqlsentinel --version
sqlsentinel --help
```

Check that https://pypi.org/project/sqlsentinel/ looks correct.

**Note:** After this, the `publish.yml` GitHub Action will auto-publish on future `v*` tags.

---

### Step 3: Create Docker Hub Account and Configure

**Time:** 15 minutes

1. Register at https://hub.docker.com/
2. Create repository: `sqlsentinel/sqlsentinel`
3. Generate an access token at https://hub.docker.com/settings/security
4. In the GitHub repo, go to **Settings > Secrets and variables > Actions**
   - Add secret: `DOCKERHUB_USERNAME` with your Docker Hub username
   - Add secret: `DOCKERHUB_TOKEN` with your access token

**Note:** The `docker-publish.yml` GitHub Action will automatically build and push multi-platform images (amd64/arm64) on push to main and on `v*` tags. No manual Docker build/push needed.

#### Verify after tag push (Step 5)

```bash
docker pull sqlsentinel/sqlsentinel:latest
docker run --rm sqlsentinel/sqlsentinel:latest --version
```

---

### Step 4: Create Demo GIF (Optional)

**Time:** 30 minutes

Record a terminal demo showing the SQL Sentinel workflow.

#### Install tools

```bash
pip install asciinema
# Install agg: https://github.com/asciinema/agg
cargo install --git https://github.com/asciinema/agg
```

#### Record

```bash
asciinema rec demo.cast
```

**Demo script (30-60 seconds):**
1. `sqlsentinel validate examples/alerts.yaml`
2. `sqlsentinel run examples/alerts.yaml --dry-run`
3. `sqlsentinel run examples/alerts.yaml --alert high_error_rate --dry-run`
4. `sqlsentinel daemon examples/alerts.yaml` (show it starting, then Ctrl+C)

#### Convert and add to README

```bash
agg demo.cast demo.gif --speed 1.5 --theme monokai
# Move to repo and add to README:
# ![Demo](demo.gif)
```

**Alternative:** Use https://terminalizer.com/ for a browser-based approach.

---

### Step 5: Tag Release and Publish

**Time:** 10 minutes

This triggers both the PyPI and Docker publish workflows automatically.

#### 5a. Create the tag

```bash
git tag -a v0.1.0 -m "Initial public alpha release"
git push origin v0.1.0
```

#### 5b. Create GitHub Release

Go to https://github.com/kyle-gehring/sql-sentinel/releases/new

- **Tag:** `v0.1.0`
- **Title:** `SQL Sentinel v0.1.0 - Public Alpha`
- **Body:**

```markdown
First public release of SQL Sentinel, an AI-first SQL alerting system for data analysts.

## Highlights

- Complete SQL-first alerting engine with YAML configuration
- Multi-database support (PostgreSQL, MySQL, SQLite, BigQuery, and more)
- Email, Slack, and webhook notifications
- Cron-based scheduling with daemon mode
- State management and alert deduplication
- Health checks and Prometheus metrics
- AI assistant integration (Claude Code, Copilot, Gemini, Codex, Cursor)
- 92.9% test coverage with 530+ passing tests
- Docker deployment ready

## Installation

**PyPI:**
```bash
pip install sqlsentinel
```

**Docker:**
```bash
docker pull sqlsentinel/sqlsentinel:latest
```

## Quick Start

See the [README](https://github.com/kyle-gehring/sql-sentinel#quick-start-5-minutes) for a 5-minute quickstart guide.

## Known Limitations

- No web UI (use CLI or AI assistants)
- `${VAR}` env var interpolation not supported in config validation

## What's Next (v0.2.0)

- MCP server for enhanced AI integration
- Additional notification channels
- Community-requested features

**Full Changelog**: https://github.com/kyle-gehring/sql-sentinel/blob/main/CHANGELOG.md
```

#### 5c. Verify

- [ ] GitHub release page looks correct
- [ ] PyPI publish workflow triggered and succeeded (check Actions tab)
- [ ] Docker publish workflow triggered and succeeded
- [ ] `pip install sqlsentinel` installs v0.1.0
- [ ] `docker pull sqlsentinel/sqlsentinel:0.1.0` works

---

### Step 6: Launch Announcements (Optional)

**Time:** 30 minutes

Post about the release in relevant communities:

- [ ] Twitter / X
- [ ] LinkedIn
- [ ] r/dataengineering
- [ ] r/python
- [ ] Hacker News (Show HN)
- [ ] Dev.to

---

### Step 7: Post-Launch

- [ ] Monitor GitHub issues for the first week
- [ ] Respond to questions promptly
- [ ] Fix any critical bugs reported
- [ ] Plan v0.2.0 based on feedback

---

## Completed Work Summary

Everything below has been implemented, tested, and committed.

### Day 0: Pre-Launch Validation ✅

- Package builds and installs correctly (56KB wheel)
- All 10 CLI subcommands work
- SQLite end-to-end alert test passes
- Example configs validate (main config; env var interpolation deferred)
- Notification configs validate without SMTP
- Repository cleaned: deprecated files archived, no secrets, no temp files
- Issues found and fixed: `--version` flag, personal email/SMTP in configs

### Day 1: Repository & CI/CD ✅

- `CONTRIBUTING.md` — dev setup, testing, code style, PR process
- `CHANGELOG.md` — v0.1.0 entry, Keep a Changelog format
- `.github/workflows/ci.yml` — test (Python 3.11/3.12), lint (Black/Ruff/mypy), security (pip-audit/Bandit)
- `.github/ISSUE_TEMPLATE/` — bug report and feature request templates
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.pre-commit-config.yaml` — Black, Ruff, mypy, pre-commit-hooks
- `pyproject.toml` — documentation URL added

### Day 2: Publishing Automation ✅

- Package tested locally: builds, installs in fresh venv, all commands work
- `.github/workflows/publish.yml` — auto-publish to PyPI on `v*` tag
- `.github/workflows/docker-publish.yml` — multi-platform Docker Hub images on push/tag

### Day 3: Documentation & AI-First ✅

- `README.md` — complete rewrite with badges, quickstart, CLI reference, AI-first section, examples, doc links
- `docs/ai-workflows.md` — Claude Code usage patterns and examples
- `docs/FAQ.md` — databases, notifications, state management, operations
- `SECURITY.md` — vulnerability reporting, credential management, Docker security
- `examples/README.md` — updated with accurate commands and all examples
- AI assistant instruction files for 5 platforms:
  - `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursorrules`
  - User-copyable templates in `docs/ai-setup/`

### Test Results

- **529 passing**, 1 expected failure (SMTP integration), 21 skipped
- **92.96% coverage** (80% minimum enforced)

---

## Optional: MCP Server (Post-Launch)

**Scope**: Minimal MCP server for installation/setup only (not NL-to-SQL).

**Tools:**
1. `install_sqlsentinel` — Install via pip or Docker
2. `init_project` — Create initial config files
3. `validate_setup` — Check installation and configuration

**Estimate**: 4-6 hours

---

## Success Metrics (Week 1)

| Metric | Target | Stretch |
|--------|--------|---------|
| GitHub stars | 5+ | 10+ |
| PyPI downloads | 10+ | 50+ |
| Docker pulls | 3+ | 10+ |
| External issues/questions | 1+ | 3+ |
| Critical bugs | 0 | 0 |
