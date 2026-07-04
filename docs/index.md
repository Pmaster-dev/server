---
layout: default
title: Home
nav_order: 1
---

# Pmaster-dev / server

Infrastructure and automation layer for the **Pmaster-dev / pinkycollie** ecosystem.

## What's here

| Module | Path | Purpose |
|--------|------|---------|
| Automation engine | `src/automation/` | Serverless Python automation with pluggable components and generator variables |
| Capability profile | `src/automation/profile.py` | Unified platform/motion/accessibility contract |
| Server config | `src/config.py` | Centralized profile resolution (env vars, JSON file, defaults) |
| Platform adapters | `src/adapters/` | Optional per-target input/output adapters (CLI, IDE, web app, OS/frame, embedded) |
| Handoff module | `src/handoff/` | Cross-service handoff coordination |
| Auth utilities | `auth/utils.py` | JWT, bcrypt password hashing, session management |
| OpenAPI contracts | `docs/openapi/` | Machine-readable API contracts consumed by downstream services |

## Getting started

→ [Getting started guide](guides/getting-started)

→ [Configuration convention](guides/configuration)

## API reference

→ [Automation API](api/automation)

## Ecosystem

→ [Cross-org ecosystem inventory](pinkycollie-ecosystem-inventory)

---

*Source: [github.com/Pmaster-dev/server](https://github.com/Pmaster-dev/server)*
