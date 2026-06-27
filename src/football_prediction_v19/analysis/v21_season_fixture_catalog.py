# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_football_data_live_adapter import run_football_data_live_adapter
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context, normalize_match_date
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league
from football_prediction_v19.analysis.v20_understat_live_adapter import run_understat_live_adapter
from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league, resolve_league_support


def build_v21_season_fixture_catalog(
    competition: str,
    season: str,
    output_dir: str | Path,
    *,
    source_profile: str = "config/v20_internet_sources.yaml",
    enable_network: bool = False,
    cache_only: bool = False,
    cache_dir: str | Path | None = None,
    mock_data_dir: str | Path | None = None,
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    support = resolve_league_support(competition)
    mapping = resolve_source_league(competition, season, out)
    fallback = Path(mock_data_dir) if mock_data_dir else None
    context = resolve_analysis_cutoff(build_match_context("Catalog Home", "Catalog Away", competition, season, f"{season[:4] if season[:4].isdigit() else '2025'}-08-01"))
    football = run_football_data_live_adapter(
        mapping,
        context,
        out,
        enable_network=enable_network and not cache_only,
        cache_dir=cache_dir or out / "cache",
        mock_csv_path=(fallback / "football_data_live_mock.csv") if fallback and (fallback / "football_data_live_mock.csv").exists() and not cache_only else None,
    )
    understat = run_understat_live_adapter(
        mapping,
        context,
        out,
        enable_network=enable_network and not cache_only,
        cache_dir=cache_dir or out / "cache",
        mock_json_path=(fallback / "understat_league_mock.json") if fallback and (fallback / "understat_league_mock.json").exists() and not cache_only else None,
    )
    football_df = _read_csv(football.get("football_data_live_normalized_path", ""), ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"])
    understat_df = _read_csv(understat.get("understat_live_matches_normalized_path", ""), ["id", "date", "home_team", "away_team", "home_xg", "away_xg"])
    catalog, unmatched_fd, unmatched_us, aliases = join_fixture_sources(football_df, understat_df, competition, season, support.prediction_tier)
    paths = _write_catalog_outputs(out, catalog, unmatched_fd, unmatched_us, aliases, support.to_dict(), football, understat, source_profile)
    return {
        "v21_season_fixture_catalog_status": "READY" if not catalog.empty else "BLOCKED",
        "competition": competition,
        "season": season,
        "matches_total": int(len(catalog)),
        "football_data_status": football.get("football_data_live_status"),
        "understat_status": understat.get("understat_live_status"),
        "cache_used": bool(football.get("cache_used") or understat.get("cache_used")),
        "network_calls_enabled": bool(enable_network and not cache_only),
        **paths,
    }


def join_fixture_sources(football_df: pd.DataFrame, understat_df: pd.DataFrame, competition: str, season: str, prediction_tier: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fd = football_df.copy()
    us = understat_df.copy()
    records: list[dict[str, object]] = []
    matched_us: set[int] = set()
    for idx, row in fd.iterrows():
        date = normalize_match_date(str(row.get("Date", "")))
        home = str(row.get("HomeTeam", ""))
        away = str(row.get("AwayTeam", ""))
        hit = _understat_hit(us, date, home, away)
        understat_available = hit is not None
        if hit is not None:
            matched_us.add(int(hit.name))
        canonical_match_id = canonical_match_id_for(competition, season, date, home, away)
        result_available = str(row.get("FTR", "")).strip() != ""
        can_predict = prediction_tier in {"TIER_1_FULL_XG", "TIER_2_RESULTS_ONLY"}
        reason = "" if can_predict else "unsupported league tier"
        records.append(
            {
                "canonical_match_id": canonical_match_id,
                "competition": competition,
                "season": season,
                "match_date": date,
                "kickoff_time": "",
                "home_team": home,
                "away_team": away,
                "home_team_source_name": home,
                "away_team_source_name": away,
                "football_data_match_key": f"{date}|{home}|{away}",
                "understat_match_id": "" if hit is None else hit.get("id", ""),
                "football_data_available": True,
                "understat_available": understat_available,
                "xg_available": understat_available,
                "odds_available": False,
                "result_available": result_available,
                "fixture_status": "RESOLVED" if understat_available or prediction_tier == "TIER_2_RESULTS_ONLY" else "PARTIAL",
                "prediction_tier": prediction_tier,
                "can_predict_winner": can_predict,
                "cannot_predict_reason": reason,
                "home_goals": row.get("FTHG", ""),
                "away_goals": row.get("FTAG", ""),
                "actual_result": row.get("FTR", ""),
            }
        )
    catalog = pd.DataFrame(records)
    expected_columns = ["canonical_match_id", "competition", "season", "match_date", "kickoff_time", "home_team", "away_team", "home_team_source_name", "away_team_source_name", "football_data_match_key", "understat_match_id", "football_data_available", "understat_available", "xg_available", "odds_available", "result_available", "fixture_status", "prediction_tier", "can_predict_winner", "cannot_predict_reason", "home_goals", "away_goals", "actual_result"]
    for column in expected_columns:
        if column not in catalog.columns:
            catalog[column] = []
    unmatched_fd = fd.iloc[0:0].copy()
    unmatched_us = us.drop(index=list(matched_us), errors="ignore") if not us.empty else us
    aliases = _alias_suggestions(fd, us)
    return catalog, unmatched_fd, unmatched_us, aliases


def canonical_match_id_for(competition: str, season: str, match_date: str, home_team: str, away_team: str) -> str:
    raw = f"{competition}_{season}_{normalize_match_date(match_date)}_{normalize_team_or_league(home_team)}_{normalize_team_or_league(away_team)}"
    return raw.replace("/", "_").replace(" ", "_").lower()


def _understat_hit(us: pd.DataFrame, date: str, home: str, away: str) -> pd.Series | None:
    if us.empty:
        return None
    mask = (
        us["date"].map(lambda v: normalize_match_date(str(v))).eq(date)
        & us["home_team"].map(normalize_team_or_league).eq(normalize_team_or_league(home))
        & us["away_team"].map(normalize_team_or_league).eq(normalize_team_or_league(away))
    )
    if mask.any():
        return us[mask].iloc[0]
    return None


def _alias_suggestions(fd: pd.DataFrame, us: pd.DataFrame) -> pd.DataFrame:
    rows = []
    fd_teams = set(fd.get("HomeTeam", pd.Series(dtype=str)).astype(str)) | set(fd.get("AwayTeam", pd.Series(dtype=str)).astype(str))
    us_teams = set(us.get("home_team", pd.Series(dtype=str)).astype(str)) | set(us.get("away_team", pd.Series(dtype=str)).astype(str))
    for fd_team in sorted(fd_teams):
        for us_team in sorted(us_teams):
            if fd_team != us_team and normalize_team_or_league(fd_team) == normalize_team_or_league(us_team):
                rows.append({"football_data_team": fd_team, "understat_team": us_team, "normalized": normalize_team_or_league(fd_team)})
    return pd.DataFrame(rows, columns=["football_data_team", "understat_team", "normalized"])


def _write_catalog_outputs(out: Path, catalog: pd.DataFrame, unmatched_fd: pd.DataFrame, unmatched_us: pd.DataFrame, aliases: pd.DataFrame, support: dict[str, object], football: dict[str, object], understat: dict[str, object], source_profile: str) -> dict[str, str]:
    csv_path = out / "season_fixture_catalog.csv"
    json_path = out / "season_fixture_catalog.json"
    report_path = out / "season_fixture_catalog_report.md"
    unmatched_fd_path = out / "unmatched_football_data_rows.csv"
    unmatched_us_path = out / "unmatched_understat_rows.csv"
    aliases_path = out / "team_alias_suggestions.csv"
    coverage_path = out / "source_coverage_by_match.csv"
    catalog.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(catalog.to_dict(orient="records"), indent=2), encoding="utf-8")
    unmatched_fd.to_csv(unmatched_fd_path, index=False)
    unmatched_us.to_csv(unmatched_us_path, index=False)
    aliases.to_csv(aliases_path, index=False)
    catalog[["canonical_match_id", "football_data_available", "understat_available", "xg_available", "odds_available", "can_predict_winner"]].to_csv(coverage_path, index=False)
    report_path.write_text(
        "# v2.1 Season Fixture Catalog\n\n"
        + f"- matches_total: {len(catalog)}\n- prediction_tier: {support.get('prediction_tier')}\n- football_data_status: {football.get('football_data_live_status')}\n- understat_status: {understat.get('understat_live_status')}\n- source_profile: {source_profile}\n",
        encoding="utf-8",
    )
    return {
        "season_fixture_catalog_csv_path": str(csv_path.resolve()),
        "season_fixture_catalog_json_path": str(json_path.resolve()),
        "season_fixture_catalog_report_path": str(report_path.resolve()),
        "unmatched_football_data_rows_path": str(unmatched_fd_path.resolve()),
        "unmatched_understat_rows_path": str(unmatched_us_path.resolve()),
        "team_alias_suggestions_path": str(aliases_path.resolve()),
        "source_coverage_by_match_path": str(coverage_path.resolve()),
    }


def _read_csv(path: object, columns: list[str]) -> pd.DataFrame:
    p = Path(str(path))
    if not str(path) or not p.exists():
        return pd.DataFrame(columns=columns)
    return pd.read_csv(p, keep_default_na=False)
