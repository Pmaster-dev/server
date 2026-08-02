"""
Decision Engine — answers "why?"

Evaluates a decision policy (rule-based or AI-driven) against the current
context and records a ``Decision`` with full rationale, actor, and timestamp.

Expected context keys
---------------------
decision_type : str
    The kind of decision to evaluate (e.g. ``"eligibility"``,
    ``"accommodation-approval"``).
subject : dict
    The entity being evaluated (e.g. a Person or Case record).
accessibility : dict, optional
    AccessibilityProfile of the relevant user, forwarded to the policy
    so rationale can reference language/communication context.
policy_version : str, optional
    Pin a specific policy version.  Defaults to ``"latest"``.

Returned keys
-------------
decision_id : str or None
    ID of the persisted ``Decision`` record.
choice : str
    The resolved option or value.
rationale : str
    Human-readable explanation of the decision.
policy_version : str
    The policy version that was applied.
"""

from __future__ import annotations

from typing import Any, Dict

from ._base import KernelEngine


class DecisionEngine(KernelEngine):
    """
    Decision Engine: auditable, policy-driven decision recording.

    This stub provides the interface contract.  A full implementation
    persists records to the ``decisions`` table defined in
    ``docs/openapi/kernel.yaml``.
    """

    engine_name = "decision"

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a decision policy and record the result.

        Args:
            context: Must contain ``decision_type`` (str) and ``subject``
                     (dict).  May contain ``accessibility`` and
                     ``policy_version``.

        Returns:
            Dict with ``decision_id``, ``choice``, ``rationale``, and
            ``policy_version``.
        """
        return {
            "decision_id": None,
            "choice": "",
            "rationale": "",
            "policy_version": "latest",
        }
