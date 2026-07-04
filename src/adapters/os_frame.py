"""OS/frame platform adapter."""

from __future__ import annotations

from automation.components import ComponentInput, ComponentOutput
from automation.profile import CapabilityProfile

from .base import PlatformAdapter


class OSFrameAdapter(PlatformAdapter):
    """
    Adapter for OS-level frame/window-manager deployments.

    Carries high-refresh-rate and low-jitter constraints end-to-end so
    native OS renderers and compositors can prioritise frames accordingly.
    """

    @property
    def platform_name(self) -> str:
        return "os_frame"

    def adapt_input(
        self,
        input_: ComponentInput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentInput:
        meta = self._annotate_meta(input_.metadata, profile)
        if profile is not None:
            meta["sign_language_overlay"] = profile.accessibility.sign_language_overlay
            meta["high_contrast"] = profile.accessibility.high_contrast
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
