# -*- coding: utf-8 -*-
"""Audit Phase 16.2 single-match analysis report preview."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY = "SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY"
BUILD_SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW = "BUILD_SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW"
FIX_SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW = "FIX_SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW"

OUTPUT_CSV = "single_match_analysis_report_preview_summary.csv"
OUTPUT_MD = "single_match_analysis_report_preview_summary.md"

REQUIRED_COLUMNS = {
    "report_id", "source_id", "provider_match_id", "league", "season",
    "input_path", "report_path", "summary_path", "rows_input",
    "rows_reported", "missing_required_columns", "missing_required_values",
    "network_calls_enabled", "prediction_logic_enabled",
    "betting_logic_enabled", "report_status", "recommendation", "notes",
}
REQUIRED_MARKDOWN = [
    "preview-only analysis report",
    "no model prediction was run",
    "no betting/staking recommendation was generated",
    "no live external data was fetched",
]
PROTECTED_TOKENS = [
    "manual_xg_manifest",
    "trusted_xg_sources/accepted",
    "trusted_xg_sources\\accepted",
    "trusted_xg_sources/raw",
    "trusted_xg_sources\\raw",
    "data/processed",
    "data\\processed",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "analysis_preview" / "single_match_report"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _manifest_path(manifest: str | Path | None, preview_dir: str | Path) -> Path | None:
    if manifest:
        return Path(manifest)
    path = Path(preview_dir) / "single_match_analysis_report_manifest.csv"
    return path if path.exists() else None


def _under_report(path_text: str, base: Path) -> bool:
    if not str(path_text).strip():
        return True
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    try:
        resolved = path.resolve()
    except OSError:
        return False
    allowed = (base / "outputs" / "analysis_preview" / "single_match_report").resolve()
    return resolved == allowed or allowed in resolved.parents


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _has_protected_output(path_text: str) -> bool:
    text = str(path_text).replace("\\", "/").lower()
    return any(token.replace("\\", "/").lower() in text for token in PROTECTED_TOKENS)


def _markdown_ok(report_path: str, base: Path) -> bool:
    if not report_path or not _under_report(report_path, base):
        return False
    path = Path(report_path)
    if not path.is_absolute():
        path = base / path
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8").lower()
    return all(fragment in text for fragment in REQUIRED_MARKDOWN)


def audit_manifest(path: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    if not _under_report(str(path), base):
        errors.append("UNSAFE_MANIFEST_PATH")
    try:
        table = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return {
            "manifest_path": str(path),
            "reports_found": 0,
            "missing_required_columns": "ALL",
            "ready_status": False,
            "rows_input_nonzero": False,
            "rows_reported_one": False,
            "network_calls_enabled": True,
            "prediction_logic_enabled": True,
            "betting_logic_enabled": True,
            "output_paths_safe": False,
            "markdown_required_text_present": False,
            "preview_valid": False,
            "blocking_reasons": " | ".join([*errors, str(exc)]),
        }
    missing = sorted(REQUIRED_COLUMNS - set(table.columns))
    if missing:
        errors.append("MISSING_REQUIRED_COLUMNS")
    ready = set(table["report_status"].astype(str)) == {SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY} if "report_status" in table.columns else False
    if not ready:
        errors.append("REPORT_NOT_READY")
    rows_input = pd.to_numeric(table["rows_input"], errors="coerce").fillna(0) if "rows_input" in table.columns else pd.Series([0])
    rows_reported = pd.to_numeric(table["rows_reported"], errors="coerce").fillna(0) if "rows_reported" in table.columns else pd.Series([0])
    rows_input_nonzero = bool((rows_input > 0).all())
    rows_reported_one = bool((rows_reported == 1).all())
    if not rows_input_nonzero:
        errors.append("ROWS_INPUT_ZERO")
    if not rows_reported_one:
        errors.append("ROWS_REPORTED_NOT_ONE")
    network_enabled = any(_as_bool(value) for value in table["network_calls_enabled"]) if "network_calls_enabled" in table.columns else True
    prediction_enabled = any(_as_bool(value) for value in table["prediction_logic_enabled"]) if "prediction_logic_enabled" in table.columns else True
    betting_enabled = any(_as_bool(value) for value in table["betting_logic_enabled"]) if "betting_logic_enabled" in table.columns else True
    if network_enabled:
        errors.append("NETWORK_CALLS_ENABLED")
    if prediction_enabled:
        errors.append("PREDICTION_LOGIC_ENABLED")
    if betting_enabled:
        errors.append("BETTING_LOGIC_ENABLED")
    paths = []
    if "report_path" in table.columns:
        paths.extend(table["report_path"].fillna("").astype(str).tolist())
    if "summary_path" in table.columns:
        paths.extend(table["summary_path"].fillna("").astype(str).tolist())
    output_safe = all(_under_report(path_value, base) and not _has_protected_output(path_value) for path_value in paths)
    if not output_safe:
        errors.append("UNSAFE_OUTPUT_PATH")
    markdown_ok = all(_markdown_ok(path_value, base) for path_value in table["report_path"].fillna("").astype(str).tolist()) if "report_path" in table.columns else False
    if not markdown_ok:
        errors.append("MARKDOWN_REQUIRED_TEXT_MISSING")
    return {
        "manifest_path": str(path),
        "reports_found": int(len(table)),
        "missing_required_columns": " | ".join(missing),
        "ready_status": ready,
        "rows_input_nonzero": rows_input_nonzero,
        "rows_reported_one": rows_reported_one,
        "network_calls_enabled": network_enabled,
        "prediction_logic_enabled": prediction_enabled,
        "betting_logic_enabled": betting_enabled,
        "output_paths_safe": output_safe,
        "markdown_required_text_present": markdown_ok,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW
    if table["preview_valid"].any():
        return SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY
    return FIX_SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 16.2 Single Match Analysis Report Preview Audit",
        "",
        "Phase 16.2 audits preview-only single-match reports. No network, prediction, or betting logic is enabled.",
        "",
        "## A. Executive Summary",
        f"- manifests audited: {len(table)}",
        f"- valid manifests: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Diagnostics",
    ]
    if table.empty:
        lines += ["No single-match analysis report manifest found.", ""]
    else:
        cols = ["reports_found", "ready_status", "rows_input_nonzero", "rows_reported_one", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "output_paths_safe", "markdown_required_text_present", "preview_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- No live scraping/API fetching is active.",
        "- No model predictions are run.",
        "- No betting or staking logic is run.",
        "- Output paths must stay under outputs/analysis_preview/single_match_report.",
        "- No model, probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 16.2 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    manifest: str | Path | None = None,
    preview_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "single_match_report",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    path = _manifest_path(manifest, preview_dir)
    rows = [audit_manifest(path, base_dir=base_dir)] if path else []
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = build_markdown(table, rec)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(manifest=args.manifest, preview_dir=args.preview_dir, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

