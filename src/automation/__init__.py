"""
Serverless Python automation with pluggable components and generator variables.

Quick-start::

    from automation import AutomationEngine, AutomationDefinition, TriggerEvent
    from automation import Component, ComponentInput, ComponentRegistry
    from automation import GeneratorVariable, VariableRegistry

    engine = AutomationEngine()

    # 1. Register a component
    engine.register_fn("greet", lambda inp: f"Hello, {inp.payload}!")

    # 2. Define a generator variable
    engine.define_variable("counter", lambda: (i for i in range(100)))

    # 3. Define an automation
    engine.define(AutomationDefinition(
        name="greet_on_request",
        triggers=["user.request"],
        steps=["greet"],
        variables=["counter"],
    ))

    # 4. Fire an event (serverless – no threads, no server)
    results = engine.trigger_type("user.request", payload="world")
    print(results[0].status)   # RunStatus.SUCCESS
"""

from .engine import (
    AutomationDefinition,
    AutomationEngine,
    RunResult,
    RunStatus,
    TriggerEvent,
    default_engine,
    trigger,
)
from .components import (
    Component,
    ComponentInput,
    ComponentOutput,
    ComponentRegistry,
    FunctionComponent,
)
from .variables import (
    GeneratorVariable,
    VariableRegistry,
)

__all__ = [
    # Engine
    "AutomationEngine",
    "AutomationDefinition",
    "TriggerEvent",
    "RunResult",
    "RunStatus",
    "default_engine",
    "trigger",
    # Components
    "Component",
    "ComponentInput",
    "ComponentOutput",
    "ComponentRegistry",
    "FunctionComponent",
    # Variables
    "GeneratorVariable",
    "VariableRegistry",
]
