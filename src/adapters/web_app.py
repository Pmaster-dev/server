"""Web-app platform adapter."""

from __future__ import annotations

from automation.components import ComponentInput, ComponentOutput
from automation.profile import CapabilityProfile

from .base import PlatformAdapter


class WebAppAdapter(PlatformAdapter):
    """
    Adapter for web-application deployments.

    Enriches metadata with sign-language overlay and motion-stability hints
    so browser-side renderers can apply the correct constraints without
    re-querying the server profile.
    """

    @property
    def platform_name(self) -> str:
        return "web_app"

    def adapt_input(
        self,
        input_: ComponentInput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentInput:
        meta = self._annotate_meta(input_.metadata, profile)
        if profile is not None:
            meta["sign_language_overlay"] = profile.accessibility.sign_language_overlay
            meta["reduced_motion"] = profile.accessibility.reduced_motion
        return ComponentInput(name=input_.name, payload=input_.payload, metadata=meta)

    def adapt_output(
        self,
        output: ComponentOutput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentOutput:
        meta = self._annotate_meta(output.metadata, profile)
        if profile is not None and profile.is_motion_constrained:
            meta["motion_stability"] = profile.motion_stability.to_dict()
        return ComponentOutput(
            component=output.component,
            result=output.result,
            success=output.success,
            error=output.error,
            metadata=meta,
        )
