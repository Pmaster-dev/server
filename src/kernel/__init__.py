"""
MBTQ Kernel — six engine capabilities for the Business OS.

Quick-start::

    from kernel import (
        RegistryEngine,
        EventStoreEngine,
        WorkflowEngine,
        DecisionEngine,
        DocumentEngine,
        OutcomeEngine,
    )

    registry = RegistryEngine()
    result = registry.process({"object_type": "user"})
    print(result["total"])   # 0 (stub)

Each engine exposes a single :meth:`~_base.KernelEngine.process` method that
accepts a context dict and returns a result dict.  See
``docs/architecture/engines.md`` for the full input/output contracts and
``docs/openapi/kernel.yaml`` for the shared data model.
"""

from .registry import RegistryEngine
from .events import EventStoreEngine
from .workflows import WorkflowEngine
from .decisions import DecisionEngine
from .documents import DocumentEngine
from .outcomes import OutcomeEngine
from ._base import KernelEngine

__all__ = [
    "KernelEngine",
    "RegistryEngine",
    "EventStoreEngine",
    "WorkflowEngine",
    "DecisionEngine",
    "DocumentEngine",
    "OutcomeEngine",
]
