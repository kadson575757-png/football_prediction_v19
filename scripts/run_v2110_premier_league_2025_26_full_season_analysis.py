# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v21_season_fixture_catalog import build_v21_season_fixture_catalog  # noqa: E402
from football_prediction_v19.analysis.v20_historical_match_context import normalize_match_date  # noqa: E402
from scripts.run_match_probability_analysis import run_match_probability_analysis  # noqa: E402


EXPECTED_PL_FIXTURE_COUNT = 380
DEFAULT_OUTPUT_DIR = "outputs/premier_league_2025_26_full_analysis"

INDICATORS: list[tuple[str, str]] = [
    ("Home/Away PPG", "ppg"),
    ("Last-5 Form", "last5"),
    ("Goal Difference", "gd"),
    ("Goals For", "gf"),
    ("Goals Against", "ga"),
    ("Draw Tendency", "dt"),
    ("Venue Result Rate", "vr"),
    ("Goal Margin Profile", "gm"),
    ("Venue Scoring Balance", "vsb"),
    ("Clean Sheet / Failed To Score", "csfts"),
    ("Rest Days Congestion", "rdc"),
    ("Table Strength Gap", "tsg"),
    ("Comeback / Blown Lead", "cbl"),
    ("Opponent Adjusted Recent Form", "oarf"),
    ("Recent Goal Trend", "rgt"),
    ("Venue Recent Momentum", "vrm"),
    ("Result Volatility Consistency", "rvc"),
    ("Result Streak", "rsp"),
    ("Scoring Run", "srp"),
    ("Head To Head Context", "h2hc"),
    ("League Zone Pressure", "lzp"),
    ("Common Opponent Performance", "cop"),
    ("Strength Band Performance", "sbp"),
    ("Response After Result", "rar"),
    ("Heavy Result Exposure", "hre"),
    ("Attack Defense Matchup", "adm"),
    ("Venue Split Delta", "vsd"),
    ("Draw Pressure Composite", "dpc"),
    ("Shadow Consensus Alignment", "sca"),
]

MIX_PREFIXES = ["mix", "v2105_mix", "combined_mix", "v2106_mix", "v2106_combined_mix", "v2107_mix", "v2107_combined_mix", "v2108_mix", "v2108_combined_mix", "v2109_mix", "v2109_combined_mix"]

FORBIDDEN_REPORT_TERMS = ("stake", "roi", "profit", "yield", "bankroll")


def build_pl_fixture_list(fixtures: pd.DataFrame, competition: str = "Premier League", season: str = "2025/26", expected_count: int = EXPECTED_PL_FIXTURE_COUNT) -> tuple[pd.DataFrame, dict[str, object]]:
    work = fixtures.copy()
    rename = {"Date": "match_date", "HomeTeam": "home_team", "AwayTeam": "away_team"}
    work = work.rename(columns={key: value for key, value in rename.items() if key in work.columns})
    for column in ["competition", "season", "match_date", "home_team", "away_team", "source", "fixture_id"]:
        if column not in work.columns:
            work[column] = ""
    work["competition"] = work["competition"].replace("", competition)
    work["season"] = work["season"].replace("", season)
    work["source"] = work["source"].replace("", "fixture_catalog")
    work["match_date"] = work["match_date"].map(lambda value: _safe_date(value))
    before = len(work)
    unique = work.drop_duplicates(subset=["competition", "season", "home_team", "away_team", "match_date"]).reset_index(drop=True)
    duplicate_count = before - len(unique)
    coverage = round(len(unique) / expected_count, 4) if expected_count else 0.0
    summary = {
        "v2110_pl_fixture_list_status": "READY" if len(unique) >= expected_count else ("READY_WITH_WARNINGS" if len(unique) else "EMPTY"),
        "competition": competition,
        "season": season,
        "fixtures_found": int(before),
        "fixtures_unique": int(len(unique)),
        "duplicate_count": int(duplicate_count),
        "expected_fixture_count": int(expected_count),
        "fixture_coverage_rate": coverage,
        "missing_fixture_warning": bool(len(unique) < expected_count),
    }
    return unique, summary


def load_pl_fixtures(
    competition: str,
    season: str,
    output_dir: str | Path,
    *,
    source_profile: str = "config/v20_internet_sources.yaml",
    enable_network: bool = False,
    cache_only: bool = False,
    expected_count: int = EXPECTED_PL_FIXTURE_COUNT,
) -> tuple[pd.DataFrame, dict[str, object]]:
    out = Path(output_dir)
    catalog = build_v21_season_fixture_catalog(
        competition=competition,
        season=season,
        output_dir=out / "fixture_catalog",
        source_profile=source_profile,
        enable_network=enable_network,
        cache_only=cache_only,
    )
    path = Path(str(catalog.get("season_fixture_catalog_csv_path", "")))
    frame = pd.read_csv(path, keep_default_na=False) if path.exists() else pd.DataFrame()
    fixtures, summary = build_pl_fixture_list(frame, competition, season, expected_count)
    summary["fixture_catalog_status"] = catalog.get("v21_season_fixture_catalog_status", "")
    return fixtures, summary


def run_full_season_analysis(
    fixtures: pd.DataFrame,
    *,
    competition: str = "Premier League",
    season: str = "2025/26",
    source_profile: str = "config/v20_internet_sources.yaml",
    enable_network: bool = False,
    cache_only: bool = False,
    include_results: bool = False,
    write_match_reports: bool = True,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    runner: Callable[..., dict[str, object]] = run_match_probability_analysis,
) -> dict[str, object]:
    out = Path(output_dir)
    reports_dir = out / "reports"
    out.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    unique, fixture_summary = build_pl_fixture_list(fixtures, competition, season)
    unique.to_csv(out / "pl_2025_26_fixture_list.csv", index=False)
    rows: list[dict[str, object]] = []
    reports_written = 0
    failed = 0
    warnings = 0
    for idx, fixture in unique.iterrows():
        match_date = _safe_date(fixture.get("match_date", ""))
        as_of_date = _as_of_date(match_date)
        try:
            result = runner(
                competition=fixture.get("competition", competition),
                season=fixture.get("season", season),
                home=fixture.get("home_team", ""),
                away=fixture.get("away_team", ""),
                match_date=match_date,
                as_of_date=as_of_date,
                source_profile=source_profile,
                cache_only=cache_only,
                enable_network=enable_network,
                output_dir=out / "match_runs" / f"match_{idx + 1}",
            )
            row = _analysis_row(fixture, result, as_of_date, include_results)
            if str(row.get("probability_analysis_status", "")) != "READY":
                warnings += 1
        except Exception as exc:  # noqa: BLE001 - batch must not fail the season.
            failed += 1
            row = _failed_row(fixture, as_of_date, exc)
        rows.append(row)
        if write_match_reports:
            report_path = reports_dir / f"{_slug(match_date)}_{_slug(fixture.get('home_team', 'home'))}_vs_{_slug(fixture.get('away_team', 'away'))}.md"
            report_path.write_text(render_match_markdown_report(row), encoding="utf-8")
            row["report_path"] = str(report_path.resolve())
            reports_written += 1
    rows_frame = pd.DataFrame(rows)
    rows_path = out / "pl_2025_26_analysis_rows.csv"
    jsonl_path = out / "pl_2025_26_analysis_rows.jsonl"
    summary_path = out / "pl_2025_26_analysis_summary.json"
    index_path = out / "pl_2025_26_analysis_index.md"
    availability_path = out / "pl_2025_26_indicator_availability.csv"
    rows_frame.to_csv(rows_path, index=False)
    jsonl_path.write_text("\n".join(json.dumps(row, default=str) for row in rows) + ("\n" if rows else ""), encoding="utf-8")
    availability = compute_indicator_availability(rows_frame)
    availability.to_csv(availability_path, index=False)
    indicator_summary = _indicator_console_summary(availability)
    summary = _season_summary(rows_frame, fixture_summary, failed, warnings, reports_written, out, indicator_summary)
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    index_path.write_text(render_season_index(summary, rows_frame), encoding="utf-8")
    return {
        **summary,
        "fixture_list_csv_path": str((out / "pl_2025_26_fixture_list.csv").resolve()),
        "analysis_rows_csv_path": str(rows_path.resolve()),
        "analysis_rows_jsonl_path": str(jsonl_path.resolve()),
        "analysis_summary_json_path": str(summary_path.resolve()),
        "analysis_index_md_path": str(index_path.resolve()),
        "indicator_availability_csv_path": str(availability_path.resolve()),
    }


def _analysis_row(fixture: pd.Series, result: dict[str, object], as_of_date: str, include_results: bool) -> dict[str, object]:
    row = dict(result)
    row.update({
        "competition": fixture.get("competition", result.get("competition", "")),
        "season": fixture.get("season", result.get("season", "")),
        "home_team": fixture.get("home_team", result.get("home_team", "")),
        "away_team": fixture.get("away_team", result.get("away_team", "")),
        "match_date": _safe_date(fixture.get("match_date", result.get("match_date", ""))),
        "as_of_date": as_of_date,
        "fixture_source": fixture.get("source", ""),
        "fixture_id": fixture.get("fixture_id", ""),
        "post_match_analysis": False,
        "leakage_warning": False,
        "asof_guard_status": result.get("asof_guard_status", "CLEAN") or "CLEAN",
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    })
    if not include_results:
        for key in ["actual_home_goals", "actual_away_goals", "actual_result", "top_probability_hit", "home_goals", "away_goals", "real_result"]:
            row.pop(key, None)
    return row


def _failed_row(fixture: pd.Series, as_of_date: str, exc: Exception) -> dict[str, object]:
    return {
        "probability_analysis_status": "FAILED",
        "failure_reason": type(exc).__name__,
        "competition": fixture.get("competition", ""),
        "season": fixture.get("season", ""),
        "home_team": fixture.get("home_team", ""),
        "away_team": fixture.get("away_team", ""),
        "match_date": _safe_date(fixture.get("match_date", "")),
        "as_of_date": as_of_date,
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def compute_indicator_availability(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for name, prefix in INDICATORS:
        quality_col = _quality_col(prefix)
        applied_col = f"{prefix}_adjustment_applied"
        qualities = rows[quality_col].astype(str).str.upper() if quality_col in rows.columns else pd.Series(["MISSING"] * len(rows))
        applied = rows[applied_col].astype(str).str.lower().isin(["true", "1", "yes"]) if applied_col in rows.columns else pd.Series([False] * len(rows))
        total = len(rows)
        full = int(qualities.eq("FULL").sum())
        partial = int(qualities.eq("PARTIAL").sum())
        low = int(qualities.eq("LOW").sum())
        missing = int(total - full - partial - low)
        records.append({
            "indicator_name": name,
            "prefix": prefix,
            "full_quality_count": full,
            "partial_quality_count": partial,
            "low_quality_count": low,
            "missing_count": missing,
            "adjustment_applied_count": int(applied.sum()),
            "full_quality_rate": _rate(full, total),
            "partial_quality_rate": _rate(partial, total),
            "low_quality_rate": _rate(low, total),
            "adjustment_applied_rate": _rate(int(applied.sum()), total),
        })
    return pd.DataFrame(records)


def render_match_markdown_report(row: dict[str, object]) -> str:
    lines = [
        f"# {row.get('home_team', '')} vs {row.get('away_team', '')}",
        "",
        "## Match",
        f"- competition: {row.get('competition', '')}",
        f"- season: {row.get('season', '')}",
        f"- match_date: {row.get('match_date', '')}",
        f"- as_of_date: {row.get('as_of_date', '')}",
        f"- home_team: {row.get('home_team', '')}",
        f"- away_team: {row.get('away_team', '')}",
        f"- fixture source: {row.get('fixture_source', '')}",
        "",
        "## Final Probability Output",
        f"- Home %: {_pct(row.get('home_win_probability'))}",
        f"- Draw %: {_pct(row.get('draw_probability'))}",
        f"- Away %: {_pct(row.get('away_win_probability'))}",
        f"- Top probability outcome: {row.get('top_probability_outcome', '')}",
        f"- Edge: {row.get('probability_edge', '')}",
        f"- Edge band: {row.get('probability_edge_band', '')}",
        f"- Uncertainty level: {row.get('uncertainty_level', '')}",
        f"- Data quality band: {row.get('data_quality_band', row.get('source_quality_band', ''))}",
        "",
        "## Data Quality",
        f"- xg_available: {str(row.get('xg_available', False)).lower()}",
        f"- odds_available: {str(row.get('odds_available', False)).lower()}",
        f"- source_quality_band: {row.get('source_quality_band', '')}",
        f"- asof_guard_status: {row.get('asof_guard_status', '')}",
        f"- leakage_warning: {str(row.get('leakage_warning', False)).lower()}",
        "",
        "## Base Explanation",
        f"- probability_summary: {row.get('probability_summary', '')}",
        f"- probability_explanation: {row.get('probability_explanation', '')}",
        f"- signal_alignment_summary: {row.get('signal_alignment_summary', '')}",
        f"- signal_conflict_summary: {row.get('signal_conflict_summary', '')}",
        f"- final_probability_explanation: {row.get('final_probability_explanation', '')}",
        "",
        "## Indicator Quality Table",
        "| Indicator | Prefix | Quality | Adjustment Applied | Adjustment Strength | Shadow Top Outcome | Short Reason |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for name, prefix in INDICATORS:
        lines.append(f"| {name} | {prefix} | {row.get(_quality_col(prefix), '')} | {row.get(f'{prefix}_adjustment_applied', '')} | {row.get(f'{prefix}_adjustment_strength', '')} | {_top(row, prefix)} | {row.get(f'{prefix}_adjustment_reason', row.get(f'{prefix}_signal', ''))} |")
    lines += ["", "## Shadow Probability Table", "| Indicator | Home | Draw | Away | Top Outcome |", "|---|---:|---:|---:|---|"]
    for name, prefix in INDICATORS:
        lines.append(f"| {name} | {_pct(row.get(f'{prefix}_adjusted_home_win_probability'))} | {_pct(row.get(f'{prefix}_adjusted_draw_probability'))} | {_pct(row.get(f'{prefix}_adjusted_away_probability'))} | {_top(row, prefix)} |")
    lines += ["", "## Mix Table", "| Mix | Home | Draw | Away | Top Outcome |", "|---|---:|---:|---:|---|"]
    for prefix in MIX_PREFIXES:
        lines.append(f"| {prefix} | {_pct(row.get(f'{prefix}_adjusted_home_win_probability'))} | {_pct(row.get(f'{prefix}_adjusted_draw_probability'))} | {_pct(row.get(f'{prefix}_adjusted_away_probability'))} | {_top(row, prefix)} |")
    lines += [
        "",
        "## Safety",
        "- automatic_betting_enabled=false",
        "- staking_logic_enabled=false",
        "- roi_logic_enabled=false",
        "",
        "Probability-only diagnostic report. No automatic betting, no staking, no return metrics.",
        "",
    ]
    return "\n".join(lines)


def render_season_index(summary: dict[str, object], rows: pd.DataFrame) -> str:
    lines = [
        "# Premier League 2025/26 Full Season Probability Analysis",
        "",
        "## Summary",
    ]
    for key in ["fixtures_found", "fixtures_analyzed", "analysis_success_count", "analysis_warning_count", "analysis_failed_count", "probability_output_rate", "average_home_probability", "average_draw_probability", "average_away_probability", "top_probability_home_count", "top_probability_draw_count", "top_probability_away_count", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        lines.append(f"- {key}: {summary.get(key)}")
    lines += ["", "| Date | Home | Away | Home % | Draw % | Away % | Top Outcome | Edge | Data Quality | Report Link |", "|---|---|---|---:|---:|---:|---|---:|---|---|"]
    for _, row in rows.iterrows():
        report = Path(str(row.get("report_path", ""))).name if str(row.get("report_path", "")) else ""
        link = f"[report](reports/{report})" if report else ""
        lines.append(f"| {row.get('match_date', '')} | {row.get('home_team', '')} | {row.get('away_team', '')} | {_pct(row.get('home_win_probability'))} | {_pct(row.get('draw_probability'))} | {_pct(row.get('away_win_probability'))} | {row.get('top_probability_outcome', '')} | {row.get('probability_edge', '')} | {row.get('data_quality_band', row.get('source_quality_band', ''))} | {link} |")
    return "\n".join(lines)


def _season_summary(rows: pd.DataFrame, fixture_summary: dict[str, object], failed: int, warnings: int, reports_written: int, out: Path, indicator_summary: dict[str, object]) -> dict[str, object]:
    analyzed = len(rows)
    success = int(rows.get("probability_analysis_status", pd.Series(dtype=str)).astype(str).eq("READY").sum()) if analyzed else 0
    probability_output = rows.get("home_win_probability", pd.Series(dtype=object)).astype(str).ne("").sum() if analyzed else 0
    status = "READY_WITH_WARNINGS" if fixture_summary.get("missing_fixture_warning") or failed or warnings else "READY"
    return {
        "v2110_pl_full_season_analysis_status": status,
        **fixture_summary,
        "fixtures_analyzed": int(analyzed),
        "analysis_success_count": int(success),
        "analysis_warning_count": int(warnings),
        "analysis_failed_count": int(failed),
        "probability_output_rate": _rate(int(probability_output), analyzed),
        "reports_written": int(reports_written),
        "output_dir": str(out),
        "indicator_availability_status": "READY",
        **indicator_summary,
        "average_home_probability": _mean(rows, "home_win_probability"),
        "average_draw_probability": _mean(rows, "draw_probability"),
        "average_away_probability": _mean(rows, "away_win_probability"),
        "top_probability_home_count": _count(rows, "top_probability_outcome", "HOME"),
        "top_probability_draw_count": _count(rows, "top_probability_outcome", "DRAW"),
        "top_probability_away_count": _count(rows, "top_probability_outcome", "AWAY"),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def _indicator_console_summary(availability: pd.DataFrame) -> dict[str, object]:
    if availability.empty:
        return {"indicator_count": 0, "most_available_indicator": "", "least_available_indicator": "", "highest_low_quality_indicator": "", "highest_adjustment_applied_indicator": ""}
    work = availability.copy()
    work["available"] = work["full_quality_count"] + work["partial_quality_count"]
    return {
        "indicator_count": int(len(work)),
        "most_available_indicator": str(work.sort_values(["available", "full_quality_count"], ascending=False).iloc[0]["indicator_name"]),
        "least_available_indicator": str(work.sort_values(["available", "full_quality_count"], ascending=True).iloc[0]["indicator_name"]),
        "highest_low_quality_indicator": str(work.sort_values("low_quality_count", ascending=False).iloc[0]["indicator_name"]),
        "highest_adjustment_applied_indicator": str(work.sort_values("adjustment_applied_count", ascending=False).iloc[0]["indicator_name"]),
    }


def _quality_col(prefix: str) -> str:
    return {
        "gd": "goal_difference_indicator_quality",
        "gf": "goals_for_indicator_quality",
        "ga": "goals_against_indicator_quality",
    }.get(prefix, f"{prefix}_indicator_quality")


def _as_of_date(match_date: str) -> str:
    try:
        return (date.fromisoformat(match_date) - timedelta(days=1)).isoformat()
    except ValueError:
        return ""


def _safe_date(value: object) -> str:
    try:
        return normalize_match_date(str(value))
    except Exception:
        return str(value).strip()


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_") or "match"


def _rate(count: int, total: int) -> float:
    return round(float(count / total), 4) if total else 0.0


def _mean(rows: pd.DataFrame, column: str) -> float:
    return round(float(pd.to_numeric(rows.get(column, pd.Series(dtype=float)), errors="coerce").mean()), 4) if len(rows) else 0.0


def _count(rows: pd.DataFrame, column: str, value: str) -> int:
    return int(rows.get(column, pd.Series(dtype=str)).astype(str).eq(value).sum()) if len(rows) else 0


def _pct(value: object) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return ""


def _top(row: dict[str, object] | pd.Series, prefix: str) -> str:
    values = {
        "HOME": _num(row.get(f"{prefix}_adjusted_home_win_probability", 0)),
        "DRAW": _num(row.get(f"{prefix}_adjusted_draw_probability", 0)),
        "AWAY": _num(row.get(f"{prefix}_adjusted_away_probability", row.get(f"{prefix}_adjusted_away_probability", 0))),
    }
    if max(values.values()) <= 0:
        return ""
    return max(values.items(), key=lambda item: item[1])[0]


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition", default="Premier League")
    parser.add_argument("--season", default="2025/26")
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--team", default="")
    parser.add_argument("--from-date", default="")
    parser.add_argument("--to-date", default="")
    parser.add_argument("--include-results", action="store_true")
    parser.add_argument("--write-match-reports", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    fixtures, fixture_summary = load_pl_fixtures(
        args.competition,
        args.season,
        args.output_dir,
        source_profile=args.source_profile,
        enable_network=args.enable_network,
        cache_only=args.cache_only,
    )
    if args.team:
        team = args.team.casefold()
        fixtures = fixtures[fixtures["home_team"].astype(str).str.casefold().eq(team) | fixtures["away_team"].astype(str).str.casefold().eq(team)]
    if args.from_date:
        fixtures = fixtures[fixtures["match_date"].astype(str) >= args.from_date]
    if args.to_date:
        fixtures = fixtures[fixtures["match_date"].astype(str) <= args.to_date]
    if args.limit:
        fixtures = fixtures.head(args.limit)
    summary = run_full_season_analysis(
        fixtures,
        competition=args.competition,
        season=args.season,
        source_profile=args.source_profile,
        enable_network=args.enable_network,
        cache_only=args.cache_only,
        include_results=args.include_results,
        write_match_reports=args.write_match_reports,
        output_dir=args.output_dir,
    )
    summary.update({key: fixture_summary.get(key, summary.get(key)) for key in ["fixtures_found", "duplicate_count", "expected_fixture_count", "fixture_coverage_rate"]})
    for key in [
        "v2110_pl_full_season_analysis_status", "competition", "season", "expected_fixture_count",
        "fixtures_found", "fixtures_analyzed", "analysis_success_count", "analysis_warning_count",
        "analysis_failed_count", "probability_output_rate", "reports_written", "output_dir",
        "indicator_availability_status", "indicator_count", "most_available_indicator",
        "least_available_indicator", "highest_low_quality_indicator", "highest_adjustment_applied_indicator",
        "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled",
    ]:
        value = summary.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
