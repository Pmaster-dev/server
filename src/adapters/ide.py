"""IDE platform adapter."""

from __future__ import annotations

from automation.components import ComponentInput, ComponentOutput
from automation.profile import CapabilityProfile

from .base import PlatformAdapter


class IDEAdapter(PlatformAdapter):
    """
    Adapter for IDE (editor/extension) deployments.

    Annotates inputs and outputs with IDE-specific context markers so IDE
    extensions can route results to the correct editor pane or sidebar widget.
    """

    @property
    def platform_name(self) -> str:
        return "ide"

    def adapt_input(
        self,
        input_: ComponentInput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentInput:
        meta = self._annotate_meta(input_.metadata, profile)
        return ComponentInput(name=input_.name, payload=input_.payload, metadata=meta)

    def adapt_output(
        self,
        output: ComponentOutput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentOutput:
        meta = self._annotate_meta(output.metadata, profile)
        # Surface motion-stability constraints so IDE renderers can throttle
        if profile is not None and profile.is_motion_constrained:
            meta["motion_stability"] = profile.motion_stability.to_dict()
        return ComponentOutput(
            component=output.component,
            result=output.result,
            success=output.success,
            error=output.error,
            metadata=meta,
        )
