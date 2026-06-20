# -*- coding: utf-8 -*-
"""Build and audit the Phase 15.3 importer adapter interface preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_importer_adapter_interface_preview import run as run_audit  # noqa: E402
from build_importer_adapter_interface_preview import build_importer_adapter_interface_preview  # noqa: E402
from build_importer_schema_contracts_preview import build_importer_schema_contracts_preview  # noqa: E402
from build_importer_source_registry_preview import build_importer_source_registry_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "importer_preview"))
    return parser


def run_workflow(output_dir: str | Path) -> dict[str, object]:
    registry = build_importer_source_registry_preview(output_dir=output_dir, write_preview=True, base_dir=ROOT)
    contracts = build_importer_schema_contracts_preview(registry=registry.get("registry_output_path") or "", output_dir=output_dir, write_preview=True, base_dir=ROOT)
    summary = build_importer_adapter_interface_preview(
        registry=registry.get("registry_output_path") or "",
        contracts=contracts.get("contracts_output_path") or "",
        output_dir=output_dir,
        write_preview=True,
        base_dir=ROOT,
    )
    _table, _markdown, rec = run_audit(preview=summary.get("adapter_output_path") or None, output_dir=ROOT / "outputs" / "diagnostics", base_dir=ROOT)
    return {**summary, "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.output_dir)
    for key in ["importer_adapter_interface_status", "adapters_registered", "network_calls_enabled", "recommendation", "adapter_output_path", "adapter_summary_path"]:
        print(f"{key}={str(summary[key]).lower() if key == 'network_calls_enabled' else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
