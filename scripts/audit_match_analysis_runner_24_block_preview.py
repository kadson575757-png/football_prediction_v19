# -*- coding: utf-8 -*-
"""Audit match analysis runner 24-block preview."""
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

from build_match_analysis_runner_preview import build_match_analysis_runner_preview  # noqa: E402
from football_prediction_v19.analysis.human_24_block_report_preview import REQUIRED_SECTIONS  # noqa: E402
from football_prediction_v19.analysis.match_analysis_runner_preview import MANIFEST_COLUMNS, MATCH_ANALYSIS_RUNNER_PREVIEW_READY  # noqa: E402

MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW_READY = "MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW_READY"
BUILD_MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW = "BUILD_MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW"
FIX_MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW = "FIX_MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW"
OUTPUT_CSV = "match_analysis_runner_24_block_preview_summary.csv"
OUTPUT_MD = "match_analysis_runner_24_block_preview_summary.md"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", dest="runner_manifest", default=None)
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
    resolved = path.resolve()
    allowed = (base / rel).resolve()
    return resolved == allowed or allowed in resolved.parents


def _protected(path_text: str) -> bool:
    return any(token in str(path_text).replace("\\", "/").lower() for token in PROTECTED)


def audit_manifest(path: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    manifest = pd.read_csv(path, low_memory=False)
    if not set(MANIFEST_COLUMNS).issubset(manifest.columns):
        errors.append("MANIFEST_COLUMNS_MISSING")
    row = manifest.iloc[0]
    report_path = str(row.get("report_output_path", ""))
    report_text = Path(report_path).read_text(encoding="utf-8") if report_path and Path(report_path).exists() else ""
    sections_ok = int(row.get("sections_rendered", 0)) == 24 and all(f"## {section}" in report_text for section in REQUIRED_SECTIONS)
    ready = str(row.get("match_analysis_runner_status", "")) == MATCH_ANALYSIS_RUNNER_PREVIEW_READY
    rows_ok = int(row.get("rows_joined", 0)) == 1 and int(row.get("rows_written", 0)) == 1 and int(row.get("rows_reported", 0)) == 1
    safe = _under(report_path, base, "outputs/analysis_preview") and not _protected(report_path)
    network = _as_bool(row.get("network_calls_enabled", False))
    prediction = _as_bool(row.get("prediction_logic_enabled", False))
    betting = _as_bool(row.get("betting_logic_enabled", False))
    for ok, label in [(ready, "STATUS_NOT_READY"), (rows_ok, "ROWS_NOT_READY"), (sections_ok, "SECTIONS_NOT_READY"), (safe, "UNSAFE_REPORT_PATH"), (not network, "NETWORK_ENABLED"), (not prediction, "PREDICTION_ENABLED"), (not betting, "BETTING_ENABLED")]:
        if not ok:
            errors.append(label)
    return {
        "runner_manifest": str(path),
        "match_analysis_runner_status": str(row.get("match_analysis_runner_status", "")),
        "rows_joined": int(row.get("rows_joined", 0)),
        "rows_written": int(row.get("rows_written", 0)),
        "rows_reported": int(row.get("rows_reported", 0)),
        "sections_rendered": int(row.get("sections_rendered", 0)),
        "required_sections_rendered": sum(1 for section in REQUIRED_SECTIONS if f"## {section}" in report_text),
        "network_calls_enabled": network,
        "prediction_logic_enabled": prediction,
        "betting_logic_enabled": betting,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW
    if table["preview_valid"].any():
        return MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW_READY
    return FIX_MATCH_ANALYSIS_RUNNER_24_BLOCK_PREVIEW


def run(*, runner_manifest: str | Path | None = None, output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    manifest = Path(runner_manifest) if runner_manifest else None
    if manifest is None or not manifest.exists():
        summary = build_match_analysis_runner_preview(cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "match_analysis_runner", base_dir=base)
        manifest = Path(str(summary.get("manifest_path", "")))
    rows = [audit_manifest(manifest, base_dir=base)] if manifest and manifest.exists() else []
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = "\n".join(["# Phase 21 Match Analysis Runner 24-Block Audit", "", f"- flows audited: {len(table)}", f"- valid flows: {int(table['preview_valid'].sum()) if not table.empty else 0}", "- no model/probability/market/betting/staking/ROI/SUPER_A_TIER logic is invoked", "", "## Recommendation", rec, ""])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(runner_manifest=args.runner_manifest, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
