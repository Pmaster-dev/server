# Bundle Budget Policy

Defines size thresholds enforced by the headless devauto CI pipeline.

## Chunk-level budgets

| Threshold | Size | Enforcement |
|---|---|---|
| Warning | 300 kB (per JS chunk) | Vite prints a warning; build succeeds |
| Error | 500 kB (per JS chunk) | CI `check chunk size budget` step fails the build |

These limits are set in `vite.config.js` (`chunkSizeWarningLimit`) and
enforced by the inline Python size-check in `.github/workflows/headless-devauto.yml`.

## Total page weight budget

| Metric | Soft budget | Hard fail |
|---|---|---|
| Total uncompressed JS | 1 MB | Smoke test `bundle size gate` fails |
| Total transferred (all assets) | 2 MB | Manual review required |

The soft budget is verified by the Playwright smoke test in
`tests/webview/smoke.spec.js` ("Bundle size gate" suite).

## Vendor chunk splitting

Large third-party dependencies are automatically extracted into a `vendor`
chunk via the `manualChunks` rule in `vite.config.js`. This keeps the main
entry chunk small and allows browsers to cache vendor code independently.

## Sourcemaps

| Mode | Sourcemap |
|---|---|
| `development` | `true` (inline, full) |
| `production` | `"hidden"` (uploaded to error-tracking; not served publicly) |
| `analyze` | `"hidden"` |

## Trend reporting

The `devauto.report` component writes `devauto-report.json` after each run.
The `bundle.chunks` array contains per-file sizes for trend analysis.

```jsonc
{
  "bundle": {
    "chunks": [
      { "file": "index-abc123.js", "size_bytes": 42000, "size_kb": 41.0 },
      { "file": "vendor-def456.js", "size_bytes": 180000, "size_kb": 175.8 }
    ],
    "total_bytes": 222000,
    "total_kb": 216.8,
    "budget_kb": 500,
    "within_budget": true
  }
}
```

Persist `devauto-report.json` as a GitHub Actions artifact
(`devauto-report-<sha>`) to build a per-PR trend history.

## Updating budgets

Edit the constants in:
- `vite.config.js` → `CHUNK_WARN_LIMIT`, `CHUNK_ERROR_LIMIT`
- `tests/webview/smoke.spec.js` → `1024 * 1024` (total page weight gate)
- `.github/workflows/headless-devauto.yml` → inline Python `LIMIT` variable
- `src/automation/devauto.py` → `_collect_bundle_stats()` `budget_kb` field
