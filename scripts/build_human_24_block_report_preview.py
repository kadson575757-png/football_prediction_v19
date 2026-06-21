# -*- coding: utf-8 -*-
"""Build preview-only 24-block human match report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview  # noqa: E402
from football_prediction_v19.analysis.human_24_block_report_preview import Human24BlockReportConfig, Human24BlockReportRenderer  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-human-input", default=None)
    parser.add_argument("--v19-diagnostic-synthesis", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "human_24_block_report"))
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--build-missing", action=argparse.BooleanOptionalAction, default=True)
    return parser


def build_human_24_block_report_preview(*, context_human_input_path: str | Path | None = None, v19_diagnostic_synthesis_path: str | Path | None = None, output_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "human_24_block_report", base_dir: str | Path = ROOT, build_missing: bool = True) -> dict[str, object]:
    base = Path(base_dir).resolve()
    human_input = Path(context_human_input_path) if context_human_input_path else base / "outputs" / "analysis_preview" / "context_bundle_human_input" / "context_bundle_human_input.csv"
    if build_missing and not human_input.exists():
        bridge = build_context_bundle_human_input_bridge_preview(cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=base)
        human_input = Path(str(bridge.get("human_input_output_path", human_input)))
    result, _report = Human24BlockReportRenderer(Human24BlockReportConfig(context_human_input_path=human_input, v19_diagnostic_synthesis_path=v19_diagnostic_synthesis_path, output_dir=output_dir, base_dir=base)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_human_24_block_report_preview(context_human_input_path=args.context_human_input, v19_diagnostic_synthesis_path=args.v19_diagnostic_synthesis, output_dir=args.output_dir, base_dir=args.base_dir, build_missing=args.build_missing)
    for key in ["human_24_block_report_status", "v19_diagnostic_synthesis_status", "report_output_path", "rows_reported", "sections_rendered", "required_sections_rendered", "missing_required_fields_count", "missing_optional_fields_count", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
