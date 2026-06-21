# -*- coding: utf-8 -*-
"""Audit context bundle to enriched human report preview flow."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview  # noqa: E402
from build_context_enriched_human_report_preview import build_context_enriched_human_report_preview  # noqa: E402
from build_match_context_bundle_preview import build_match_context_bundle_preview  # noqa: E402
from football_prediction_v19.analysis.context_bundle_human_input_bridge_preview import CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY, MANIFEST_COLUMNS as BRIDGE_MANIFEST_COLUMNS  # noqa: E402
from football_prediction_v19.analysis.context_enriched_human_report_preview import CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY, MANIFEST_COLUMNS as REPORT_MANIFEST_COLUMNS  # noqa: E402
from football_prediction_v19.analysis.match_context_bundle_preview import MANIFEST_COLUMNS as BUNDLE_MANIFEST_COLUMNS, MATCH_CONTEXT_BUNDLE_PREVIEW_READY  # noqa: E402

CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW_READY = "CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW_READY"
BUILD_CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW = "BUILD_CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW"
FIX_CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW = "FIX_CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW"
OUTPUT_CSV = "context_bundle_to_human_report_preview_summary.csv"
OUTPUT_MD = "context_bundle_to_human_report_preview_summary.md"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"} if not isinstance(value, bool) else value


def _under(path_text: str, base: Path, rel: str) -> bool:
    if not str(path_text).strip():
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    try:
        resolved = path.resolve()
    except OSError:
        return False
    allowed = (base / rel).resolve()
    return resolved == allowed or allowed in resolved.parents


def _protected(path_text: str) -> bool:
    text = str(path_text).replace("\\", "/").lower()
    return any(token in text for token in PROTECTED)


def audit_manifests(*, bundle_manifest: str | Path, bridge_manifest: str | Path, report_manifest: str | Path, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    bundle = pd.read_csv(bundle_manifest, low_memory=False)
    bridge = pd.read_csv(bridge_manifest, low_memory=False)
    report = pd.read_csv(report_manifest, low_memory=False)
    if not set(BUNDLE_MANIFEST_COLUMNS).issubset(bundle.columns):
        errors.append("BUNDLE_MANIFEST_COLUMNS_MISSING")
    if not set(BRIDGE_MANIFEST_COLUMNS).issubset(bridge.columns):
        errors.append("BRIDGE_MANIFEST_COLUMNS_MISSING")
    if not set(REPORT_MANIFEST_COLUMNS).issubset(report.columns):
        errors.append("REPORT_MANIFEST_COLUMNS_MISSING")
    status_ok = (
        str(bundle.get("context_bundle_status", pd.Series([""])).iloc[0]) == MATCH_CONTEXT_BUNDLE_PREVIEW_READY
        and str(bridge.get("context_bridge_status", pd.Series([""])).iloc[0]) == CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY
        and str(report.get("context_report_status", pd.Series([""])).iloc[0]) == CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY
    )
    rows_ok = int(bundle.get("rows_joined", pd.Series([0])).iloc[0]) == 1 and int(bridge.get("rows_written", pd.Series([0])).iloc[0]) == 1 and int(report.get("rows_reported", pd.Series([0])).iloc[0]) == 1
    sections_ok = int(report.get("sections_rendered", pd.Series([0])).iloc[0]) >= 8
    network = any(_as_bool(v) for v in list(bundle.get("network_calls_enabled", [])) + list(bridge.get("network_calls_enabled", [])) + list(report.get("network_calls_enabled", [])))
    prediction = any(_as_bool(v) for v in list(bundle.get("prediction_logic_enabled", [])) + list(bridge.get("prediction_logic_enabled", [])) + list(report.get("prediction_logic_enabled", [])))
    betting = any(_as_bool(v) for v in list(bundle.get("betting_logic_enabled", [])) + list(bridge.get("betting_logic_enabled", [])) + list(report.get("betting_logic_enabled", [])))
    paths = [str(bundle.get("output_path", pd.Series([""])).iloc[0]), str(bridge.get("human_input_output_path", pd.Series([""])).iloc[0]), str(report.get("report_output_path", pd.Series([""])).iloc[0])]
    paths_safe = all(_under(path, base, "outputs/analysis_preview") and not _protected(path) and Path(path).exists() for path in paths)
    for ok, label in [(status_ok, "STATUS_NOT_READY"), (rows_ok, "ROW_COUNTS_NOT_READY"), (sections_ok, "SECTIONS_TOO_LOW"), (not network, "NETWORK_ENABLED"), (not prediction, "PREDICTION_ENABLED"), (not betting, "BETTING_ENABLED"), (paths_safe, "UNSAFE_OUTPUT_PATH")]:
        if not ok:
            errors.append(label)
    return {
        "bundle_manifest": str(bundle_manifest),
        "bridge_manifest": str(bridge_manifest),
        "report_manifest": str(report_manifest),
        "context_bundle_status": str(bundle.get("context_bundle_status", pd.Series([""])).iloc[0]),
        "context_bridge_status": str(bridge.get("context_bridge_status", pd.Series([""])).iloc[0]),
        "context_report_status": str(report.get("context_report_status", pd.Series([""])).iloc[0]),
        "rows_joined": int(bundle.get("rows_joined", pd.Series([0])).iloc[0]),
        "rows_written": int(bridge.get("rows_written", pd.Series([0])).iloc[0]),
        "rows_reported": int(report.get("rows_reported", pd.Series([0])).iloc[0]),
        "sections_rendered": int(report.get("sections_rendered", pd.Series([0])).iloc[0]),
        "network_calls_enabled": network,
        "prediction_logic_enabled": prediction,
        "betting_logic_enabled": betting,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW
    if table["preview_valid"].any():
        return CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW_READY
    return FIX_CONTEXT_BUNDLE_TO_HUMAN_REPORT_PREVIEW


def run(*, report_manifest: str | Path | None = None, bridge_manifest: str | Path | None = None, bundle_manifest: str | Path | None = None, output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    if not (report_manifest and bridge_manifest and bundle_manifest):
        bundle = build_match_context_bundle_preview(cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "match_context_bundle", base_dir=base)
        bridge = build_context_bundle_human_input_bridge_preview(match_context_bundle_path=bundle.get("output_path"), cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=base, build_missing=False)
        report = build_context_enriched_human_report_preview(context_human_input_path=bridge.get("human_input_output_path"), output_dir=base / "outputs" / "analysis_preview" / "context_enriched_human_report", base_dir=base, build_missing=False)
        bundle_manifest, bridge_manifest, report_manifest = bundle.get("manifest_path"), bridge.get("manifest_path"), report.get("manifest_path")
    rows = [audit_manifests(bundle_manifest=bundle_manifest, bridge_manifest=bridge_manifest, report_manifest=report_manifest, base_dir=base)] if report_manifest and bridge_manifest and bundle_manifest else []
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = "\n".join([
        "# Phase 20.2 Context Bundle To Human Report Preview Audit",
        "",
        f"- flows audited: {len(table)}",
        f"- valid flows: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "- network_calls_enabled=false",
        "- prediction_logic_enabled=false",
        "- betting_logic_enabled=false",
        "- no model/probability/market/betting/staking/ROI/SUPER_A_TIER logic is invoked",
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
    table, _markdown, rec = run(output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
