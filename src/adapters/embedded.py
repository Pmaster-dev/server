"""Embedded platform adapter."""

from __future__ import annotations

from automation.components import ComponentInput, ComponentOutput
from automation.profile import CapabilityProfile

from .base import PlatformAdapter


class EmbeddedAdapter(PlatformAdapter):
    """
    Adapter for embedded-device deployments.

    Strips heavy payload fields (e.g. raw video frames) that embedded targets
    cannot process, and enforces strict motion-stability budgets reflected in
    the output metadata so downstream embedded renderers skip overdue frames.
    """

    @property
    def platform_name(self) -> str:
        return "embedded"

    def adapt_input(
        self,
        input_: ComponentInput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentInput:
        meta = self._annotate_meta(input_.metadata, profile)
        # Remove fields that exceed embedded resource constraints
        for heavy_key in ("video_frame", "sign_language_overlay", "high_res_image"):
            meta.pop(heavy_key, None)
        return ComponentInput(name=input_.name, payload=input_.payload, metadata=meta)

    def adapt_output(
        self,
        output: ComponentOutput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentOutput:
        meta = self._annotate_meta(output.metadata, profile)
        if profile is not None:
            meta["motion_stability"] = profile.motion_stability.to_dict()
        return ComponentOutput(
            component=output.component,
            result=output.result,
            success=output.success,
            error=output.error,
            metadata=meta,
        )
