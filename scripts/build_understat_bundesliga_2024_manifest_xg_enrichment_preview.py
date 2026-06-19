# -*- coding: utf-8 -*-
"""Build and audit the Bundesliga 2024 manifest-backed xG enrichment preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_manifest_xg_enrichment_preview import run as run_audit  # noqa: E402
from build_manifest_xg_enrichment_preview import build_manifest_xg_enrichment_preview  # noqa: E402

MANIFEST_ID = "trusted_xg_understat_bundesliga_2024_manual_xg"
TARGET = ROOT / "data" / "processed" / "football_data_D1_2024_clean.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "xg_enrichment_preview"))
    return parser


def run_workflow(manifest: str | Path, output_dir: str | Path) -> dict[str, object]:
    summary = build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id=MANIFEST_ID,
        target=TARGET,
        output_dir=output_dir,
        write_preview=True,
        base_dir=ROOT,
    )
    preview = summary.get("preview_output_path") or None
    _table, _markdown, rec = run_audit(
        preview=preview,
        target=TARGET,
        expected_rows=306,
        output_dir=ROOT / "outputs" / "diagnostics",
    )
    return {**summary, "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.manifest, args.output_dir)
    for key in [
        "enrichment_status",
        "manifest_id",
        "rows_target",
        "rows_enriched",
        "rows_missing_xg",
        "join_coverage_pct",
        "recommendation",
        "preview_output_path",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
