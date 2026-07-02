# Pmaster-dev / server

Infrastructure and automation layer for the **Pmaster-dev** + **pinkycollie** ecosystem.

## What's in here

| Path | Description |
|---|---|
| `src/automation/` | Serverless Python automation engine (components, variables, event dispatch) |
| `docs/openapi/automation.yaml` | OpenAPI 3.1 contract for the Automation REST API |
| `docs/pinkycollie-ecosystem-inventory.md` | Cross-org architecture map |
| `auth/` | Auth utilities |
| `types/` | Shared type definitions |
| `spec/` | Specs and helpers |

## Quick start

```python
from automation import AutomationEngine, AutomationDefinition, TriggerEvent

engine = AutomationEngine()

# Register a component
engine.register_fn("greet", lambda inp: f"Hello, {inp.payload}!")

# Define an automation
engine.define(AutomationDefinition(
    name="greet_on_request",
    triggers=["user.request"],
    steps=["greet"],
))

# Fire an event
results = engine.trigger_type("user.request", payload="world")
print(results[0].status)   # RunStatus.SUCCESS
```

Run with the `src` layout on `PYTHONPATH`:

```bash
PYTHONPATH=src python your_script.py
```

## Automation API

The REST contract lives at [`docs/openapi/automation.yaml`](docs/openapi/automation.yaml).

Key endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/automation/events/trigger` | Trigger automation runs for an event |
| `GET` | `/automation/definitions` | List automation definitions |
| `PUT` | `/automation/definitions/{name}` | Create or replace a definition |
| `DELETE` | `/automation/definitions/{name}` | Remove a definition |
| `POST` | `/automation/definitions/{name}/enable` | Enable a definition |
| `POST` | `/automation/definitions/{name}/disable` | Disable a definition |
| `GET` | `/automation/runs` | List run history |
| `GET` | `/automation/stats` | Get aggregate run statistics |

## Ecosystem

This repo is the infrastructure layer of a two-org ecosystem. See [`docs/pinkycollie-ecosystem-inventory.md`](docs/pinkycollie-ecosystem-inventory.md) for the full cross-org architecture.
