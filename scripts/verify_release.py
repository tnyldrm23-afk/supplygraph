"""Run required quality gates and retain actual statuses, timings and compact outputs."""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("make_help", ["make", "help"]),
    ("format", [".venv/bin/black", "--check", "app", "scripts", "tests"]),
    ("lint", ["make", "lint"]),
    ("unit_api_security", ["make", "test"]),
    ("integration", ["make", "test-integration"]),
    ("compose_health", [".venv/bin/python", "scripts/check_containers.py"]),
]


def main():
    """Fail on any unmet gate; never convert skipped checks into success."""
    results = []
    for name, command in CHECKS:
        start = time.perf_counter()
        response = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        output = response.stdout + response.stderr
        results.append(
            {
                "name": name,
                "command": command,
                "exit_code": response.returncode,
                "passed": response.returncode == 0,
                "seconds": round(time.perf_counter() - start, 3),
                "output": output[-16000:],
            }
        )
        print(name, "PASS" if response.returncode == 0 else "FAIL", flush=True)
    lint_text = next(r["output"] for r in results if r["name"] == "lint")
    score = re.search(r"rated at ([\d.]+)/10", lint_text)
    text = next(r["output"] for r in results if r["name"] == "unit_api_security")
    coverage = re.search(r"Total coverage: ([\d.]+)%", text)
    report = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "author": "Tan YILDIRIM — B00822334",
        "checks": results,
        "pylint_score": float(score[1]) if score else None,
        "coverage_percent": float(coverage[1]) if coverage else None,
        "all_local_gates_passed": all(r["passed"] for r in results),
        "external_gates": {
            "github_code_published": False,
            "remote_ci_verified": False,
            "public_registry_anonymous_pull_verified": False,
            "merged_pr_verified": False,
        },
    }
    (ROOT / "reports/verification.json").write_text(json.dumps(report, indent=2))
    if not report["all_local_gates_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
