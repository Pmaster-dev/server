# pinkycollie + Pmaster-dev ecosystem inventory

## Objective

Maintain `pinkycollie` product repos and `Pmaster-dev` infrastructure repos as one coordinated ecosystem with shared CI/CD, API contracts, and automation flows.

## Ecosystem snapshot

| Org | Key repos | Current role |
|---|---|---|
| `pinkycollie` | `pinkflow`, `deaf-first-platform`, `mbtq-dev`, `NegraRosa`, `VR4Deaf` | Product/application layer with broad TS + Python footprint |
| `Pmaster-dev` | `server`, `docs`, `actions`, `electron`, `.github` | Infrastructure/automation layer, reusable tooling, shared contracts |

## Layer 1 — single source of truth for templates

- Keep `Pmaster-dev/.github` as the org template hub:
  - shared `CODEOWNERS`
  - reusable workflows in `ci/` and `deployments/`
  - shared pre-commit config
- Mirror the same model in `pinkycollie` using `pinkycollie/pinkflow` as the workflow hub.
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

| Instance | Pmaster-dev | pinkycollie |
|---|---|---|
| API server | `server/src/automation` | `pinkflow/webapp/backend` |
| API docs | `docs/openapi/` | `pinkflow/API.md` (migrate to OpenAPI) |
| Desktop client | `electron` | — |
| CI action | `actions/action.yml` | `pinkflow/.github/workflows/PinkFlow-pipeline.yml` |
| Marketing/docs site | — | `pinkflow/marketing-site/` |
| Web app | — | `pinkflow/webapp/frontend/` |
| Auth layer | — | `Nextjs-DeafAUTH` |

## Layer 4 — integration method rule

- Default to **REST** for user-initiated synchronous CRUD flows.
- Use **Webhook** for asynchronous automation events (CI, release, cross-repo signals).
- Defer **gRPC/tRPC** until latency/throughput needs justify protocol expansion.

## Layer 5 — cross-org webhook bridge

Reference flow:

`Pmaster-dev/* push/release` → `Pmaster-dev/actions` → dispatch/webhook to `pinkycollie/pinkflow` → update workflow state → run downstream checks → report status back to source PR/check.

## Layer 6 — versioned artifacts

- Machine-readable contracts: `Pmaster-dev/docs/openapi/*.yaml`
- Human-readable operational docs: `pinkflow/docs/`, `pinkflow/workflow-system/docs/`
- Agent/system context: `pinkflow/context/agents.md`
- Cross-org map (this file): `server/docs/pinkycollie-ecosystem-inventory.md`

## Priority sequence

1. Commit this ecosystem inventory document in `Pmaster-dev/server`.
2. Publish shared automation OpenAPI contracts under `docs/openapi/`.
3. Refactor duplicated `pinkflow` workflows into reusable `workflow_call` units.
4. Wire webhook bridge from `Pmaster-dev/actions` to `pinkflow/waitthenecho`.
5. Standardize framework package versions (Next.js/React) across frontend repos.
