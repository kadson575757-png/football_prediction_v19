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
    reason: str = ""
    candidate_matches: tuple[dict[str, object], ...] = ()
    suggested_team_names: tuple[str, ...] = ()
    exact_match_found: bool = False
    date_tolerance_match_found: bool = False
    season_team_pair_found: bool = False
    source_match_counts: dict[str, int] | None = None
    recommended_fix: str = ""
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["matched_sources"] = list(self.matched_sources)
        data["candidate_matches"] = list(self.candidate_matches)
        data["suggested_team_names"] = list(self.suggested_team_names)
        data["source_match_counts"] = self.source_match_counts or {}
        data["warnings"] = list(self.warnings)
        return data


def resolve_real_fixture(context: HistoricalMatchContext, source_paths: dict[str, str] | None = None, output_dir: str | Path | None = None, date_tolerance_days: int = 1) -> FixtureResolution:
    source_paths = source_paths or {}
    matched: list[str] = []
    ambiguous = False
    candidates: list[dict[str, object]] = []
    suggestions: set[str] = set()
    source_counts: dict[str, int] = {}
    exact_found = False
    tolerance_found = False
    season_found = False
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
        dates = pd.to_datetime(df[date_col], errors="coerce", format="%Y-%m-%d")
        if dates.isna().all():
            dates = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
        target = pd.to_datetime(context.match_date)
        home_norm = _norm(context.home_team); away_norm = _norm(context.away_team)
        exact_mask = df[home_col].map(_norm).eq(home_norm) & df[away_col].map(_norm).eq(away_norm) & dates.dt.strftime("%Y-%m-%d").eq(context.match_date)
        tol_mask = df[home_col].map(_norm).eq(home_norm) & df[away_col].map(_norm).eq(away_norm) & ((dates - target).abs().dt.days <= date_tolerance_days)
        season_mask = df[home_col].map(_norm).eq(home_norm) & df[away_col].map(_norm).eq(away_norm)
        fuzzy_mask = df[home_col].map(lambda v: _similar(v, context.home_team)) | df[away_col].map(lambda v: _similar(v, context.away_team))
        hits = df[exact_mask].drop_duplicates(subset=[home_col, away_col, date_col])
        if hits.empty:
            hits = df[tol_mask].drop_duplicates(subset=[home_col, away_col, date_col])
        if hits.empty:
            hits = df[season_mask].drop_duplicates(subset=[home_col, away_col, date_col])
        source_counts[source_name] = int(len(hits))
        exact_found = exact_found or bool(exact_mask.any())
        tolerance_found = tolerance_found or bool(tol_mask.any())
        season_found = season_found or bool(season_mask.any())
        for _, row in df[tol_mask | season_mask | fuzzy_mask].head(20).iterrows():
            candidates.append(_candidate(source_name, row, home_col, away_col, date_col, dates.loc[row.name] if row.name in dates.index else None, target, exact_mask.loc[row.name] if row.name in exact_mask.index else False))
        for team in list(df[home_col].dropna().unique()) + list(df[away_col].dropna().unique()):
            if _similar(team, context.home_team) or _similar(team, context.away_team):
                suggestions.add(str(team))
        if len(hits) > 1:
            ambiguous = True
        elif len(hits) == 1:
            matched.append(source_name)
    if ambiguous:
        status = "AMBIGUOUS"
    elif exact_found and matched:
        status = "RESOLVED"
    elif len(matched) >= 2 and not tolerance_found:
        status = "RESOLVED"
    elif len(matched) == 1:
        status = "PARTIAL"
    else:
        status = "NOT_FOUND"
    reason = _reason(status, exact_found, tolerance_found, season_found)
    result = FixtureResolution(status, context.home_team, context.away_team, context.match_date, tuple(matched), reason, tuple(candidates[:25]), tuple(sorted(suggestions)[:20]), exact_found, tolerance_found, season_found, source_counts, _recommended_fix(status, candidates, suggestions), () if matched else ("fixture not found in available source artifacts",))
    if output_dir is not None:
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        (out / "v20_fixture_resolution.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        (out / "v20_fixture_resolution.md").write_text(f"# v2.0 Fixture Resolution\n\n- status: {status}\n- reason: {reason}\n- matched_sources: {', '.join(matched) if matched else 'none'}\n- candidate_matches: {len(candidates)}\n- suggested_team_names: {', '.join(sorted(suggestions)) if suggestions else 'none'}\n- recommended_fix: {result.recommended_fix}\n", encoding="utf-8")
    return result


def _norm(value: object) -> str:
    aliases = {"man united": "manchester united", "man utd": "manchester united", "spurs": "tottenham", "inter": "internazionale", "leeds": "leeds united", "leeds utd": "leeds united"}
    text = " ".join(str(value).strip().lower().replace("-", " ").split())
    return aliases.get(text, text)


def _first(df: pd.DataFrame, names: list[str]) -> str:
    for name in names:
        if name in df.columns:
            return name
    return ""


def _similar(value: object, target: object) -> bool:
    v = _norm(value); t = _norm(target)
    return bool(v and t and (v in t or t in v or len(set(v.split()) & set(t.split())) >= 1))


def _candidate(source: str, row: pd.Series, home_col: str, away_col: str, date_col: str, date_value: object, target: object, exact: bool) -> dict[str, object]:
    delta = abs((date_value - target).days) if pd.notna(date_value) else 9999
    return {"source": source, "home_team": row.get(home_col, ""), "away_team": row.get(away_col, ""), "date": row.get(date_col, ""), "score": f"{row.get('FTHG', '')}-{row.get('FTAG', '')}", "confidence": 1.0 if exact else (0.85 if delta <= 1 else 0.55), "reason": "exact" if exact else ("date_tolerance" if delta <= 1 else "season_or_similar_team")}


def _reason(status: str, exact_found: bool, tolerance_found: bool, season_found: bool) -> str:
    if exact_found:
        return "exact fixture found"
    if tolerance_found:
        return "fixture found within date tolerance"
    if season_found:
        return "same teams found elsewhere in season; date may be wrong"
    if status == "AMBIGUOUS":
        return "multiple possible fixtures found"
    return "fixture not found; inspect candidate matches and suggested team names"


def _recommended_fix(status: str, candidates: list[dict[str, object]], suggestions: set[str]) -> str:
    if candidates:
        return "Review candidate_matches; the entered date or team spelling may differ from source data."
    if suggestions:
        return "Use one of suggested_team_names and rerun fixture search."
    if status == "AMBIGUOUS":
        return "Narrow the date or team names; multiple candidates match."
    return "Run scripts/search_v20_real_fixtures.py for the team and season."
