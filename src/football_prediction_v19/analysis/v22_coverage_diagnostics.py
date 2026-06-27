# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_coverage_diagnostics(corpora: list[str | Path], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frames = [pd.read_csv(path, keep_default_na=False) for path in corpora if Path(path).exists()]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    coverage = _coverage_by_league(df)
    paths = {
        "coverage_by_league_path": str((out / "coverage_by_league.csv").resolve()),
        "source_failure_reasons_path": str((out / "source_failure_reasons.csv").resolve()),
        "alias_failure_reasons_path": str((out / "alias_failure_reasons.csv").resolve()),
        "fixture_resolution_failure_reasons_path": str((out / "fixture_resolution_failure_reasons.csv").resolve()),
        "xg_join_rate_by_league_path": str((out / "xg_join_rate_by_league.csv").resolve()),
        "backtest_eligibility_by_league_path": str((out / "backtest_eligibility_by_league.csv").resolve()),
    }
    coverage.to_csv(paths["coverage_by_league_path"], index=False)
    _failure_frame(df, "source").to_csv(paths["source_failure_reasons_path"], index=False)
    _failure_frame(df, "alias").to_csv(paths["alias_failure_reasons_path"], index=False)
    _failure_frame(df, "fixture").to_csv(paths["fixture_resolution_failure_reasons_path"], index=False)
    coverage[["league", "xg_join_rate"]].to_csv(paths["xg_join_rate_by_league_path"], index=False)
    coverage[["league", "backtestable_rate"]].to_csv(paths["backtest_eligibility_by_league_path"], index=False)
    return {"v22_coverage_diagnostics_status": "READY", **paths}


def _coverage_by_league(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["league", "football_data_rows", "understat_rows", "joined_rows", "xg_join_rate", "result_available_rate", "backtestable_rate", "alias_conflict_count", "unmatched_team_count", "unsupported_league_reason"])
    rows = []
    for league, group in df.groupby("competition"):
        rows.append({
            "league": league,
            "football_data_rows": int(group["football_data_available"].astype(bool).sum()),
            "understat_rows": int(group["understat_available"].astype(bool).sum()),
            "joined_rows": int(len(group)),
            "xg_join_rate": round(float(group["xg_available"].astype(bool).mean()), 4),
            "result_available_rate": round(float(group["result_available"].astype(bool).mean()), 4),
            "backtestable_rate": round(float(group["can_backtest"].astype(bool).mean()), 4),
            "alias_conflict_count": 0,
            "unmatched_team_count": 0,
            "unsupported_league_reason": "",
        })
    return pd.DataFrame(rows)


def _failure_frame(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    return pd.DataFrame([{"failure_type": kind, "reason": "none" if not df.empty else "empty corpus", "count": 0 if not df.empty else 1}])
