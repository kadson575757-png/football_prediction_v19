# -*- coding: utf-8 -*-
"""Audit Phase 18.2 provider match finder preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_human_match_pipeline_from_manual_input_preview import build_pipeline_from_manual_input  # noqa: E402
from build_manual_input_from_provider_match_finder_preview import build_manual_input_from_provider_match_finder_preview  # noqa: E402
from find_provider_match_preview import find_provider_match_preview  # noqa: E402
from validate_manual_human_match_input import validate_manual_human_match_input  # noqa: E402

PROVIDER_MATCH_FINDER_PREVIEW_READY = "PROVIDER_MATCH_FINDER_PREVIEW_READY"
BUILD_PROVIDER_MATCH_FINDER_PREVIEW = "BUILD_PROVIDER_MATCH_FINDER_PREVIEW"
FIX_PROVIDER_MATCH_FINDER_PREVIEW = "FIX_PROVIDER_MATCH_FINDER_PREVIEW"
OUTPUT_CSV = "provider_match_finder_preview_summary.csv"
OUTPUT_MD = "provider_match_finder_preview_summary.md"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _safe_path(path_text: str, base: Path, allowed_rel: str) -> bool:
    if not str(path_text).strip():
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    resolved = path.resolve()
    allowed = (base / allowed_rel).resolve()
    text = str(resolved).replace("\\", "/").lower()
    return (resolved == allowed or allowed in resolved.parents) and not any(token in text for token in PROTECTED)


def run(*, output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
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
    checks = {
        "finder_ready": finder.get("match_finder_status") == PROVIDER_MATCH_FINDER_PREVIEW_READY,
        "bridge_ready": bridge.get("manual_input_bridge_status") == "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY",
        "validation_ready": validation.get("validation_status") == "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY",
        "pipeline_ready": pipeline.get("human_match_pipeline_status") == "HUMAN_MATCH_PIPELINE_PREVIEW_READY",
        "selected_path_safe": _safe_path(str(finder.get("selected_match_output_path", "")), base, "outputs/provider_pull_preview/match_finder"),
        "manual_path_safe": _safe_path(str(bridge.get("output_path", "")), base, "outputs/analysis_preview/manual_input"),
        "pipeline_path_safe": _safe_path(str(pipeline.get("final_report_path", "")), base, "outputs/analysis_preview"),
        "network_disabled": not any(_as_bool(x.get("network_calls_enabled", False)) for x in [finder, bridge, validation, pipeline]),
        "prediction_disabled": not any(_as_bool(x.get("prediction_logic_enabled", False)) for x in [finder, bridge, validation, pipeline]),
        "betting_disabled": not any(_as_bool(x.get("betting_logic_enabled", False)) for x in [finder, bridge, validation, pipeline]),
    }
    errors = [key for key, ok in checks.items() if not ok]
    rec = PROVIDER_MATCH_FINDER_PREVIEW_READY if not errors else FIX_PROVIDER_MATCH_FINDER_PREVIEW
    row = {
        **checks,
        "match_finder_status": finder.get("match_finder_status", ""),
        "manual_input_bridge_status": bridge.get("manual_input_bridge_status", ""),
        "validation_status": validation.get("validation_status", ""),
        "human_match_pipeline_status": pipeline.get("human_match_pipeline_status", ""),
        "rows_written": bridge.get("rows_written", 0),
        "rows_reported": pipeline.get("rows_reported", 0),
        "candidates_matched": finder.get("candidates_matched", 0),
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
        "recommendation": rec,
    }
    table = pd.DataFrame([row])
    markdown = "\n".join([
        "# Phase 18.2 Provider Match Finder Preview Audit",
        "",
        f"- preview_valid: {str(row['preview_valid']).lower()}",
        f"- match_finder_status: {row['match_finder_status']}",
        f"- candidates_matched: {row['candidates_matched']}",
        "- no live network calls",
        "- no model predictions are run",
        "- no betting/staking recommendations are generated",
        "",
        "## Recommendation",
        rec,
        "",
    ])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _table, _markdown, rec = run(output_dir=args.output_dir, base_dir=args.base_dir)
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
