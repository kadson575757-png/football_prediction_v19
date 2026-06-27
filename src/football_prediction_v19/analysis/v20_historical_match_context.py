# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True)
class HistoricalMatchContext:
    match_id: str
    home_team: str
    away_team: str
    competition: str
    season: str
    match_date: str
    kickoff_time: str = ""
    matchday: str = ""
    analysis_cutoff: str = ""
    cutoff_policy: str = "MATCH_DATE_START"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_match_context(home_team: str, away_team: str, competition: str, season: str, match_date: str, *, kickoff_time: str = "", matchday: str = "", analysis_cutoff: str = "", cutoff_policy: str = "MATCH_DATE_START") -> HistoricalMatchContext:
    normalized_date = normalize_match_date(match_date)
    match_id = f"{competition}_{season}_{home_team}_{away_team}_{normalized_date}".lower().replace(" ", "_").replace("/", "_")
    return HistoricalMatchContext(match_id, home_team, away_team, competition, season, normalized_date, kickoff_time, matchday, analysis_cutoff, cutoff_policy)


def parse_dt(value: str) -> datetime:
    text = str(value).strip()
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d.%m.%Y %H:%M", "%d.%m.%Y"]:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return datetime.fromisoformat(text)


def normalize_match_date(value: str) -> str:
    return parse_dt(str(value).strip()).strftime("%Y-%m-%d")
