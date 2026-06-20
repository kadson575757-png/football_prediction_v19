# -*- coding: utf-8 -*-
"""Audit Phase 15.4 file-based importer dry-run preview."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

FILE_BASED_IMPORTER_DRY_RUN_READY = "FILE_BASED_IMPORTER_DRY_RUN_READY"
BUILD_FILE_BASED_IMPORTER_DRY_RUN_PREVIEW = "BUILD_FILE_BASED_IMPORTER_DRY_RUN_PREVIEW"
FIX_FILE_BASED_IMPORTER_DRY_RUN_PREVIEW = "FIX_FILE_BASED_IMPORTER_DRY_RUN_PREVIEW"

OUTPUT_CSV = "file_based_importer_dry_run_preview_summary.csv"
OUTPUT_MD = "file_based_importer_dry_run_preview_summary.md"

REQUIRED_COLUMNS = {
    "source_id", "contract_id", "input_path", "output_path", "rows_input",
    "rows_normalized", "missing_required_columns", "network_calls_enabled",
    "dry_run_status", "recommendation", "notes",
}
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
    parser.add_argument("--preview", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "importer_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _preview_path(preview: str | Path | None, preview_dir: str | Path) -> Path | None:
    if preview:
        return Path(preview)
    path = Path(preview_dir) / "file_based_importer_dry_run_preview.csv"
    return path if path.exists() else None


def _under_preview(path_text: str, base: Path) -> bool:
    if not str(path_text).strip():
        return True
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    try:
        resolved = path.resolve()
    except OSError:
        return False
    allowed = (base / "outputs" / "importer_preview").resolve()
    return resolved == allowed or allowed in resolved.parents


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _has_protected_output(path_text: str) -> bool:
    text = str(path_text).replace("\\", "/").lower()
    return any(token.replace("\\", "/").lower() in text for token in PROTECTED_TOKENS)


def audit_preview(path: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    if not _under_preview(str(path), base):
        errors.append("UNSAFE_PREVIEW_PATH")
    try:
        table = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return {
            "preview_path": str(path),
            "rows_found": 0,
            "missing_required_columns": "ALL",
            "network_calls_enabled": True,
            "ready_status": False,
            "nonzero_rows": False,
            "output_paths_safe": False,
            "preview_valid": False,
            "blocking_reasons": " | ".join([*errors, str(exc)]),
        }
    missing = sorted(REQUIRED_COLUMNS - set(table.columns))
    if missing:
        errors.append("MISSING_REQUIRED_COLUMNS")
    network_enabled = any(_as_bool(value) for value in table["network_calls_enabled"]) if "network_calls_enabled" in table.columns else True
    if network_enabled:
        errors.append("NETWORK_CALLS_ENABLED")
    ready = set(table["dry_run_status"].astype(str)) == {FILE_BASED_IMPORTER_DRY_RUN_READY} if "dry_run_status" in table.columns else False
    if not ready:
        errors.append("DRY_RUN_NOT_READY")
    rows_input = pd.to_numeric(table["rows_input"], errors="coerce").fillna(0) if "rows_input" in table.columns else pd.Series([0])
    rows_normalized = pd.to_numeric(table["rows_normalized"], errors="coerce").fillna(0) if "rows_normalized" in table.columns else pd.Series([0])
    nonzero = bool((rows_input > 0).all() and (rows_normalized > 0).all())
    if not nonzero:
        errors.append("ROWS_NOT_NORMALIZED")
    paths = table["output_path"].fillna("").astype(str).tolist() if "output_path" in table.columns else [""]
    output_safe = all(_under_preview(path_value, base) and not _has_protected_output(path_value) for path_value in paths)
    if not output_safe:
        errors.append("UNSAFE_OUTPUT_PATH")
    return {
        "preview_path": str(path),
        "rows_found": int(len(table)),
        "missing_required_columns": " | ".join(missing),
        "network_calls_enabled": network_enabled,
        "ready_status": ready,
        "nonzero_rows": nonzero,
        "output_paths_safe": output_safe,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_FILE_BASED_IMPORTER_DRY_RUN_PREVIEW
    if table["preview_valid"].any():
        return FILE_BASED_IMPORTER_DRY_RUN_READY
    return FIX_FILE_BASED_IMPORTER_DRY_RUN_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 15.4 File-Based Importer Dry Run Preview Audit",
        "",
        "Phase 15.4 audits local CSV dry-run importer previews only. No network calls are made.",
        "",
        "## A. Executive Summary",
        f"- previews audited: {len(table)}",
        f"- valid previews: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Diagnostics",
    ]
    if table.empty:
        lines += ["No file-based importer dry-run preview found.", ""]
    else:
        cols = ["rows_found", "network_calls_enabled", "ready_status", "nonzero_rows", "output_paths_safe", "preview_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- No live scraping/API fetching is active.",
        "- Output paths must stay under outputs/importer_preview.",
        "- Production targets, accepted artifacts, manifests, and raw sources are not written.",
        "- No model, probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 15.4 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    preview: str | Path | None = None,
    preview_dir: str | Path = ROOT / "outputs" / "importer_preview",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    path = _preview_path(preview, preview_dir)
    rows = [audit_preview(path, base_dir=base_dir)] if path else []
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
    table, _markdown, rec = run(preview=args.preview, preview_dir=args.preview_dir, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

