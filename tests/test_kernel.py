"""
Smoke tests for src/kernel — one test per engine module.

Each test asserts:
1. The engine class is importable via the package public API.
2. It is a subclass of KernelEngine.
3. It exposes a callable ``process`` method.
4. ``process`` returns a dict when called with a minimal valid context.
"""

import pytest

from kernel import (
    KernelEngine,
    RegistryEngine,
    EventStoreEngine,
    WorkflowEngine,
    DecisionEngine,
    DocumentEngine,
    OutcomeEngine,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_kernel_engine(cls) -> bool:
    return issubclass(cls, KernelEngine)


def _has_process(instance) -> bool:
    return callable(getattr(instance, "process", None))


# ---------------------------------------------------------------------------
# RegistryEngine
# ---------------------------------------------------------------------------

def test_registry_engine_is_kernel_engine():
    assert _is_kernel_engine(RegistryEngine)


def test_registry_engine_has_process():
    assert _has_process(RegistryEngine())


def test_registry_engine_process_returns_dict():
    result = RegistryEngine().process({"object_type": "user"})
    assert isinstance(result, dict)
    assert "results" in result
    assert "total" in result


def test_registry_engine_name():
    assert RegistryEngine().name == "registry"


# ---------------------------------------------------------------------------
# EventStoreEngine
# ---------------------------------------------------------------------------

def test_event_store_engine_is_kernel_engine():
    assert _is_kernel_engine(EventStoreEngine)


def test_event_store_engine_has_process():
    assert _has_process(EventStoreEngine())


def test_event_store_engine_process_returns_dict():
    result = EventStoreEngine().process({"action": "query"})
    assert isinstance(result, dict)
    assert "events" in result


def test_event_store_engine_name():
    assert EventStoreEngine().name == "event_store"


# ---------------------------------------------------------------------------
# WorkflowEngine
# ---------------------------------------------------------------------------

def test_workflow_engine_is_kernel_engine():
    assert _is_kernel_engine(WorkflowEngine)


def test_workflow_engine_has_process():
    assert _has_process(WorkflowEngine())


def test_workflow_engine_process_returns_dict():
    result = WorkflowEngine().process({"workflow_name": "intake"})
    assert isinstance(result, dict)
    assert "next_steps" in result
    assert "updated_state" in result


def test_workflow_engine_name():
    assert WorkflowEngine().name == "workflow"


# ---------------------------------------------------------------------------
# DecisionEngine
# ---------------------------------------------------------------------------

def test_decision_engine_is_kernel_engine():
    assert _is_kernel_engine(DecisionEngine)


def test_decision_engine_has_process():
    assert _has_process(DecisionEngine())


def test_decision_engine_process_returns_dict():
    result = DecisionEngine().process(
        {"decision_type": "eligibility", "subject": {"id": "abc"}}
    )
    assert isinstance(result, dict)
    assert "choice" in result
    assert "rationale" in result


def test_decision_engine_name():
    assert DecisionEngine().name == "decision"


# ---------------------------------------------------------------------------
# DocumentEngine
# ---------------------------------------------------------------------------

def test_document_engine_is_kernel_engine():
    assert _is_kernel_engine(DocumentEngine)


def test_document_engine_has_process():
    assert _has_process(DocumentEngine())


def test_document_engine_process_returns_dict():
    result = DocumentEngine().process(
        {"action": "create", "document": {"title": "Intake Form", "document_type": "form"}}
    )
    assert isinstance(result, dict)
    assert "document_id" in result
    assert "version" in result
    assert "storage_ref" in result


def test_document_engine_name():
    assert DocumentEngine().name == "document"


# ---------------------------------------------------------------------------
# OutcomeEngine
# ---------------------------------------------------------------------------

def test_outcome_engine_is_kernel_engine():
    assert _is_kernel_engine(OutcomeEngine)


def test_outcome_engine_has_process():
    assert _has_process(OutcomeEngine())


def test_outcome_engine_process_returns_dict():
    result = OutcomeEngine().process(
        {
            "action": "summarise",
            "outcome_type": "employment",
            "subject_type": "case",
            "subject_id": "xyz",
        }
    )
    assert isinstance(result, dict)
    assert "summary" in result


def test_outcome_engine_name():
    assert OutcomeEngine().name == "outcome"


# ---------------------------------------------------------------------------
# Package-level: __doc__ smoke test
# ---------------------------------------------------------------------------

def test_kernel_package_docstring_references_engines():
    import kernel
    assert kernel.__doc__ is not None
    assert "RegistryEngine" in kernel.__doc__
