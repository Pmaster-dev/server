"""
Tests for CapabilityProfile, MotionStability, AccessibilityFlags, and the
centralized server config module.

Run with:  PYTHONPATH=src pytest --tb=short -q
"""

import os
import json
import tempfile

import pytest

from automation.profile import (
    AccessibilityFlags,
    CapabilityProfile,
    MotionStability,
    TargetPlatform,
    default_profile,
    DEFAULT_PROFILES,
)


# ---------------------------------------------------------------------------
# MotionStability validation
# ---------------------------------------------------------------------------

class TestMotionStabilityValidation:
    def test_zero_values_are_valid(self):
        ms = MotionStability()
        assert ms.validate() == []

    def test_positive_values_are_valid(self):
        ms = MotionStability(min_fps=30, max_latency_ms=100, jitter_budget_ms=16)
        assert ms.validate() == []

    def test_negative_fps_is_invalid(self):
        errors = MotionStability(min_fps=-1).validate()
        assert any("min_fps" in e for e in errors)

    def test_negative_latency_is_invalid(self):
        errors = MotionStability(max_latency_ms=-5).validate()
        assert any("max_latency_ms" in e for e in errors)

    def test_negative_jitter_is_invalid(self):
        errors = MotionStability(jitter_budget_ms=-1).validate()
        assert any("jitter_budget_ms" in e for e in errors)

    def test_latency_less_than_frame_period_is_invalid(self):
        # At 60 fps, one frame ≈ 16.67 ms.  A latency cap of 10 ms is impossible.
        errors = MotionStability(min_fps=60, max_latency_ms=10).validate()
        assert len(errors) == 1
        assert "less than one frame period" in errors[0]

    def test_latency_equal_to_frame_period_is_valid(self):
        # Exactly one frame period should be accepted
        errors = MotionStability(min_fps=60, max_latency_ms=1000 / 60).validate()
        assert errors == []

    def test_roundtrip_serialization(self):
        ms = MotionStability(min_fps=30, max_latency_ms=80, jitter_budget_ms=8)
        assert MotionStability.from_dict(ms.to_dict()) == ms


# ---------------------------------------------------------------------------
# AccessibilityFlags serialisation
# ---------------------------------------------------------------------------

class TestAccessibilityFlags:
    def test_defaults(self):
        af = AccessibilityFlags()
        assert af.sign_language_overlay is False
        assert af.visual_video_enabled is True
        assert af.high_contrast is False
        assert af.reduced_motion is False

    def test_roundtrip_serialization(self):
        af = AccessibilityFlags(
            sign_language_overlay=True,
            visual_video_enabled=False,
            high_contrast=True,
            reduced_motion=True,
        )
        assert AccessibilityFlags.from_dict(af.to_dict()) == af


# ---------------------------------------------------------------------------
# CapabilityProfile validation
# ---------------------------------------------------------------------------

class TestCapabilityProfileValidation:
    def test_valid_profile_returns_no_errors(self):
        profile = CapabilityProfile(name="test", target=TargetPlatform.WEB_APP)
        assert profile.validate() == []

    def test_empty_name_is_invalid(self):
        profile = CapabilityProfile(name="", target=TargetPlatform.CLI)
        errors = profile.validate()
        assert any("name" in e for e in errors)

    def test_whitespace_only_name_is_invalid(self):
        profile = CapabilityProfile(name="   ", target=TargetPlatform.CLI)
        errors = profile.validate()
        assert any("name" in e for e in errors)

    def test_embedded_without_latency_warns(self):
        profile = CapabilityProfile(
            name="bare-embedded",
            target=TargetPlatform.EMBEDDED,
            # max_latency_ms defaults to 0 (unconstrained)
        )
        errors = profile.validate()
        assert any("embedded" in e for e in errors)

    def test_embedded_with_latency_is_valid(self):
        profile = CapabilityProfile(
            name="constrained-embedded",
            target=TargetPlatform.EMBEDDED,
            motion_stability=MotionStability(
                min_fps=15, max_latency_ms=200, jitter_budget_ms=33
            ),
        )
        assert profile.validate() == []

    def test_invalid_motion_stability_surfaces_in_profile_validate(self):
        profile = CapabilityProfile(
            name="bad-motion",
            target=TargetPlatform.WEB_APP,
            motion_stability=MotionStability(min_fps=-5),
        )
        errors = profile.validate()
        assert any("min_fps" in e for e in errors)


# ---------------------------------------------------------------------------
# CapabilityProfile helpers
# ---------------------------------------------------------------------------

class TestCapabilityProfileHelpers:
    def test_is_visual_true_when_visual_video_enabled(self):
        profile = CapabilityProfile(
            name="p",
            target=TargetPlatform.WEB_APP,
            accessibility=AccessibilityFlags(visual_video_enabled=True),
        )
        assert profile.is_visual is True

    def test_is_visual_false_when_disabled(self):
        profile = CapabilityProfile(
            name="p",
            target=TargetPlatform.CLI,
            accessibility=AccessibilityFlags(visual_video_enabled=False),
        )
        assert profile.is_visual is False

    def test_is_motion_constrained_false_for_zero_motion(self):
        profile = CapabilityProfile(name="p", target=TargetPlatform.WEB_APP)
        assert profile.is_motion_constrained is False

    def test_is_motion_constrained_true_when_fps_set(self):
        profile = CapabilityProfile(
            name="p",
            target=TargetPlatform.WEB_APP,
            motion_stability=MotionStability(min_fps=30),
        )
        assert profile.is_motion_constrained is True

    def test_roundtrip_serialization(self):
        profile = CapabilityProfile(
            name="web-prod",
            target=TargetPlatform.WEB_APP,
            motion_stability=MotionStability(min_fps=30, max_latency_ms=80),
            accessibility=AccessibilityFlags(sign_language_overlay=True),
            custom={"theme": "dark"},
        )
        assert CapabilityProfile.from_dict(profile.to_dict()) == profile


# ---------------------------------------------------------------------------
# Built-in default profiles
# ---------------------------------------------------------------------------

class TestDefaultProfiles:
    def test_all_platforms_have_a_default(self):
        for platform in TargetPlatform:
            profile = default_profile(platform)
            assert isinstance(profile, CapabilityProfile)
            assert profile.target == platform

    def test_default_profiles_are_individually_valid(self):
        """Each built-in default must be self-consistent."""
        for platform in TargetPlatform:
            profile = default_profile(platform)
            errors = profile.validate()
            assert errors == [], (
                f"Default profile for {platform.value} has validation errors: {errors}"
            )

    def test_cli_default_has_visual_video_disabled(self):
        assert default_profile(TargetPlatform.CLI).is_visual is False

    def test_web_app_default_has_sign_language_overlay(self):
        assert default_profile(TargetPlatform.WEB_APP).accessibility.sign_language_overlay is True

    def test_embedded_default_has_motion_constraints(self):
        assert default_profile(TargetPlatform.EMBEDDED).is_motion_constrained is True


# ---------------------------------------------------------------------------
# Centralized config module
# ---------------------------------------------------------------------------

class TestServerConfig:
    """Tests for src/config.py (centralized server configuration)."""

    def setup_method(self):
        # Ensure a clean state before each test
        from config import clear_profile
        clear_profile()
        # Remove all SERVER_* env vars that might bleed between tests
        for key in list(os.environ):
            if key.startswith("SERVER_"):
                del os.environ[key]

    def teardown_method(self):
        from config import clear_profile
        clear_profile()
        for key in list(os.environ):
            if key.startswith("SERVER_"):
                del os.environ[key]

    def test_returns_capability_profile(self):
        from config import get_profile
        profile = get_profile()
        assert isinstance(profile, CapabilityProfile)

    def test_set_profile_overrides_resolution(self):
        from config import get_profile, set_profile
        custom = CapabilityProfile(name="custom", target=TargetPlatform.CLI)
        set_profile(custom)
        assert get_profile() is custom

    def test_clear_profile_restores_auto_resolution(self):
        from config import clear_profile, get_profile, set_profile
        custom = CapabilityProfile(name="custom", target=TargetPlatform.CLI)
        set_profile(custom)
        clear_profile()
        profile = get_profile()
        assert profile is not custom
        assert isinstance(profile, CapabilityProfile)

    def test_server_target_env_selects_platform(self):
        from config import get_profile
        os.environ["SERVER_TARGET"] = "cli"
        profile = get_profile()
        assert profile.target == TargetPlatform.CLI

    def test_unknown_server_target_falls_back_to_web_app(self):
        from config import get_profile
        os.environ["SERVER_TARGET"] = "nonexistent"
        profile = get_profile()
        assert profile.target == TargetPlatform.WEB_APP

    def test_server_min_fps_env_overrides(self):
        from config import get_profile
        os.environ["SERVER_TARGET"] = "web_app"
        os.environ["SERVER_MIN_FPS"] = "60"
        profile = get_profile()
        assert profile.motion_stability.min_fps == 60.0

    def test_server_sign_language_overlay_env_true(self):
        from config import get_profile
        os.environ["SERVER_TARGET"] = "cli"
        os.environ["SERVER_SIGN_LANGUAGE_OVERLAY"] = "true"
        profile = get_profile()
        assert profile.accessibility.sign_language_overlay is True

    def test_server_sign_language_overlay_env_false(self):
        from config import get_profile
        os.environ["SERVER_TARGET"] = "web_app"
        os.environ["SERVER_SIGN_LANGUAGE_OVERLAY"] = "false"
        profile = get_profile()
        assert profile.accessibility.sign_language_overlay is False

    def test_config_file_is_loaded(self):
        from config import get_profile
        data = {
            "name": "file-profile",
            "target": "ide",
            "motion_stability": {"min_fps": 24, "max_latency_ms": 100, "jitter_budget_ms": 0},
            "accessibility": {
                "sign_language_overlay": False,
                "visual_video_enabled": True,
                "high_contrast": False,
                "reduced_motion": False,
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fh:
            json.dump(data, fh)
            tmp_path = fh.name

        try:
            os.environ["SERVER_CONFIG_FILE"] = tmp_path
            profile = get_profile()
            assert profile.name == "file-profile"
            assert profile.target == TargetPlatform.IDE
            assert profile.motion_stability.min_fps == 24.0
        finally:
            os.unlink(tmp_path)

    def test_env_overrides_applied_on_top_of_config_file(self):
        from config import get_profile
        data = {"name": "base", "target": "web_app"}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fh:
            json.dump(data, fh)
            tmp_path = fh.name

        try:
            os.environ["SERVER_CONFIG_FILE"] = tmp_path
            os.environ["SERVER_PROFILE_NAME"] = "overridden"
            profile = get_profile()
            assert profile.name == "overridden"
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Platform adapter smoke tests
# ---------------------------------------------------------------------------

class TestPlatformAdapters:
    def test_get_adapter_returns_correct_type(self):
        from adapters import get_adapter, CLIAdapter, WebAppAdapter
        assert isinstance(get_adapter(TargetPlatform.CLI), CLIAdapter)
        assert isinstance(get_adapter(TargetPlatform.WEB_APP), WebAppAdapter)

    def test_all_platforms_have_adapter(self):
        from adapters import get_adapter
        for platform in TargetPlatform:
            adapter = get_adapter(platform)
            assert adapter.platform_name == platform.value

    def test_cli_adapter_strips_sign_language_key(self):
        from adapters import CLIAdapter
        from automation.components import ComponentInput
        adapter = CLIAdapter()
        inp = ComponentInput(
            name="step",
            payload="hello",
            metadata={"sign_language_overlay": True, "keep": "yes"},
        )
        out = adapter.adapt_input(inp)
        assert "sign_language_overlay" not in out.metadata
        assert out.metadata["keep"] == "yes"

    def test_web_app_adapter_injects_sign_language_flag(self):
        from adapters import WebAppAdapter
        from automation.components import ComponentInput
        profile = CapabilityProfile(
            name="web",
            target=TargetPlatform.WEB_APP,
            accessibility=AccessibilityFlags(sign_language_overlay=True),
        )
        adapter = WebAppAdapter()
        inp = ComponentInput(name="step", payload=None, metadata={})
        out = adapter.adapt_input(inp, profile=profile)
        assert out.metadata["sign_language_overlay"] is True

    def test_web_app_adapter_injects_motion_stability(self):
        from adapters import WebAppAdapter
        from automation.components import ComponentOutput
        profile = CapabilityProfile(
            name="web",
            target=TargetPlatform.WEB_APP,
            motion_stability=MotionStability(min_fps=30, max_latency_ms=80),
        )
        adapter = WebAppAdapter()
        out = ComponentOutput(component="step", result="ok", success=True)
        adapted = adapter.adapt_output(out, profile=profile)
        assert "motion_stability" in adapted.metadata

    def test_embedded_adapter_strips_heavy_fields(self):
        from adapters import EmbeddedAdapter
        from automation.components import ComponentInput
        adapter = EmbeddedAdapter()
        inp = ComponentInput(
            name="step",
            payload=b"bytes",
            metadata={"video_frame": b"...", "sign_language_overlay": True, "ok": 1},
        )
        out = adapter.adapt_input(inp)
        assert "video_frame" not in out.metadata
        assert "sign_language_overlay" not in out.metadata
        assert out.metadata["ok"] == 1


# ---------------------------------------------------------------------------
# Engine integration: profile flows through run metadata
# ---------------------------------------------------------------------------

class TestEngineProfileIntegration:
    def test_definition_profile_appears_in_run_metadata(self):
        from automation.engine import AutomationDefinition, AutomationEngine

        captured = {}

        def capture_meta(inp):
            captured.update(inp.metadata)
            return inp.payload

        profile = CapabilityProfile(
            name="integration",
            target=TargetPlatform.WEB_APP,
            accessibility=AccessibilityFlags(sign_language_overlay=True),
        )

        engine = AutomationEngine()
        engine.register_fn("capture", capture_meta)
        engine.define(
            AutomationDefinition(
                name="test-profile-flow",
                triggers=["test"],
                steps=["capture"],
                profile=profile,
            )
        )

        results = engine.trigger_type("test", payload="hello")
        assert results[0].status.value == "success"
        assert "profile" in captured
        assert captured["profile"]["name"] == "integration"
        assert captured["profile"]["accessibility"]["sign_language_overlay"] is True
