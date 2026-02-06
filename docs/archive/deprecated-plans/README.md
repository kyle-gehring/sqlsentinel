# Deprecated Plans Archive

This directory contains historical planning documents that are **no longer active** but preserved for reference.

## Archived Documents

### IMPLEMENTATION_ROADMAP.md
**Date:** 2025-01-XX
**Status:** Superseded

Original 12-week implementation roadmap that included:
- Full React Web UI (Sprints 9-12)
- Multi-cloud Terraform modules for AWS/Azure (Sprints 5-8)
- REST API with authentication
- Enterprise features (SSO, RBAC, multi-tenancy)

**Why Deprecated:** Strategic pivot to AI-first approach eliminated need for Web UI and multi-cloud complexity. Focus shifted to Claude Code integration and excellent documentation.

**Replaced By:** [PUBLIC_ALPHA_PLAN.md](../../PUBLIC_ALPHA_PLAN.md)

### AI_FIRST_ROADMAP.md
**Date:** 2025-02-05
**Status:** Superseded

7-day AI-first roadmap that included:
- Complex MCP server with natural language → SQL conversion
- Full AI-optimized documentation suite
- Video production
- Advanced telemetry and observability

**Why Deprecated:** Scope was too ambitious for initial release. Revised to focus on core public release (PyPI + Docker + docs) with optional minimal MCP server.

**Replaced By:** [PUBLIC_ALPHA_PLAN.md](../../PUBLIC_ALPHA_PLAN.md)

---

## Current Active Plan

**See:** [docs/PUBLIC_ALPHA_PLAN.md](../../PUBLIC_ALPHA_PLAN.md)

**Scope:** 3-day public alpha release focused on:
- PyPI package publication
- Docker Hub images
- GitHub repository with CI/CD
- Excellent documentation for AI-assisted workflows
- Optional minimal MCP server for installation/setup only

**Target:** v0.1.0 Public Alpha

---

## Historical Context

These documents represent the evolution of SQL Sentinel's scope:

1. **Original Vision** (IMPLEMENTATION_ROADMAP.md): Full-featured enterprise product with Web UI
2. **AI-First Pivot** (AI_FIRST_ROADMAP.md): Recognition that AI assistants could replace GUI
3. **Focused MVP** (PUBLIC_ALPHA_PLAN.md): Ship core value quickly, iterate based on feedback

The final approach reflects lean startup principles: validate the core product before investing in advanced features.

---

**Last Updated:** 2025-02-05
