# -*- coding: utf-8 -*-
"""Build and audit offline Understat real snapshot smoke preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_understat_real_snapshot_smoke_preview import run as run_audit  # noqa: E402
from build_understat_real_snapshot_smoke_preview import build_understat_real_snapshot_smoke_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def run_workflow(base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    fixture = ROOT / "tests" / "fixtures" / "understat" / "understat_bundesliga_2024_fixture.json"
    summary = build_understat_real_snapshot_smoke_preview(local_snapshot=fixture, output_dir=base / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot", base_dir=base)
    _table, _md, rec = run_audit(manifest=summary.get("manifest_path") or None, output_dir=base / "outputs" / "diagnostics", base_dir=base)
    return {**summary, "understat_real_snapshot_smoke_status": summary["real_snapshot_status"], "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.base_dir)
    for key in ["understat_real_snapshot_smoke_status", "provider", "league", "season", "rows_normalized", "network_calls_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
