---
layout: default
title: Configuration
nav_order: 4
---

# Configuration convention

This document defines the naming, defaults, and override order for all
server-layer configuration in `Pmaster-dev/server`.  Follow these rules when
adding new settings to keep customisation controlled and standardized.

---

## The capability profile

Every deployment has exactly one **capability profile** — a
`CapabilityProfile` object that is the authoritative source of truth for:

| Field group | What it governs |
|---|---|
| `target` | Deployment platform (`cli`, `ide`, `web_app`, `os_frame`, `embedded`) |
| `motion_stability` | Frame-rate, latency, and jitter budgets for visual/video/sign-language pipelines |
| `accessibility` | Sign-language overlay, visual video, high-contrast, reduced-motion |
| `custom` | Project-specific extension keys |

All modules and components **must** read values from the profile via
`config.get_profile()`.  Do **not** read `os.environ` directly inside
components or automation definitions.

---

## Resolution order

Settings are resolved in the following priority order (first match wins):

1. **Explicit override** — `config.set_profile(profile)` in application startup
   code.  Highest priority; overrides everything else.

2. **JSON config file** — the file at `SERVER_CONFIG_FILE` (env var) or
   `./server_config.json` in the working directory if the env var is absent.
   The file may contain any subset of profile fields; missing fields fall back
   to the platform default.

3. **Environment variable overrides** — individual `SERVER_*` variables (see
   table below) applied on top of whichever base is resolved in step 1–4.

4. **Platform default** — the built-in default profile for the platform named
   in `SERVER_TARGET` (default: `web_app`).

---

## Environment variables

All variables are prefixed with `SERVER_` to avoid collisions.

| Variable | Type | Default | Description |
|---|---|---|---|
| `SERVER_TARGET` | string | `web_app` | Target platform.  One of `cli`, `ide`, `web_app`, `os_frame`, `embedded`. |
| `SERVER_PROFILE_NAME` | string | _(platform default)_ | Override the profile `name` field. |
| `SERVER_MIN_FPS` | float | _(platform default)_ | Override `motion_stability.min_fps`. |
| `SERVER_MAX_LATENCY_MS` | float | _(platform default)_ | Override `motion_stability.max_latency_ms`. |
| `SERVER_JITTER_BUDGET_MS` | float | _(platform default)_ | Override `motion_stability.jitter_budget_ms`. |
| `SERVER_SIGN_LANGUAGE_OVERLAY` | bool† | _(platform default)_ | Enable sign-language overlay. |
| `SERVER_VISUAL_VIDEO_ENABLED` | bool† | _(platform default)_ | Enable visual video output. |
| `SERVER_HIGH_CONTRAST` | bool† | _(platform default)_ | Enable high-contrast mode. |
| `SERVER_REDUCED_MOTION` | bool† | _(platform default)_ | Enable reduced-motion mode. |
| `SERVER_CONFIG_FILE` | path | `./server_config.json` | Path to a JSON config file. |

†  Boolean variables accept `1`/`true`/`yes` (true) or `0`/`false`/`no` (false).
   Values are case-insensitive.

---

## JSON config file format

```json
{
  "name": "prod-web",
  "version": "1.0.0",
  "target": "web_app",
  "motion_stability": {
    "min_fps": 30,
    "max_latency_ms": 80,
    "jitter_budget_ms": 16
  },
  "accessibility": {
    "sign_language_overlay": true,
    "visual_video_enabled": true,
    "high_contrast": false,
    "reduced_motion": false
  },
  "custom": {
    "theme": "dark"
  }
}
```

All fields except `name` and `target` are optional; omitted fields are filled
from the platform default.

---

## Platform defaults

Each target has a built-in default that is suitable for typical deployments of
that type.  Custom profiles should override only the fields they care about.

| Platform | `min_fps` | `max_latency_ms` | `sign_language_overlay` | `visual_video` | `reduced_motion` |
|---|---|---|---|---|---|
| `cli` | 0 | 0 | false | **false** | **true** |
| `ide` | 24 | 100 | false | true | false |
| `web_app` | 30 | 80 | **true** | true | false |
| `os_frame` | 60 | 50 | **true** | true | false |
| `embedded` | 15 | 200 | false | **false** | **true** |

---

## Platform adapters

Each target has a matching `PlatformAdapter` in `src/adapters/`.  Adapters
are **optional** — they only need to be used when a pipeline entry point must
apply platform-specific pre- or post-processing.

```python
from adapters import get_adapter
from automation.profile import TargetPlatform

adapter = get_adapter(TargetPlatform.WEB_APP)
adapted_input = adapter.adapt_input(component_input, profile=profile)
adapted_output = adapter.adapt_output(component_output, profile=profile)
```

Adapters must **not** contain business logic.  They are only responsible for
enriching or stripping metadata so the core engine remains platform-agnostic.

---

## Adding a new configuration key

1. **Check whether the key belongs in an existing group.**  Motion or timing
   values → `MotionStability`.  Accessibility/rendering flags → `AccessibilityFlags`.
   Everything else → `custom`.

2. **If the key belongs in a structured group**, add it to the relevant
   dataclass in `src/automation/profile.py`, add a corresponding env var to
   `src/config.py`, update the OpenAPI schema in
   `docs/openapi/automation.yaml`, and add a test in `tests/test_profile.py`.

3. **If the key is project-specific**, put it in `custom` and document it in
   this file under a project-specific section.  Do not expand the shared
   schema for project-specific concerns.

4. **Never** hard-code a configuration value inside a component.  Always read
   from `config.get_profile()`.

---

## Naming convention

| Scope | Convention | Example |
|---|---|---|
| Environment variable | `SERVER_<SCREAMING_SNAKE_CASE>` | `SERVER_MIN_FPS` |
| JSON config key | `snake_case` | `min_fps` |
| Python field | `snake_case` | `motion_stability.min_fps` |
| Profile name | `<env>-<platform>` (kebab) | `prod-web`, `dev-cli` |
| Adapter class | `<PascalPlatform>Adapter` | `WebAppAdapter` |
