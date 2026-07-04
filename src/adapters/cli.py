"""CLI platform adapter."""

from __future__ import annotations

from automation.components import ComponentInput, ComponentOutput
from automation.profile import CapabilityProfile

from .base import PlatformAdapter


class CLIAdapter(PlatformAdapter):
    """
    Adapter for CLI (terminal) deployments.

    Strips metadata fields that are only meaningful in visual environments
    (e.g. sign-language overlay markers) and annotates outputs with the
    platform tag so downstream consumers can route accordingly.
    """

    @property
    def platform_name(self) -> str:
        return "cli"

    def adapt_input(
        self,
        input_: ComponentInput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentInput:
        meta = self._annotate_meta(input_.metadata, profile)
        # Remove visual-only keys that are irrelevant in a terminal context
        meta.pop("sign_language_overlay", None)
        meta.pop("video_frame", None)
        return ComponentInput(name=input_.name, payload=input_.payload, metadata=meta)

    def adapt_output(
        self,
        output: ComponentOutput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentOutput:
        meta = self._annotate_meta(output.metadata, profile)
        return ComponentOutput(
            component=output.component,
            result=output.result,
            success=output.success,
            error=output.error,
            metadata=meta,
        )
