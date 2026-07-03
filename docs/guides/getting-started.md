---
layout: default
title: Getting Started
nav_order: 2
---

# Getting Started

## Prerequisites

- Python 3.11+
- pip

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/Pmaster-dev/server.git
cd server
pip install -r requirements.txt
```

## Using the automation engine

The `src/automation` package is a self-contained, serverless automation engine. Set `PYTHONPATH=src` so Python can locate it without installing it as a package.

```bash
export PYTHONPATH=src
```

### Define and trigger an automation

```python
from automation import AutomationEngine, AutomationDefinition

engine = AutomationEngine()

# 1. Register a component function
engine.register_fn("greet", lambda inp: f"Hello, {inp.payload}!")

# 2. Define an automation that fires on the "user.request" event
engine.define(AutomationDefinition(
    name="greet_on_request",
    triggers=["user.request"],
    steps=["greet"],
))

# 3. Trigger the event
results = engine.trigger_type("user.request", payload="world")
print(results[0].status)   # RunStatus.SUCCESS
print(results[0].outputs[0].result)  # Hello, world!
```

### Generator variables

Variables inject dynamic, lazily-evaluated values into components at runtime.

```python
from automation import AutomationEngine, AutomationDefinition

engine = AutomationEngine()

# Define a generator variable (values are pulled on demand)
engine.define_variable("request_id", lambda: (f"req-{i}" for i in range(9999)))

engine.register_fn("log", lambda inp: f"Processing {inp.variables['request_id']}")

engine.define(AutomationDefinition(
    name="log_request",
    triggers=["api.call"],
    steps=["log"],
    variables=["request_id"],
))

results = engine.trigger_type("api.call")
print(results[0].outputs[0].result)  # Processing req-0
```

### Enable / disable automations

```python
engine.disable("greet_on_request")
engine.enable("greet_on_request")
```

## Auth utilities

The `auth/utils.py` module provides JWT token creation/verification, bcrypt password hashing, and session helpers. It depends on Flask and `flask-jwt-extended`.

```python
from auth.utils import PasswordUtils, JWTUtils

hashed = PasswordUtils.hash_password("supersecret")
assert PasswordUtils.verify_password("supersecret", hashed)

access_token, refresh_token = JWTUtils.create_tokens("user-123", "alice")
payload = JWTUtils.decode_token(access_token)
print(payload["username"])  # alice
```

> **Note**: Set the `JWT_SECRET_KEY` environment variable in production. The default value is insecure.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET_KEY` | Yes (prod) | Secret key used to sign JWT tokens |
| `REDIS_URL` | Yes (prod) | Redis connection URL for session caching |

## Running type checks

```bash
pip install pyre-check
pyre --source-directory src --source-directory auth check
```
