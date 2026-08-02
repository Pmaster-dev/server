import pytest

from automation import __doc__ as automation_doc
from automation import EngineNotStartedError
from automation.components import Component, ComponentInput, ComponentRegistry, FunctionComponent
from automation.engine import AutomationDefinition, AutomationEngine, RunStatus
from automation.guardrails import DEFAULT_TEXT_EXTENSIONS, TextFileGuardrail
from automation.variables import GeneratorVariable


def test_collect_includes_peeked_value():
    variable = GeneratorVariable.from_iterable([1, 2, 3])

    assert variable.peek() == 1
    assert variable.collect() == [1, 2, 3]


class LifecycleHelperComponent(Component):
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

    registry.register("step", LifecycleHelperComponent(events, "old"))
    registry.register("step", LifecycleHelperComponent(events, "new"))
    assert registry.deregister("step") is True

    assert events == ["old-setup", "old-teardown", "new-setup", "new-teardown"]


def test_function_component_returns_traceback_on_failure():
    def broken(input_):
        assert input_.name == "broken"
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
    engine.start()
    engine.register_fn("echo", lambda input_: input_.payload)
    engine.define(
        AutomationDefinition(
            name="uses-missing-variable",
            triggers=["demo"],
            steps=["echo"],
            variables=["missing"],
        )
    )

    results = engine.trigger_type("demo", payload="hello")

    assert len(results) == 1
    result = results[0]
    assert result.status is RunStatus.FAILED
    assert result.error is not None
    assert "KeyError" in result.error
    assert "Variable 'missing' not found in registry" in result.error
    assert result.outputs[0].component == "__engine__"
    assert result.outputs[0].success is False


def test_quick_start_uses_package_imports():
    assert isinstance(automation_doc, str)
    assert automation_doc.strip()
    assert "from automation import AutomationEngine" in automation_doc
    assert "from src.automation import" not in automation_doc


# ---------------------------------------------------------------------------
# Lifecycle guardrail: start / stop
# ---------------------------------------------------------------------------

def test_trigger_before_start_raises_engine_not_started_error():
    engine = AutomationEngine()
    engine.register_fn("echo", lambda inp: inp.payload)
    engine.define(AutomationDefinition(name="a", triggers=["x"], steps=["echo"]))

    with pytest.raises(EngineNotStartedError, match="start\\(\\)"):
        engine.trigger_type("x")


def test_trigger_after_start_succeeds():
    engine = AutomationEngine()
    engine.start()
    engine.register_fn("echo", lambda inp: inp.payload)
    engine.define(AutomationDefinition(name="a", triggers=["x"], steps=["echo"]))

    results = engine.trigger_type("x", payload="hello")
    assert len(results) == 1
    assert results[0].status is RunStatus.SUCCESS


def test_trigger_after_stop_raises_engine_not_started_error():
    engine = AutomationEngine()
    engine.start()
    engine.stop()

    with pytest.raises(EngineNotStartedError):
        engine.trigger_type("x")


def test_start_is_idempotent():
    engine = AutomationEngine()
    engine.start()
    engine.start()  # second call must not raise
    assert engine.is_running is True


def test_start_emits_debug_log(caplog):
    engine = AutomationEngine()

    with caplog.at_level("DEBUG", logger="automation.engine"):
        engine.start()

    start_logs = [
        record for record in caplog.records
        if record.name == "automation.engine" and record.message == "AutomationEngine started"
    ]
    assert len(start_logs) == 1
    assert start_logs[0].levelname == "DEBUG"


def test_stop_calls_component_teardown():
    events = []

    class TrackedComponent(Component):
        def teardown(self):
            events.append("teardown")

        def execute(self, input_: ComponentInput):
            return self._ok(input_.payload)

    engine = AutomationEngine()
    engine.start()
    engine.components.register("tracked", TrackedComponent())
    engine.stop()

    assert "teardown" in events
    assert engine.is_running is False


def test_restart_after_stop_works():
    engine = AutomationEngine()
    engine.start()
    engine.stop()
    engine.start()
    engine.register_fn("echo", lambda inp: inp.payload)
    engine.define(AutomationDefinition(name="a", triggers=["x"], steps=["echo"]))

    results = engine.trigger_type("x", payload="hi")
    assert results[0].status is RunStatus.SUCCESS


# ---------------------------------------------------------------------------
# TextFileGuardrail
# ---------------------------------------------------------------------------

def test_text_file_guardrail_passes_valid_txt():
    guardrail = TextFileGuardrail()
    inp = ComponentInput(name="guard", payload="notes.txt")
    valid, reason = guardrail.validate(inp)
    assert valid is True
    assert reason == ""


def test_text_file_guardrail_passes_through_payload_on_execute():
    guardrail = TextFileGuardrail()
    inp = ComponentInput(name="guard", payload="report.csv")
    out = guardrail.execute(inp)
    assert out.success is True
    assert out.result == "report.csv"


def test_text_file_guardrail_rejects_path_traversal():
    guardrail = TextFileGuardrail()
    for path in ["../secrets.txt", "a/../../etc/passwd.txt", "..\\config.txt"]:
        inp = ComponentInput(name="guard", payload=path)
        valid, reason = guardrail.validate(inp)
        assert valid is False, f"Expected rejection for {path!r}"
        assert "traversal" in reason.lower() or ".." in reason


def test_text_file_guardrail_rejects_disallowed_extension():
    guardrail = TextFileGuardrail()
    inp = ComponentInput(name="guard", payload="script.exe")
    valid, reason = guardrail.validate(inp)
    assert valid is False
    assert "extension" in reason.lower()


def test_text_file_guardrail_rejects_absolute_path():
    guardrail = TextFileGuardrail(allow_absolute=False)
    inp = ComponentInput(name="guard", payload="/etc/hosts.txt")
    valid, reason = guardrail.validate(inp)
    assert valid is False
    assert "absolute" in reason.lower()


def test_text_file_guardrail_allows_absolute_when_configured():
    guardrail = TextFileGuardrail(allow_absolute=True)
    inp = ComponentInput(name="guard", payload="/var/log/app.log")
    valid, reason = guardrail.validate(inp)
    assert valid is True


def test_text_file_guardrail_rejects_null_byte():
    guardrail = TextFileGuardrail()
    inp = ComponentInput(name="guard", payload="file\x00.txt")
    valid, reason = guardrail.validate(inp)
    assert valid is False
    assert "null" in reason.lower()


def test_text_file_guardrail_rejects_non_string_payload():
    guardrail = TextFileGuardrail()
    inp = ComponentInput(name="guard", payload=12345)
    valid, reason = guardrail.validate(inp)
    assert valid is False
    assert "string" in reason.lower()


def test_text_file_guardrail_in_pipeline_blocks_bad_payload():
    engine = AutomationEngine()
    engine.start()
    engine.components.register("guard", TextFileGuardrail())
    engine.register_fn("process", lambda inp: f"processed:{inp.payload}")
    engine.define(AutomationDefinition(
        name="safe_process",
        triggers=["file.process"],
        steps=["guard", "process"],
    ))

    results = engine.trigger_type("file.process", payload="../bad.txt")
    assert len(results) == 1
    assert results[0].status is RunStatus.FAILED


def test_text_file_guardrail_in_pipeline_passes_valid_payload():
    engine = AutomationEngine()
    engine.start()
    engine.components.register("guard", TextFileGuardrail())
    engine.register_fn("process", lambda inp: f"processed:{inp.payload}")
    engine.define(AutomationDefinition(
        name="safe_process",
        triggers=["file.process"],
        steps=["guard", "process"],
    ))

    results = engine.trigger_type("file.process", payload="data.txt")
    assert len(results) == 1
    assert results[0].status is RunStatus.SUCCESS


def test_default_text_extensions_contains_txt():
    assert ".txt" in DEFAULT_TEXT_EXTENSIONS
