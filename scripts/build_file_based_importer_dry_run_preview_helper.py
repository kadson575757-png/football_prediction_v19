# -*- coding: utf-8 -*-
"""Build and audit the Phase 15.4 file-based importer dry-run preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_file_based_importer_dry_run_preview import run as run_audit  # noqa: E402
from build_file_based_importer_dry_run_preview import build_file_based_importer_dry_run_preview  # noqa: E402
from build_importer_schema_contracts_preview import build_importer_schema_contracts_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "importer_preview"))
    return parser


def run_workflow(output_dir: str | Path) -> dict[str, object]:
    contracts = build_importer_schema_contracts_preview(output_dir=output_dir, write_preview=True, base_dir=ROOT)
    summary = build_file_based_importer_dry_run_preview(
        contracts=contracts.get("contracts_output_path") or "",
        output_dir=output_dir,
        write_preview=True,
        base_dir=ROOT,
    )
    _table, _markdown, rec = run_audit(preview=summary.get("preview_output_path") or None, output_dir=ROOT / "outputs" / "diagnostics", base_dir=ROOT)
    return {**summary, "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.output_dir)
    for key in ["file_importer_status", "rows_input", "rows_normalized", "network_calls_enabled", "recommendation", "normalized_output_path"]:
        print(f"{key}={str(summary[key]).lower() if key == 'network_calls_enabled' else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

