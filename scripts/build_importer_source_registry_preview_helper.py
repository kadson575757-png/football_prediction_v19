# -*- coding: utf-8 -*-
"""Build and audit the Phase 15.1 importer source registry preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_importer_source_registry_preview import run as run_audit  # noqa: E402
from build_importer_source_registry_preview import build_importer_source_registry_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "importer_preview"))
    parser.add_argument("--sources", default=None)
    return parser


def run_workflow(output_dir: str | Path, *, sources: str | None = None) -> dict[str, object]:
    summary = build_importer_source_registry_preview(output_dir=output_dir, write_preview=True, sources=sources, base_dir=ROOT)
    _table, _markdown, rec = run_audit(registry=summary.get("registry_output_path") or None, output_dir=ROOT / "outputs" / "diagnostics", base_dir=ROOT)
    return {**summary, "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.output_dir, sources=args.sources)
    for key in ["importer_registry_status", "sources_registered", "network_calls_enabled", "recommendation", "registry_output_path", "registry_summary_path"]:
        print(f"{key}={str(summary[key]).lower() if key == 'network_calls_enabled' else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
