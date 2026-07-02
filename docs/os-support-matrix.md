# OS Support Matrix

Headless devauto pipeline support across operating systems.

## Primary: Linux

| Distribution | CI/CD | Build | Smoke Tests | Notes |
|---|---|---|---|---|
| Ubuntu 22.04 LTS | ✅ | ✅ | ✅ chromium · firefox · webkit | Reference platform (GitHub Actions `ubuntu-latest`) |
| Ubuntu 20.04 LTS | ✅ | ✅ | ✅ | |
| Debian 12 (Bookworm) | ✅ | ✅ | ✅ | |
| Alpine 3.19 | ⚠️ | ✅ | ✅ chromium · firefox | WebKit deps not available on musl; use `--project=chromium --project=firefox` |
| Fedora 40 | ✅ | ✅ | ✅ | |
| Arch Linux | ✅ | ✅ | ✅ | Rolling; pin Node LTS |

## Secondary: BSD (best-effort)

WebKit is not available on BSD because the upstream Playwright binaries are
compiled for Linux/macOS only. All other functionality is supported.

| Platform | Build | Smoke Tests | Notes |
|---|---|---|---|
| FreeBSD 14 | ✅ | ✅ chromium · firefox | `pkg install chromium firefox`; skip `--project=webkit` |
| OpenBSD 7.5 | ⚠️ | ⚠️ chromium only | Firefox headless may be unreliable; chromium via `pkg_add` |
| NetBSD 10 | ⚠️ | ⚠️ chromium only | Limited pkgsrc support |
| DragonFly BSD 6.4 | 🔬 experimental | 🔬 experimental | Community-only; no CI lane |

### Running on BSD

```bash
# Skip webkit project
npx playwright test --project=chromium --project=firefox

# Or use the devauto entrypoint (detects BSD automatically)
bash scripts/devauto.sh test
```

### BSD-specific `devauto.sh` behaviour

`scripts/devauto.sh` detects the OS via `uname -s` and:
- Skips `npx playwright install webkit` on FreeBSD, OpenBSD, NetBSD.
- Passes `--project=chromium --project=firefox` to the test runner.

## macOS (developer machines)

| Version | Build | Smoke Tests |
|---|---|---|
| macOS 14 Sonoma | ✅ | ✅ all browsers |
| macOS 13 Ventura | ✅ | ✅ all browsers |

## Not supported

| OS | Reason |
|---|---|
| Windows | No CI lane; contributions welcome |
| iOS / Android | Out of scope (native webview toolchain differs) |

---

## Node & Python version requirements

| Runtime | Minimum | Recommended |
|---|---|---|
| Node.js | 18 LTS | 20 LTS |
| npm | 9 | 10 |
| Python | 3.10 | 3.11 |
