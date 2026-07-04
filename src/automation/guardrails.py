"""
Built-in guardrail components for the serverless automation engine.

Guardrails are :class:`~automation.components.Component` subclasses that act as
safety gates in a pipeline.  They validate their input and return an error
output (without raising) when the input violates a policy, letting the engine
record the failure and invoke after-run hooks as normal.

Included guardrails
-------------------
* :class:`TextFileGuardrail` – validates payloads that reference text-based
  file paths (any extension in :data:`DEFAULT_TEXT_EXTENSIONS`, including
  ``.txt``, ``.log``, ``.csv``, etc.), blocking path-traversal attacks, null
  bytes, absolute paths, and disallowed file extensions.
"""

from __future__ import annotations

import os
from typing import FrozenSet

from .components import Component, ComponentInput, ComponentOutput

# ---------------------------------------------------------------------------
# Allowed text-file extensions
# ---------------------------------------------------------------------------

#: Extensions that are treated as significant text files and subjected to
#: guardrail checks when a payload string ends with one of these suffixes.
#: The set is intentionally conservative; extend via subclassing or by
#: passing *allowed_extensions* to :class:`TextFileGuardrail`.
DEFAULT_TEXT_EXTENSIONS: FrozenSet[str] = frozenset(
    {".txt", ".text", ".log", ".csv", ".tsv", ".md", ".rst", ".ini", ".cfg"}
)


# ---------------------------------------------------------------------------
# TextFileGuardrail
# ---------------------------------------------------------------------------

class TextFileGuardrail(Component):
    """
    Safety guardrail for text-file path payloads.

    When this component is included as a step in an automation pipeline it
    inspects the current ``payload`` (expected to be a file path string) and
    rejects it if any of the following conditions are true:

    * The payload is not a string.
    * The file extension is not in *allowed_extensions*.
    * The path contains ``..`` (directory traversal).
    * The path contains a null byte.
    * The path is an absolute path (configurable via *allow_absolute*).

    On success the payload is passed through unchanged so that subsequent
    pipeline steps can continue processing it.

    Args:
        allowed_extensions: Set of lowercase file extensions (including the
            leading dot) that are permitted.  Defaults to
            :data:`DEFAULT_TEXT_EXTENSIONS`.
        allow_absolute: When ``False`` (default) absolute paths are rejected.

    Example::

        engine = AutomationEngine()
        engine.start()
        engine.register_fn("read_file", lambda inp: open(inp.payload).read())
        engine.components.register("guard", TextFileGuardrail())

        engine.define(AutomationDefinition(
            name="safe_read",
            triggers=["file.read"],
            steps=["guard", "read_file"],
        ))

        results = engine.trigger_type("file.read", payload="notes.txt")
    """

    name = "text_file_guardrail"
    description = (
        "Validates text-file path payloads: rejects path traversal, null bytes, "
        "absolute paths, and disallowed extensions."
    )

    def __init__(
        self,
        allowed_extensions: FrozenSet[str] = DEFAULT_TEXT_EXTENSIONS,
        allow_absolute: bool = False,
    ) -> None:
        self._allowed_extensions = frozenset(ext.lower() for ext in allowed_extensions)
        self._allow_absolute = allow_absolute

    def validate(self, input_: ComponentInput) -> tuple[bool, str]:
        payload = input_.payload

        if not isinstance(payload, str):
            return False, (
                f"TextFileGuardrail: payload must be a string file path, "
                f"got {type(payload).__name__!r}"
            )

        if "\x00" in payload:
            return False, "TextFileGuardrail: payload contains a null byte"

        if not self._allow_absolute and os.path.isabs(payload):
            return False, (
                "TextFileGuardrail: absolute paths are not permitted; "
                f"got {payload!r}"
            )

        # Normalise separators then check for traversal components
        normalised = payload.replace("\\", "/")
        parts = normalised.split("/")
        if ".." in parts:
            return False, (
                "TextFileGuardrail: path traversal ('..') detected in "
                f"{payload!r}"
            )

        _, ext = os.path.splitext(payload)
        if ext.lower() not in self._allowed_extensions:
            return False, (
                f"TextFileGuardrail: file extension {ext!r} is not in the "
                f"allowed set {sorted(self._allowed_extensions)}"
            )

        return True, ""

    def execute(self, input_: ComponentInput) -> ComponentOutput:
        """Pass the validated payload through unchanged."""
        return self._ok(input_.payload)
