"""
Outcome Engine — answers "did it work?"

Aggregates ``Outcome`` records attached to Cases, Projects, and Workflows;
computes metrics; and surfaces progress against defined success criteria.

Expected context keys
---------------------
action : str
    ``"record"`` to store a new outcome, or ``"summarise"`` to aggregate
    outcomes for a subject.
outcome_type : str
    The kind of outcome (e.g. ``"employment"`, ``"goal-achieved"``).
subject_type : str
    The kernel object type the outcome is attached to (e.g. ``"case"``).
subject_id : str
    ID of the subject.
value : any, optional
    Measured result.  Required for ``"record"``.
baseline : any, optional
    Expected or target value used for comparison.

Returned keys
-------------
outcome_id : str or None
    ID of the persisted ``Outcome`` record (``"record"`` only).
summary : dict
    Aggregated metrics by status (``"summarise"`` only).
"""

from __future__ import annotations

from typing import Any, Dict

from ._base import KernelEngine


class OutcomeEngine(KernelEngine):
    """
    Outcome Engine: domain-level outcome tracking and aggregation.

    This stub provides the interface contract.  A full implementation
    persists records to the ``outcomes`` table defined in
    ``docs/openapi/kernel.yaml``.
    """

    engine_name = "outcome"

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record a new outcome or summarise existing ones.

        Args:
            context: Must contain ``action`` (str), ``outcome_type`` (str),
                     ``subject_type`` (str), and ``subject_id`` (str).
                     For ``"record"``, also ``value``.

        Returns:
            Dict with ``outcome_id`` (record) or ``summary`` (summarise).
        """
        return {"outcome_id": None, "summary": {}}
