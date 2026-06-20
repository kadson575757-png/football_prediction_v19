# -*- coding: utf-8 -*-
"""Audit Phase 16.3 single-match context enrichment preview."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY = "SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY"
SINGLE_MATCH_CONTEXT_ENRICHMENT_PARTIAL_READY = "SINGLE_MATCH_CONTEXT_ENRICHMENT_PARTIAL_READY"
BUILD_SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW = "BUILD_SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW"
FIX_SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW = "FIX_SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW"

OUTPUT_CSV = "single_match_context_enrichment_preview_summary.csv"
OUTPUT_MD = "single_match_context_enrichment_preview_summary.md"

REQUIRED_COLUMNS = {
    "enrichment_id", "source_id", "provider_match_id", "league", "season",
    "base_report_manifest_path", "output_report_path", "output_summary_path",
    "rows_reported", "contexts_checked", "contexts_available",
    "contexts_missing_optional", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "enrichment_status",
    "recommendation", "notes",
}
REQUIRED_MARKDOWN = [
    "preview-only context enrichment",
    "no model prediction was run",
    "no betting/staking recommendation was generated",
    "no live external data was fetched",
    "missing optional context is not inferred or invented",
]
PROTECTED_TOKENS = ["manual_xg_manifest", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "data/processed"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "analysis_preview" / "single_match_context"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _manifest_path(manifest: str | Path | None, preview_dir: str | Path) -> Path | None:
    if manifest:
        return Path(manifest)
    path = Path(preview_dir) / "single_match_context_enrichment_manifest.csv"
    return path if path.exists() else None


def _under_context(path_text: str, base: Path) -> bool:
    if not str(path_text).strip():
        return True
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    try:
        resolved = path.resolve()
    except OSError:
        return False
    allowed = (base / "outputs" / "analysis_preview" / "single_match_context").resolve()
    return resolved == allowed or allowed in resolved.parents


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _has_protected_output(path_text: str) -> bool:
    text = str(path_text).replace("\\", "/").lower()
    return any(token in text for token in PROTECTED_TOKENS)


def _markdown_ok(report_path: str, base: Path) -> bool:
    if not report_path or not _under_context(report_path, base):
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
    if not _under_context(str(path), base):
        errors.append("UNSAFE_MANIFEST_PATH")
    try:
        table = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return _row(path, errors + [str(exc)])
    missing = sorted(REQUIRED_COLUMNS - set(table.columns))
    if missing:
        errors.append("MISSING_REQUIRED_COLUMNS")
    status_ok = set(table["enrichment_status"].astype(str)).issubset({SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY, SINGLE_MATCH_CONTEXT_ENRICHMENT_PARTIAL_READY}) if "enrichment_status" in table.columns else False
    rows_ok = bool((pd.to_numeric(table["rows_reported"], errors="coerce").fillna(0) == 1).all()) if "rows_reported" in table.columns else False
    contexts_ok = bool((pd.to_numeric(table["contexts_checked"], errors="coerce").fillna(0) > 0).all()) if "contexts_checked" in table.columns else False
    network_enabled = any(_as_bool(v) for v in table["network_calls_enabled"]) if "network_calls_enabled" in table.columns else True
    prediction_enabled = any(_as_bool(v) for v in table["prediction_logic_enabled"]) if "prediction_logic_enabled" in table.columns else True
    betting_enabled = any(_as_bool(v) for v in table["betting_logic_enabled"]) if "betting_logic_enabled" in table.columns else True
    paths = []
    if "output_report_path" in table.columns:
        paths.extend(table["output_report_path"].fillna("").astype(str).tolist())
    if "output_summary_path" in table.columns:
        paths.extend(table["output_summary_path"].fillna("").astype(str).tolist())
    output_safe = all(_under_context(p, base) and not _has_protected_output(p) for p in paths)
    markdown_ok = all(_markdown_ok(p, base) for p in table["output_report_path"].fillna("").astype(str).tolist()) if "output_report_path" in table.columns else False
    if not status_ok:
        errors.append("ENRICHMENT_NOT_READY")
    if not rows_ok:
        errors.append("ROWS_REPORTED_NOT_ONE")
    if not contexts_ok:
        errors.append("CONTEXTS_CHECKED_ZERO")
    if network_enabled:
        errors.append("NETWORK_CALLS_ENABLED")
    if prediction_enabled:
        errors.append("PREDICTION_LOGIC_ENABLED")
    if betting_enabled:
        errors.append("BETTING_LOGIC_ENABLED")
    if not output_safe:
        errors.append("UNSAFE_OUTPUT_PATH")
    if not markdown_ok:
        errors.append("MARKDOWN_REQUIRED_TEXT_MISSING")
    return {
        "manifest_path": str(path),
        "enrichments_found": int(len(table)),
        "missing_required_columns": " | ".join(missing),
        "ready_status": status_ok,
        "rows_reported_one": rows_ok,
        "contexts_checked_nonzero": contexts_ok,
        "network_calls_enabled": network_enabled,
        "prediction_logic_enabled": prediction_enabled,
        "betting_logic_enabled": betting_enabled,
        "output_paths_safe": output_safe,
        "markdown_required_text_present": markdown_ok,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def _row(path: Path, errors: list[str]) -> dict[str, Any]:
    return {
        "manifest_path": str(path), "enrichments_found": 0, "missing_required_columns": "ALL",
        "ready_status": False, "rows_reported_one": False, "contexts_checked_nonzero": False,
        "network_calls_enabled": True, "prediction_logic_enabled": True, "betting_logic_enabled": True,
        "output_paths_safe": False, "markdown_required_text_present": False, "preview_valid": False,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW
    if table["preview_valid"].any():
        return SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY
    return FIX_SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = ["# Phase 16.3 Single Match Context Enrichment Preview Audit", "", f"- manifests audited: {len(table)}", f"- valid manifests: {int(table['preview_valid'].sum()) if not table.empty else 0}", "", "## Recommendation", rec, ""]
    return "\n".join(lines)


def run(*, manifest: str | Path | None = None, preview_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "single_match_context", output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT) -> tuple[pd.DataFrame, str, str]:
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

