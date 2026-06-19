# -*- coding: utf-8 -*-
"""Build the Bundesliga 2024 manifest-backed xG readiness report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_manifest_xg_readiness import run  # noqa: E402

MANIFEST_ID = "trusted_xg_understat_bundesliga_2024_manual_xg"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def run_report(manifest: str | Path, output_dir: str | Path) -> dict[str, object]:
    table, _markdown, rec = run(
        manifest=manifest,
        manifest_id=MANIFEST_ID,
        output_dir=output_dir,
        base_dir=ROOT,
    )
    if table.empty:
        return {
            "manifest_id": MANIFEST_ID,
            "rows_target": 0,
            "rows_enriched": 0,
            "rows_missing_xg": 0,
            "join_coverage_pct": 0.0,
            "readiness_status": "",
            "model_integration_status": "",
            "recommendation": rec,
        }
    row = table.iloc[0].to_dict()
    return {**row, "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_report(args.manifest, args.output_dir)
    for key in [
        "manifest_id",
        "rows_target",
        "rows_enriched",
        "rows_missing_xg",
        "join_coverage_pct",
        "readiness_status",
        "model_integration_status",
        "recommendation",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
