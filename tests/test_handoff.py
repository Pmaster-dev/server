from handoff.handoff import HandoffManager, HandoffStatus


def test_handoff_manager_flow():
    manager = HandoffManager()
    context = manager.initiate_handoff(
        task_id="task:100",
        source_agent="agent-a",
        target_agent="agent-b",
        task_state={"step": 1},
    )
    assert context.handoff_id is not None
    assert manager.prepare_handoff(context.handoff_id) is True
    assert manager.transmit_handoff(context.handoff_id) is True
    assert manager.receive_handoff(context.handoff_id) is True
    assert manager.accept_handoff(context.handoff_id) is True
    assert manager.complete_handoff(context.handoff_id) is True
    assert manager.get_handoff_status(context.handoff_id) == HandoffStatus.COMPLETED
