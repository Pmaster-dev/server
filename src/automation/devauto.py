"""
Headless devauto automation components for Pmaster AI Operator.

Registers build, test, and report components into the shared
AutomationEngine so that the devauto pipeline can be triggered
programmatically from any Python context.

Usage (standalone)::

    from automation.devauto import run_report
    import json
    print(json.dumps(run_report(), indent=2, default=str))

Usage (via the default engine)::

    from automation import trigger
    results = trigger("devauto.full")
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List

from .components import Component, ComponentInput, ComponentOutput
from .engine import AutomationDefinition, AutomationEngine, TriggerEvent

# ---------------------------------------------------------------------------
# Engine instance for devauto
# ---------------------------------------------------------------------------

devauto_engine = AutomationEngine()

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
DIST_DIR = REPO_ROOT / "dist"

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _shell(cmd: List[str], cwd: pathlib.Path = REPO_ROOT) -> Dict[str, Any]:
    """Run a shell command and return a result dict."""
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": "timeout"}
    except FileNotFoundError as exc:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": str(exc)}


def _collect_bundle_stats() -> Dict[str, Any]:
    """Collect size statistics for all JS chunks in dist/assets/."""
    assets_dir = DIST_DIR / "assets"
    stats: List[Dict[str, Any]] = []
    total_bytes = 0

    if assets_dir.exists():
        for f in sorted(assets_dir.glob("*.js")):
            sz = f.stat().st_size
            total_bytes += sz
            stats.append({"file": f.name, "size_bytes": sz, "size_kb": round(sz / 1024, 1)})

    return {
        "chunks": stats,
        "total_bytes": total_bytes,
        "total_kb": round(total_bytes / 1024, 1),
        "budget_kb": 500,
        "within_budget": total_bytes <= 500 * 1024,
    }


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------


@devauto_engine.component("devauto.build", "Run Vite production build via npm")
class BuildComponent(Component):
    name = "devauto.build"
    description = "Install Node deps and run Vite production build."

    def validate(self, input_: ComponentInput):  # type: ignore[override]
        if not (REPO_ROOT / "package.json").exists():
            return False, "package.json not found – frontend not set up"
        return True, ""

    def execute(self, input_: ComponentInput) -> ComponentOutput:
        node_env = os.environ.get("NODE_ENV", "production")
        env = {**os.environ, "NODE_ENV": node_env}

        # npm ci (deterministic) with fallback to npm install
        install = subprocess.run(
            ["npm", "ci", "--prefer-offline"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
        )
        if install.returncode != 0:
            install = subprocess.run(
                ["npm", "install"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=180,
                env=env,
            )

        if install.returncode != 0:
            return ComponentOutput(
                component=self.name,
                result=None,
                success=False,
                error=f"npm install failed:\n{install.stderr}",
            )

        build = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        success = build.returncode == 0
        bundle_stats = _collect_bundle_stats() if success else {}
        return ComponentOutput(
            component=self.name,
            result={
                "stdout": build.stdout,
                "stderr": build.stderr,
                "bundle": bundle_stats,
            },
            success=success,
            error=build.stderr if not success else None,
        )


@devauto_engine.component("devauto.smoke", "Run headless Playwright smoke tests")
class SmokeComponent(Component):
    name = "devauto.smoke"
    description = "Execute headless Playwright webview smoke tests."

    def execute(self, input_: ComponentInput) -> ComponentOutput:
        result = _shell(["npx", "playwright", "test", "--reporter=list"])
        return ComponentOutput(
            component=self.name,
            result=result,
            success=result["success"],
            error=result["stderr"] if not result["success"] else None,
        )


@devauto_engine.component("devauto.report", "Generate devauto status report JSON")
class ReportComponent(Component):
    name = "devauto.report"
    description = "Aggregate build + test results into a structured JSON report."

    def execute(self, input_: ComponentInput) -> ComponentOutput:
        prior = input_.payload or {}
        bundle = _collect_bundle_stats()
        report = {
            "generated_at": datetime.now().isoformat(),
            "repo": str(REPO_ROOT),
            "platform": sys.platform,
            "python": sys.version.split()[0],
            "bundle": bundle,
            "build_success": prior.get("build_success", None),
            "smoke_success": prior.get("smoke_success", None),
            "tasks": {
                "os_support_matrix": (REPO_ROOT / "docs" / "os-support-matrix.md").exists(),
                "bundle_budget_policy": (REPO_ROOT / "docs" / "bundle-budget.md").exists(),
                "vite_config": (REPO_ROOT / "vite.config.js").exists(),
                "smoke_tests": (REPO_ROOT / "tests" / "webview" / "smoke.spec.js").exists(),
                "ci_workflow": (REPO_ROOT / ".github" / "workflows" / "headless-devauto.yml").exists(),
                "devauto_entrypoint": (REPO_ROOT / "scripts" / "devauto.sh").exists(),
            },
            "risks": _compute_risks(bundle),
        }

        # Write report to disk
        out = REPO_ROOT / "devauto-report.json"
        out.write_text(json.dumps(report, indent=2, default=str))

        return ComponentOutput(
            component=self.name,
            result=report,
            success=True,
        )


def _compute_risks(bundle: Dict[str, Any]) -> List[str]:
    risks: List[str] = []
    if not bundle.get("within_budget"):
        risks.append(
            f"Bundle total {bundle.get('total_kb', '?')} kB exceeds 500 kB budget"
        )
    if not bundle.get("chunks"):
        risks.append("No dist/assets found – run `npm run build` first")
    return risks


# ---------------------------------------------------------------------------
# Automation definitions
# ---------------------------------------------------------------------------

devauto_engine.define(
    AutomationDefinition(
        name="devauto.full",
        triggers=["devauto.full"],
        steps=["devauto.build", "devauto.smoke", "devauto.report"],
        description="Full headless devauto pipeline: build → smoke → report",
    )
)

devauto_engine.define(
    AutomationDefinition(
        name="devauto.build-only",
        triggers=["devauto.build-only"],
        steps=["devauto.build", "devauto.report"],
        description="Build and report only (no smoke tests)",
    )
)

devauto_engine.define(
    AutomationDefinition(
        name="devauto.report-only",
        triggers=["devauto.report-only"],
        steps=["devauto.report"],
        description="Generate report from existing dist/ artefacts",
    )
)


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def run_report() -> Dict[str, Any]:
    """
    Convenience function: trigger the report-only automation and return the
    JSON-serialisable result dict.

    Example::

        from automation.devauto import run_report
        import json
        print(json.dumps(run_report(), indent=2, default=str))
    """
    results = devauto_engine.trigger(TriggerEvent("devauto.report-only"))
    if not results:
        return {"error": "No automation matched trigger 'devauto.report-only'"}
    last = results[-1]
    if last.outputs and last.outputs[-1].result:
        return last.outputs[-1].result  # type: ignore[return-value]
    return {"status": last.status.value, "error": last.error}


def run_full() -> List[Dict[str, Any]]:
    """Run the full devauto pipeline (build → smoke → report)."""
    results = devauto_engine.trigger(TriggerEvent("devauto.full"))
    return [r.to_dict() for r in results]


if __name__ == "__main__":
    import json
    print(json.dumps(run_report(), indent=2, default=str))
