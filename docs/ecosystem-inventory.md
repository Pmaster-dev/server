# Pmaster-dev ecosystem inventory

## Objective

Maintain `Pmaster-dev` infrastructure repos as the core foundation for an AI-agent-first ecosystem built on `magician-core`, `a2a` (Agent-to-Agent), and the AI SDK.

## Ecosystem snapshot

| Org | Key repos | Current role |
|---|---|---|
| `360magicians` | `magician-core`, `a2a`, `magician-sdk` | Core AI agent orchestration and Agent-to-Agent protocols |
| `Pmaster-dev` | `server`, `docs`, `actions`, `electron`, `.github` | Infrastructure/automation layer, reusable tooling, shared contracts |

## Kernel Layer — single source of truth for data

All products are **views into the kernel**.  The kernel lives in `Pmaster-dev/server`.

The kernel defines:

- **11 kernel objects** — Person, Organization, Case, Project, Service, Accommodation, Document, Workflow, Decision, Outcome, Event (see [`docs/architecture/kernel.md`](architecture/kernel.md))
- **8 core tables** — `users`, `organizations`, `workflows`, `events`, `documents`, `accommodations`, `decisions`, `outcomes`
- **6 engine capabilities** — Registry, Event Store, Workflow, Decision, Document, Outcome (see [`docs/architecture/engines.md`](architecture/engines.md))
- **Shared OpenAPI contracts** — [`docs/openapi/kernel.yaml`](openapi/kernel.yaml) imported by all downstream services
- **Python implementation** — `src/kernel/` package, one module per engine

No product creates its own parallel data model.  If a concept isn't in the kernel, it is proposed here first.

---

## Layer 1 — single source of truth for templates

- Keep `Pmaster-dev/.github` as the org template hub:
  - shared `CODEOWNERS`
  - reusable workflows in `ci/` and `deployments/`
  - shared pre-commit config
- Mirror the same model in `360magicians` using `magician-core` as the workflow hub.
- Replace duplicated per-repo workflows with reusable `workflow_call` workflows.

## Layer 2 — standardized pipeline lifecycle

Standard stage order for every repo:

`[Scan/Lint] → [Build] → [Test] → [Security] → [Deploy/Publish]`

Target mapping:

- Scan: `pr-security.yml`, `semgrep.yml`, `codeql.yml`
- Lint: `pylint.yml`, `super-linter.yml`
- Build: `rust-ci.yml`, `nextjs.yml`, `deploy-marketing-site.yml`
- Test: `vitest`, `pytest`
- Deploy: `github-pages.yml`, `deploy.yml`, `release.yml`

## Layer 3 — framework instances to align

| Instance | Pmaster-dev | 360magicians |
|---|---|---|
| API server | `server/src/automation` | `magician-core` |
| API docs | `docs/openapi/` | `a2a` protocol spec |
| Desktop client | `electron` | — |
| CI action | `actions/action.yml` | `magician-sdk` |
| Marketing/docs site | — | `mbtq.dev` |
| Web app | — | `magician-sdk` frontend |
| Auth layer | — | `a2a` identity layer |

## Layer 4 — integration method rule

- Default to **REST** for user-initiated synchronous CRUD flows.
- Use **Webhook** for asynchronous automation events (CI, release, cross-repo signals).
- Defer **gRPC/tRPC** until latency/throughput needs justify protocol expansion.

## Layer 5 — cross-org webhook bridge

Reference flow:

`Pmaster-dev/* push/release` → `Pmaster-dev/actions` → dispatch/webhook to `360magicians/magician-core` → update workflow state → run downstream checks → report status back to source PR/check.

## Layer 6 — versioned artifacts

- Machine-readable contracts: `docs/openapi/*.yaml`
- Human-readable operational docs: `docs/api/`, `docs/guides/`
- Agent/system context: `magician-core` agent definitions
- Cross-org map (this file): `docs/ecosystem-inventory.md`

## Priority sequence

1. Commit this ecosystem inventory document in `Pmaster-dev/server`.
2. Publish shared automation OpenAPI contracts under `docs/openapi/`.
3. Refactor duplicated workflows into reusable `workflow_call` units.
4. Wire webhook bridge from `Pmaster-dev/actions` to `360magicians/magician-core`.
5. Standardize framework package versions across frontend repos.
