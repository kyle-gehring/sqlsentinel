# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SQL Sentinel is an open-source, lightweight SQL-first alerting system that enables data analysts to monitor business metrics and data quality using only SQL queries. The system allows users to define alerts through YAML configuration files, execute SQL queries on a schedule, and receive notifications when specified conditions are met.

## Architecture

This is a **greenfield project** - currently only documentation exists. The system will be implemented with the following architecture:

### Core Components
- **Configuration Layer**: YAML-based alert definitions
- **Alert Engine**: Scheduler, Executor, and Evaluator components
- **Database Adapters**: SQLAlchemy-based adapters for multiple database types
- **Notification System**: Multi-channel notification delivery
- **State Management**: Minimal state tracking to prevent duplicate alerts

### Technology Stack
- **Language**: Python (for SQL ecosystem and analyst familiarity)
- **Configuration**: YAML files
- **Database**: SQLAlchemy for multi-database support
- **Deployment**: Docker-first approach
- **Scheduling**: Cron-based scheduling system

## Development Setup

Since this is a new project, there are no existing build commands. The development environment is configured for:

- DevContainer with Python development environment
- VS Code with ESLint, Prettier, and Claude Code extensions
- Zsh terminal with Git support

## Key Implementation Guidelines

### Alert Query Contract
All alert queries must return a result set with:
- **Required**: `status` column with values 'ALERT' or 'OK'
- **Optional**: `actual_value` - the metric value that triggered the alert
- **Optional**: `threshold` - the threshold that was exceeded
- **Optional**: Additional columns for context in notifications

### Supported Data Platforms (Target)
- **Cloud Data Warehouses**: BigQuery, Snowflake, Redshift, Synapse Analytics
- **Traditional Databases**: PostgreSQL, MySQL/MariaDB, Microsoft SQL Server
- **Local/Development**: SQLite, DuckDB
- **Cloud Analytics**: Athena, Azure Data Explorer

### Configuration Example
```yaml
alerts:
  - name: "Low Daily Revenue"
    description: "Alert when yesterday's revenue falls below threshold"
    query: |
      SELECT 
        CASE WHEN SUM(revenue) < 10000 THEN 'ALERT' ELSE 'OK' END as status,
        SUM(revenue) as actual_value,
        10000 as threshold
      FROM orders 
      WHERE date = CURRENT_DATE - 1
    schedule: "0 9 * * *"
    notify:
      - channel: email
        recipients: ["team@company.com"]
```

## Implementation Phases

### Phase 1: MVP
- Basic YAML configuration parser
- PostgreSQL support only
- Simple cron scheduling
- Email notifications only
- Docker container

### Phase 2: Core Features
- Multiple database support via SQLAlchemy
- Slack and webhook notifications
- State tracking (prevent duplicate alerts)
- Error handling and retries
- Cloud storage support

### Phase 3: Production Ready
- Web UI for configuration
- Alert history and analytics
- Multiple notification channels
- Terraform modules and Helm charts

## Design Principles

1. **SQL-First**: No proprietary query language or complex DSL
2. **Lightweight**: Minimal resource requirements
3. **GitOps Friendly**: Configuration as code
4. **Cloud Agnostic**: Runs anywhere Docker runs
5. **Analyst Focused**: Built for SQL users, not developers

## Quick Start Target

The system should enable a data analyst with only SQL knowledge to successfully deploy and use it within 15 minutes.

**Local Development:**
```bash
docker run -d \
  -v $(pwd)/alerts.yaml:/config/alerts.yaml \
  -e DATABASE_URL="postgresql://user:pass@host/db" \
  sqlsentinel/sqlsentinel:latest
```

**Cloud Deployment (Any Platform):**
```bash
# Choose your platform
./scripts/deploy-gcp.sh --project=YOUR-PROJECT        # Google Cloud
./scripts/deploy-aws.sh --cluster=YOUR-CLUSTER       # AWS  
./scripts/deploy-azure.sh --workspace=YOUR-WORKSPACE # Azure
./scripts/deploy-snowflake.sh --account=YOUR-ACCOUNT # Snowflake
```