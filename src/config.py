"""
Centralized server configuration for the Pmaster-dev server layer.

All modules read configuration from :func:`get_profile` rather than querying
environment variables ad-hoc.  This guarantees a single normalized
:class:`~automation.profile.CapabilityProfile` is used everywhere.

Resolution order (first match wins):

1. An explicit profile supplied via :func:`set_profile`.
2. A JSON config file at the path given by the ``SERVER_CONFIG_FILE``
   environment variable.
3. A JSON config file at ``./server_config.json`` in the working directory.
4. Environment-variable overrides applied to the built-in platform default.
5. The built-in default profile for the platform named in ``SERVER_TARGET``
   (default: ``"web_app"``).

Environment variables
---------------------

``SERVER_TARGET``
    Target platform name.  One of ``cli``, ``ide``, ``web_app``,
    ``os_frame``, ``embedded``.  Default: ``web_app``.

``SERVER_PROFILE_NAME``
    Override the profile ``name`` field.

``SERVER_MIN_FPS``
    Override ``motion_stability.min_fps``.

``SERVER_MAX_LATENCY_MS``
    Override ``motion_stability.max_latency_ms``.

``SERVER_JITTER_BUDGET_MS``
    Override ``motion_stability.jitter_budget_ms``.

``SERVER_SIGN_LANGUAGE_OVERLAY``
    ``"1"`` / ``"true"`` / ``"yes"`` to enable sign-language overlay.

``SERVER_VISUAL_VIDEO_ENABLED``
    ``"0"`` / ``"false"`` / ``"no"`` to disable visual video.

``SERVER_HIGH_CONTRAST``
    ``"1"`` / ``"true"`` / ``"yes"`` to enable high-contrast mode.

``SERVER_REDUCED_MOTION``
    ``"1"`` / ``"true"`` / ``"yes"`` to enable reduced-motion mode.

``SERVER_CONFIG_FILE``
    Absolute or relative path to a JSON file that can contain any subset of
    the :class:`~automation.profile.CapabilityProfile` fields.

Usage::

    from config import get_profile

    profile = get_profile()
    if profile.accessibility.sign_language_overlay:
        ...
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from automation.profile import (
    AccessibilityFlags,
    CapabilityProfile,
    MotionStability,
    TargetPlatform,
    default_profile,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level override (set_profile / get_profile)
# ---------------------------------------------------------------------------

_override_profile: Optional[CapabilityProfile] = None


def set_profile(profile: CapabilityProfile) -> None:
    """
    Set an explicit profile that overrides all other resolution sources.

    Call this at application startup before any module reads the profile.
    Useful for testing and for deployments that construct the profile
    programmatically.
    """
    global _override_profile
    _override_profile = profile


def clear_profile() -> None:
    """Clear the explicit override and fall back to automatic resolution."""
    global _override_profile
    _override_profile = None


# ---------------------------------------------------------------------------
# Boolean env-var helper
# ---------------------------------------------------------------------------

def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes"}


# ---------------------------------------------------------------------------
# Profile resolution
# ---------------------------------------------------------------------------

def _load_from_file(path: str) -> Optional[dict]:
    """Load a JSON config dict from *path*, or return ``None`` on failure."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except Exception as exc:
        logger.warning("Could not load server config from %s: %s", path, exc)
        return None


def _apply_env_overrides(profile: CapabilityProfile) -> CapabilityProfile:
    """
    Return a new :class:`CapabilityProfile` with any relevant environment
    variable overrides applied.
    """
    name = os.environ.get("SERVER_PROFILE_NAME", profile.name)

    min_fps = profile.motion_stability.min_fps
    max_latency_ms = profile.motion_stability.max_latency_ms
    jitter_budget_ms = profile.motion_stability.jitter_budget_ms

    if "SERVER_MIN_FPS" in os.environ:
        min_fps = float(os.environ["SERVER_MIN_FPS"])
    if "SERVER_MAX_LATENCY_MS" in os.environ:
        max_latency_ms = float(os.environ["SERVER_MAX_LATENCY_MS"])
    if "SERVER_JITTER_BUDGET_MS" in os.environ:
        jitter_budget_ms = float(os.environ["SERVER_JITTER_BUDGET_MS"])

    sign_language_overlay = _env_bool(
        "SERVER_SIGN_LANGUAGE_OVERLAY",
        profile.accessibility.sign_language_overlay,
    )
    visual_video_enabled = _env_bool(
        "SERVER_VISUAL_VIDEO_ENABLED",
        profile.accessibility.visual_video_enabled,
    )
    high_contrast = _env_bool(
        "SERVER_HIGH_CONTRAST",
        profile.accessibility.high_contrast,
    )
    reduced_motion = _env_bool(
        "SERVER_REDUCED_MOTION",
        profile.accessibility.reduced_motion,
    )

    return CapabilityProfile(
        name=name,
        version=profile.version,
        target=profile.target,
        motion_stability=MotionStability(
            min_fps=min_fps,
            max_latency_ms=max_latency_ms,
            jitter_budget_ms=jitter_budget_ms,
        ),
        accessibility=AccessibilityFlags(
            sign_language_overlay=sign_language_overlay,
            visual_video_enabled=visual_video_enabled,
            high_contrast=high_contrast,
            reduced_motion=reduced_motion,
        ),
        custom=profile.custom,
    )


def get_profile() -> CapabilityProfile:
    """
    Return the active :class:`~automation.profile.CapabilityProfile`.

    Resolution order:

    1. Explicit override set via :func:`set_profile`.
    2. JSON config file (``SERVER_CONFIG_FILE`` env var, then
       ``./server_config.json``).
    3. Env-var overrides applied to the built-in platform default.
    4. Built-in default for the current ``SERVER_TARGET``.
    """
    if _override_profile is not None:
        return _override_profile

    # --- Try config file ---
    config_path = os.environ.get(
        "SERVER_CONFIG_FILE",
        str(Path.cwd() / "server_config.json"),
    )
    file_data = _load_from_file(config_path)
    if file_data is not None:
        try:
            profile = CapabilityProfile.from_dict(file_data)
            profile = _apply_env_overrides(profile)
            return profile
        except Exception as exc:
            logger.warning(
                "Ignoring malformed config file %s: %s", config_path, exc
            )

    # --- Env-var overrides on top of platform default ---
    raw_target = os.environ.get("SERVER_TARGET", "web_app")
    try:
        target = TargetPlatform(raw_target)
    except ValueError:
        valid = [t.value for t in TargetPlatform]
        logger.warning(
            "SERVER_TARGET=%r is not a valid platform (%s); falling back to web_app",
            raw_target,
            valid,
        )
        target = TargetPlatform.WEB_APP

    profile = default_profile(target)
    return _apply_env_overrides(profile)
