# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league  # noqa: E402
from scripts.analyze_v2112_exact_scoreline_pattern_test import (  # noqa: E402
    _last_team_match,
    _prepare_matches,
    _rate,
    _reference_hit,
    _safe_date,
    _score,
    _own_pattern_seen_count,
    load_fixture_results,
    team_scoreline_pattern,
)


DEFAULT_OUTPUT_DIR = "outputs/v2113_exact_scoreline_pattern_goal_bucket_test"
GOAL_BUCKETS = ["GOALS_0_1", "GOALS_2_3", "GOALS_4_PLUS"]
REFERENCE_SOURCES = ["exact_pair", "combined_single", "home_single", "away_single"]


def goal_bucket(total_goals: object) -> str:
    goals = _score(total_goals)
    if goals is None:
        return "UNKNOWN"
    if goals <= 1:
        return "GOALS_0_1"
    if goals <= 3:
        return "GOALS_2_3"
    return "GOALS_4_PLUS"


def total_goals(row: pd.Series | dict[str, object]) -> int | None:
    home = _score(row.get("actual_home_goals", row.get("home_goals", row.get("FTHG", ""))))
    away = _score(row.get("actual_away_goals", row.get("away_goals", row.get("FTAG", ""))))
    if home is None or away is None:
        return None
    return home + away


def analyze_exact_scoreline_goal_buckets(fixtures: pd.DataFrame, *, competition: str = "Premier League", season: str = "2025/26", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    matches = _prepare_matches(fixtures, competition, season)
    rows = [_analyze_target_match(matches, idx) for idx in matches.index]
    rows_frame = pd.DataFrame(rows)
    summary = compute_goal_bucket_summary(rows_frame, fixtures_loaded=len(matches), competition=competition, season=season, output_dir=out)
    ref_sources = reference_source_breakdown(rows_frame)
    distribution = goal_bucket_distribution(rows_frame)

    rows_path = out / "v2113_exact_scoreline_goal_bucket_rows.csv"
    summary_path = out / "v2113_exact_scoreline_goal_bucket_summary.json"
    report_path = out / "v2113_exact_scoreline_goal_bucket_report.md"
    ref_path = out / "v2113_exact_scoreline_goal_bucket_reference_sources.csv"
    distribution_path = out / "v2113_exact_scoreline_goal_bucket_distribution.csv"
    rows_frame.to_csv(rows_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    report_path.write_text(render_report(summary), encoding="utf-8")
    ref_sources.to_csv(ref_path, index=False)
    distribution.to_csv(distribution_path, index=False)
    return {
        **summary,
        "rows_csv_path": str(rows_path.resolve()),
        "summary_json_path": str(summary_path.resolve()),
        "report_md_path": str(report_path.resolve()),
        "reference_sources_csv_path": str(ref_path.resolve()),
        "distribution_csv_path": str(distribution_path.resolve()),
    }


def _analyze_target_match(matches: pd.DataFrame, idx: int) -> dict[str, object]:
    target = matches.loc[idx]
    prior = matches[matches["match_date"] < target["match_date"]]
    home_last = _last_team_match(prior, target["home_team"])
    away_last = _last_team_match(prior, target["away_team"])
    home_pattern = team_scoreline_pattern(home_last, target["home_team"]) if home_last is not None else {"pattern": ""}
    away_pattern = team_scoreline_pattern(away_last, target["away_team"]) if away_last is not None else {"pattern": ""}
    refs = find_goal_references(matches, idx, str(home_pattern["pattern"]), str(away_pattern["pattern"]))
    final = choose_final_goal_reference(refs)
    actual_total = total_goals(target)
    actual_bucket = goal_bucket(actual_total)
    row = {
        "competition": target["competition"],
        "season": target["season"],
        "match_date": target["match_date"],
        "home_team": target["home_team"],
        "away_team": target["away_team"],
        "actual_home_goals": target["actual_home_goals"],
        "actual_away_goals": target["actual_away_goals"],
        "actual_total_goals": "" if actual_total is None else actual_total,
        "actual_goal_bucket": actual_bucket,
        "home_last_match_date": "" if home_last is None else home_last["match_date"],
        "home_last_pattern": home_pattern["pattern"],
        "away_last_match_date": "" if away_last is None else away_last["match_date"],
        "away_last_pattern": away_pattern["pattern"],
        "home_own_pattern_seen_before": _own_pattern_seen_count(prior, target["home_team"], home_last, str(home_pattern["pattern"])) > 0,
        "away_own_pattern_seen_before": _own_pattern_seen_count(prior, target["away_team"], away_last, str(away_pattern["pattern"])) > 0,
        "final_goal_reference_source": final["source"],
        "final_goal_reference_count": final["goal_reference_count"],
        "final_reference_goals_0_1_rate": final["goals_0_1_rate"],
        "final_reference_goals_2_3_rate": final["goals_2_3_rate"],
        "final_reference_goals_4_plus_rate": final["goals_4_plus_rate"],
        "final_reference_top_goal_bucket": final["top_goal_bucket"],
        "final_reference_average_total_goals": final["average_total_goals"],
        "final_reference_median_total_goals": final["median_total_goals"],
        "final_reference_most_common_total_goals": final["most_common_total_goals"],
        "goal_bucket_hit": _goal_bucket_hit(final["top_goal_bucket"], actual_bucket),
        "exact_total_goals_hit": _exact_total_goals_hit(final["most_common_total_goals"], actual_total),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    for name, stats in refs.items():
        row.update(_prefixed_goal_stats(name, stats))
    return row


def find_goal_references(matches: pd.DataFrame, target_idx: int, home_pattern: str, away_pattern: str) -> dict[str, dict[str, object]]:
    target = matches.loc[target_idx]
    candidates = matches[matches["match_date"] < target["match_date"]]
    exact_indices: list[int] = []
    home_indices: list[int] = []
    away_indices: list[int] = []
    for idx, row in candidates.iterrows():
        cand_prior = matches[matches["match_date"] < row["match_date"]]
        cand_home_last = _last_team_match(cand_prior, row["home_team"])
        cand_away_last = _last_team_match(cand_prior, row["away_team"])
        cand_home_pattern = team_scoreline_pattern(cand_home_last, row["home_team"])["pattern"] if cand_home_last is not None else ""
        cand_away_pattern = team_scoreline_pattern(cand_away_last, row["away_team"])["pattern"] if cand_away_last is not None else ""
        home_hit = bool(home_pattern and cand_home_pattern == home_pattern)
        away_hit = bool(away_pattern and cand_away_pattern == away_pattern)
        if home_hit:
            home_indices.append(idx)
        if away_hit:
            away_indices.append(idx)
        if home_hit and away_hit:
            exact_indices.append(idx)
    combined = sorted(set(home_indices) | set(away_indices))
    return {
        "exact_pair": goal_reference_stats(matches.loc[exact_indices] if exact_indices else matches.iloc[0:0]),
        "combined_single": goal_reference_stats(matches.loc[combined] if combined else matches.iloc[0:0]),
        "home_single": goal_reference_stats(matches.loc[home_indices] if home_indices else matches.iloc[0:0]),
        "away_single": goal_reference_stats(matches.loc[away_indices] if away_indices else matches.iloc[0:0]),
    }


def goal_reference_stats(rows: pd.DataFrame) -> dict[str, object]:
    goals = [value for value in (total_goals(row) for _, row in rows.iterrows()) if value is not None]
    count = len(goals)
    if not count:
        return {
            "goal_reference_count": 0,
            "goals_0_1_count": 0,
            "goals_2_3_count": 0,
            "goals_4_plus_count": 0,
            "goals_0_1_rate": 0.0,
            "goals_2_3_rate": 0.0,
            "goals_4_plus_rate": 0.0,
            "top_goal_bucket": "NO_REFERENCE",
            "average_total_goals": 0.0,
            "median_total_goals": 0.0,
            "most_common_total_goals": "",
        }
    bucket_counts = {bucket: sum(goal_bucket(value) == bucket for value in goals) for bucket in GOAL_BUCKETS}
    rates = {bucket: _rate(bucket_counts[bucket], count) for bucket in GOAL_BUCKETS}
    top_bucket = _top_bucket(rates)
    value_counts = pd.Series(goals).value_counts()
    max_count = int(value_counts.max())
    most_common_values = sorted(int(value) for value, freq in value_counts.items() if int(freq) == max_count)
    most_common = most_common_values[0] if len(most_common_values) == 1 else ""
    return {
        "goal_reference_count": count,
        "goals_0_1_count": int(bucket_counts["GOALS_0_1"]),
        "goals_2_3_count": int(bucket_counts["GOALS_2_3"]),
        "goals_4_plus_count": int(bucket_counts["GOALS_4_PLUS"]),
        "goals_0_1_rate": rates["GOALS_0_1"],
        "goals_2_3_rate": rates["GOALS_2_3"],
        "goals_4_plus_rate": rates["GOALS_4_PLUS"],
        "top_goal_bucket": top_bucket,
        "average_total_goals": round(float(sum(goals) / count), 4),
        "median_total_goals": round(float(statistics.median(goals)), 4),
        "most_common_total_goals": most_common,
    }


def choose_final_goal_reference(refs: dict[str, dict[str, object]]) -> dict[str, object]:
    saw_unclear = False
    for source, label in [("exact_pair", "EXACT_PAIR"), ("combined_single", "COMBINED_SINGLE"), ("home_single", "HOME_SINGLE"), ("away_single", "AWAY_SINGLE")]:
        stats = refs[source]
        if int(stats["goal_reference_count"]) <= 0:
            continue
        if stats["top_goal_bucket"] in GOAL_BUCKETS:
            return {"source": label, **stats}
        saw_unclear = True
    empty = goal_reference_stats(pd.DataFrame())
    empty["top_goal_bucket"] = "NO_CLEAR_TOP" if saw_unclear else "NO_REFERENCE"
    return {"source": "NO_CLEAR_TOP" if saw_unclear else "NO_REFERENCE", **empty}


def compute_goal_bucket_summary(rows: pd.DataFrame, *, fixtures_loaded: int, competition: str, season: str, output_dir: Path) -> dict[str, object]:
    evaluatable = _bucket_evaluable(rows, "final_reference")
    exact_eval = _bucket_evaluable(rows, "exact_pair")
    combined_eval = _bucket_evaluable(rows, "combined_single")
    home_eval = _bucket_evaluable(rows, "home_single")
    away_eval = _bucket_evaluable(rows, "away_single")
    exact_total_eval = rows[rows["exact_total_goals_hit"].astype(str).str.lower().isin(["true", "false"])] if not rows.empty else pd.DataFrame()
    exact_total_hits = int(exact_total_eval["exact_total_goals_hit"].astype(str).str.lower().eq("true").sum()) if not exact_total_eval.empty else 0
    return {
        "v2113_exact_scoreline_goal_bucket_test_status": "READY",
        "competition": competition,
        "season": season,
        "fixtures_loaded": int(fixtures_loaded),
        "fixtures_analyzed": int(len(rows)),
        "goal_bucket_evaluable_count": int(len(evaluatable)),
        "goal_bucket_no_reference_count": int(rows["final_reference_top_goal_bucket"].astype(str).eq("NO_REFERENCE").sum()) if not rows.empty else 0,
        "goal_bucket_no_clear_top_count": int(rows["final_reference_top_goal_bucket"].astype(str).eq("NO_CLEAR_TOP").sum()) if not rows.empty else 0,
        "goal_bucket_hit_count": _hit_count(evaluatable, "goal_bucket_hit"),
        "goal_bucket_miss_count": int(len(evaluatable) - _hit_count(evaluatable, "goal_bucket_hit")),
        "goal_bucket_hit_rate": _hit_rate(evaluatable, "goal_bucket_hit"),
        "exact_pair_goal_bucket_evaluable_count": int(len(exact_eval)),
        "exact_pair_goal_bucket_hit_rate": _hit_rate(exact_eval, "exact_pair_goal_bucket_hit"),
        "combined_single_goal_bucket_evaluable_count": int(len(combined_eval)),
        "combined_single_goal_bucket_hit_rate": _hit_rate(combined_eval, "combined_single_goal_bucket_hit"),
        "home_single_goal_bucket_evaluable_count": int(len(home_eval)),
        "home_single_goal_bucket_hit_rate": _hit_rate(home_eval, "home_single_goal_bucket_hit"),
        "away_single_goal_bucket_evaluable_count": int(len(away_eval)),
        "away_single_goal_bucket_hit_rate": _hit_rate(away_eval, "away_single_goal_bucket_hit"),
        "predicted_goals_0_1_count": _pred_count(rows, "GOALS_0_1"),
        "predicted_goals_2_3_count": _pred_count(rows, "GOALS_2_3"),
        "predicted_goals_4_plus_count": _pred_count(rows, "GOALS_4_PLUS"),
        "actual_goals_0_1_count": _actual_count(rows, "GOALS_0_1"),
        "actual_goals_2_3_count": _actual_count(rows, "GOALS_2_3"),
        "actual_goals_4_plus_count": _actual_count(rows, "GOALS_4_PLUS"),
        "exact_total_goals_evaluable_count": int(len(exact_total_eval)),
        "exact_total_goals_hit_count": exact_total_hits,
        "exact_total_goals_hit_rate": _rate(exact_total_hits, len(exact_total_eval)),
        "output_dir": str(output_dir),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def reference_source_breakdown(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for source, group in rows.groupby("final_goal_reference_source", dropna=False) if not rows.empty else []:
        evaluatable = group[group["goal_bucket_hit"].astype(str).str.lower().isin(["true", "false"])]
        records.append({"final_goal_reference_source": source, "n": len(group), "evaluable": len(evaluatable), "hit_rate": _hit_rate(evaluatable, "goal_bucket_hit")})
    return pd.DataFrame(records)


def goal_bucket_distribution(rows: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{"bucket": bucket, "predicted_count": _pred_count(rows, bucket), "actual_count": _actual_count(rows, bucket)} for bucket in GOAL_BUCKETS])


def render_report(summary: dict[str, object]) -> str:
    return "\n".join([
        "# v2.11.3 Exact Scoreline Pattern Goal Bucket Test",
        "",
        f"- fixtures_loaded: {summary['fixtures_loaded']}",
        f"- fixtures_analyzed: {summary['fixtures_analyzed']}",
        f"- goal_bucket_hit_rate: {summary['goal_bucket_hit_rate']}",
        f"- exact_total_goals_hit_rate: {summary['exact_total_goals_hit_rate']}",
        "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _prefixed_goal_stats(prefix: str, stats: dict[str, object]) -> dict[str, object]:
    return {f"{prefix}_{key}": value for key, value in stats.items()}


def _top_bucket(rates: dict[str, float]) -> str:
    best = max(rates.values()) if rates else 0.0
    leaders = [bucket for bucket, rate in rates.items() if rate == best]
    if best <= 0:
        return "NO_REFERENCE"
    return leaders[0] if len(leaders) == 1 else "NO_CLEAR_TOP"


def _goal_bucket_hit(predicted: object, actual: object) -> object:
    if str(predicted) not in GOAL_BUCKETS or str(actual) not in GOAL_BUCKETS:
        return ""
    return str(predicted) == str(actual)


def _exact_total_goals_hit(predicted: object, actual_total: int | None) -> object:
    if predicted == "" or actual_total is None:
        return ""
    try:
        return int(predicted) == int(actual_total)
    except (TypeError, ValueError):
        return ""


def _bucket_evaluable(rows: pd.DataFrame, prefix: str) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame()
    if prefix == "final_reference":
        count_col = "final_goal_reference_count"
        top_col = "final_reference_top_goal_bucket"
        hit_col = "goal_bucket_hit"
    else:
        count_col = f"{prefix}_goal_reference_count"
        top_col = f"{prefix}_top_goal_bucket"
        hit_col = f"{prefix}_goal_bucket_hit"
        rows = rows.copy()
        rows[hit_col] = rows.apply(lambda row: _goal_bucket_hit(row.get(top_col, ""), row.get("actual_goal_bucket", "")), axis=1)
    if count_col not in rows.columns or top_col not in rows.columns:
        return pd.DataFrame()
    mask = pd.to_numeric(rows[count_col], errors="coerce").fillna(0).gt(0) & rows[top_col].astype(str).isin(GOAL_BUCKETS) & rows["actual_goal_bucket"].astype(str).isin(GOAL_BUCKETS)
    return rows[mask].copy()


def _hit_count(rows: pd.DataFrame, column: str) -> int:
    return int(rows[column].astype(str).str.lower().eq("true").sum()) if not rows.empty and column in rows.columns else 0


def _hit_rate(rows: pd.DataFrame, column: str) -> float:
    return _rate(_hit_count(rows, column), len(rows))


def _pred_count(rows: pd.DataFrame, bucket: str) -> int:
    return int(rows["final_reference_top_goal_bucket"].astype(str).eq(bucket).sum()) if not rows.empty and "final_reference_top_goal_bucket" in rows.columns else 0


def _actual_count(rows: pd.DataFrame, bucket: str) -> int:
    return int(rows["actual_goal_bucket"].astype(str).eq(bucket).sum()) if not rows.empty and "actual_goal_bucket" in rows.columns else 0


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
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    fixtures = load_fixture_results(args.competition, args.season, args.output_dir, source_profile=args.source_profile, enable_network=args.enable_network, cache_only=args.cache_only)
    fixtures = _prepare_matches(fixtures, args.competition, args.season)
    if args.team:
        team = normalize_team_or_league(args.team)
        fixtures = fixtures[(fixtures["home_team"].map(normalize_team_or_league).eq(team)) | (fixtures["away_team"].map(normalize_team_or_league).eq(team))]
    if args.from_date:
        fixtures = fixtures[fixtures["match_date"].map(_safe_date) >= args.from_date]
    if args.to_date:
        fixtures = fixtures[fixtures["match_date"].map(_safe_date) <= args.to_date]
    if args.limit:
        fixtures = fixtures.head(args.limit)
    result = analyze_exact_scoreline_goal_buckets(fixtures, competition=args.competition, season=args.season, output_dir=args.output_dir)
    for key in [
        "v2113_exact_scoreline_goal_bucket_test_status", "competition", "season", "fixtures_loaded", "fixtures_analyzed",
        "goal_bucket_evaluable_count", "goal_bucket_no_reference_count", "goal_bucket_no_clear_top_count",
        "goal_bucket_hit_count", "goal_bucket_miss_count", "goal_bucket_hit_rate",
        "exact_pair_goal_bucket_evaluable_count", "exact_pair_goal_bucket_hit_rate",
        "combined_single_goal_bucket_evaluable_count", "combined_single_goal_bucket_hit_rate",
        "home_single_goal_bucket_evaluable_count", "home_single_goal_bucket_hit_rate",
        "away_single_goal_bucket_evaluable_count", "away_single_goal_bucket_hit_rate",
        "predicted_goals_0_1_count", "predicted_goals_2_3_count", "predicted_goals_4_plus_count",
        "actual_goals_0_1_count", "actual_goals_2_3_count", "actual_goals_4_plus_count",
        "exact_total_goals_hit_rate", "output_dir", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
