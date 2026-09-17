from automation.engine import AutomationEngine, AutomationDefinition, TriggerEvent, RunStatus


def test_automation_engine_basic_flow():
    engine = AutomationEngine()
    engine.register_fn("greet", lambda inp: f"Hello, {inp.payload}!")
    engine.define(AutomationDefinition(name="hello", triggers=["user.request"], steps=["greet"]))
    results = engine.trigger_type("user.request", payload="world")
    assert len(results) == 1
    assert results[0].status == RunStatus.SUCCESS
    assert results[0].outputs[0].result == "Hello, world!"
