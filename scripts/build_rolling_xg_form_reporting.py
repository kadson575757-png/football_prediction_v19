# -*- coding: utf-8 -*-
"""Build rolling pre-match xG form reporting previews."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_xg_reporting_preview import XG_REPORTING_PREVIEW_READY, build_xg_reporting_preview  # noqa: E402

ROLLING_XG_FORM_REPORTING_READY = "ROLLING_XG_FORM_REPORTING_READY"
ROLLING_XG_FORM_REPORTING_BLOCKED_MISSING_XG = "ROLLING_XG_FORM_REPORTING_BLOCKED_MISSING_XG"
ROLLING_XG_FORM_REPORTING_BLOCKED_INVALID_PREVIEW = "ROLLING_XG_FORM_REPORTING_BLOCKED_INVALID_PREVIEW"
ROLLING_XG_FORM_REPORTING_BLOCKED_UNSAFE_PATH = "ROLLING_XG_FORM_REPORTING_BLOCKED_UNSAFE_PATH"

OUTPUT_DIR = ROOT / "outputs" / "xg_reporting_preview"

ROLLING_COLUMNS = [
    "rolling_matches_available",
    "rolling_xg_for",
    "rolling_xg_against",
    "rolling_xg_diff",
    "rolling_goals_for",
    "rolling_goals_against",
    "rolling_goal_diff",
    "rolling_goals_minus_xg_for",
    "rolling_goals_against_minus_xg_against",
    "rolling_points",
    "rolling_home_xg_for",
    "rolling_home_xg_against",
    "rolling_away_xg_for",
    "rolling_away_xg_against",
    "xg_form_status",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reporting-preview", default=None)
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
        raise ValueError("ROLLING_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_XG_REPORTING_PREVIEW")
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


def _points_for(goals_for: pd.Series, goals_against: pd.Series) -> pd.Series:
    return (goals_for > goals_against).astype(int) * 3 + (goals_for == goals_against).astype(int)


def _build_or_read_reporting_preview(
    reporting_preview: str | Path | None,
    manifest: str | Path,
    manifest_id: str | None,
    output_dir: Path,
    base_dir: Path,
) -> tuple[pd.DataFrame, str, str]:
    if reporting_preview:
        path = Path(reporting_preview)
        return pd.read_csv(path, low_memory=False), path.stem, str(path)
    summary = build_xg_reporting_preview(
        manifest=manifest,
        manifest_id=manifest_id,
        output_dir=output_dir,
        write_preview=True,
        base_dir=base_dir,
    )
    if summary["reporting_status"] != XG_REPORTING_PREVIEW_READY or not summary["reporting_output_path"]:
        raise ValueError(str(summary["reporting_status"]))
    return pd.read_csv(summary["reporting_output_path"], low_memory=False), str(summary["manifest_id"]), str(summary["reporting_output_path"])


def build_team_match_rows(reporting_df: pd.DataFrame) -> pd.DataFrame:
    required = {"home_team", "away_team", "home_xg", "away_xg"}
    if not required.issubset(reporting_df.columns):
        raise ValueError("MISSING_REPORTING_COLUMNS")
    df = reporting_df.copy()
    home_xg = pd.to_numeric(df["home_xg"], errors="coerce")
    away_xg = pd.to_numeric(df["away_xg"], errors="coerce")
    if home_xg.isna().any() or away_xg.isna().any():
        raise ValueError("MISSING_XG")
    home_goals, away_goals = _goal_columns(df)
    if home_goals.isna().any() or away_goals.isna().any():
        raise ValueError("MISSING_GOALS")
    date_col = _find_col(df, "date", "Date")
    if date_col is None:
        raise ValueError("MISSING_DATE")
    match_date = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    home = pd.DataFrame({
        "match_index": range(len(df)),
        "date": match_date,
        "team": df["home_team"],
        "opponent": df["away_team"],
        "venue_side": "home",
        "goals_for": home_goals,
        "goals_against": away_goals,
        "xg_for": home_xg,
        "xg_against": away_xg,
        "points": _points_for(home_goals, away_goals),
    })
    away = pd.DataFrame({
        "match_index": range(len(df)),
        "date": match_date,
        "team": df["away_team"],
        "opponent": df["home_team"],
        "venue_side": "away",
        "goals_for": away_goals,
        "goals_against": home_goals,
        "xg_for": away_xg,
        "xg_against": home_xg,
        "points": _points_for(away_goals, home_goals),
    })
    rows = pd.concat([home, away], ignore_index=True).sort_values(["team", "date", "match_index", "venue_side"]).reset_index(drop=True)
    rows["goal_diff"] = rows["goals_for"] - rows["goals_against"]
    rows["xg_diff"] = rows["xg_for"] - rows["xg_against"]
    rows["goals_minus_xg_for"] = rows["goals_for"] - rows["xg_for"]
    rows["goals_against_minus_xg_against"] = rows["goals_against"] - rows["xg_against"]
    return rows


def add_rolling_form(team_rows: pd.DataFrame, *, window: int = 5) -> pd.DataFrame:
    if window < 1:
        raise ValueError("WINDOW_MUST_BE_POSITIVE")
    out = team_rows.copy()
    metrics = [
        "xg_for",
        "xg_against",
        "xg_diff",
        "goals_for",
        "goals_against",
        "goal_diff",
        "goals_minus_xg_for",
        "goals_against_minus_xg_against",
        "points",
    ]
    out["rolling_matches_available"] = 0
    for metric in metrics:
        out[f"rolling_{metric}"] = 0.0
    out["rolling_home_xg_for"] = 0.0
    out["rolling_home_xg_against"] = 0.0
    out["rolling_away_xg_for"] = 0.0
    out["rolling_away_xg_against"] = 0.0
    for _team, idx in out.groupby("team", sort=False).groups.items():
        group = out.loc[idx].sort_values(["date", "match_index"])
        shifted_count = group["xg_for"].shift(1).rolling(window, min_periods=0).count()
        out.loc[group.index, "rolling_matches_available"] = shifted_count.astype(int)
        for metric in metrics:
            out.loc[group.index, f"rolling_{metric}"] = group[metric].shift(1).rolling(window, min_periods=0).sum().fillna(0.0)
        for side in ("home", "away"):
            side_mask = group["venue_side"].eq(side)
            side_xgf = group["xg_for"].where(side_mask)
            side_xga = group["xg_against"].where(side_mask)
            out.loc[group.index, f"rolling_{side}_xg_for"] = side_xgf.shift(1).rolling(window, min_periods=0).sum().fillna(0.0)
            out.loc[group.index, f"rolling_{side}_xg_against"] = side_xga.shift(1).rolling(window, min_periods=0).sum().fillna(0.0)
    out["xg_form_status"] = out["rolling_matches_available"].map(lambda n: "NO_PRIOR_MATCHES" if int(n) == 0 else "ROLLING_XG_FORM_READY")
    return out.sort_values(["date", "match_index", "venue_side", "team"]).reset_index(drop=True)


def build_rolling_xg_form_reporting(
    *,
    reporting_preview: str | Path | None = None,
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
        return _blocked(ROLLING_XG_FORM_REPORTING_BLOCKED_UNSAFE_PATH, str(exc))
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    try:
        reporting_df, source_stem, source_path = _build_or_read_reporting_preview(reporting_preview, manifest_path, manifest_id, out_dir, base)
        rows_missing = int(reporting_df[["home_xg", "away_xg"]].isna().any(axis=1).sum())
        if rows_missing:
            return _blocked(ROLLING_XG_FORM_REPORTING_BLOCKED_MISSING_XG, "MISSING_XG", manifest_id or source_stem, rows_missing=rows_missing)
        team_rows = build_team_match_rows(reporting_df)
        form = add_rolling_form(team_rows, window=window)
    except ValueError as exc:
        status = ROLLING_XG_FORM_REPORTING_BLOCKED_MISSING_XG if "MISSING_XG" in str(exc) else ROLLING_XG_FORM_REPORTING_BLOCKED_INVALID_PREVIEW
        return _blocked(status, str(exc), manifest_id or "")
    output = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = manifest_id or source_stem
        path = (out_dir / f"{stem}_rolling_xg_form_reporting.csv").resolve()
        if out_dir not in path.parents:
            return _blocked(ROLLING_XG_FORM_REPORTING_BLOCKED_UNSAFE_PATH, "ROLLING_OUTPUT_OUTSIDE_OUTPUT_DIR", manifest_id or source_stem)
        form.to_csv(path, index=False)
        output = str(path)
    return {
        "form_status": ROLLING_XG_FORM_REPORTING_READY,
        "manifest_id": manifest_id or source_stem,
        "teams_reported": int(form["team"].nunique()),
        "team_match_rows": int(len(form)),
        "window": int(window),
        "rows_missing_xg": 0,
        "form_output_path": output,
        "reporting_preview_path": source_path,
        "blocking_reasons": "",
    }


def _blocked(status: str, reason: str, manifest_id: str = "", *, rows_missing: int = 0) -> dict[str, Any]:
    return {
        "form_status": status,
        "manifest_id": manifest_id,
        "teams_reported": 0,
        "team_match_rows": 0,
        "window": 0,
        "rows_missing_xg": rows_missing,
        "form_output_path": "",
        "reporting_preview_path": "",
        "blocking_reasons": reason,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_rolling_xg_form_reporting(
        reporting_preview=args.reporting_preview,
        manifest=args.manifest,
        manifest_id=args.manifest_id,
        window=args.window,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        base_dir=args.base_dir,
    )
    for key in ["form_status", "manifest_id", "teams_reported", "team_match_rows", "window", "rows_missing_xg", "form_output_path"]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
