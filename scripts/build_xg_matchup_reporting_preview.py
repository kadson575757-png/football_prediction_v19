# -*- coding: utf-8 -*-
"""Build match-level xG matchup reporting previews from pre-match rolling form."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_rolling_xg_form_reporting import ROLLING_XG_FORM_REPORTING_READY, build_rolling_xg_form_reporting  # noqa: E402
from build_xg_reporting_preview import XG_REPORTING_PREVIEW_READY, build_xg_reporting_preview  # noqa: E402

XG_MATCHUP_REPORTING_PREVIEW_READY = "XG_MATCHUP_REPORTING_PREVIEW_READY"
XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_MISSING_XG = "XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_MISSING_XG"
XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_MISSING_ROLLING_CONTEXT = "XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_MISSING_ROLLING_CONTEXT"
XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_INVALID_PREVIEW = "XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_INVALID_PREVIEW"
XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH = "XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH"

OUTPUT_DIR = ROOT / "outputs" / "xg_reporting_preview"

ROLLING_BASE = [
    "rolling_matches_available",
    "rolling_xg_for",
    "rolling_xg_against",
    "rolling_xg_diff",
    "rolling_goals_for",
    "rolling_goals_against",
    "rolling_goal_diff",
    "rolling_goals_minus_xg_for",
]

REQUIRED_MATCHUP_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "home_xg",
    "away_xg",
    "actual_result_label",
    "xg_result_label",
    "home_rolling_matches_available",
    "away_rolling_matches_available",
    "home_rolling_xg_for",
    "home_rolling_xg_against",
    "home_rolling_xg_diff",
    "away_rolling_xg_for",
    "away_rolling_xg_against",
    "away_rolling_xg_diff",
    "home_rolling_goals_for",
    "home_rolling_goals_against",
    "away_rolling_goals_for",
    "away_rolling_goals_against",
    "home_rolling_goal_diff",
    "away_rolling_goal_diff",
    "home_rolling_goals_minus_xg_for",
    "away_rolling_goals_minus_xg_for",
    "matchup_rolling_xg_diff_home",
    "matchup_rolling_goal_diff_home",
    "matchup_reporting_status",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reporting-preview", default=None)
    parser.add_argument("--rolling-form-preview", default=None)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--manifest-id", default=None)
    parser.add_argument("--window", type=int, default=5)
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
        raise ValueError("MATCHUP_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_XG_REPORTING_PREVIEW")
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


def _build_or_read_reporting(reporting_preview: str | Path | None, manifest: str | Path, manifest_id: str | None, output_dir: Path, base_dir: Path) -> tuple[pd.DataFrame, str, str]:
    if reporting_preview:
        path = Path(reporting_preview)
        return pd.read_csv(path, low_memory=False), path.stem, str(path)
    summary = build_xg_reporting_preview(manifest=manifest, manifest_id=manifest_id, output_dir=output_dir, write_preview=True, base_dir=base_dir)
    if summary["reporting_status"] != XG_REPORTING_PREVIEW_READY or not summary["reporting_output_path"]:
        raise ValueError(str(summary["reporting_status"]))
    return pd.read_csv(summary["reporting_output_path"], low_memory=False), str(summary["manifest_id"]), str(summary["reporting_output_path"])


def _build_or_read_rolling(rolling_preview: str | Path | None, manifest: str | Path, manifest_id: str | None, window: int, output_dir: Path, base_dir: Path) -> tuple[pd.DataFrame, str]:
    if rolling_preview:
        path = Path(rolling_preview)
        return pd.read_csv(path, low_memory=False), str(path)
    summary = build_rolling_xg_form_reporting(manifest=manifest, manifest_id=manifest_id, window=window, output_dir=output_dir, write_preview=True, base_dir=base_dir)
    if summary["form_status"] != ROLLING_XG_FORM_REPORTING_READY or not summary["form_output_path"]:
        raise ValueError(str(summary["form_status"]))
    return pd.read_csv(summary["form_output_path"], low_memory=False), str(summary["form_output_path"])


def build_matchup_frame(reporting_df: pd.DataFrame, rolling_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    required_reporting = {"date", "home_team", "away_team", "home_xg", "away_xg"}
    required_rolling = {"match_index", "team", "venue_side", *ROLLING_BASE}
    if not required_reporting.issubset(reporting_df.columns) or not required_rolling.issubset(rolling_df.columns):
        raise ValueError("MISSING_MATCHUP_INPUT_COLUMNS")
    reporting = reporting_df.copy().reset_index(drop=True)
    reporting["match_index"] = range(len(reporting))
    if reporting[["home_xg", "away_xg"]].isna().any().any():
        raise ValueError("MISSING_XG")
    home_goals, away_goals = _goal_columns(reporting)
    reporting["home_goals"] = home_goals
    reporting["away_goals"] = away_goals
    home_ctx = rolling_df[rolling_df["venue_side"].eq("home")].copy()
    away_ctx = rolling_df[rolling_df["venue_side"].eq("away")].copy()
    rename_home = {col: f"home_{col}" for col in ROLLING_BASE}
    rename_away = {col: f"away_{col}" for col in ROLLING_BASE}
    home_cols = ["match_index", "team", *ROLLING_BASE]
    away_cols = ["match_index", "team", *ROLLING_BASE]
    out = reporting.merge(home_ctx[home_cols].rename(columns={"team": "home_team", **rename_home}), on=["match_index", "home_team"], how="left")
    out = out.merge(away_ctx[away_cols].rename(columns={"team": "away_team", **rename_away}), on=["match_index", "away_team"], how="left")
    rolling_cols = [f"home_{col}" for col in ROLLING_BASE] + [f"away_{col}" for col in ROLLING_BASE]
    missing_context = int(out[rolling_cols].isna().any(axis=1).sum())
    out["matchup_rolling_xg_diff_home"] = out["home_rolling_xg_diff"] - out["away_rolling_xg_diff"]
    out["matchup_rolling_goal_diff_home"] = out["home_rolling_goal_diff"] - out["away_rolling_goal_diff"]
    out["matchup_reporting_status"] = out[rolling_cols].isna().any(axis=1).map(lambda value: "MISSING_ROLLING_CONTEXT" if value else "XG_MATCHUP_REPORTING_READY")
    return out, missing_context


def build_xg_matchup_reporting_preview(
    *,
    reporting_preview: str | Path | None = None,
    rolling_form_preview: str | Path | None = None,
    manifest: str | Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    manifest_id: str | None = None,
    window: int = 5,
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    try:
        out_dir = _safe_output_dir(output_dir, base)
    except ValueError as exc:
        return _blocked(XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH, str(exc))
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    try:
        reporting_df, source_stem, _reporting_path = _build_or_read_reporting(reporting_preview, manifest_path, manifest_id, out_dir, base)
        rolling_df, _rolling_path = _build_or_read_rolling(rolling_form_preview, manifest_path, manifest_id, window, out_dir, base)
        rows_missing_xg = int(reporting_df[["home_xg", "away_xg"]].isna().any(axis=1).sum())
        if rows_missing_xg:
            return _blocked(XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_MISSING_XG, "MISSING_XG", manifest_id or source_stem, rows_missing_xg=rows_missing_xg)
        matchup, missing_context = build_matchup_frame(reporting_df, rolling_df)
    except ValueError as exc:
        status = XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_MISSING_XG if "MISSING_XG" in str(exc) else XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_INVALID_PREVIEW
        return _blocked(status, str(exc), manifest_id or "")
    if missing_context:
        return _blocked(XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_MISSING_ROLLING_CONTEXT, "MISSING_ROLLING_CONTEXT", manifest_id or source_stem, rows_missing_context=missing_context)
    output = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = manifest_id or source_stem
        path = (out_dir / f"{stem}_xg_matchup_reporting_preview.csv").resolve()
        if out_dir not in path.parents:
            return _blocked(XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH, "MATCHUP_OUTPUT_OUTSIDE_OUTPUT_DIR", manifest_id or source_stem)
        matchup.to_csv(path, index=False)
        output = str(path)
    return {
        "matchup_status": XG_MATCHUP_REPORTING_PREVIEW_READY,
        "manifest_id": manifest_id or source_stem,
        "matches_reported": int(len(matchup)),
        "rows_missing_xg": 0,
        "rows_missing_rolling_context": 0,
        "window": int(window),
        "matchup_output_path": output,
        "blocking_reasons": "",
    }


def _blocked(status: str, reason: str, manifest_id: str = "", *, rows_missing_xg: int = 0, rows_missing_context: int = 0) -> dict[str, Any]:
    return {
        "matchup_status": status,
        "manifest_id": manifest_id,
        "matches_reported": 0,
        "rows_missing_xg": rows_missing_xg,
        "rows_missing_rolling_context": rows_missing_context,
        "window": 0,
        "matchup_output_path": "",
        "blocking_reasons": reason,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_xg_matchup_reporting_preview(
        reporting_preview=args.reporting_preview,
        rolling_form_preview=args.rolling_form_preview,
        manifest=args.manifest,
        manifest_id=args.manifest_id,
        window=args.window,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        base_dir=args.base_dir,
    )
    for key in ["matchup_status", "manifest_id", "matches_reported", "rows_missing_xg", "rows_missing_rolling_context", "window", "matchup_output_path"]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
