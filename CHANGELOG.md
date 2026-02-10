# Changelog

All notable changes to SQL Sentinel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-02-09

### Added

- SQL-first alerting engine with YAML configuration
- Multi-database support via SQLAlchemy (PostgreSQL, MySQL, SQLite, BigQuery, and more)
- Cron-based scheduling with daemon mode
- Email, Slack, and webhook notification channels
- Alert state management with deduplication
- Alert silencing and unsilencing
- Dry-run mode for testing alerts without sending notifications
- Health check endpoint for monitoring
- Prometheus metrics export
- CLI with 10 subcommands: `validate`, `run`, `daemon`, `history`, `healthcheck`, `metrics`, `silence`, `unsilence`, `status`, `init`
- Docker support with multi-platform images
- 92.9% test coverage with 530+ passing tests

[Unreleased]: https://github.com/kyle-gehring/sqlsentinel/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kyle-gehring/sqlsentinel/releases/tag/v0.1.0
