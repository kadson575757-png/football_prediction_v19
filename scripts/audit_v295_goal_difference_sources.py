# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v20_historical_match_context import normalize_match_date  # noqa: E402
from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league  # noqa: E402
from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date  # noqa: E402
from football_prediction_v19.analysis.v294_goal_difference_indicator import _load_match_rows  # noqa: E402


def audit_goal_difference_sources(
    *,
    competition: str = "",
    season: str = "",
    home: str = "",
    away: str = "",
    match_date: str = "",
    rows: str | Path | None = None,
    source_profile: str = "config/v20_internet_sources.yaml",
    cache_only: bool = True,
    enable_network: bool = False,
    output_dir: str | Path = "outputs/v295_goal_difference_source_audit",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    audits = []
    home_details = []
    away_details = []
    if rows:
        match_inputs = _rows_to_match_inputs(rows)
    else:
        resolved = _resolve_single_match_date(
            competition=competition,
            season=season,
            home=home,
            away=away,
            match_date=match_date,
            source_profile=source_profile,
            cache_only=cache_only,
            enable_network=enable_network,
        )
        if resolved["status"] == "DATA_BLOCKED":
            return _write_blocked_outputs(out, str(resolved["reason"]))
        match_inputs = [{"competition": competition, "season": season, "home_team": home, "away_team": away, "match_date": resolved["match_date"]}]
    for item in match_inputs:
        audit = audit_single_goal_difference_source(
            competition=str(item.get("competition", "")),
            season=str(item.get("season", "")),
            home_team=str(item.get("home_team", "")),
            away_team=str(item.get("away_team", "")),
            match_date=str(item.get("match_date", "")),
            source_profile=source_profile,
            cache_only=cache_only,
            enable_network=enable_network,
        )
        audits.append(audit["row"])
        home_details.extend(audit["home_matches"])
        away_details.extend(audit["away_matches"])
    rows_frame = pd.DataFrame(audits)
    home_frame = pd.DataFrame(home_details)
    away_frame = pd.DataFrame(away_details)
    summary = _summary(rows_frame)
    rows_path = out / "v295_goal_difference_source_audit_rows.csv"
    home_path = out / "v295_goal_difference_source_audit_home_matches.csv"
    away_path = out / "v295_goal_difference_source_audit_away_matches.csv"
    json_path = out / "v295_goal_difference_source_audit_summary.json"
    md_path = out / "v295_goal_difference_source_audit_report.md"
    rows_frame.to_csv(rows_path, index=False)
    home_frame.to_csv(home_path, index=False)
    away_frame.to_csv(away_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(summary), encoding="utf-8")
    first = audits[0] if audits else {}
    return {
        **summary,
        **{key: first.get(key, "") for key in [
            "home_goal_difference_before_match",
            "away_goal_difference_before_match",
            "goal_difference_diff",
            "leakage_check_status",
            "current_match_excluded",
            "post_match_games_used_count",
        ]},
        "rows_csv_path": str(rows_path.resolve()),
        "home_matches_csv_path": str(home_path.resolve()),
        "away_matches_csv_path": str(away_path.resolve()),
        "summary_json_path": str(json_path.resolve()),
        "report_md_path": str(md_path.resolve()),
    }


def _resolve_single_match_date(
    *,
    competition: str,
    season: str,
    home: str,
    away: str,
    match_date: str,
    source_profile: str,
    cache_only: bool,
    enable_network: bool,
) -> dict[str, object]:
    if str(match_date).strip():
        return {"status": "READY", "match_date": match_date, "reason": "explicit match_date provided"}
    resolver = resolve_fixture_date(
        competition,
        season,
        home,
        away,
        source_profile=source_profile,
        cache_only=cache_only,
        enable_network=enable_network,
    )
    if resolver.get("resolver_status") == "RESOLVED" and resolver.get("match_date"):
        return {"status": "READY", "match_date": str(resolver["match_date"]), "reason": resolver.get("reason", "")}
    return {"status": "DATA_BLOCKED", "match_date": "", "reason": "match_date missing and fixture could not be resolved"}


def _write_blocked_outputs(out: Path, reason: str) -> dict[str, object]:
    summary = {
        "v295_goal_difference_source_audit_status": "DATA_BLOCKED",
        "reason": reason,
        "rows_audited": 0,
        "clean_count": 0,
        "failed_count": 0,
        "current_match_excluded_count": 0,
        "post_match_games_used_total": 0,
        "full_quality_count": 0,
        "partial_quality_count": 0,
        "low_quality_count": 0,
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    rows_path = out / "v295_goal_difference_source_audit_rows.csv"
    home_path = out / "v295_goal_difference_source_audit_home_matches.csv"
    away_path = out / "v295_goal_difference_source_audit_away_matches.csv"
    json_path = out / "v295_goal_difference_source_audit_summary.json"
    md_path = out / "v295_goal_difference_source_audit_report.md"
    pd.DataFrame().to_csv(rows_path, index=False)
    pd.DataFrame().to_csv(home_path, index=False)
    pd.DataFrame().to_csv(away_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(summary), encoding="utf-8")
    return {
        **summary,
        "rows_csv_path": str(rows_path.resolve()),
        "home_matches_csv_path": str(home_path.resolve()),
        "away_matches_csv_path": str(away_path.resolve()),
        "summary_json_path": str(json_path.resolve()),
        "report_md_path": str(md_path.resolve()),
    }


def audit_single_goal_difference_source(
    *,
    competition: str,
    season: str,
    home_team: str,
    away_team: str,
    match_date: str,
    source_profile: str = "config/v20_internet_sources.yaml",
    cache_only: bool = True,
    enable_network: bool = False,
) -> dict[str, object]:
    del source_profile
    rows = _load_match_rows(competition, season, home_team, away_team, match_date, cache_only=cache_only, enable_network=enable_network)
    audited_date = _safe_date(match_date)
    home_matches = _detail_rows(rows, audited_home=home_team, audited_away=away_team, audited_date=audited_date, team=home_team)
    away_matches = _detail_rows(rows, audited_home=home_team, audited_away=away_team, audited_date=audited_date, team=away_team)
    home_included = [row for row in home_matches if row["included_in_goal_difference"]]
    away_included = [row for row in away_matches if row["included_in_goal_difference"]]
    home_for = sum(int(row["team_goals_for"]) for row in home_included)
    home_against = sum(int(row["team_goals_against"]) for row in home_included)
    away_for = sum(int(row["team_goals_for"]) for row in away_included)
    away_against = sum(int(row["team_goals_against"]) for row in away_included)
    home_gd = home_for - home_against
    away_gd = away_for - away_against
    post_used = _post_match_games_used_count(home_matches + away_matches, audited_date)
    current_excluded = _current_match_excluded(home_matches + away_matches, home_team, away_team, audited_date)
    quality = _quality(len(home_included), len(away_included))
    return {
        "row": {
            "competition": competition,
            "season": season,
            "home_team": home_team,
            "away_team": away_team,
            "match_date": audited_date,
            "as_of_date": _as_of_date(audited_date),
            "home_matches_before_match": len(home_included),
            "away_matches_before_match": len(away_included),
            "home_goals_for_before_match": home_for,
            "home_goals_against_before_match": home_against,
            "away_goals_for_before_match": away_for,
            "away_goals_against_before_match": away_against,
            "home_goal_difference_before_match": home_gd,
            "away_goal_difference_before_match": away_gd,
            "goal_difference_diff": home_gd - away_gd,
            "goal_difference_indicator_quality": quality,
            "leakage_check_status": "FAILED" if post_used else "CLEAN",
            "current_match_excluded": current_excluded,
            "post_match_games_used_count": post_used,
        },
        "home_matches": home_matches,
        "away_matches": away_matches,
    }


def _detail_rows(frame: pd.DataFrame, *, audited_home: str, audited_away: str, audited_date: str, team: str) -> list[dict[str, object]]:
    if frame.empty:
        return []
    team_norm = normalize_team_or_league(team)
    details = []
    for _, row in frame.iterrows():
        home = str(row.get("home_team", ""))
        away = str(row.get("away_team", ""))
        home_norm = normalize_team_or_league(home)
        away_norm = normalize_team_or_league(away)
        if team_norm not in {home_norm, away_norm}:
            continue
        source_date = _safe_date(row.get("match_date", ""))
        home_goals = _int(row.get("home_goals", 0))
        away_goals = _int(row.get("away_goals", 0))
        is_home_team = home_norm == team_norm
        goals_for = home_goals if is_home_team else away_goals
        goals_against = away_goals if is_home_team else home_goals
        is_current = source_date == audited_date and home_norm == normalize_team_or_league(audited_home) and away_norm == normalize_team_or_league(audited_away)
        included = bool(source_date and source_date < audited_date and not is_current)
        reason = "" if included else ("NOT_BEFORE_MATCH_DATE" if source_date >= audited_date else "INVALID_DATE")
        details.append(
            {
                "audited_match_home": audited_home,
                "audited_match_away": audited_away,
                "audited_match_date": audited_date,
                "team": team,
                "source_match_date": source_date,
                "source_home_team": home,
                "source_away_team": away,
                "source_home_goals": home_goals,
                "source_away_goals": away_goals,
                "team_goals_for": goals_for,
                "team_goals_against": goals_against,
                "included_in_goal_difference": included,
                "exclusion_reason": reason,
            }
        )
    return details


def _rows_to_match_inputs(rows: str | Path | None) -> list[dict[str, object]]:
    if not rows:
        return []
    frame = pd.read_csv(rows, keep_default_na=False)
    result = []
    for _, row in frame.iterrows():
        result.append(
            {
                "competition": row.get("competition", ""),
                "season": row.get("season", ""),
                "home_team": row.get("home_team", ""),
                "away_team": row.get("away_team", ""),
                "match_date": row.get("input_match_date") or row.get("match_date") or row.get("resolved_match_date", ""),
            }
        )
    return result


def _summary(rows_frame: pd.DataFrame) -> dict[str, object]:
    if rows_frame.empty:
        clean = failed = current = post = full = partial = low = 0
    else:
        clean = int(rows_frame["leakage_check_status"].astype(str).eq("CLEAN").sum())
        failed = int(rows_frame["leakage_check_status"].astype(str).eq("FAILED").sum())
        current = int(rows_frame["current_match_excluded"].astype(str).str.lower().isin(["true", "1"]).sum())
        post = int(pd.to_numeric(rows_frame["post_match_games_used_count"], errors="coerce").fillna(0).sum())
        full = int(rows_frame["goal_difference_indicator_quality"].astype(str).eq("FULL").sum())
        partial = int(rows_frame["goal_difference_indicator_quality"].astype(str).eq("PARTIAL").sum())
        low = int(rows_frame["goal_difference_indicator_quality"].astype(str).eq("LOW").sum())
    return {
        "v295_goal_difference_source_audit_status": "READY",
        "rows_audited": int(len(rows_frame)),
        "clean_count": clean,
        "failed_count": failed,
        "current_match_excluded_count": current,
        "post_match_games_used_total": post,
        "full_quality_count": full,
        "partial_quality_count": partial,
        "low_quality_count": low,
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def _post_match_games_used_count(details: list[dict[str, object]], audited_date: str) -> int:
    return sum(1 for row in details if bool(row.get("included_in_goal_difference")) and str(row.get("source_match_date", "")) >= audited_date)


def _current_match_excluded(details: list[dict[str, object]], home: str, away: str, audited_date: str) -> bool:
    home_norm = normalize_team_or_league(home)
    away_norm = normalize_team_or_league(away)
    current_rows = [
        row for row in details
        if str(row.get("source_match_date", "")) == audited_date
        and normalize_team_or_league(row.get("source_home_team", "")) == home_norm
        and normalize_team_or_league(row.get("source_away_team", "")) == away_norm
    ]
    return bool(current_rows) and not any(bool(row.get("included_in_goal_difference")) for row in current_rows)


def _quality(home_n: int, away_n: int) -> str:
    if home_n >= 8 and away_n >= 8:
        return "FULL"
    if home_n >= 3 and away_n >= 3:
        return "PARTIAL"
    return "LOW"


def _safe_date(value: object) -> str:
    try:
        return normalize_match_date(str(value))
    except Exception:
        return ""


def _as_of_date(match_date: str) -> str:
    try:
        return (datetime.strptime(match_date, "%Y-%m-%d") - timedelta(days=1)).date().isoformat()
    except ValueError:
        return ""


def _int(value: object) -> int:
    try:
        if str(value).strip() == "":
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _markdown(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# v2.9.5 Goal Difference Source Audit",
            "",
            f"- status: {summary['v295_goal_difference_source_audit_status']}",
            f"- reason: {summary.get('reason', '')}",
            f"- rows_audited: {summary['rows_audited']}",
            f"- clean_count: {summary['clean_count']}",
            f"- failed_count: {summary['failed_count']}",
            f"- post_match_games_used_total: {summary['post_match_games_used_total']}",
            "",
            "Diagnostic-only source audit. No probabilities were changed.",
            "",
            "## Safety",
            "- automatic_betting_enabled: false",
            "- staking_logic_enabled: false",
            "- roi_logic_enabled: false",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition", default="")
    parser.add_argument("--season", default="")
    parser.add_argument("--home", default="")
    parser.add_argument("--away", default="")
    parser.add_argument("--match-date", default="")
    parser.add_argument("--rows", default="")
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--output-dir", default="outputs/v295_goal_difference_source_audit")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = audit_goal_difference_sources(
        competition=args.competition,
        season=args.season,
        home=args.home,
        away=args.away,
        match_date=args.match_date,
        rows=args.rows or None,
        source_profile=args.source_profile,
        cache_only=args.cache_only,
        enable_network=args.enable_network,
        output_dir=args.output_dir,
    )
    for key in [
        "v295_goal_difference_source_audit_status",
        "reason",
        "rows_audited",
        "home_goal_difference_before_match",
        "away_goal_difference_before_match",
        "goal_difference_diff",
        "clean_count",
        "failed_count",
        "current_match_excluded_count",
        "post_match_games_used_total",
        "leakage_check_status",
        "current_match_excluded",
        "post_match_games_used_count",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
