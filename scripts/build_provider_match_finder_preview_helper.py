# -*- coding: utf-8 -*-
"""Build full Phase 18.2 provider match finder preview workflow."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_provider_match_finder_preview import run as run_audit  # noqa: E402
from build_human_match_pipeline_from_manual_input_preview import build_pipeline_from_manual_input  # noqa: E402
from build_manual_input_from_provider_match_finder_preview import build_manual_input_from_provider_match_finder_preview  # noqa: E402
from find_provider_match_preview import find_provider_match_preview  # noqa: E402
from validate_manual_human_match_input import validate_manual_human_match_input  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def run_workflow(base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    finder = find_provider_match_preview(
        provider_match_id="u-bundesliga-2024-001",
        output_dir=base / "outputs" / "provider_pull_preview" / "match_finder",
        base_dir=base,
    )
    bridge = build_manual_input_from_provider_match_finder_preview(
        output_dir=base / "outputs" / "analysis_preview" / "manual_input",
        base_dir=base,
    )
    validation = validate_manual_human_match_input(input_path=bridge.get("output_path", ""), output_dir=base / "outputs" / "analysis_preview" / "manual_input", base_dir=base)
    pipeline = build_pipeline_from_manual_input(input_path=bridge.get("output_path", ""), output_dir=base / "outputs" / "analysis_preview" / "human_match_pipeline", base_dir=base)
    _table, _markdown, rec = run_audit(output_dir=base / "outputs" / "diagnostics", base_dir=base)
    return {
        **finder,
        **bridge,
        **validation,
        **pipeline,
        "provider_match_finder_status": finder.get("match_finder_status", ""),
        "recommendation": rec,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.base_dir)
    for key in [
        "provider_match_finder_status",
        "manual_input_bridge_status",
        "validation_status",
        "human_match_pipeline_status",
        "rows_written",
        "rows_reported",
        "candidates_matched",
        "network_calls_enabled",
        "prediction_logic_enabled",
        "betting_logic_enabled",
        "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
