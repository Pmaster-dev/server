"""
Serverless automation engine for Pmaster AI Operator.

The engine is *serverless* in the sense that it is purely function-driven:
there is no persistent background thread or network listener.  Automation
runs are triggered by explicit calls, making the engine safe to use inside
FaaS environments (AWS Lambda, Google Cloud Functions, etc.) as well as
in-process within any Python application.

Architecture::

    ┌──────────────────────────────────────────────────────┐
    │                   AutomationEngine                   │
    │                                                      │
    │  VariableRegistry  ←──  GeneratorVariable(s)         │
    │       │                                              │
    │  ComponentRegistry ←──  Component / FunctionComponent│
    │       │                                              │
    │  Trigger dispatcher                                  │
    │       │                                              │
    │  RunResult / RunHistory                              │
    └──────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .components import (
    Component,
    ComponentInput,
    ComponentOutput,
    ComponentRegistry,
    FunctionComponent,
)
from .variables import GeneratorVariable, VariableRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class RunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TriggerEvent:
    """Represents an event that can trigger an automation run."""
    event_type: str
    payload: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


@dataclass
class RunResult:
    """Result of a single automation run."""
    run_id: str
    trigger: TriggerEvent
    status: RunStatus
    outputs: List[ComponentOutput] = field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None

    @property
    def duration_ms(self) -> Optional[float]:
        """Wall-clock duration in milliseconds, or ``None`` if not finished."""
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return delta.total_seconds() * 1000
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "trigger": {
                "event_type": self.trigger.event_type,
                "event_id": self.trigger.event_id,
                "timestamp": self.trigger.timestamp.isoformat(),
            },
            "status": self.status.value,
            "outputs": [
                {
                    "component": o.component,
                    "success": o.success,
                    "error": o.error,
                }
                for o in self.outputs
            ],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Automation definition
# ---------------------------------------------------------------------------

@dataclass
class AutomationDefinition:
    """
    Declarative description of an automation.

    An automation is defined by:

    * A *name* (unique identifier).
    * A list of *triggers*: event type strings that activate the automation.
    * An ordered list of *steps*: component names executed in sequence.
    * Optional *variables*: names from the :class:`VariableRegistry` that are
      injected into each step's ``metadata`` before execution.
    """
    name: str
    triggers: List[str]
    steps: List[str]
    variables: List[str] = field(default_factory=list)
    description: str = ""
    enabled: bool = True


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class AutomationEngine:
    """
    Serverless automation engine.

    The engine binds together a :class:`ComponentRegistry` (what to run) and a
    :class:`VariableRegistry` (runtime data), wires up event-based dispatch,
    and keeps a lightweight run history.

    Usage::

        engine = AutomationEngine()

        # Register a component
        engine.components.register_fn("echo", lambda inp: inp.payload)

        # Define an automation
        engine.define(AutomationDefinition(
            name="on_hello",
            triggers=["hello"],
            steps=["echo"],
        ))

        # Fire an event
        result = engine.trigger(TriggerEvent("hello", payload="world"))
        print(result[0].status)   # RunStatus.SUCCESS
    """

    def __init__(self) -> None:
        self.components = ComponentRegistry()
        self.variables = VariableRegistry()

        self._automations: Dict[str, AutomationDefinition] = {}
        self._history: List[RunResult] = []

        # Middleware hooks: callables invoked before/after each run
        self._before_run: List[Callable[[RunResult, TriggerEvent], None]] = []
        self._after_run: List[Callable[[RunResult], None]] = []

    # ------------------------------------------------------------------
    # Component & variable shortcuts
    # ------------------------------------------------------------------

    def component(self, name: str, description: str = "") -> Callable:
        """Decorator that registers a :class:`Component` subclass."""
        return self.components.component(name, description)

    def register_fn(
        self,
        name: str,
        fn: Callable[[ComponentInput], Any],
        description: str = "",
    ) -> "AutomationEngine":
        """Register a plain callable as a component. Returns self."""
        self.components.register_fn(name, fn, description)
        return self

    def define_variable(
        self,
        name: str,
        factory: Callable,
    ) -> GeneratorVariable:
        """Create a generator variable and add it to the variable registry."""
        return self.variables.define(name, factory)

    # ------------------------------------------------------------------
    # Automation registration
    # ------------------------------------------------------------------

    def define(self, automation: AutomationDefinition) -> "AutomationEngine":
        """Register an automation definition. Returns self for chaining."""
        self._automations[automation.name] = automation
        return self

    def undefine(self, name: str) -> bool:
        """Remove an automation by name. Returns ``True`` if it existed."""
        return self._automations.pop(name, None) is not None

    def enable(self, name: str) -> None:
        """Enable a previously disabled automation."""
        if name in self._automations:
            self._automations[name].enabled = True

    def disable(self, name: str) -> None:
        """Disable an automation without removing it."""
        if name in self._automations:
            self._automations[name].enabled = False

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    def before_run(self, fn: Callable[[RunResult, TriggerEvent], None]) -> Callable:
        """Register a hook called just before each automation run starts."""
        self._before_run.append(fn)
        return fn

    def after_run(self, fn: Callable[[RunResult], None]) -> Callable:
        """Register a hook called just after each automation run finishes."""
        self._after_run.append(fn)
        return fn

    # ------------------------------------------------------------------
    # Triggering
    # ------------------------------------------------------------------

    def trigger(self, event: TriggerEvent) -> List[RunResult]:
        """
        Dispatch *event* to all matching, enabled automations.

        Returns the list of :class:`RunResult` objects produced (one per
        matching automation).
        """
        results: List[RunResult] = []

        for automation in self._automations.values():
            if not automation.enabled:
                continue
            if event.event_type not in automation.triggers:
                continue
            result = self._run(automation, event)
            results.append(result)

        return results

    def trigger_type(self, event_type: str, payload: Any = None, **metadata: Any) -> List[RunResult]:
        """Convenience wrapper: build a :class:`TriggerEvent` and dispatch it."""
        event = TriggerEvent(event_type=event_type, payload=payload, metadata=metadata)
        return self.trigger(event)

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _run(self, automation: AutomationDefinition, event: TriggerEvent) -> RunResult:
        """Execute a single automation in response to *event*."""
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        result = RunResult(
            run_id=run_id,
            trigger=event,
            status=RunStatus.PENDING,
        )

        # Before-run hooks
        for hook in self._before_run:
            try:
                hook(result, event)
            except Exception:
                logger.exception("before_run hook %r raised an exception", hook)

        result.started_at = datetime.now()
        result.status = RunStatus.RUNNING

        try:
            # Build variable snapshot for this run
            var_snapshot = self._snapshot_variables(automation.variables)

            # Merge event metadata with variable snapshot
            run_meta: Dict[str, Any] = {**event.metadata, "variables": var_snapshot}

            # Execute the component pipeline
            outputs = self.components.run_pipeline(
                steps=automation.steps,
                initial_payload=event.payload,
                metadata=run_meta,
            )
            result.outputs = outputs

            # Determine overall status
            if outputs and not outputs[-1].success:
                result.status = RunStatus.FAILED
                result.error = outputs[-1].error
            else:
                result.status = RunStatus.SUCCESS

        except Exception as exc:
            result.status = RunStatus.FAILED
            result.error = f"{type(exc).__name__}: {exc}"
            result.outputs.append(
                ComponentOutput(
                    component="__engine__",
                    result=None,
                    success=False,
                    error=traceback.format_exc(),
                )
            )

        result.finished_at = datetime.now()
        self._history.append(result)

        # After-run hooks
        for hook in self._after_run:
            try:
                hook(result)
            except Exception:
                logger.exception("after_run hook %r raised an exception", hook)

        return result

    def _snapshot_variables(self, names: List[str]) -> Dict[str, Any]:
        """
        Peek at the next value of each named variable.

        Values are peeked (not consumed) so the same run can be replayed
        without advancing the generators.
        """
        snapshot: Dict[str, Any] = {}
        for name in names:
            snapshot[name] = self.variables.require(name).peek()
        return snapshot

    # ------------------------------------------------------------------
    # History & introspection
    # ------------------------------------------------------------------

    def history(self, limit: Optional[int] = None) -> List[RunResult]:
        """Return run history, most-recent first, optionally limited."""
        runs = list(reversed(self._history))
        return runs[:limit] if limit is not None else runs

    def automations(self) -> Dict[str, AutomationDefinition]:
        """Return a copy of the registered automations map."""
        return dict(self._automations)

    def stats(self) -> Dict[str, Any]:
        """Return aggregate run statistics."""
        total = len(self._history)
        by_status: Dict[str, int] = {}
        for run in self._history:
            key = run.status.value
            by_status[key] = by_status.get(key, 0) + 1

        return {
            "total_runs": total,
            "automations": len(self._automations),
            "components": len(self.components),
            "variables": len(self.variables),
            "by_status": by_status,
        }

    def __repr__(self) -> str:
        return (
            f"AutomationEngine("
            f"automations={len(self._automations)}, "
            f"components={len(self.components)}, "
            f"variables={len(self.variables)})"
        )


# ---------------------------------------------------------------------------
# Module-level default engine
# ---------------------------------------------------------------------------

#: Default engine instance – use this for simple single-engine setups.
default_engine = AutomationEngine()


def trigger(event_type: str, payload: Any = None, **metadata: Any) -> List[RunResult]:
    """Trigger *event_type* on the module-level :data:`default_engine`."""
    return default_engine.trigger_type(event_type, payload=payload, **metadata)
