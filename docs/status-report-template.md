# Devauto Status Report Template

Copy and fill in this template for each sprint or pipeline run.

---

## Run metadata

| Field | Value |
|---|---|
| Report date | `YYYY-MM-DD HH:MM UTC` |
| Git SHA | `<commit-sha>` |
| Branch | `<branch-name>` |
| Triggered by | `push \| PR \| manual` |
| Platform | `linux \| freebsd \| macos` |
| Pipeline run URL | `https://github.com/Pmaster-dev/server/actions/runs/<run-id>` |

---

## Task checklist

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | OS support matrix reviewed | ✅ / ⚠️ / ❌ | |
| 2 | Headless workflow executed | ✅ / ⚠️ / ❌ | |
| 3 | Vite build completed | ✅ / ⚠️ / ❌ | |
| 4 | Chunk size budget passed | ✅ / ⚠️ / ❌ | |
| 5 | Webview smoke tests passed | ✅ / ⚠️ / ❌ | |
| 6 | Python automation report generated | ✅ / ⚠️ / ❌ | |
| 7 | Artifacts uploaded | ✅ / ⚠️ / ❌ | |

---

## Build results

| Metric | Value |
|---|---|
| Build status | `SUCCESS \| FAILED` |
| Build duration | `XX s` |
| Entry chunk | `assets/index-<hash>.js` — `XX kB` |
| Vendor chunk | `assets/vendor-<hash>.js` — `XX kB` |
| Total bundle size | `XX kB` (budget: 500 kB) |
| Within budget | `YES \| NO` |

---

## Smoke test results

| Browser | Passed | Failed | Skipped |
|---|---|---|---|
| Chromium | X | X | X |
| Firefox | X | X | X |
| WebKit | X | X | X (BSD: skipped) |

**Total:** X / X passed

### Failures (if any)

```
<paste Playwright failure output here>
```

---

## Risks & blockers

| # | Severity | Description | Owner | Status |
|---|---|---|---|---|
| 1 | HIGH / MED / LOW | `<description>` | `@handle` | Open / In progress / Resolved |

---

## Next sprint actions

- [ ] `<action 1>`
- [ ] `<action 2>`
- [ ] `<action 3>`

---

## Automated JSON report location

Artifact: `devauto-report-<sha>` → `devauto-report.json`

```jsonc
// Preview of devauto-report.json fields:
{
  "generated_at": "...",
  "bundle": { "total_kb": 0, "within_budget": true, "chunks": [] },
  "tasks": { "vite_config": true, "smoke_tests": true, ... },
  "risks": []
}
```
