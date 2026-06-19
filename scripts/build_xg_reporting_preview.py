# -*- coding: utf-8 -*-
"""Build a manifest-backed xG reporting preview.

Reporting/diagnostic preview only. This script never modifies source, target,
accepted artifact, manifest, model features, predictions, probabilities, or
market logic.
"""
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

from build_manifest_xg_enrichment_preview import (  # noqa: E402
    MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_INVALID_MANIFEST,
    MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_LOW_COVERAGE,
    MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH,
    MANIFEST_XG_ENRICHMENT_PREVIEW_READY,
    _accepted_entries,
    _enrich_target,
    _is_outputs_path,
    _repo_relative,
    _select_entry,
    _validate_entry,
)
from football_prediction_v19.importers.manual_xg_manifest import load_manual_xg_manifest  # noqa: E402,F401

XG_REPORTING_PREVIEW_READY = "XG_REPORTING_PREVIEW_READY"
XG_REPORTING_PREVIEW_BLOCKED_MISSING_XG = "XG_REPORTING_PREVIEW_BLOCKED_MISSING_XG"
XG_REPORTING_PREVIEW_BLOCKED_LOW_COVERAGE = "XG_REPORTING_PREVIEW_BLOCKED_LOW_COVERAGE"
XG_REPORTING_PREVIEW_BLOCKED_INVALID_MANIFEST = "XG_REPORTING_PREVIEW_BLOCKED_INVALID_MANIFEST"
XG_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH = "XG_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH"

REPORTING_COLUMNS = [
    "home_xg",
    "away_xg",
    "xg_total",
    "xg_diff_home",
    "goal_diff_home",
    "home_xg_minus_goals",
    "away_xg_minus_goals",
    "xg_result_label",
    "actual_result_label",
    "xg_result_matches_actual",
    "xg_reporting_status",
]

OUTPUT_DIR = ROOT / "outputs" / "xg_reporting_preview"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--manifest-id", default=None)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "xg_reporting_preview").resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("REPORTING_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_XG_REPORTING_PREVIEW")
    return resolved


def _find_col(df: pd.DataFrame, *names: str) -> str | None:
    normalized = {"".join(ch for ch in str(col).lower() if ch.isalnum()): col for col in df.columns}
    for name in names:
        key = "".join(ch for ch in name.lower() if ch.isalnum())
        if key in normalized:
            return normalized[key]
    return None


def _goal_columns(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    home_col = _find_col(df, "home_goals", "FTHG")
    away_col = _find_col(df, "away_goals", "FTAG")
    if home_col and away_col:
        return pd.to_numeric(df[home_col], errors="coerce"), pd.to_numeric(df[away_col], errors="coerce")
    score_col = _find_col(df, "score")
    if score_col:
        parts = df[score_col].astype(str).str.extract(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$")
        return pd.to_numeric(parts[0], errors="coerce"), pd.to_numeric(parts[1], errors="coerce")
    empty = pd.Series([pd.NA] * len(df), index=df.index, dtype="Float64")
    return empty, empty


def _result_label(diff: Any) -> str:
    if pd.isna(diff):
        return ""
    value = float(diff)
    if value > 0:
        return "H"
    if value < 0:
        return "A"
    return "D"


def _actual_result_labels(df: pd.DataFrame, goal_diff: pd.Series) -> pd.Series:
    ftr = _find_col(df, "FTR", "result")
    if ftr:
        labels = df[ftr].astype(str).str.strip().str.upper()
        valid = labels.where(labels.isin(["H", "D", "A"]), "")
        if valid.astype(bool).any():
            return valid
    return goal_diff.map(_result_label)


def _build_reporting_frame(enriched: pd.DataFrame) -> pd.DataFrame:
    out = enriched.copy()
    home_xg = pd.to_numeric(out["home_xg"], errors="coerce")
    away_xg = pd.to_numeric(out["away_xg"], errors="coerce")
    home_goals, away_goals = _goal_columns(out)
    goal_diff = home_goals - away_goals
    out["home_xg"] = home_xg
    out["away_xg"] = away_xg
    out["xg_total"] = home_xg + away_xg
    out["xg_diff_home"] = home_xg - away_xg
    out["goal_diff_home"] = goal_diff
    out["home_xg_minus_goals"] = home_xg - home_goals
    out["away_xg_minus_goals"] = away_xg - away_goals
    out["xg_result_label"] = out["xg_diff_home"].map(_result_label)
    out["actual_result_label"] = _actual_result_labels(out, goal_diff)
    out["xg_result_matches_actual"] = out["xg_result_label"].eq(out["actual_result_label"])
    missing = out[["home_xg", "away_xg"]].isna().any(axis=1)
    out["xg_reporting_status"] = missing.map(lambda value: "MISSING_XG" if value else "XG_REPORTING_READY")
    return out


def _output_path(entry: Any, output_dir: Path) -> Path:
    return output_dir / f"{entry.manifest_id}_xg_reporting_preview.csv"


def build_xg_reporting_preview(
    *,
    manifest: str | Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    manifest_id: str | None = None,
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    try:
        out_dir = _safe_output_dir(output_dir, base)
    except ValueError as exc:
        return _blocked(XG_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH, str(exc))
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    try:
        entry = _select_entry(_accepted_entries(manifest_path, base), manifest_id, None, base)
    except Exception as exc:
        return _blocked(XG_REPORTING_PREVIEW_BLOCKED_INVALID_MANIFEST, str(exc))
    if entry is None:
        return _blocked(XG_REPORTING_PREVIEW_BLOCKED_INVALID_MANIFEST, "NO_ACCEPTED_PRODUCTION_MANIFEST_ENTRY")
    status, details = _validate_entry(entry, base)
    if status:
        mapped = XG_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH if status == MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH else XG_REPORTING_PREVIEW_BLOCKED_INVALID_MANIFEST
        return _blocked(mapped, details.get("blocking_reasons", ""), entry)
    try:
        xg_df = pd.read_csv(details["xg_abs_path"], low_memory=False)
        target_df = pd.read_csv(details["target_abs_path"], low_memory=False)
        enriched, rows_enriched, rows_missing = _enrich_target(xg_df, target_df)
    except Exception as exc:
        return _blocked(XG_REPORTING_PREVIEW_BLOCKED_INVALID_MANIFEST, str(exc), entry)
    rows_target = int(len(target_df))
    coverage = round((rows_enriched / rows_target * 100.0), 2) if rows_target else 0.0
    min_coverage = float(entry.min_join_coverage_pct)
    if rows_missing:
        status = XG_REPORTING_PREVIEW_BLOCKED_MISSING_XG
    elif coverage < min_coverage:
        status = XG_REPORTING_PREVIEW_BLOCKED_LOW_COVERAGE
    else:
        status = XG_REPORTING_PREVIEW_READY
    output = ""
    if status == XG_REPORTING_PREVIEW_READY:
        reporting = _build_reporting_frame(enriched)
        if write_preview:
            out_dir.mkdir(parents=True, exist_ok=True)
            path = _output_path(entry, out_dir).resolve()
            if out_dir not in path.parents:
                return _blocked(XG_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH, "REPORTING_OUTPUT_OUTSIDE_OUTPUT_DIR", entry)
            reporting.to_csv(path, index=False)
            output = str(path)
    return {
        "reporting_status": status,
        "manifest_id": entry.manifest_id,
        "rows_reported": rows_enriched if status == XG_REPORTING_PREVIEW_READY else 0,
        "rows_missing_xg": rows_missing,
        "join_coverage_pct": coverage,
        "reporting_output_path": output,
        "blocking_reasons": "" if status == XG_REPORTING_PREVIEW_READY else status,
    }


def _blocked(status: str, reason: str, entry: Any | None = None) -> dict[str, Any]:
    return {
        "reporting_status": status,
        "manifest_id": getattr(entry, "manifest_id", ""),
        "rows_reported": 0,
        "rows_missing_xg": 0,
        "join_coverage_pct": 0.0,
        "reporting_output_path": "",
        "blocking_reasons": reason,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_xg_reporting_preview(
        manifest=args.manifest,
        manifest_id=args.manifest_id,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        base_dir=args.base_dir,
    )
    for key in [
        "reporting_status",
        "manifest_id",
        "rows_reported",
        "rows_missing_xg",
        "join_coverage_pct",
        "reporting_output_path",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
