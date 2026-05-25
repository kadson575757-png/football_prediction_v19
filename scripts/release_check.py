"""Release readiness check: doctor + pytest + run_all + docs existence."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCS = [
    "CHANGELOG.md",
    "docs/QUICKSTART.md",
    "docs/COMMANDS.md",
    "docs/DATA_REQUIREMENTS.md",
    "README.md",
]


def check_docs() -> bool:
    ok = True
    for doc in REQUIRED_DOCS:
        p = ROOT / doc
        if p.exists():
            print(f"  [OK] {doc}")
        else:
            print(f"  [MISSING] {doc}")
            ok = False
    return ok


def run_step(label: str, cmd: list[str]) -> bool:
    print(f"\n=== {label} ===")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"  [FAILED] {label}")
        return False
    return True


def main() -> None:
    steps_ok = True

    print("\n=== Docs existence check ===")
    if not check_docs():
        steps_ok = False

    if not run_step("doctor", [sys.executable, "-m", "football_prediction_v19.cli", "doctor"]):
        steps_ok = False

    if not run_step("pytest", [sys.executable, "-m", "pytest", "tests", "--tb=short", "-q"]):
        steps_ok = False

    if not run_step("run_all smoke", [sys.executable, "scripts/run_all.py"]):
        steps_ok = False

    print()
    if steps_ok:
        print("Release check passed. Ready to tag v0.1.0.")
        sys.exit(0)
    else:
        print("Release check FAILED. Fix the issues above before releasing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
