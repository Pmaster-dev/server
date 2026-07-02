#!/usr/bin/env bash
# scripts/devauto.sh – Headless devauto entrypoint (Linux / BSD)
#
# Usage:
#   bash scripts/devauto.sh [command]
#
# Commands:
#   build       – Install deps & run Vite production build
#   test        – Run Playwright webview smoke tests headlessly
#   report      – Run Python automation engine report
#   full        – build → test → report  (default)
#   clean       – Remove dist/ and playwright-report/
#
# Environment variables (all optional):
#   CI                 – Set by GitHub Actions; enables strict mode
#   VITE_PREVIEW_PORT  – Preview server port (default: 4173)
#   PYTHONPATH         – Injected automatically from src/ layout
#   NODE_ENV           – Passed to Vite (default: production)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
REPORT_DIR="${REPO_ROOT}/playwright-report"
PYTHON_REPORT="${REPO_ROOT}/devauto-report.json"
NODE_ENV="${NODE_ENV:-production}"

# ── Colour helpers ────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_GREEN="\033[0;32m"; C_YELLOW="\033[0;33m"
  C_RED="\033[0;31m";   C_RESET="\033[0m"
else
  C_GREEN=""; C_YELLOW=""; C_RED=""; C_RESET=""
fi
log_info()  { echo -e "${C_GREEN}[devauto]${C_RESET} $*"; }
log_warn()  { echo -e "${C_YELLOW}[devauto]${C_RESET} $*"; }
log_error() { echo -e "${C_RED}[devauto ERROR]${C_RESET} $*" >&2; }

# ── OS detection ──────────────────────────────────────────────────────────────
OS="$(uname -s)"
case "${OS}" in
  Linux*)   PLATFORM="linux" ;;
  FreeBSD*) PLATFORM="freebsd" ;;
  OpenBSD*) PLATFORM="openbsd" ;;
  NetBSD*)  PLATFORM="netbsd" ;;
  Darwin*)  PLATFORM="macos" ;;
  *)        PLATFORM="unknown" ;;
esac
log_info "Platform detected: ${PLATFORM}"

# ── Dependency checks ─────────────────────────────────────────────────────────
require_cmd() {
  if ! command -v "$1" &>/dev/null; then
    log_error "Required command not found: $1"
    exit 1
  fi
}

require_cmd node
require_cmd npm
require_cmd python3

# ── Commands ──────────────────────────────────────────────────────────────────

cmd_build() {
  log_info "Installing Node dependencies…"
  npm ci --prefer-offline 2>/dev/null || npm install
  log_info "Running Vite build (NODE_ENV=${NODE_ENV})…"
  NODE_ENV="${NODE_ENV}" npm run build
  log_info "Build complete → ${DIST_DIR}"
}

cmd_test() {
  log_info "Running headless Playwright smoke tests…"

  # WebKit binaries are not available on BSD; skip that project
  if [[ "${PLATFORM}" == freebsd* ]] || [[ "${PLATFORM}" == openbsd* ]] || [[ "${PLATFORM}" == netbsd* ]]; then
    log_warn "BSD detected – skipping WebKit project"
    PLAYWRIGHT_ARGS="--project=chromium --project=firefox"
  else
    PLAYWRIGHT_ARGS=""
  fi

  # Install browser binaries if not already present (CI)
  if [[ "${CI:-}" == "true" ]]; then
    npx playwright install --with-deps chromium firefox || true
    [[ "${PLATFORM}" != *bsd* ]] && npx playwright install --with-deps webkit || true
  fi

  # shellcheck disable=SC2086
  npx playwright test ${PLAYWRIGHT_ARGS}
  log_info "Smoke tests passed → ${REPORT_DIR}"
}

cmd_report() {
  log_info "Generating Python automation devauto report…"
  PYTHONPATH="${REPO_ROOT}/src" python3 - <<'PYEOF'
import json, sys, datetime, pathlib

# Import the devauto automation components
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src") if "__file__" in dir() else "src")
from automation.devauto import run_report

result = run_report()
out_path = pathlib.Path("devauto-report.json")
out_path.write_text(json.dumps(result, indent=2, default=str))
print(f"Report written to {out_path}")
PYEOF
  log_info "Python report complete → ${PYTHON_REPORT}"
}

cmd_full() {
  cmd_build
  cmd_test
  cmd_report
  log_info "Full devauto pipeline complete ✓"
}

cmd_clean() {
  log_info "Cleaning build artifacts…"
  rm -rf "${DIST_DIR}" "${REPORT_DIR}" "${PYTHON_REPORT}"
  log_info "Clean complete"
}

# ── Dispatch ──────────────────────────────────────────────────────────────────

COMMAND="${1:-full}"

case "${COMMAND}" in
  build)   cmd_build ;;
  test)    cmd_test ;;
  report)  cmd_report ;;
  full)    cmd_full ;;
  clean)   cmd_clean ;;
  *)
    log_error "Unknown command: ${COMMAND}"
    echo "Usage: $0 [build|test|report|full|clean]"
    exit 1
    ;;
esac
