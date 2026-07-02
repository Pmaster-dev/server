---
layout: default
title: Automation API
nav_order: 3
---

# Automation API

The Automation API exposes the engine over HTTP. Machine-readable contract: [`openapi/automation.yaml`](../openapi/automation.yaml).

## Base URL

The base URL is resolved per deployment environment (see `servers` block in the OpenAPI spec).

---

## Trigger an event

**`POST /automation/events/trigger`**

Triggers all enabled automations that listen to the given event type.

### Request body

```json
{
  "event_type": "user.request",
  "payload": { "key": "value" },
  "metadata": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_type` | string | ✅ | The event name to match against automation triggers |
| `payload` | object | | Arbitrary payload forwarded to each automation step |
| `metadata` | object | | Optional metadata attached to the run record |

### Response `200`

```json
{
  "runs": [
    {
      "run_id": "abc123",
      "trigger": {
        "event_type": "user.request",
        "event_id": "evt-001",
        "timestamp": "2026-07-01T00:00:00Z"
      },
      "status": "success",
      "outputs": [
        {
          "component": "greet",
          "success": true,
          "result": "Hello, world!",
          "error": null,
          "metadata": {}
        }
      ],
      "started_at": "2026-07-01T00:00:00Z",
      "finished_at": "2026-07-01T00:00:00.010Z",
      "duration_ms": 10
    }
  ]
}
```

---

## List automation definitions

**`GET /automation/definitions`**

Returns all registered automation definitions.

### Response `200`

```json
{
  "definitions": [
    {
      "name": "greet_on_request",
      "triggers": ["user.request"],
      "steps": ["greet"],
      "variables": [],
      "description": "",
      "enabled": true
    }
  ]
}
```

---

## Create or replace a definition

**`PUT /automation/definitions/{name}`**

Upserts an automation definition by name.

### Path parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Unique automation name |

### Request body

```json
{
  "name": "greet_on_request",
  "triggers": ["user.request"],
  "steps": ["greet"],
  "variables": ["request_id"],
  "description": "Greet users on request",
  "enabled": true
}
```

### Response `200` — definition stored

---

## Delete a definition

**`DELETE /automation/definitions/{name}`**

Removes a definition.

### Responses

| Status | Description |
|--------|-------------|
| `204` | Deleted |
| `404` | Not found |

---

## Enable / Disable a definition

**`POST /automation/definitions/{name}/enable`**  
**`POST /automation/definitions/{name}/disable`**

Both return `204` on success.

---

## List run history

**`GET /automation/runs?limit=50`**

Returns past run records, newest first.

| Query param | Type | Default | Max |
|-------------|------|---------|-----|
| `limit` | integer | 50 | 1000 |

---

## Aggregate stats

**`GET /automation/stats`**

```json
{
  "total_runs": 142,
  "automations": 5,
  "components": 12,
  "variables": 3,
  "by_status": {
    "success": 138,
    "failed": 4
  }
}
```

---

## Status values

| Value | Description |
|-------|-------------|
| `pending` | Queued, not yet started |
| `running` | Currently executing |
| `success` | All steps completed successfully |
| `failed` | One or more steps errored |
| `skipped` | Automation was disabled at trigger time |
