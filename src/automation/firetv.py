"""
Fire TV remote keyboard shortcut components for the automation engine.

Provides a mapping from keyboard key names to Fire TV ADB keycodes and two
pluggable components that can be composed in an automation pipeline:

* :class:`KeyboardShortcutComponent` – translates a keyboard key name into a
  :class:`FireTVKey` keycode.
* :class:`FireTVADBComponent` – sends a keycode to a Fire TV device via
  ``adb shell input keyevent``.

Typical pipeline::

    engine.components.register("keyboard_to_firetv", KeyboardShortcutComponent())
    engine.components.register("firetv_adb_send", FireTVADBComponent(device="192.168.1.10:5555"))

    engine.define(AutomationDefinition(
        name="firetv_shortcut",
        triggers=["keyboard.keypress"],
        steps=["keyboard_to_firetv", "firetv_adb_send"],
    ))

    # Press the Enter key on the Fire TV remote
    engine.trigger_type("keyboard.keypress", payload="Enter")
"""

from __future__ import annotations

import subprocess
from enum import IntEnum
from typing import Dict, Optional

from .components import Component, ComponentInput, ComponentOutput


class FireTVKey(IntEnum):
    """ADB keycode constants for Fire TV remote buttons."""
    HOME = 3
    BACK = 4
    DPAD_UP = 19
    DPAD_DOWN = 20
    DPAD_LEFT = 21
    DPAD_RIGHT = 22
    DPAD_CENTER = 23       # Select / OK
    VOLUME_UP = 24
    VOLUME_DOWN = 25
    PLAY_PAUSE = 85
    REWIND = 89
    FAST_FORWARD = 90
    MENU = 82
    MEDIA_NEXT = 87
    MEDIA_PREVIOUS = 88
    MUTE = 164


#: Default keyboard key name → Fire TV remote button mapping.
#: Key names follow the Web KeyboardEvent.key convention so they can be
#: forwarded directly from browser or Electron key events.
KEYBOARD_SHORTCUTS: Dict[str, FireTVKey] = {
    "ArrowUp": FireTVKey.DPAD_UP,
    "ArrowDown": FireTVKey.DPAD_DOWN,
    "ArrowLeft": FireTVKey.DPAD_LEFT,
    "ArrowRight": FireTVKey.DPAD_RIGHT,
    "Enter": FireTVKey.DPAD_CENTER,
    "Escape": FireTVKey.BACK,
    "Backspace": FireTVKey.BACK,
    "Home": FireTVKey.HOME,
    "m": FireTVKey.MENU,
    " ": FireTVKey.PLAY_PAUSE,           # Spacebar
    "MediaPlayPause": FireTVKey.PLAY_PAUSE,
    "MediaRewind": FireTVKey.REWIND,
    "MediaFastForward": FireTVKey.FAST_FORWARD,
    "MediaTrackPrevious": FireTVKey.MEDIA_PREVIOUS,
    "MediaTrackNext": FireTVKey.MEDIA_NEXT,
    "+": FireTVKey.VOLUME_UP,
    "-": FireTVKey.VOLUME_DOWN,
    "AudioVolumeMute": FireTVKey.MUTE,
}


class KeyboardShortcutComponent(Component):
    """
    Translates a keyboard key name into a :class:`FireTVKey` keycode.

    Input payload
        Keyboard key name string, e.g. ``"ArrowUp"`` or ``"Enter"``.

    Output result
        The matching :class:`FireTVKey` value.

    On failure
        Returns an error output when the key name has no mapped shortcut.
    """

    name = "keyboard_to_firetv"
    description = "Maps a keyboard key name to a Fire TV remote keycode."

    def __init__(self, shortcuts: Optional[Dict[str, FireTVKey]] = None) -> None:
        """
        Args:
            shortcuts: Custom key-name → :class:`FireTVKey` mapping.
                       Defaults to :data:`KEYBOARD_SHORTCUTS` when ``None``.
        """
        self._shortcuts: Dict[str, FireTVKey] = (
            shortcuts if shortcuts is not None else KEYBOARD_SHORTCUTS
        )

    def execute(self, input_: ComponentInput) -> ComponentOutput:
        key_name: str = input_.payload
        firetv_key = self._shortcuts.get(key_name)
        if firetv_key is None:
            return self._err(f"No Fire TV mapping for key: {key_name!r}")
        return self._ok(firetv_key)


class FireTVADBComponent(Component):
    """
    Sends a Fire TV remote keycode to a device via ``adb shell input keyevent``.

    Input payload
        A :class:`FireTVKey` value or any ``int`` ADB keycode.

    Metadata
        ``"device"`` (str) – ADB device address (e.g. ``"192.168.1.10:5555"``).
        When present, overrides the *device* argument passed to the constructor.

    Output result
        ``{"keycode": int, "device": str | None, "stdout": str}`` on success.
    """

    name = "firetv_adb_send"
    description = "Sends a keyevent to a Fire TV device via ADB."

    def __init__(self, device: Optional[str] = None) -> None:
        """
        Args:
            device: Default ADB device address.  Can be overridden per-run
                    via the ``"device"`` key in the component input metadata.
        """
        self._device = device

    def execute(self, input_: ComponentInput) -> ComponentOutput:
        keycode = int(input_.payload)
        device: Optional[str] = input_.metadata.get("device") or self._device

        cmd = ["adb"]
        if device:
            cmd += ["-s", device]
        cmd += ["shell", "input", "keyevent", str(keycode)]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except FileNotFoundError:
            return self._err("adb not found; ensure Android SDK platform-tools are on PATH")
        except subprocess.TimeoutExpired:
            return self._err("adb command timed out")

        if proc.returncode != 0:
            return self._err(
                f"adb exited with code {proc.returncode}: {proc.stderr.strip()}"
            )

        return self._ok(
            {"keycode": keycode, "device": device, "stdout": proc.stdout.strip()}
        )
