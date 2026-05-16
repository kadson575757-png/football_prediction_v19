from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

COMPETITIONS = {
    "premier_league": 9,
    "la_liga": 12,
    "bundesliga": 20,
    "serie_a": 11,
    "ligue_1": 13,
}


def fetch_fbref_schedules(start_year: int, end_year: int, comp_ids: Iterable[int] = (9, 12)) -> pd.DataFrame:
    """Fetch FBref schedule tables using the same idea as the course project.

    Network access is required. FBref may rate-limit; cache your output CSV.
    """
    all_dfs = []
    for season_start in range(start_year, end_year + 1):
        season = f"{season_start}-{season_start + 1}"
        for comp_id in comp_ids:
            url = f"https://fbref.com/en/comps/{comp_id}/{season}/schedule/{season}-Scores-and-Fixtures"
            table_id = f"sched_{season}_{comp_id}_1"
            try:
                df = pd.read_html(url, attrs={"id": table_id})[0]
            except Exception:
                # FBref URLs include competition names in some seasons; fallback to all tables.
                tables = pd.read_html(url)
                df = tables[0]
            df["season"] = season
            df["comp_id"] = comp_id
            all_dfs.append(df)
    if not all_dfs:
        return pd.DataFrame()
    out = pd.concat(all_dfs, ignore_index=True)
    if "Wk" in out.columns:
        out = out.dropna(subset=["Wk"])
    drop_cols = [c for c in ["Match Report", "Notes"] if c in out.columns]
    if drop_cols:
        out = out.drop(columns=drop_cols)
    return out


def fetch_and_save(output: str | Path, start_year: int, end_year: int, comp_ids: Iterable[int]) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df = fetch_fbref_schedules(start_year=start_year, end_year=end_year, comp_ids=comp_ids)
    df.to_csv(output, index=False)
    return output
