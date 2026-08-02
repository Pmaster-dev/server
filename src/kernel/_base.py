"""
MBTQ Kernel — base engine interface.

Every kernel engine inherits from :class:`KernelEngine` and implements
:meth:`process`.  The contract is intentionally minimal: each engine
receives a plain dict *context* and returns a plain dict *result*.
Domain-specific I/O shapes are documented in ``docs/architecture/engines.md``
and formalised in ``docs/openapi/kernel.yaml``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class KernelEngine(ABC):
    """
    Abstract base class for all MBTQ kernel engines.

    Subclasses implement :meth:`process` to provide engine-specific
    behaviour.  The *context* dict carries all inputs needed for one
    operation; the returned dict carries all outputs.

    The engine name is derived from the subclass name by default but
    can be overridden via the :attr:`engine_name` class attribute.
    """

    #: Human-readable name for this engine.
    engine_name: str = ""

    @abstractmethod
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute one operation against the kernel.

        Args:
            context: Input dict whose required keys are defined per engine
                     in ``docs/architecture/engines.md``.

        Returns:
            Output dict whose keys are defined per engine.
        """

    @property
    def name(self) -> str:
        """Return the resolved engine name."""
        return self.engine_name or type(self).__name__
