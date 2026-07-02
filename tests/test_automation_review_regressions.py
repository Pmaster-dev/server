from automation import __doc__ as automation_doc
from automation.components import Component, ComponentInput, ComponentRegistry, FunctionComponent
from automation.engine import AutomationDefinition, AutomationEngine, RunStatus
from automation.variables import GeneratorVariable


def test_collect_includes_peeked_value():
    variable = GeneratorVariable.from_iterable([1, 2, 3])

    assert variable.peek() == 1
    assert variable.collect() == [1, 2, 3]


class _LifecycleComponent(Component):
    def __init__(self, events, label):
        self._events = events
        self._label = label

    def setup(self) -> None:
        self._events.append(f"{self._label}-setup")

    def teardown(self) -> None:
        self._events.append(f"{self._label}-teardown")

    def execute(self, input_: ComponentInput):
        return self._ok(input_.payload)


def test_register_replaces_component_with_teardown():
    events = []
    registry = ComponentRegistry()

    registry.register("step", _LifecycleComponent(events, "old"))
    registry.register("step", _LifecycleComponent(events, "new"))

    assert events == ["old-setup", "old-teardown", "new-setup"]


def test_function_component_returns_traceback_on_failure():
    def broken(input_):
        del input_
        raise RuntimeError("boom")

    output = FunctionComponent(broken, name="broken").execute(
        ComponentInput(name="broken", payload=None)
    )

    assert output.success is False
    assert output.error is not None
    assert "Traceback" in output.error
    assert "RuntimeError: boom" in output.error


def test_missing_variables_fail_run_instead_of_being_silently_dropped():
    engine = AutomationEngine()
    engine.register_fn("echo", lambda input_: input_.payload)
    engine.define(
        AutomationDefinition(
            name="uses-missing-variable",
            triggers=["demo"],
            steps=["echo"],
            variables=["missing"],
        )
    )

    [result] = engine.trigger_type("demo", payload="hello")

    assert result.status is RunStatus.FAILED
    assert result.error is not None
    assert "Variable 'missing' not found in registry" in result.error
    assert result.outputs[0].component == "__engine__"
    assert result.outputs[0].success is False


def test_quick_start_uses_package_imports():
    assert automation_doc is not None
    assert "from automation import AutomationEngine" in automation_doc
    assert "from src.automation import" not in automation_doc
