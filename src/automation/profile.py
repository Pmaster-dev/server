"""
Capability profile contract for the Pmaster server automation layer.

A :class:`CapabilityProfile` is a single, normalized description of *what a
deployment target can do* and *what constraints it operates under*.  It covers:

* The **target platform** (CLI, IDE, web app, OS/frame, embedded).
* **Motion stability** requirements for visual/video/sign-language pipelines
  (minimum frame rate, maximum tolerated latency, jitter budget).
* **Accessibility flags** that gate sign-language overlay rendering, reduced-
  motion mode, high-contrast output, and visual-video streaming.
* A **custom** dict for any project-specific extensions that do not belong in
  the shared contract.

Usage::

    from automation.profile import CapabilityProfile, TargetPlatform, MotionStability, AccessibilityFlags

    profile = CapabilityProfile(
        name="my-service",
        target=TargetPlatform.WEB_APP,
        motion_stability=MotionStability(min_fps=30, max_latency_ms=100),
        accessibility=AccessibilityFlags(sign_language_overlay=True),
    )

    errors = profile.validate()
    if errors:
        raise ValueError(errors)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Target platforms
# ---------------------------------------------------------------------------

class TargetPlatform(str, Enum):
    """Deployment target platforms supported by the server layer."""
    CLI = "cli"
    IDE = "ide"
    WEB_APP = "web_app"
    OS_FRAME = "os_frame"
    EMBEDDED = "embedded"


# ---------------------------------------------------------------------------
# Motion stability
# ---------------------------------------------------------------------------

@dataclass
class MotionStability:
    """
    Motion and timing constraints for visual/video/sign-language pipelines.

    All three fields default to permissive values (no hard constraints).
    Set them explicitly for targets that require consistent motion rendering.

    Attributes:
        min_fps: Minimum acceptable rendered frames per second.  Zero means
            no constraint.
        max_latency_ms: Maximum end-to-end latency in milliseconds before a
            frame or sign is considered late.  Zero means no constraint.
        jitter_budget_ms: Maximum allowed frame-to-frame timing variance in
            milliseconds.  Zero means no constraint.
    """
    min_fps: float = 0.0
    max_latency_ms: float = 0.0
    jitter_budget_ms: float = 0.0

    def validate(self) -> List[str]:
        """Return a list of validation error strings, empty when valid."""
        errors: List[str] = []
        if self.min_fps < 0:
            errors.append("motion_stability.min_fps must be >= 0")
        if self.max_latency_ms < 0:
            errors.append("motion_stability.max_latency_ms must be >= 0")
        if self.jitter_budget_ms < 0:
            errors.append("motion_stability.jitter_budget_ms must be >= 0")
        if self.min_fps > 0 and self.max_latency_ms > 0:
            # If both are set, latency must leave room for at least one frame
            frame_period_ms = 1000.0 / self.min_fps
            if self.max_latency_ms < frame_period_ms:
                errors.append(
                    f"motion_stability.max_latency_ms ({self.max_latency_ms} ms) "
                    f"is less than one frame period at {self.min_fps} fps "
                    f"({frame_period_ms:.2f} ms)"
                )
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_fps": self.min_fps,
            "max_latency_ms": self.max_latency_ms,
            "jitter_budget_ms": self.jitter_budget_ms,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MotionStability":
        return MotionStability(
            min_fps=float(data.get("min_fps", 0.0)),
            max_latency_ms=float(data.get("max_latency_ms", 0.0)),
            jitter_budget_ms=float(data.get("jitter_budget_ms", 0.0)),
        )


# ---------------------------------------------------------------------------
# Accessibility flags
# ---------------------------------------------------------------------------

@dataclass
class AccessibilityFlags:
    """
    Accessibility feature switches for visual and sign-language pipelines.

    Attributes:
        sign_language_overlay: Enable sign-language overlay rendering in
            video/visual outputs.
        visual_video_enabled: Allow visual video output (disable for purely
            audio or headless targets).
        high_contrast: Request high-contrast color palettes across all UI
            rendered outputs.
        reduced_motion: Suppress or minimise animated transitions.  Must be
            honoured by all animation-producing components.
    """
    sign_language_overlay: bool = False
    visual_video_enabled: bool = True
    high_contrast: bool = False
    reduced_motion: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sign_language_overlay": self.sign_language_overlay,
            "visual_video_enabled": self.visual_video_enabled,
            "high_contrast": self.high_contrast,
            "reduced_motion": self.reduced_motion,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AccessibilityFlags":
        return AccessibilityFlags(
            sign_language_overlay=bool(data.get("sign_language_overlay", False)),
            visual_video_enabled=bool(data.get("visual_video_enabled", True)),
            high_contrast=bool(data.get("high_contrast", False)),
            reduced_motion=bool(data.get("reduced_motion", False)),
        )


# ---------------------------------------------------------------------------
# Capability profile
# ---------------------------------------------------------------------------

@dataclass
class CapabilityProfile:
    """
    Unified capability contract for a server deployment target.

    Every module, component, and automation definition reads from **one**
    profile rather than scattered environment variables or hard-coded defaults.

    Attributes:
        name: Human-readable profile identifier (e.g. ``"prod-web"``,
            ``"dev-cli"``).
        version: Semantic version of the profile schema (``"1.0.0"``).
        target: Deployment target platform.
        motion_stability: Frame-rate and latency constraints for
            visual/video/sign pipelines.  Defaults to unconstrained.
        accessibility: Feature flags governing accessibility overlays and
            reduced-motion behaviour.  Defaults to all-off except
            ``visual_video_enabled``.
        custom: Free-form extension dict for project-specific keys that do
            not belong in the shared schema.
    """
    name: str
    target: TargetPlatform
    version: str = "1.0.0"
    motion_stability: MotionStability = field(default_factory=MotionStability)
    accessibility: AccessibilityFlags = field(default_factory=AccessibilityFlags)
    custom: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> List[str]:
        """
        Return a list of validation errors.

        An empty list means the profile is well-formed and safe to use.
        """
        errors: List[str] = []

        if not self.name or not self.name.strip():
            errors.append("profile.name must not be empty")

        if not isinstance(self.target, TargetPlatform):
            errors.append(
                f"profile.target must be a TargetPlatform value, got {self.target!r}"
            )

        # Embedded targets have tighter defaults; warn when unconstrained
        if self.target == TargetPlatform.EMBEDDED:
            if self.motion_stability.max_latency_ms == 0:
                errors.append(
                    "embedded profiles should set motion_stability.max_latency_ms "
                    "to reflect hardware timing constraints"
                )

        errors.extend(self.motion_stability.validate())
        return errors

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "target": self.target.value,
            "motion_stability": self.motion_stability.to_dict(),
            "accessibility": self.accessibility.to_dict(),
            "custom": self.custom,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CapabilityProfile":
        return CapabilityProfile(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            target=TargetPlatform(data["target"]),
            motion_stability=MotionStability.from_dict(
                data.get("motion_stability", {})
            ),
            accessibility=AccessibilityFlags.from_dict(
                data.get("accessibility", {})
            ),
            custom=data.get("custom", {}),
        )

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def is_visual(self) -> bool:
        """True when this target renders visual output."""
        return self.accessibility.visual_video_enabled

    @property
    def is_motion_constrained(self) -> bool:
        """True when at least one motion constraint is non-zero."""
        ms = self.motion_stability
        return ms.min_fps > 0 or ms.max_latency_ms > 0 or ms.jitter_budget_ms > 0

    def __repr__(self) -> str:
        return (
            f"CapabilityProfile("
            f"name={self.name!r}, "
            f"target={self.target.value!r}, "
            f"version={self.version!r})"
        )


# ---------------------------------------------------------------------------
# Built-in default profiles (one per platform)
# ---------------------------------------------------------------------------

#: Sensible defaults for each :class:`TargetPlatform`.  Override individual
#: fields via :func:`config.get_profile` or by constructing directly.
DEFAULT_PROFILES: Dict[TargetPlatform, CapabilityProfile] = {
    TargetPlatform.CLI: CapabilityProfile(
        name="default-cli",
        target=TargetPlatform.CLI,
        accessibility=AccessibilityFlags(
            visual_video_enabled=False,
            reduced_motion=True,
        ),
    ),
    TargetPlatform.IDE: CapabilityProfile(
        name="default-ide",
        target=TargetPlatform.IDE,
        motion_stability=MotionStability(min_fps=24, max_latency_ms=100),
    ),
    TargetPlatform.WEB_APP: CapabilityProfile(
        name="default-web",
        target=TargetPlatform.WEB_APP,
        motion_stability=MotionStability(min_fps=30, max_latency_ms=80, jitter_budget_ms=16),
        accessibility=AccessibilityFlags(
            sign_language_overlay=True,
            visual_video_enabled=True,
        ),
    ),
    TargetPlatform.OS_FRAME: CapabilityProfile(
        name="default-os-frame",
        target=TargetPlatform.OS_FRAME,
        motion_stability=MotionStability(min_fps=60, max_latency_ms=50, jitter_budget_ms=8),
        accessibility=AccessibilityFlags(
            sign_language_overlay=True,
            visual_video_enabled=True,
        ),
    ),
    TargetPlatform.EMBEDDED: CapabilityProfile(
        name="default-embedded",
        target=TargetPlatform.EMBEDDED,
        motion_stability=MotionStability(min_fps=15, max_latency_ms=200, jitter_budget_ms=33),
        accessibility=AccessibilityFlags(
            visual_video_enabled=False,
            reduced_motion=True,
        ),
    ),
}


def default_profile(target: TargetPlatform) -> CapabilityProfile:
    """Return a copy of the built-in default profile for *target*."""
    return DEFAULT_PROFILES[target]
