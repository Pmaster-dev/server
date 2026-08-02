"""
Workflow Engine — answers "what's next?"

Resolves the current state of a ``Workflow`` instance, advances it on
incoming events, and emits the next required action.

Expected context keys
---------------------
workflow_name : str
    Name of the workflow template to instantiate or advance.
workflow_id : str, optional
    ID of an existing workflow instance.  If omitted, a new instance is
    created.
state : dict, optional
    Current state of the workflow instance.
event : dict, optional
    Triggering event that advances the workflow.

Returned keys
-------------
workflow_id : str
    ID of the (new or existing) workflow instance.
next_steps : list[str]
    Ordered step names to execute next.
updated_state : dict
    Workflow state after advancement.
"""

from __future__ import annotations

from typing import Any, Dict

from ._base import KernelEngine


class WorkflowEngine(KernelEngine):
    """
    Workflow Engine: step-by-step advancement of workflow instances.

    This stub provides the interface contract.  A full implementation
    persists records to the ``workflows`` table and delegates step
    execution to ``src/automation/engine.py``.
    """

    engine_name = "workflow"

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or advance a workflow instance.

        Args:
            context: Must contain ``workflow_name`` (str).  May contain
                     ``workflow_id``, ``state``, and ``event``.

        Returns:
            Dict with ``workflow_id``, ``next_steps``, and
            ``updated_state``.
        """
        return {"workflow_id": None, "next_steps": [], "updated_state": {}}
