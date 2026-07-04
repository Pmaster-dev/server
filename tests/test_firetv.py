"""Tests for Fire TV remote keyboard shortcut components."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from automation.components import ComponentInput
from automation.engine import AutomationDefinition, AutomationEngine, RunStatus
from automation.firetv import (
    KEYBOARD_SHORTCUTS,
    FireTVADBComponent,
    FireTVKey,
    KeyboardShortcutComponent,
)


def _inp(payload, name="test", metadata=None):
    return ComponentInput(name=name, payload=payload, metadata=metadata or {})


# ---------------------------------------------------------------------------
# FireTVKey
# ---------------------------------------------------------------------------

class TestFireTVKey:
    def test_navigation_key_values(self):
        assert FireTVKey.HOME == 3
        assert FireTVKey.BACK == 4
        assert FireTVKey.DPAD_UP == 19
        assert FireTVKey.DPAD_DOWN == 20
        assert FireTVKey.DPAD_LEFT == 21
        assert FireTVKey.DPAD_RIGHT == 22
        assert FireTVKey.DPAD_CENTER == 23

    def test_media_key_values(self):
        assert FireTVKey.PLAY_PAUSE == 85
        assert FireTVKey.REWIND == 89
        assert FireTVKey.FAST_FORWARD == 90
        assert FireTVKey.MUTE == 164

    def test_is_int_enum(self):
        assert int(FireTVKey.DPAD_UP) == 19


# ---------------------------------------------------------------------------
# KEYBOARD_SHORTCUTS
# ---------------------------------------------------------------------------

class TestKeyboardShortcuts:
    def test_arrow_keys_mapped(self):
        assert KEYBOARD_SHORTCUTS["ArrowUp"] is FireTVKey.DPAD_UP
        assert KEYBOARD_SHORTCUTS["ArrowDown"] is FireTVKey.DPAD_DOWN
        assert KEYBOARD_SHORTCUTS["ArrowLeft"] is FireTVKey.DPAD_LEFT
        assert KEYBOARD_SHORTCUTS["ArrowRight"] is FireTVKey.DPAD_RIGHT

    def test_enter_mapped_to_select(self):
        assert KEYBOARD_SHORTCUTS["Enter"] is FireTVKey.DPAD_CENTER

    def test_escape_and_backspace_mapped_to_back(self):
        assert KEYBOARD_SHORTCUTS["Escape"] is FireTVKey.BACK
        assert KEYBOARD_SHORTCUTS["Backspace"] is FireTVKey.BACK

    def test_spacebar_mapped_to_play_pause(self):
        assert KEYBOARD_SHORTCUTS[" "] is FireTVKey.PLAY_PAUSE

    def test_home_mapped(self):
        assert KEYBOARD_SHORTCUTS["Home"] is FireTVKey.HOME

    def test_volume_keys_mapped(self):
        assert KEYBOARD_SHORTCUTS["+"] is FireTVKey.VOLUME_UP
        assert KEYBOARD_SHORTCUTS["-"] is FireTVKey.VOLUME_DOWN
        assert KEYBOARD_SHORTCUTS["AudioVolumeMute"] is FireTVKey.MUTE


# ---------------------------------------------------------------------------
# KeyboardShortcutComponent
# ---------------------------------------------------------------------------

class TestKeyboardShortcutComponent:
    def setup_method(self):
        self.comp = KeyboardShortcutComponent()

    def test_maps_known_key(self):
        out = self.comp.execute(_inp("ArrowUp"))
        assert out.success is True
        assert out.result is FireTVKey.DPAD_UP

    def test_maps_enter_key(self):
        out = self.comp.execute(_inp("Enter"))
        assert out.success is True
        assert out.result is FireTVKey.DPAD_CENTER

    def test_returns_error_for_unknown_key(self):
        out = self.comp.execute(_inp("F1"))
        assert out.success is False
        assert "F1" in out.error

    def test_custom_shortcuts_override_defaults(self):
        custom = {"q": FireTVKey.HOME}
        comp = KeyboardShortcutComponent(shortcuts=custom)
        out = comp.execute(_inp("q"))
        assert out.success is True
        assert out.result is FireTVKey.HOME

    def test_custom_shortcuts_do_not_include_defaults(self):
        custom = {"q": FireTVKey.HOME}
        comp = KeyboardShortcutComponent(shortcuts=custom)
        out = comp.execute(_inp("ArrowUp"))
        assert out.success is False

    def test_component_name_and_description(self):
        assert self.comp.name == "keyboard_to_firetv"
        assert self.comp.description


# ---------------------------------------------------------------------------
# FireTVADBComponent
# ---------------------------------------------------------------------------

class TestFireTVADBComponent:
    def _mock_proc(self, returncode=0, stdout="", stderr=""):
        return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_sends_keyevent_without_device(self):
        comp = FireTVADBComponent()
        with patch("automation.firetv.subprocess.run", return_value=self._mock_proc()) as mock_run:
            out = comp.execute(_inp(FireTVKey.DPAD_UP))
        assert out.success is True
        cmd = mock_run.call_args[0][0]
        assert cmd == ["adb", "shell", "input", "keyevent", "19"]

    def test_sends_keyevent_with_constructor_device(self):
        comp = FireTVADBComponent(device="192.168.1.100:5555")
        with patch("automation.firetv.subprocess.run", return_value=self._mock_proc()) as mock_run:
            out = comp.execute(_inp(FireTVKey.DPAD_CENTER))
        assert out.success is True
        cmd = mock_run.call_args[0][0]
        assert cmd == ["adb", "-s", "192.168.1.100:5555", "shell", "input", "keyevent", "23"]

    def test_device_from_metadata_overrides_constructor(self):
        comp = FireTVADBComponent(device="default:5555")
        with patch("automation.firetv.subprocess.run", return_value=self._mock_proc()) as mock_run:
            out = comp.execute(_inp(FireTVKey.HOME, metadata={"device": "override:5555"}))
        assert out.success is True
        cmd = mock_run.call_args[0][0]
        assert "override:5555" in cmd
        assert "default:5555" not in cmd

    def test_output_contains_keycode_and_device(self):
        comp = FireTVADBComponent(device="10.0.0.1:5555")
        with patch("automation.firetv.subprocess.run", return_value=self._mock_proc(stdout="ok")):
            out = comp.execute(_inp(FireTVKey.PLAY_PAUSE))
        assert out.result["keycode"] == int(FireTVKey.PLAY_PAUSE)
        assert out.result["device"] == "10.0.0.1:5555"
        assert out.result["stdout"] == "ok"

    def test_adb_not_found_returns_error(self):
        comp = FireTVADBComponent()
        with patch("automation.firetv.subprocess.run", side_effect=FileNotFoundError):
            out = comp.execute(_inp(FireTVKey.HOME))
        assert out.success is False
        assert "adb not found" in out.error

    def test_adb_nonzero_exit_returns_error(self):
        comp = FireTVADBComponent()
        with patch("automation.firetv.subprocess.run", return_value=self._mock_proc(returncode=1, stderr="no device")):
            out = comp.execute(_inp(FireTVKey.HOME))
        assert out.success is False
        assert "code 1" in out.error

    def test_adb_timeout_returns_error(self):
        comp = FireTVADBComponent()
        with patch("automation.firetv.subprocess.run", side_effect=subprocess.TimeoutExpired("adb", 10)):
            out = comp.execute(_inp(FireTVKey.HOME))
        assert out.success is False
        assert "timed out" in out.error

    def test_component_name_and_description(self):
        comp = FireTVADBComponent()
        assert comp.name == "firetv_adb_send"
        assert comp.description


# ---------------------------------------------------------------------------
# End-to-end automation pipeline
# ---------------------------------------------------------------------------

class TestFireTVAutomationPipeline:
    def test_full_pipeline_success(self):
        engine = AutomationEngine()
        engine.components.register("keyboard_to_firetv", KeyboardShortcutComponent())
        engine.components.register("firetv_adb_send", FireTVADBComponent())
        engine.define(AutomationDefinition(
            name="firetv_shortcut",
            triggers=["keyboard.keypress"],
            steps=["keyboard_to_firetv", "firetv_adb_send"],
        ))

        mock_proc = MagicMock(returncode=0, stdout="", stderr="")
        with patch("automation.firetv.subprocess.run", return_value=mock_proc):
            results = engine.trigger_type("keyboard.keypress", payload="Enter")

        assert len(results) == 1
        assert results[0].status is RunStatus.SUCCESS
        assert len(results[0].outputs) == 2

    def test_unknown_key_fails_pipeline_before_adb(self):
        engine = AutomationEngine()
        engine.components.register("keyboard_to_firetv", KeyboardShortcutComponent())
        engine.components.register("firetv_adb_send", FireTVADBComponent())
        engine.define(AutomationDefinition(
            name="firetv_shortcut",
            triggers=["keyboard.keypress"],
            steps=["keyboard_to_firetv", "firetv_adb_send"],
        ))

        with patch("automation.firetv.subprocess.run") as mock_run:
            results = engine.trigger_type("keyboard.keypress", payload="F12")

        assert len(results) == 1
        assert results[0].status is RunStatus.FAILED
        # ADB should not have been called
        mock_run.assert_not_called()

    def test_all_default_shortcuts_route_correctly(self):
        """Every entry in KEYBOARD_SHORTCUTS should produce a SUCCESS output."""
        comp = KeyboardShortcutComponent()
        for key_name in KEYBOARD_SHORTCUTS:
            out = comp.execute(_inp(key_name))
            assert out.success is True, f"Failed for key: {key_name!r}"
