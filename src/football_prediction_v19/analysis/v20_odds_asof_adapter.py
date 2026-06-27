# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext


def build_odds_asof(odds_csv: str | Path, totals_csv: str | Path | None, context: HistoricalMatchContext, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    frames = [frame for frame in [pd.read_csv(odds_csv, keep_default_na=False), pd.read_csv(totals_csv, keep_default_na=False) if totals_csv else pd.DataFrame()] if not frame.empty]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["match_date", "home_team", "away_team", "snapshot_time", "market", "selection", "odds"])
    df["snapshot_dt"] = pd.to_datetime(df["snapshot_time"])
    cutoff = pd.to_datetime(context.analysis_cutoff)
    target = df[df["home_team"].eq(context.home_team) & df["away_team"].eq(context.away_team) & df["match_date"].eq(context.match_date)].copy()
    target["valid_for_cutoff"] = target["snapshot_dt"] <= cutoff
    target["leakage_status"] = target["valid_for_cutoff"].map(lambda x: "CLEAN" if x else "AFTER_CUTOFF")
    target["implied_probability"] = (1 / target["odds"].astype(float)).round(4)
    clean = target[target["valid_for_cutoff"]].copy(); excluded = target[~target["valid_for_cutoff"]].copy()
    clean_path = out / "odds_asof_clean.csv"; excluded_path = out / "odds_asof_excluded.csv"
    clean.to_csv(clean_path, index=False); excluded.to_csv(excluded_path, index=False)
    result = {"odds_asof_status": "READY", "odds_available": not clean.empty, "odds_1x2_available": not clean[clean["market"].eq("1X2")].empty, "odds_totals_available": not clean[clean["market"].eq("OU25")].empty, "odds_asof_clean_path": str(clean_path.resolve()), "odds_asof_excluded_path": str(excluded_path.resolve())}
    (out / "odds_asof_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "odds_asof_report.md").write_text("# v2.0 Odds As-Of Report\n\n" + (clean.to_csv(index=False) if not clean.empty else "No valid odds.") + "\n", encoding="utf-8")
    result["odds_asof_report_path"] = str((out / "odds_asof_report.md").resolve())
    return result
