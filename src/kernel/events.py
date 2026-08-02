"""
Event Store Engine — answers "what happened?"

Append-only log of every ``Event`` in the system.  Events are immutable
facts; state is derived by replaying them.

Expected context keys
---------------------
action : str
    ``"append"`` to record a new event, or ``"query"`` to retrieve events.
event : dict, optional
    Required when ``action == "append"``.  Must include ``event_type`` and
    ``occurred_at``; may include ``actor_id``, ``subject_type``,
    ``subject_id``, and ``payload``.
filters : dict, optional
    Used when ``action == "query"`` to narrow the event stream.

Returned keys
-------------
event_id : str or None
    ID assigned to the appended event (``action == "append"`` only).
events : list[dict]
    Ordered event records (``action == "query"`` only).
"""

from __future__ import annotations

from typing import Any, Dict

from ._base import KernelEngine


class EventStoreEngine(KernelEngine):
    """
    Event Store Engine: immutable, append-only fact log.

    This stub provides the interface contract.  A full implementation
    persists records to the ``events`` table defined in
    ``docs/openapi/kernel.yaml``.
    """

    engine_name = "event_store"

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append or query events in the event store.

        Args:
            context: Must contain ``action`` (``"append"`` | ``"query"``).
                     For ``"append"``, must also contain ``event`` (dict).

        Returns:
            Dict with ``event_id`` (append) or ``events`` (query).
        """
        return {"event_id": None, "events": []}
