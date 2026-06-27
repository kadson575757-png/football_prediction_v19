# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

import pandas as pd

from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext


@dataclass(frozen=True)
class FixtureResolution:
    fixture_resolution_status: str
    home_team: str
    away_team: str
    match_date: str
    matched_sources: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["matched_sources"] = list(self.matched_sources)
        data["warnings"] = list(self.warnings)
        return data


def resolve_real_fixture(context: HistoricalMatchContext, source_paths: dict[str, str] | None = None, output_dir: str | Path | None = None, date_tolerance_days: int = 1) -> FixtureResolution:
    source_paths = source_paths or {}
    matched: list[str] = []
    ambiguous = False
    for source_name, path in source_paths.items():
        if not path or not Path(path).exists() or Path(path).suffix.lower() != ".csv":
            continue
        df = pd.read_csv(path, keep_default_na=False)
        if df.empty:
            continue
        home_col = _first(df, ["HomeTeam", "home_team"])
        away_col = _first(df, ["AwayTeam", "away_team"])
        date_col = _first(df, ["Date", "date", "match_date"])
        if not home_col or not away_col or not date_col:
            continue
        dates = pd.to_datetime(df[date_col], errors="coerce")
        target = pd.to_datetime(context.match_date)
        mask = df[home_col].map(_norm).eq(_norm(context.home_team)) & df[away_col].map(_norm).eq(_norm(context.away_team)) & ((dates - target).abs().dt.days <= date_tolerance_days)
        hits = df[mask].drop_duplicates(subset=[home_col, away_col, date_col])
        if len(hits) > 1:
            ambiguous = True
        elif len(hits) == 1:
            matched.append(source_name)
    if ambiguous:
        status = "AMBIGUOUS"
    elif len(matched) >= 2:
        status = "RESOLVED"
    elif len(matched) == 1:
        status = "PARTIAL"
    else:
        status = "NOT_FOUND"
    result = FixtureResolution(status, context.home_team, context.away_team, context.match_date, tuple(matched), () if matched else ("fixture not found in available source artifacts",))
    if output_dir is not None:
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        (out / "v20_fixture_resolution.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        (out / "v20_fixture_resolution.md").write_text(f"# v2.0 Fixture Resolution\n\n- status: {status}\n- matched_sources: {', '.join(matched) if matched else 'none'}\n", encoding="utf-8")
    return result


def _norm(value: object) -> str:
    return " ".join(str(value).strip().lower().replace("-", " ").split())


def _first(df: pd.DataFrame, names: list[str]) -> str:
    for name in names:
        if name in df.columns:
            return name
    return ""
