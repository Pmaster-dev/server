"""
Base class for platform adapters.

A :class:`PlatformAdapter` is an optional, stateless boundary that can
pre-process :class:`~automation.components.ComponentInput` before a component
executes and post-process :class:`~automation.components.ComponentOutput`
after it returns.

All built-in adapter implementations extend this class.  Third-party adapters
must also extend it to be usable with :func:`adapters.get_adapter`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from automation.components import ComponentInput, ComponentOutput
from automation.profile import CapabilityProfile


class PlatformAdapter(ABC):
    """
    Abstract base class for platform-specific input/output adapters.

    Subclass and override :meth:`adapt_input` and/or :meth:`adapt_output` to
    inject platform-specific behaviour into the automation pipeline without
    modifying any component logic.

    Both methods receive the profile active for the current run so adapters can
    make decisions based on motion-stability or accessibility constraints.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable name of the target platform (e.g. ``"cli"``)."""

    def adapt_input(
        self,
        input_: ComponentInput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentInput:
        """
        Pre-process *input_* for this platform.

        The default implementation returns *input_* unchanged.  Override to
        strip, enrich, or transform the input before the component sees it.

        Args:
            input_: The original component input.
            profile: The capability profile active for the current run, if any.

        Returns:
            The (possibly modified) :class:`ComponentInput` to forward to the
            component.
        """
        return input_

    def adapt_output(
        self,
        output: ComponentOutput,
        profile: CapabilityProfile | None = None,
    ) -> ComponentOutput:
        """
        Post-process *output* for this platform.

        The default implementation returns *output* unchanged.  Override to
        transform, filter, or annotate the output before it reaches the caller.

        Args:
            output: The original component output.
            profile: The capability profile active for the current run, if any.

        Returns:
            The (possibly modified) :class:`ComponentOutput` to return to the
            caller.
        """
        return output

    def _annotate_meta(
        self,
        meta: Dict[str, Any],
        profile: CapabilityProfile | None,
    ) -> Dict[str, Any]:
        """
        Helper: merge profile summary into an existing metadata dict.

        Returns a *new* dict; the original is not mutated.
        """
        merged = dict(meta)
        if profile is not None:
            merged.setdefault("platform", self.platform_name)
            merged.setdefault("profile_name", profile.name)
        return merged

    def __repr__(self) -> str:
        return f"{type(self).__name__}(platform={self.platform_name!r})"
