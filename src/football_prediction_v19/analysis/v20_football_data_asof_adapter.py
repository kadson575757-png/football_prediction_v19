# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext


def build_football_data_asof(csv_path: str | Path, context: HistoricalMatchContext, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(csv_path, keep_default_na=False)
    df["_date"] = pd.to_datetime(df["Date"], errors="coerce", format="%Y-%m-%d")
    if df["_date"].isna().all():
        df["_date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    prior = df[df["_date"] < pd.to_datetime(context.analysis_cutoff)].copy()
    table = _table(prior)
    form = _form(prior)
    table_path = out / "football_data_asof_table.csv"; form_path = out / "football_data_asof_form.csv"
    table.to_csv(table_path, index=False); form.to_csv(form_path, index=False)
    result = {"football_data_asof_status": "READY", "matches_used": len(prior), "table_available": not table.empty, "form_available": not form.empty, "football_data_asof_table_path": str(table_path.resolve()), "football_data_asof_form_path": str(form_path.resolve())}
    (out / "football_data_asof_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "football_data_asof_report.md").write_text("# v2.0 football-data As-Of Report\n\n" + table.to_csv(index=False) + "\n", encoding="utf-8")
    result["football_data_asof_report_path"] = str((out / "football_data_asof_report.md").resolve())
    return result


def _table(df: pd.DataFrame) -> pd.DataFrame:
    stats: dict[str, dict[str, float]] = {}
    for _, r in df.iterrows():
        home, away = r["HomeTeam"], r["AwayTeam"]; hg, ag = int(r["FTHG"]), int(r["FTAG"])
        for team in [home, away]:
            stats.setdefault(team, {"team": team, "played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0})
        stats[home]["played"] += 1; stats[away]["played"] += 1
        stats[home]["goals_for"] += hg; stats[home]["goals_against"] += ag
        stats[away]["goals_for"] += ag; stats[away]["goals_against"] += hg
        if hg > ag:
            stats[home]["wins"] += 1; stats[away]["losses"] += 1; stats[home]["points"] += 3
        elif hg < ag:
            stats[away]["wins"] += 1; stats[home]["losses"] += 1; stats[away]["points"] += 3
        else:
            stats[home]["draws"] += 1; stats[away]["draws"] += 1; stats[home]["points"] += 1; stats[away]["points"] += 1
    frame = pd.DataFrame(stats.values())
    if frame.empty: return frame
    frame["goal_diff"] = frame["goals_for"] - frame["goals_against"]; frame["points_per_game"] = (frame["points"] / frame["played"]).round(3)
    return frame.sort_values(["points", "goal_diff"], ascending=False).reset_index(drop=True)


def _form(df: pd.DataFrame) -> pd.DataFrame:
    table = _table(df)
    rows = []
    for team in table["team"].tolist() if not table.empty else []:
        games = df[(df["HomeTeam"].eq(team)) | (df["AwayTeam"].eq(team))].sort_values("_date").tail(5)
        pts = gf = ga = 0
        for _, r in games.iterrows():
            home = r["HomeTeam"] == team; a, b = (int(r["FTHG"]), int(r["FTAG"])) if home else (int(r["FTAG"]), int(r["FTHG"]))
            gf += a; ga += b; pts += 3 if a > b else (1 if a == b else 0)
        rows.append({"team": team, "recent_form_points_5": pts, "recent_goals_for_5": gf, "recent_goals_against_5": ga})
    return pd.DataFrame(rows)
