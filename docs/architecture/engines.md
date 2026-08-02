# MBTQ Kernel — Engine Capabilities

The six engines below are the missing kernel capabilities identified in the
MBTQ Business OS architecture.  Every product—dashboards, AI agents,
mobile apps, sign-language models—sits **on top of** these foundations.

See [`kernel.md`](kernel.md) for the data model they operate on.

---

## 1. Registry Engine

**Responsibility:** Answer "what exists?" — maintain a live index of every
kernel object (Person, Organization, Case, etc.) and expose it for lookup,
search, and enumeration.

**Input:** object type + optional filter criteria  
**Output:** list of matching kernel object references (id, type, summary)

**Existing coverage in `src/automation`:**  
`ComponentRegistry` already implements a named-object registry pattern
(register, deregister, lookup by name).  The kernel `RegistryEngine` extends
this pattern to persistent, typed kernel objects.

---

## 2. Event Store Engine

**Responsibility:** Answer "what happened?" — append-only log of every
`Event` in the system.  Events are immutable facts.  Nothing is deleted;
state is derived by replaying events.

**Input:** `Event` record (type, actor, subject, timestamp, payload)  
**Output:** event id; query interface returns ordered event streams

**Existing coverage in `src/automation`:**  
`AutomationEngine.trigger_type` already emits `TriggerEvent` objects that
carry `event_type`, `event_id`, and `timestamp`.  The kernel `EventStoreEngine`
generalises this into a durable, queryable log.

---

## 3. Workflow Engine

**Responsibility:** Answer "what's next?" — resolve the current state of a
`Workflow` instance, advance it on incoming events, and emit the next
required action.

**Input:** workflow template name + current state + triggering event  
**Output:** next step(s) to execute; updated workflow state

**Existing coverage in `src/automation`:**  
`AutomationEngine` + `AutomationDefinition` already model trigger→steps
pipelines.  The kernel `WorkflowEngine` adds state persistence, branching,
and multi-step advancement on top of that foundation.

---

## 4. Decision Engine

**Responsibility:** Answer "why?" — evaluate a decision policy (rule-based
or AI-driven) against the current context and record a `Decision` with full
rationale, actor, and timestamp.

**Input:** decision type + context (Person, Case, Event, accessibility profile)  
**Output:** `Decision` record (choice, confidence, rationale, policy version)

**Existing coverage in `src/automation`:**  
`Component.validate` already implements a binary decision contract
`(bool, reason)`.  The kernel `DecisionEngine` generalises this into a
multi-valued, auditable decision record stored in the `decisions` table.

---

## 5. Document Engine

**Responsibility:** Answer "prove it" — manage the lifecycle of every
`Document`: creation, versioning, format conversion, accessibility
rendering, and archival.

**Input:** document payload + metadata (type, owner, format, accessibility profile)  
**Output:** `Document` record with storage reference, version, and rendered variants

**Existing coverage in `src/automation`:**  
`TextFileGuardrail` already enforces input validation rules on file payloads.
The kernel `DocumentEngine` extends this to full document lifecycle management
with accessibility-aware rendering.

---

## 6. Outcome Engine

**Responsibility:** Answer "did it work?" — aggregate `Outcome` records
attached to Cases, Projects, and Workflows; compute metrics; and surface
progress against defined success criteria.

**Input:** outcome type + subject reference (Case id, Project id, etc.) + measured value  
**Output:** `Outcome` record; summary metrics; comparison against baseline

**Existing coverage in `src/automation`:**  
`RunResult` already captures `status`, `outputs`, `started_at`,
`finished_at`, and `duration_ms` for each automation run—the same shape as
an `Outcome`.  The kernel `OutcomeEngine` generalises this to domain-level
outcome tracking.
