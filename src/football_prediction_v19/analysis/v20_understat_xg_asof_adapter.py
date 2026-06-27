# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext


def build_understat_xg_asof(xg_csv: str | Path, player_csv: str | Path | None, context: HistoricalMatchContext, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(xg_csv, keep_default_na=False); df["_date"] = pd.to_datetime(df["date"])
    prior = df[df["_date"] < pd.to_datetime(context.analysis_cutoff)].copy()
    teams = _team_xg(prior, context)
    players = _player_xg(player_csv, context) if player_csv else pd.DataFrame()
    team_path = out / "understat_xg_asof_team.csv"; player_path = out / "understat_xg_asof_player.csv"
    teams.to_csv(team_path, index=False); players.to_csv(player_path, index=False)
    result = {"understat_xg_asof_status": "READY", "xg_available": not teams.empty, "player_xg_available": not players.empty, "understat_xg_asof_team_path": str(team_path.resolve()), "understat_xg_asof_player_path": str(player_path.resolve())}
    (out / "understat_xg_asof_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "understat_xg_asof_report.md").write_text("# v2.0 Understat xG As-Of Report\n\n" + (teams.to_csv(index=False) if not teams.empty else "No xG rows.") + "\n", encoding="utf-8")
    result["understat_xg_asof_report_path"] = str((out / "understat_xg_asof_report.md").resolve())
    return result


def _team_xg(df: pd.DataFrame, context: HistoricalMatchContext) -> pd.DataFrame:
    rows = []
    for team in sorted(set(df["home_team"]).union(set(df["away_team"]))):
        games = df[(df["home_team"].eq(team)) | (df["away_team"].eq(team))].sort_values("_date")
        xf = xa = hxf = hxa = axf = axa = 0.0
        for _, r in games.iterrows():
            home = r["home_team"] == team
            f = float(r["home_xg"] if home else r["away_xg"]); a = float(r["away_xg"] if home else r["home_xg"])
            xf += f; xa += a
            if home: hxf += f; hxa += a
            else: axf += f; axa += a
        last = games.tail(5)
        rxf = rxa = 0.0
        for _, r in last.iterrows():
            home = r["home_team"] == team
            rxf += float(r["home_xg"] if home else r["away_xg"]); rxa += float(r["away_xg"] if home else r["home_xg"])
        rows.append({"team": team, "matches_count": len(games), "xg_for": round(xf, 3), "xg_against": round(xa, 3), "xg_diff": round(xf-xa, 3), "rolling_xg_for_5": round(rxf, 3), "rolling_xg_against_5": round(rxa, 3), "home_xg_for": round(hxf, 3), "home_xg_against": round(hxa, 3), "away_xg_for": round(axf, 3), "away_xg_against": round(axa, 3), "source_name": "understat_mock", "asof_cutoff": context.analysis_cutoff})
    return pd.DataFrame(rows)


def _player_xg(player_csv: str | Path, context: HistoricalMatchContext) -> pd.DataFrame:
    df = pd.read_csv(player_csv, keep_default_na=False); df["_date"] = pd.to_datetime(df["date"])
    prior = df[df["_date"] < pd.to_datetime(context.analysis_cutoff)].copy()
    if prior.empty: return pd.DataFrame()
    agg = prior.groupby(["player", "team"], as_index=False).agg({"minutes": "sum", "goals": "sum", "assists": "sum", "xg": "sum", "xa": "sum", "npxg": "sum"})
    agg["source_name"] = "understat_player_mock"; agg["asof_cutoff"] = context.analysis_cutoff
    return agg
