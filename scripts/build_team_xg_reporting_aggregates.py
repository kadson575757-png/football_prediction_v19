# -*- coding: utf-8 -*-
"""Build team-level xG reporting aggregates from match-level reporting previews."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_xg_reporting_preview import (  # noqa: E402
    XG_REPORTING_PREVIEW_READY,
    build_xg_reporting_preview,
)

TEAM_XG_REPORTING_AGGREGATES_READY = "TEAM_XG_REPORTING_AGGREGATES_READY"
TEAM_XG_REPORTING_AGGREGATES_BLOCKED_MISSING_XG = "TEAM_XG_REPORTING_AGGREGATES_BLOCKED_MISSING_XG"
TEAM_XG_REPORTING_AGGREGATES_BLOCKED_INVALID_PREVIEW = "TEAM_XG_REPORTING_AGGREGATES_BLOCKED_INVALID_PREVIEW"
TEAM_XG_REPORTING_AGGREGATES_BLOCKED_UNSAFE_PATH = "TEAM_XG_REPORTING_AGGREGATES_BLOCKED_UNSAFE_PATH"

OUTPUT_DIR = ROOT / "outputs" / "xg_reporting_preview"

REQUIRED_COLUMNS = ["home_team", "away_team", "home_xg", "away_xg"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reporting-preview", default=None)
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
        raise ValueError("AGGREGATE_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_XG_REPORTING_PREVIEW")
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


def build_team_aggregates(reporting_df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_COLUMNS if col not in reporting_df.columns]
    if missing:
        raise ValueError("missing reporting columns: " + ", ".join(missing))
    df = reporting_df.copy()
    home_xg = pd.to_numeric(df["home_xg"], errors="coerce")
    away_xg = pd.to_numeric(df["away_xg"], errors="coerce")
    if home_xg.isna().any() or away_xg.isna().any():
        raise ValueError("MISSING_XG")
    home_goals, away_goals = _goal_columns(df)
    if home_goals.isna().any() or away_goals.isna().any():
        raise ValueError("MISSING_GOALS")
    home = pd.DataFrame({
        "team": df["home_team"],
        "venue_side": "home",
        "goals_for": home_goals,
        "goals_against": away_goals,
        "xg_for": home_xg,
        "xg_against": away_xg,
        "points": _points_for(home_goals, away_goals),
    })
    away = pd.DataFrame({
        "team": df["away_team"],
        "venue_side": "away",
        "goals_for": away_goals,
        "goals_against": home_goals,
        "xg_for": away_xg,
        "xg_against": home_xg,
        "points": _points_for(away_goals, home_goals),
    })
    long = pd.concat([home, away], ignore_index=True)
    base = long.groupby("team", as_index=False).agg(
        matches=("team", "size"),
        goals_for=("goals_for", "sum"),
        goals_against=("goals_against", "sum"),
        xg_for=("xg_for", "sum"),
        xg_against=("xg_against", "sum"),
        points=("points", "sum"),
    )
    for side in ("home", "away"):
        side_df = long[long["venue_side"] == side].groupby("team", as_index=False).agg(
            **{
                f"{side}_matches": ("team", "size"),
                f"{side}_goals_for": ("goals_for", "sum"),
                f"{side}_goals_against": ("goals_against", "sum"),
                f"{side}_xg_for": ("xg_for", "sum"),
                f"{side}_xg_against": ("xg_against", "sum"),
            }
        )
        base = base.merge(side_df, on="team", how="left")
    numeric_fill = [col for col in base.columns if col != "team"]
    base[numeric_fill] = base[numeric_fill].fillna(0)
    base["goal_diff"] = base["goals_for"] - base["goals_against"]
    base["xg_diff"] = base["xg_for"] - base["xg_against"]
    base["goals_minus_xg_for"] = base["goals_for"] - base["xg_for"]
    base["goals_against_minus_xg_against"] = base["goals_against"] - base["xg_against"]
    base["xg_reporting_status"] = "TEAM_XG_REPORTING_READY"
    ordered = [
        "team",
        "matches",
        "goals_for",
        "goals_against",
        "goal_diff",
        "xg_for",
        "xg_against",
        "xg_diff",
        "goals_minus_xg_for",
        "goals_against_minus_xg_against",
        "points",
        "home_matches",
        "home_goals_for",
        "home_goals_against",
        "home_xg_for",
        "home_xg_against",
        "away_matches",
        "away_goals_for",
        "away_goals_against",
        "away_xg_for",
        "away_xg_against",
        "xg_reporting_status",
    ]
    return base[ordered].sort_values(["points", "goal_diff", "goals_for", "team"], ascending=[False, False, False, True]).reset_index(drop=True)


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


def build_team_xg_reporting_aggregates(
    *,
    reporting_preview: str | Path | None = None,
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
        return _blocked(TEAM_XG_REPORTING_AGGREGATES_BLOCKED_UNSAFE_PATH, str(exc))
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    try:
        reporting_df, source_stem, source_path = _build_or_read_reporting_preview(reporting_preview, manifest_path, manifest_id, out_dir, base)
        rows_missing = int(reporting_df[["home_xg", "away_xg"]].isna().any(axis=1).sum())
        if rows_missing:
            return _blocked(TEAM_XG_REPORTING_AGGREGATES_BLOCKED_MISSING_XG, "MISSING_XG", manifest_id or source_stem, rows_missing=rows_missing)
        aggregates = build_team_aggregates(reporting_df)
    except ValueError as exc:
        status = TEAM_XG_REPORTING_AGGREGATES_BLOCKED_MISSING_XG if "MISSING_XG" in str(exc) else TEAM_XG_REPORTING_AGGREGATES_BLOCKED_INVALID_PREVIEW
        return _blocked(status, str(exc), manifest_id or "")
    output = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = manifest_id or source_stem
        path = (out_dir / f"{stem}_team_xg_reporting_aggregates.csv").resolve()
        if out_dir not in path.parents:
            return _blocked(TEAM_XG_REPORTING_AGGREGATES_BLOCKED_UNSAFE_PATH, "AGGREGATE_OUTPUT_OUTSIDE_OUTPUT_DIR", manifest_id or source_stem)
        aggregates.to_csv(path, index=False)
        output = str(path)
    return {
        "aggregate_status": TEAM_XG_REPORTING_AGGREGATES_READY,
        "manifest_id": manifest_id or source_stem,
        "teams_reported": int(len(aggregates)),
        "matches_used": int(len(reporting_df)),
        "rows_missing_xg": 0,
        "aggregate_output_path": output,
        "reporting_preview_path": source_path,
        "blocking_reasons": "",
    }


def _blocked(status: str, reason: str, manifest_id: str = "", *, rows_missing: int = 0) -> dict[str, Any]:
    return {
        "aggregate_status": status,
        "manifest_id": manifest_id,
        "teams_reported": 0,
        "matches_used": 0,
        "rows_missing_xg": rows_missing,
        "aggregate_output_path": "",
        "reporting_preview_path": "",
        "blocking_reasons": reason,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_team_xg_reporting_aggregates(
        reporting_preview=args.reporting_preview,
        manifest=args.manifest,
        manifest_id=args.manifest_id,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        base_dir=args.base_dir,
    )
    for key in ["aggregate_status", "manifest_id", "teams_reported", "matches_used", "rows_missing_xg", "aggregate_output_path"]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
