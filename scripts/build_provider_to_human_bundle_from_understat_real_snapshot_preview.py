# -*- coding: utf-8 -*-
"""Run provider-to-human bundle from an Understat real snapshot normalized preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_human_match_pipeline_from_manual_input_preview import build_pipeline_from_manual_input  # noqa: E402
from build_manual_input_from_provider_match_finder_preview import build_manual_input_from_provider_match_finder_preview  # noqa: E402
from find_provider_match_preview import find_provider_match_preview  # noqa: E402
from validate_manual_human_match_input import validate_manual_human_match_input  # noqa: E402

PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_READY = "PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_READY"
PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_MISSING_NORMALIZED_INPUT = "PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_MISSING_NORMALIZED_INPUT"
PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_MATCH_FINDER = "PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_MATCH_FINDER"
PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_MANUAL_BRIDGE = "PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_MANUAL_BRIDGE"
PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_VALIDATION = "PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_VALIDATION"
PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_HUMAN_PIPELINE = "PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_HUMAN_PIPELINE"
PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_UNSAFE_PATH = "PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_UNSAFE_PATH"
PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_NETWORK_DISABLED_BY_DESIGN = "PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_NETWORK_DISABLED_BY_DESIGN"
PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_MODEL_DISABLED_BY_DESIGN = "PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_MODEL_DISABLED_BY_DESIGN"
PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BETTING_DISABLED_BY_DESIGN = "PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BETTING_DISABLED_BY_DESIGN"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-input", default=None)
    parser.add_argument("--provider-match-id", default=None)
    parser.add_argument("--home-team", default=None)
    parser.add_argument("--away-team", default=None)
    parser.add_argument("--match-date", default=None)
    parser.add_argument("--alias-registry", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "provider_to_human_real_snapshot_bundle"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_bundle_from_real_snapshot(**kwargs) -> dict[str, object]:
    base = Path(kwargs.get("base_dir", ROOT)).resolve()
    out = _safe_output(kwargs.get("output_dir", base / "outputs" / "analysis_preview" / "provider_to_human_real_snapshot_bundle"), base)
    if out is None:
        return _summary(PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_UNSAFE_PATH)
    source = Path(kwargs.get("normalized_input") or base / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot" / "normalized" / "understat_real_snapshot_normalized.csv")
    if not source.is_absolute():
        source = base / source
    if not source.exists():
        return _summary(PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_MISSING_NORMALIZED_INPUT)
    finder = find_provider_match_preview(normalized_input=source, provider_match_id=kwargs.get("provider_match_id"), home_team=kwargs.get("home_team"), away_team=kwargs.get("away_team"), match_date=kwargs.get("match_date"), alias_registry=kwargs.get("alias_registry"), output_dir=base / "outputs" / "provider_pull_preview" / "match_finder", base_dir=base, build_missing=False)
    if finder["match_finder_status"] != "PROVIDER_MATCH_FINDER_PREVIEW_READY":
        return _summary(PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_MATCH_FINDER, finder=finder)
    bridge = build_manual_input_from_provider_match_finder_preview(selected_match=finder["selected_match_output_path"], output_dir=base / "outputs" / "analysis_preview" / "manual_input", base_dir=base)
    if bridge["manual_input_bridge_status"] != "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY":
        return _summary(PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_MANUAL_BRIDGE, finder=finder, bridge=bridge)
    validation = validate_manual_human_match_input(input_path=bridge["output_path"], output_dir=base / "outputs" / "analysis_preview" / "manual_input", base_dir=base)
    if validation["validation_status"] != "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY":
        return _summary(PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_VALIDATION, finder=finder, bridge=bridge, validation=validation)
    pipeline = build_pipeline_from_manual_input(input_path=bridge["output_path"], output_dir=base / "outputs" / "analysis_preview" / "human_match_pipeline", base_dir=base)
    if pipeline["human_match_pipeline_status"] != "HUMAN_MATCH_PIPELINE_PREVIEW_READY":
        return _summary(PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_BLOCKED_HUMAN_PIPELINE, finder=finder, bridge=bridge, validation=validation, pipeline=pipeline)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{**finder, **bridge, **validation, **pipeline, "real_snapshot_bundle_status": PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_READY}]).to_csv(out / "provider_to_human_real_snapshot_bundle_summary.csv", index=False)
    return _summary(PROVIDER_TO_HUMAN_REAL_SNAPSHOT_BUNDLE_READY, finder=finder, bridge=bridge, validation=validation, pipeline=pipeline)


def _summary(status: str, *, finder=None, bridge=None, validation=None, pipeline=None) -> dict[str, object]:
    finder = finder or {}
    bridge = bridge or {}
    validation = validation or {}
    pipeline = pipeline or {}
    return {
        "real_snapshot_bundle_status": status,
        "provider_match_id": finder.get("provider_match_id", ""),
        "match_finder_status": finder.get("match_finder_status", ""),
        "manual_input_bridge_status": bridge.get("manual_input_bridge_status", ""),
        "validation_status": validation.get("validation_status", ""),
        "human_match_pipeline_status": pipeline.get("human_match_pipeline_status", ""),
        "rows_reported": pipeline.get("rows_reported", 0),
        "steps_failed": pipeline.get("steps_failed", 0),
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "final_report_path": pipeline.get("final_report_path", ""),
        "recommendation": status,
    }


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "provider_to_human_real_snapshot_bundle").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_bundle_from_real_snapshot(normalized_input=args.normalized_input, provider_match_id=args.provider_match_id, home_team=args.home_team, away_team=args.away_team, match_date=args.match_date, alias_registry=args.alias_registry, output_dir=args.output_dir, base_dir=args.base_dir)
    for key in ["real_snapshot_bundle_status", "provider_match_id", "match_finder_status", "manual_input_bridge_status", "validation_status", "human_match_pipeline_status", "rows_reported", "steps_failed", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "final_report_path", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
