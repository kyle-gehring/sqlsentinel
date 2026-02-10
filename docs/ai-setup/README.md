# AI Assistant Setup for SQL Sentinel

These template files help AI coding assistants (Claude Code, GitHub Copilot, Cursor) understand SQL Sentinel when working in **your project**.

## Why?

When you `pip install sqlsentinel` and use it in your own project, your AI assistant doesn't automatically know about SQL Sentinel's config format, CLI commands, or query contract. Dropping one of these files into your project gives the AI that context.

## Setup

Copy the file for your AI assistant into your project root:

### Claude Code

```bash
cp CLAUDE.md /path/to/your/project/CLAUDE.md
```

Claude Code automatically reads `CLAUDE.md` from any directory it works in.

### GitHub Copilot

```bash
mkdir -p /path/to/your/project/.github
cp copilot-instructions.md /path/to/your/project/.github/copilot-instructions.md
```

### Cursor

```bash
cp .cursorrules /path/to/your/project/.cursorrules
```

## What's Included

Each template tells the AI assistant:

- What SQL Sentinel is and how it works
- The YAML config structure (database URL, alerts, schedules, notifications)
- The query contract (`status` column returning `'ALERT'` or `'OK'`)
- All CLI commands and their flags
- Supported databases and notification channels
- How to create, test, and validate alerts step by step

## Customizing

Feel free to edit the templates after copying. You might want to add:

- Your specific database type and connection details
- Team notification preferences
- Project-specific alert patterns
- Internal conventions for alert naming or scheduling
