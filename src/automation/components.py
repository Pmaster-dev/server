"""
Pluggable component registry for serverless automation.

Components are self-describing units of work that can be registered by name
and composed inside automation pipelines.  The registry enforces a consistent
interface while remaining fully decoupled from any specific runtime or
framework.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type


# ---------------------------------------------------------------------------
# Component contract
# ---------------------------------------------------------------------------

@dataclass
class ComponentInput:
    """Typed input envelope passed to a component."""
    name: str
    payload: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentOutput:
    """Typed output envelope returned by a component."""
    component: str
    result: Any
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Component(ABC):
    """
    Base class for all pluggable components.

    Subclass and implement :meth:`execute` to create a new component.
    Register the component with a :class:`ComponentRegistry` using
    :meth:`ComponentRegistry.register`.

    Subclasses may optionally implement:

    * :meth:`validate` – return ``(True, "")`` to accept the input or
      ``(False, "<reason>")`` to reject it before execution.
    * :meth:`setup` / :meth:`teardown` – hooks called once when the
      component is registered / deregistered.
    """

    #: Human-readable name shown in registry listings.  Defaults to the
    #: class name when not overridden.
    name: str = ""

    #: Short description surfaced by :meth:`ComponentRegistry.describe`.
    description: str = ""

    def validate(self, input_: ComponentInput) -> tuple[bool, str]:
        """
        Validate *input_* before execution.

        Returns:
            A ``(valid, reason)`` tuple.  ``valid`` is ``True`` when the
            input is acceptable.  ``reason`` is an empty string on success
            or a human-readable message on failure.
        """
        return True, ""

    @abstractmethod
    def execute(self, input_: ComponentInput) -> ComponentOutput:
        """Process *input_* and return a :class:`ComponentOutput`."""

    def setup(self) -> None:
        """Optional lifecycle hook called when the component is registered."""

    def teardown(self) -> None:
        """Optional lifecycle hook called when the component is removed."""

    # Convenience method so subclasses can build outputs without importing the class
    def _ok(self, result: Any, **meta: Any) -> ComponentOutput:
        return ComponentOutput(
            component=self.name or type(self).__name__,
            result=result,
            success=True,
            metadata=meta,
        )

    def _err(self, error: str, **meta: Any) -> ComponentOutput:
        return ComponentOutput(
            component=self.name or type(self).__name__,
            result=None,
            success=False,
            error=error,
            metadata=meta,
        )


# ---------------------------------------------------------------------------
# Function-based component adapter
# ---------------------------------------------------------------------------

class FunctionComponent(Component):
    """
    Wraps a plain callable as a :class:`Component`.

    Useful for registering lambda functions or module-level functions
    without creating a full subclass::

        def double(inp):
            return inp.payload * 2

        registry.register_fn("double", double)
    """

    def __init__(
        self,
        fn: Callable[[ComponentInput], Any],
        name: str = "",
        description: str = "",
    ) -> None:
        self.name = name or fn.__name__
        self.description = description or (inspect.getdoc(fn) or "")
        self._fn = fn

    def execute(self, input_: ComponentInput) -> ComponentOutput:
        try:
            result = self._fn(input_)
            return self._ok(result)
        except Exception as exc:
            return self._err(str(exc))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ComponentRegistry:
    """
    Central store of named :class:`Component` instances.

    Components are looked up by *name* (a plain string) so that pipelines
    can remain decoupled from concrete implementations.

    Usage::

        registry = ComponentRegistry()

        @registry.component("greet")
        class GreetComponent(Component):
            description = "Returns a greeting string."

            def execute(self, inp):
                return self._ok(f"Hello, {inp.payload}!")

        output = registry.run("greet", ComponentInput("greet", "world"))
        print(output.result)   # Hello, world!
    """

    def __init__(self) -> None:
        self._components: Dict[str, Component] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, component: Component) -> "ComponentRegistry":
        """
        Register *component* under *name*.

        Calls :meth:`Component.setup` and returns *self* for chaining.
        """
        component.name = component.name or name
        component.setup()
        self._components[name] = component
        return self

    def register_class(self, name: str, cls: Type[Component], **kwargs: Any) -> "ComponentRegistry":
        """Instantiate *cls* with **kwargs** and register the instance."""
        return self.register(name, cls(**kwargs))

    def register_fn(
        self,
        name: str,
        fn: Callable[[ComponentInput], Any],
        description: str = "",
    ) -> "ComponentRegistry":
        """Wrap *fn* in a :class:`FunctionComponent` and register it."""
        return self.register(name, FunctionComponent(fn, name=name, description=description))

    def component(self, name: str, description: str = "") -> Callable[[Type[Component]], Type[Component]]:
        """
        Class decorator that registers a component under *name*::

            @registry.component("my_step")
            class MyStep(Component):
                ...
        """
        def _decorator(cls: Type[Component]) -> Type[Component]:
            if description:
                cls.description = description
            self.register_class(name, cls)
            return cls

        return _decorator

    def deregister(self, name: str) -> bool:
        """
        Remove the component registered as *name*.

        Calls :meth:`Component.teardown` if found.  Returns ``True`` when
        a component was removed.
        """
        component = self._components.pop(name, None)
        if component is not None:
            component.teardown()
            return True
        return False

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self, name: str, input_: ComponentInput) -> ComponentOutput:
        """
        Execute the component registered as *name*.

        Validates the input first; returns an error output if the component
        is not found or validation fails.
        """
        component = self._components.get(name)
        if component is None:
            return ComponentOutput(
                component=name,
                result=None,
                success=False,
                error=f"Component '{name}' not registered",
            )

        valid, reason = component.validate(input_)
        if not valid:
            return ComponentOutput(
                component=name,
                result=None,
                success=False,
                error=f"Validation failed: {reason}",
            )

        return component.execute(input_)

    def run_pipeline(
        self,
        steps: List[str],
        initial_payload: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[ComponentOutput]:
        """
        Run a sequential pipeline of named components.

        Each step's ``result`` is forwarded as the ``payload`` of the next
        step's :class:`ComponentInput`.  Execution stops on the first
        failure encountered.

        Args:
            steps: Ordered list of registered component names.
            initial_payload: Payload for the first step.
            metadata: Optional metadata forwarded to every step.

        Returns:
            List of :class:`ComponentOutput` objects, one per step executed.
            The list may be shorter than *steps* if a failure occurred early.
        """
        outputs: List[ComponentOutput] = []
        payload = initial_payload
        meta = metadata or {}

        for step in steps:
            inp = ComponentInput(name=step, payload=payload, metadata=meta)
            out = self.run(step, inp)
            outputs.append(out)
            if not out.success:
                break
            payload = out.result

        return outputs

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def names(self) -> List[str]:
        """Return registered component names."""
        return list(self._components.keys())

    def get(self, name: str) -> Optional[Component]:
        """Return the component registered as *name*, or ``None``."""
        return self._components.get(name)

    def describe(self, name: str) -> str:
        """Return the description of the component registered as *name*."""
        component = self._components.get(name)
        if component is None:
            return f"(no component named '{name}')"
        return component.description or "(no description)"

    def describe_all(self) -> Dict[str, str]:
        """Return a mapping of name → description for every registered component."""
        return {name: (c.description or "") for name, c in self._components.items()}

    def __contains__(self, name: str) -> bool:
        return name in self._components

    def __len__(self) -> int:
        return len(self._components)

    def __repr__(self) -> str:
        return f"ComponentRegistry({list(self._components.keys())!r})"
