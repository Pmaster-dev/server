# MBTQ Kernel — Data Model

The MBTQ Business OS is not a collection of apps.  Every product—DeafAuth,
PinkSync, VR4Deaf, FibonRose, MagicianCore—is a **view** into the same
underlying system.  This document defines that system: its kernel objects,
core database tables, and the accessibility-as-metadata pattern that
influences every interaction.

---

## 11 Kernel Objects

Everything that can happen in MBTQ is expressible as a combination of these
objects:

| Object | Description |
|---|---|
| **Person** | Any human actor: client, employee, contractor, partner |
| **Organization** | Any institutional actor: employer, agency, vendor, partner org |
| **Case** | A tracked interaction between a Person and an Organization (e.g. VR intake) |
| **Project** | A time-boxed unit of work owned by a Person or Organization |
| **Service** | A defined offering provided by an Organization |
| **Accommodation** | An accessibility or reasonable-accommodation record attached to a Person |
| **Document** | Any file, form, report, or artifact produced or consumed by the system |
| **Workflow** | A reusable sequence of steps governing how work moves forward |
| **Decision** | A recorded choice made by a person, agent, or policy rule |
| **Outcome** | A measurable result tied to a Case, Project, or Workflow |
| **Event** | An immutable fact that something happened (source of truth for the Event Store) |

### Composite examples

| Role | Kernel composition |
|---|---|
| VR Client | Person + Accommodation + Workflow + Outcome |
| Entrepreneur | Person + Project + Document + Outcome |
| Vendor | Organization + Service + Document |
| State Agency | Organization + Workflow + Document + Outcome |
| MagicianCore trigger | Event + Decision + Workflow |

---

## 8 Core Database Tables

A minimal schema from which all products extend:

```sql
users           -- identity + accessibility profile
organizations   -- institutional actors
workflows       -- reusable step templates
events          -- append-only fact log
documents       -- files and structured forms
accommodations  -- per-user accessibility records
decisions       -- recorded choices with rationale
outcomes        -- measured results
```

All domain tables (cases, projects, services, etc.) are **extensions** of
these eight—either as join tables, typed sub-records, or views.

---

## Accessibility as Metadata

Accessibility is not a feature module.  It is a **profile attached to every
user** that influences every engine, workflow, document, and communication in
the system.

```json
{
  "user_id": "123",
  "preferred_language": "ASL",
  "communication_mode": "video",
  "captions_required": true,
  "screen_reader": false,
  "preferred_format": "plain-text"
}
```

Every engine reads this profile before acting.  A workflow that sends a
notification checks `communication_mode`.  A document engine checks
`preferred_format`.  A decision engine logs the language context with every
`Decision` record.

---

## Relationship to `src/kernel`

The Python package at `src/kernel/` implements the six engine capabilities
described in [`engines.md`](engines.md).  The 8 core tables above define
the shared persistence contract published in
[`../openapi/kernel.yaml`](../openapi/kernel.yaml).
