# -*- coding: utf-8 -*-
"""Build and audit Bundesliga 2024 rolling xG form reporting."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_rolling_xg_form_reporting import run as run_audit  # noqa: E402
from build_rolling_xg_form_reporting import build_rolling_xg_form_reporting  # noqa: E402

MANIFEST_ID = "trusted_xg_understat_bundesliga_2024_manual_xg"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "xg_reporting_preview"))
    return parser


def run_workflow(manifest: str | Path, output_dir: str | Path, *, window: int = 5) -> dict[str, object]:
    summary = build_rolling_xg_form_reporting(
        manifest=manifest,
        manifest_id=MANIFEST_ID,
        window=window,
        output_dir=output_dir,
        write_preview=True,
        base_dir=ROOT,
    )
    _table, _markdown, rec = run_audit(
        preview=summary.get("form_output_path") or None,
        output_dir=ROOT / "outputs" / "diagnostics",
        expected_team_match_rows=int(summary.get("team_match_rows", 0)) or 612,
        expected_teams=int(summary.get("teams_reported", 0)) or 18,
    )
    return {**summary, "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.manifest, args.output_dir, window=args.window)
    for key in [
        "form_status",
        "manifest_id",
        "teams_reported",
        "team_match_rows",
        "window",
        "rows_missing_xg",
        "recommendation",
        "form_output_path",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
