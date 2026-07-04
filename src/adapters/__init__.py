"""
Platform adapters for the Pmaster server automation layer.

An *adapter* is a thin, optional boundary between the core server logic and a
specific deployment target.  It can rewrite :class:`ComponentInput` before a
step executes (pre-processing) and :class:`ComponentOutput` after (post-
processing), without touching the core engine or any component implementation.

Adapters respect the :class:`~automation.profile.CapabilityProfile` of the
target platform.  The core engine remains platform-agnostic; all
platform-specific concerns live here.

Available adapters
------------------

+------------------+--------------------------------------------+
| Class            | Target platform                            |
+==================+============================================+
| CLIAdapter       | TargetPlatform.CLI                         |
+------------------+--------------------------------------------+
| IDEAdapter       | TargetPlatform.IDE                         |
+------------------+--------------------------------------------+
| WebAppAdapter    | TargetPlatform.WEB_APP                     |
+------------------+--------------------------------------------+
| OSFrameAdapter   | TargetPlatform.OS_FRAME                    |
+------------------+--------------------------------------------+
| EmbeddedAdapter  | TargetPlatform.EMBEDDED                    |
+------------------+--------------------------------------------+

Usage::

    from adapters import get_adapter
    from automation.profile import TargetPlatform

    adapter = get_adapter(TargetPlatform.WEB_APP)
    adapted_input = adapter.adapt_input(component_input)
    adapted_output = adapter.adapt_output(component_output)
"""

from .base import PlatformAdapter
from .cli import CLIAdapter
from .embedded import EmbeddedAdapter
from .ide import IDEAdapter
from .os_frame import OSFrameAdapter
from .web_app import WebAppAdapter
from automation.profile import TargetPlatform

__all__ = [
    "PlatformAdapter",
    "CLIAdapter",
    "IDEAdapter",
    "WebAppAdapter",
    "OSFrameAdapter",
    "EmbeddedAdapter",
    "get_adapter",
]

_REGISTRY = {
    TargetPlatform.CLI: CLIAdapter,
    TargetPlatform.IDE: IDEAdapter,
    TargetPlatform.WEB_APP: WebAppAdapter,
    TargetPlatform.OS_FRAME: OSFrameAdapter,
    TargetPlatform.EMBEDDED: EmbeddedAdapter,
}


def get_adapter(target: TargetPlatform) -> PlatformAdapter:
    """Return the adapter instance for *target*."""
    cls = _REGISTRY.get(target)
    if cls is None:
        raise KeyError(f"No adapter registered for platform {target!r}")
    return cls()
