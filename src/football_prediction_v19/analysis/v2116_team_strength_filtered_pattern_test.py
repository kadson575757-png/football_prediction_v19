# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from scripts.analyze_v2112_exact_scoreline_pattern_test import (
    _last_team_match,
    _prepare_matches,
    _rate,
    _safe_date,
    _score,
    actual_result,
    team_scoreline_pattern,
)
from scripts.analyze_v2113_exact_scoreline_pattern_goal_bucket_test import goal_bucket, total_goals

GOAL_BUCKETS = ["GOALS_0_1", "GOALS_2_3", "GOALS_4_PLUS"]
OUTCOMES = ["HOME", "DRAW", "AWAY"]
SOURCES = [("exact_pair", "EXACT_PAIR"), ("combined_single", "COMBINED_SINGLE"), ("home_single", "HOME_SINGLE"), ("away_single", "AWAY_SINGLE")]
STRATEGIES = [
    "BASELINE_UNFILTERED",
    "STRENGTH_HOME_AWAY",
    "STRENGTH_GAP_ONLY",
    "STRENGTH_HOME_AWAY_AND_GAP",
    "STRENGTH_LOOSE",
    "STRENGTH_STRICT",
    "STRENGTH_READY_ONLY",
    "STRENGTH_WITH_REF_6_10",
]


def compute_team_strength_before_match(prior: pd.DataFrame, team: str, *, min_strength_matches: int = 3) -> dict[str, object]:
    team_norm = normalize_team_or_league(team)
    rows = prior[
        prior["home_team"].map(normalize_team_or_league).eq(team_norm)
        | prior["away_team"].map(normalize_team_or_league).eq(team_norm)
    ]
    wins = draws = losses = goals_for = goals_against = points = 0
    for _, row in rows.iterrows():
        home = normalize_team_or_league(row.get("home_team", ""))
        gf_home = _score(row.get("actual_home_goals", ""))
        gf_away = _score(row.get("actual_away_goals", ""))
        if gf_home is None or gf_away is None:
            continue
        if home == team_norm:
            gf, ga = gf_home, gf_away
        else:
            gf, ga = gf_away, gf_home
        goals_for += gf
        goals_against += ga
        if gf > ga:
            wins += 1
            points += 3
        elif gf == ga:
            draws += 1
            points += 1
        else:
            losses += 1
    played = wins + draws + losses
    ppg = round(points / played, 4) if played else 0.0
    gd = goals_for - goals_against
    gd_per_match = round(gd / played, 4) if played else 0.0
    strength = round(ppg + gd_per_match * 0.35, 4)
    return {
        "matches_played_before_match": int(played),
        "points_before_match": int(points),
        "wins_before_match": int(wins),
        "draws_before_match": int(draws),
        "losses_before_match": int(losses),
        "goals_for_before_match": int(goals_for),
        "goals_against_before_match": int(goals_against),
        "goal_difference_before_match": int(gd),
        "ppg_before_match": ppg,
        "goal_difference_per_match_before_match": gd_per_match,
        "strength_score_before_match": strength,
        "strength_quality": "READY" if played >= min_strength_matches else "LOW",
    }


def strength_filter_mask(
    references: pd.DataFrame,
    target_strength: dict[str, object],
    strategy: str,
    *,
    home_strength_tolerance: float = 0.45,
    away_strength_tolerance: float = 0.45,
    gap_strength_tolerance: float = 0.55,
) -> pd.Series:
    if references.empty:
        return pd.Series(dtype=bool)
    if strategy == "BASELINE_UNFILTERED":
        return pd.Series(True, index=references.index)
    home_tol, away_tol, gap_tol = home_strength_tolerance, away_strength_tolerance, gap_strength_tolerance
    if strategy == "STRENGTH_LOOSE":
        home_tol, away_tol, gap_tol = 0.65, 0.65, 0.75
    if strategy == "STRENGTH_STRICT":
        home_tol, away_tol, gap_tol = 0.30, 0.30, 0.40
    home_ok = (references["reference_home_strength_score"].astype(float) - float(target_strength["home_strength_score"])).abs().le(home_tol)
    away_ok = (references["reference_away_strength_score"].astype(float) - float(target_strength["away_strength_score"])).abs().le(away_tol)
    gap_ok = (references["reference_strength_gap"].astype(float) - float(target_strength["strength_gap"])).abs().le(gap_tol)
    ready_ok = references["reference_strength_quality"].astype(str).eq("READY") & (str(target_strength.get("strength_quality", "")) == "READY")
    if strategy == "STRENGTH_HOME_AWAY":
        return home_ok & away_ok
    if strategy == "STRENGTH_GAP_ONLY":
        return gap_ok
    if strategy in {"STRENGTH_HOME_AWAY_AND_GAP", "STRENGTH_LOOSE", "STRENGTH_STRICT"}:
        return home_ok & away_ok & gap_ok
    if strategy == "STRENGTH_READY_ONLY":
        return ready_ok
    if strategy == "STRENGTH_WITH_REF_6_10":
        return home_ok & away_ok & gap_ok
    return pd.Series(True, index=references.index)


def analyze_team_strength_filtered_patterns(
    fixtures: pd.DataFrame,
    *,
    competition: str = "Premier League",
    season: str = "2025/26",
    output_dir: str | Path = "outputs/v2116_team_strength_filtered_pattern_test",
    home_strength_tolerance: float = 0.45,
    away_strength_tolerance: float = 0.45,
    gap_strength_tolerance: float = 0.55,
    min_strength_matches: int = 3,
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    matches = add_strength_snapshots(_prepare_matches(fixtures, competition, season), min_strength_matches=min_strength_matches)
    rows = []
    for idx in matches.index:
        for strategy in STRATEGIES:
            rows.append(analyze_match_strategy(
                matches,
                idx,
                strategy,
                home_strength_tolerance=home_strength_tolerance,
                away_strength_tolerance=away_strength_tolerance,
                gap_strength_tolerance=gap_strength_tolerance,
            ))
    rows_frame = pd.DataFrame(rows)
    strategy_summary = compute_strategy_summary(rows_frame)
    goal_summary = strategy_summary[[c for c in strategy_summary.columns if c.startswith("strategy_name") or c.startswith("goal_") or c.startswith("predicted_") or c.startswith("actual_") or c.endswith("_precision") or c.endswith("_recall") or c.endswith("_bias")]].copy()
    result_summary = strategy_summary[[c for c in strategy_summary.columns if c.startswith("strategy_name") or c.startswith("result_") or c in ["home_precision", "draw_precision", "away_precision", "home_recall", "draw_recall", "away_recall"]]].copy()
    summary = build_summary(strategy_summary, fixtures_loaded=len(matches), fixtures_analyzed=len(matches), competition=competition, season=season, output_dir=out)
    rows_frame.to_csv(out / "v2116_team_strength_filtered_rows.csv", index=False)
    strategy_summary.to_csv(out / "v2116_team_strength_strategy_summary.csv", index=False)
    goal_summary.to_csv(out / "v2116_team_strength_goal_bucket_summary.csv", index=False)
    result_summary.to_csv(out / "v2116_team_strength_result_direction_summary.csv", index=False)
    (out / "v2116_team_strength_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (out / "v2116_team_strength_report.md").write_text(render_report(summary, strategy_summary), encoding="utf-8")
    return {
        **summary,
        "rows_csv_path": str((out / "v2116_team_strength_filtered_rows.csv").resolve()),
        "strategy_summary_csv_path": str((out / "v2116_team_strength_strategy_summary.csv").resolve()),
        "summary_json_path": str((out / "v2116_team_strength_summary.json").resolve()),
        "report_md_path": str((out / "v2116_team_strength_report.md").resolve()),
    }


def add_strength_snapshots(matches: pd.DataFrame, *, min_strength_matches: int = 3) -> pd.DataFrame:
    rows = []
    for idx, row in matches.iterrows():
        prior = matches[matches["match_date"] < row["match_date"]]
        home = compute_team_strength_before_match(prior, str(row["home_team"]), min_strength_matches=min_strength_matches)
        away = compute_team_strength_before_match(prior, str(row["away_team"]), min_strength_matches=min_strength_matches)
        home_last = _last_team_match(prior, row["home_team"])
        away_last = _last_team_match(prior, row["away_team"])
        home_pattern = team_scoreline_pattern(home_last, row["home_team"]) if home_last is not None else {"pattern": ""}
        away_pattern = team_scoreline_pattern(away_last, row["away_team"]) if away_last is not None else {"pattern": ""}
        item = row.to_dict()
        for prefix, stats in [("home", home), ("away", away)]:
            for key, value in stats.items():
                item[f"{prefix}_{key}"] = value
        item["strength_gap_before_match"] = round(float(home["strength_score_before_match"]) - float(away["strength_score_before_match"]), 4)
        item["strength_quality"] = "READY" if home["strength_quality"] == "READY" and away["strength_quality"] == "READY" else "LOW"
        item["home_last_match_date"] = "" if home_last is None else home_last["match_date"]
        item["home_last_pattern"] = home_pattern["pattern"]
        item["away_last_match_date"] = "" if away_last is None else away_last["match_date"]
        item["away_last_pattern"] = away_pattern["pattern"]
        rows.append(item)
    return pd.DataFrame(rows).reset_index(drop=True)


def analyze_match_strategy(matches: pd.DataFrame, idx: int, strategy: str, *, home_strength_tolerance: float = 0.45, away_strength_tolerance: float = 0.45, gap_strength_tolerance: float = 0.55) -> dict[str, object]:
    target = matches.loc[idx]
    home_pattern = {"pattern": target.get("home_last_pattern", "")}
    away_pattern = {"pattern": target.get("away_last_pattern", "")}
    raw_refs = find_pattern_reference_rows(matches, idx, str(home_pattern["pattern"]), str(away_pattern["pattern"]))
    target_strength = {
        "home_strength_score": target["home_strength_score_before_match"],
        "away_strength_score": target["away_strength_score_before_match"],
        "strength_gap": target["strength_gap_before_match"],
        "strength_quality": target["strength_quality"],
    }
    filtered_refs = {}
    for source, frame in raw_refs.items():
        enriched = reference_strength_frame(frame)
        mask = strength_filter_mask(enriched, target_strength, strategy, home_strength_tolerance=home_strength_tolerance, away_strength_tolerance=away_strength_tolerance, gap_strength_tolerance=gap_strength_tolerance)
        filtered = enriched[mask].copy() if not enriched.empty else enriched
        filtered_refs[source] = filtered
    if strategy == "BASELINE_UNFILTERED":
        filtered_refs = raw_refs
    final = choose_final_filtered_reference(filtered_refs)
    actual_total = total_goals(target)
    actual_bucket = goal_bucket(actual_total)
    actual_outcome = actual_result(target["actual_home_goals"], target["actual_away_goals"])
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
        "actual_result_outcome": actual_outcome,
        "home_last_match_date": target.get("home_last_match_date", ""),
        "home_last_pattern": home_pattern["pattern"],
        "away_last_match_date": target.get("away_last_match_date", ""),
        "away_last_pattern": away_pattern["pattern"],
        "target_home_matches_played_before_match": target["home_matches_played_before_match"],
        "target_away_matches_played_before_match": target["away_matches_played_before_match"],
        "target_home_strength_score": target["home_strength_score_before_match"],
        "target_away_strength_score": target["away_strength_score_before_match"],
        "target_strength_gap": target["strength_gap_before_match"],
        "target_strength_quality": target["strength_quality"],
        "strategy_name": strategy,
        "final_reference_source": final["source"],
        "final_reference_count": final["reference_count"],
        "final_reference_top_goal_bucket": final["top_goal_bucket"],
        "final_reference_goals_0_1_rate": final["goals_0_1_rate"],
        "final_reference_goals_2_3_rate": final["goals_2_3_rate"],
        "final_reference_goals_4_plus_rate": final["goals_4_plus_rate"],
        "goal_bucket_hit": _hit(final["top_goal_bucket"], actual_bucket, GOAL_BUCKETS),
        "final_reference_top_result_outcome": final["top_result_outcome"],
        "final_reference_home_win_rate": final["home_win_rate"],
        "final_reference_draw_rate": final["draw_rate"],
        "final_reference_away_win_rate": final["away_win_rate"],
        "result_hit": _hit(final["top_result_outcome"], actual_outcome, OUTCOMES),
    }
    if strategy == "STRENGTH_WITH_REF_6_10" and not (6 <= int(row["final_reference_count"]) <= 10):
        row.update(_empty_prediction("NO_CLEAR_TOP" if int(row["final_reference_count"]) > 0 else "NO_REFERENCE"))
    return row


def find_pattern_reference_rows(matches: pd.DataFrame, target_idx: int, home_pattern: str, away_pattern: str) -> dict[str, pd.DataFrame]:
    target = matches.loc[target_idx]
    candidates = matches[matches["match_date"] < target["match_date"]]
    home_mask = candidates["home_last_pattern"].astype(str).eq(home_pattern) if home_pattern and "home_last_pattern" in candidates.columns else pd.Series(False, index=candidates.index)
    away_mask = candidates["away_last_pattern"].astype(str).eq(away_pattern) if away_pattern and "away_last_pattern" in candidates.columns else pd.Series(False, index=candidates.index)
    exact_indices = candidates[home_mask & away_mask].index.tolist()
    home_indices = candidates[home_mask].index.tolist()
    away_indices = candidates[away_mask].index.tolist()
    combined = sorted(set(home_indices) | set(away_indices))
    empty = matches.iloc[0:0]
    return {
        "exact_pair": matches.loc[exact_indices] if exact_indices else empty,
        "combined_single": matches.loc[combined] if combined else empty,
        "home_single": matches.loc[home_indices] if home_indices else empty,
        "away_single": matches.loc[away_indices] if away_indices else empty,
    }


def reference_strength_frame(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows.copy()
    frame = rows.copy()
    frame["reference_home_strength_score"] = frame["home_strength_score_before_match"]
    frame["reference_away_strength_score"] = frame["away_strength_score_before_match"]
    frame["reference_strength_gap"] = frame["strength_gap_before_match"]
    frame["reference_strength_quality"] = frame["strength_quality"]
    return frame


def choose_final_filtered_reference(refs: dict[str, pd.DataFrame]) -> dict[str, object]:
    saw_unclear = False
    for key, label in SOURCES:
        stats = filtered_reference_stats(refs.get(key, pd.DataFrame()))
        if stats["reference_count"] <= 0:
            continue
        if stats["top_goal_bucket"] in GOAL_BUCKETS:
            return {"source": label, **stats}
        saw_unclear = True
    empty = filtered_reference_stats(pd.DataFrame())
    status = "NO_CLEAR_TOP" if saw_unclear else "NO_REFERENCE"
    empty["top_goal_bucket"] = status
    empty["top_result_outcome"] = status
    return {"source": status, **empty}


def filtered_reference_stats(rows: pd.DataFrame) -> dict[str, object]:
    if rows.empty:
        return _stats_empty("NO_REFERENCE")
    totals = [total_goals(row) for _, row in rows.iterrows()]
    goals = [value for value in totals if value is not None]
    outcomes = [actual_result(row["actual_home_goals"], row["actual_away_goals"]) for _, row in rows.iterrows()]
    count = len(rows)
    bucket_rates = {bucket: _rate(sum(goal_bucket(value) == bucket for value in goals), len(goals)) for bucket in GOAL_BUCKETS} if goals else {bucket: 0.0 for bucket in GOAL_BUCKETS}
    outcome_rates = {outcome: _rate(outcomes.count(outcome), len(outcomes)) for outcome in OUTCOMES} if outcomes else {outcome: 0.0 for outcome in OUTCOMES}
    return {
        "reference_count": int(count),
        "goals_0_1_rate": bucket_rates["GOALS_0_1"],
        "goals_2_3_rate": bucket_rates["GOALS_2_3"],
        "goals_4_plus_rate": bucket_rates["GOALS_4_PLUS"],
        "top_goal_bucket": _top(bucket_rates, "NO_CLEAR_TOP"),
        "home_win_rate": outcome_rates["HOME"],
        "draw_rate": outcome_rates["DRAW"],
        "away_win_rate": outcome_rates["AWAY"],
        "top_result_outcome": _top(outcome_rates, "NO_CLEAR_TOP"),
    }


def compute_strategy_summary(rows: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([_strategy_metrics(strategy, group) for strategy, group in rows.groupby("strategy_name", sort=False)])


def build_summary(strategy_summary: pd.DataFrame, *, fixtures_loaded: int, fixtures_analyzed: int, competition: str, season: str, output_dir: Path) -> dict[str, object]:
    baseline = _summary_row(strategy_summary, "BASELINE_UNFILTERED")
    best_goal = _best(strategy_summary, "goal_bucket_hit_rate", "goal_bucket_evaluable_count")
    best_result = _best(strategy_summary, "result_hit_rate", "result_evaluable_count")
    baseline_goal = float(baseline.get("goal_bucket_hit_rate", 0.0))
    baseline_result = float(baseline.get("result_hit_rate", 0.0))
    best_goal_rate = float(best_goal.get("goal_bucket_hit_rate", 0.0))
    best_result_rate = float(best_result.get("result_hit_rate", 0.0))
    best_ref = int(best_goal.get("goal_bucket_evaluable_count", 0))
    recommendation = _recommendation(best_goal_rate - baseline_goal, best_ref, int(fixtures_analyzed))
    return {
        "v2116_team_strength_filtered_pattern_test_status": "READY",
        "competition": competition,
        "season": season,
        "fixtures_loaded": int(fixtures_loaded),
        "fixtures_analyzed": int(fixtures_analyzed),
        "baseline_goal_bucket_hit_rate": baseline_goal,
        "best_goal_bucket_strategy": best_goal.get("strategy_name", ""),
        "best_goal_bucket_evaluable_count": int(best_goal.get("goal_bucket_evaluable_count", 0)),
        "best_goal_bucket_hit_rate": best_goal_rate,
        "best_goal_bucket_delta_vs_baseline": round(best_goal_rate - baseline_goal, 4),
        "baseline_result_hit_rate": baseline_result,
        "best_result_strategy": best_result.get("strategy_name", ""),
        "best_result_evaluable_count": int(best_result.get("result_evaluable_count", 0)),
        "best_result_hit_rate": best_result_rate,
        "best_result_delta_vs_baseline": round(best_result_rate - baseline_result, 4),
        "best_strategy_reference_count": best_ref,
        "best_strategy_goals_2_3_bias": int(best_goal.get("goals_2_3_prediction_bias", 0)),
        "recommendation": recommendation,
        "output_dir": str(output_dir),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def render_report(summary: dict[str, object], strategy_summary: pd.DataFrame) -> str:
    return "\n".join([
        "# v2.11.6 Team Strength Filtered Pattern Reference Test",
        "",
        "Diagnostic-only test. Pattern references are found first; team strength is applied only as a post-filter.",
        "",
        f"- fixtures_loaded: {summary['fixtures_loaded']}",
        f"- fixtures_analyzed: {summary['fixtures_analyzed']}",
        f"- baseline_goal_bucket_hit_rate: {summary['baseline_goal_bucket_hit_rate']}",
        f"- best_goal_bucket_strategy: {summary['best_goal_bucket_strategy']}",
        f"- best_goal_bucket_hit_rate: {summary['best_goal_bucket_hit_rate']}",
        f"- baseline_result_hit_rate: {summary['baseline_result_hit_rate']}",
        f"- best_result_strategy: {summary['best_result_strategy']}",
        f"- best_result_hit_rate: {summary['best_result_hit_rate']}",
        f"- recommendation: {summary['recommendation']}",
        "",
        _markdown_table(strategy_summary),
        "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _strategy_metrics(strategy: str, group: pd.DataFrame) -> dict[str, object]:
    goal_eval = group[group["goal_bucket_hit"].astype(str).str.lower().isin(["true", "false"])]
    result_eval = group[group["result_hit"].astype(str).str.lower().isin(["true", "false"])]
    record = {
        "strategy_name": strategy,
        "goal_bucket_evaluable_count": len(goal_eval),
        "goal_bucket_no_reference_count": int(group["final_reference_top_goal_bucket"].astype(str).eq("NO_REFERENCE").sum()),
        "goal_bucket_no_clear_top_count": int(group["final_reference_top_goal_bucket"].astype(str).eq("NO_CLEAR_TOP").sum()),
        "goal_bucket_hit_count": _bool_hits(goal_eval, "goal_bucket_hit"),
        "goal_bucket_miss_count": len(goal_eval) - _bool_hits(goal_eval, "goal_bucket_hit"),
        "goal_bucket_hit_rate": _rate(_bool_hits(goal_eval, "goal_bucket_hit"), len(goal_eval)),
        "result_evaluable_count": len(result_eval),
        "result_no_reference_count": int(group["final_reference_top_result_outcome"].astype(str).eq("NO_REFERENCE").sum()),
        "result_no_clear_top_count": int(group["final_reference_top_result_outcome"].astype(str).eq("NO_CLEAR_TOP").sum()),
        "result_hit_count": _bool_hits(result_eval, "result_hit"),
        "result_miss_count": len(result_eval) - _bool_hits(result_eval, "result_hit"),
        "result_hit_rate": _rate(_bool_hits(result_eval, "result_hit"), len(result_eval)),
    }
    record.update(_bucket_metrics(goal_eval))
    record.update(_result_metrics(result_eval))
    return record


def _bucket_metrics(rows: pd.DataFrame) -> dict[str, object]:
    record: dict[str, object] = {}
    for bucket in GOAL_BUCKETS:
        suffix = _bucket_suffix(bucket)
        pred = rows["final_reference_top_goal_bucket"].astype(str).eq(bucket) if not rows.empty else pd.Series(dtype=bool)
        actual = rows["actual_goal_bucket"].astype(str).eq(bucket) if not rows.empty else pd.Series(dtype=bool)
        tp = int((pred & actual).sum()) if not rows.empty else 0
        record[f"predicted_{suffix}_count"] = int(pred.sum()) if not rows.empty else 0
        record[f"actual_{suffix}_count"] = int(actual.sum()) if not rows.empty else 0
        record[f"{suffix}_precision"] = _rate(tp, int(pred.sum()) if not rows.empty else 0)
        record[f"{suffix}_recall"] = _rate(tp, int(actual.sum()) if not rows.empty else 0)
    record["goals_2_3_prediction_bias"] = record["predicted_goals_2_3_count"] - record["actual_goals_2_3_count"]
    return record


def _result_metrics(rows: pd.DataFrame) -> dict[str, object]:
    record: dict[str, object] = {}
    for outcome in OUTCOMES:
        label = "home" if outcome == "HOME" else outcome.lower()
        pred = rows["final_reference_top_result_outcome"].astype(str).eq(outcome) if not rows.empty else pd.Series(dtype=bool)
        actual = rows["actual_result_outcome"].astype(str).eq(outcome) if not rows.empty else pd.Series(dtype=bool)
        tp = int((pred & actual).sum()) if not rows.empty else 0
        record[f"{label}_precision"] = _rate(tp, int(pred.sum()) if not rows.empty else 0)
        record[f"{label}_recall"] = _rate(tp, int(actual.sum()) if not rows.empty else 0)
    return record


def _empty_prediction(status: str) -> dict[str, object]:
    return {
        "final_reference_source": status,
        "final_reference_count": 0,
        "final_reference_top_goal_bucket": status,
        "final_reference_goals_0_1_rate": 0.0,
        "final_reference_goals_2_3_rate": 0.0,
        "final_reference_goals_4_plus_rate": 0.0,
        "goal_bucket_hit": "",
        "final_reference_top_result_outcome": status,
        "final_reference_home_win_rate": 0.0,
        "final_reference_draw_rate": 0.0,
        "final_reference_away_win_rate": 0.0,
        "result_hit": "",
    }


def _stats_empty(status: str) -> dict[str, object]:
    return {
        "reference_count": 0,
        "goals_0_1_rate": 0.0,
        "goals_2_3_rate": 0.0,
        "goals_4_plus_rate": 0.0,
        "top_goal_bucket": status,
        "home_win_rate": 0.0,
        "draw_rate": 0.0,
        "away_win_rate": 0.0,
        "top_result_outcome": status,
    }


def _top(rates: dict[str, float], tie_label: str) -> str:
    best = max(rates.values()) if rates else 0.0
    if best <= 0:
        return "NO_REFERENCE"
    leaders = [key for key, value in rates.items() if value == best]
    return leaders[0] if len(leaders) == 1 else tie_label


def _hit(predicted: object, actual: object, valid: Iterable[str]) -> object:
    valid_set = set(valid)
    return str(predicted) == str(actual) if str(predicted) in valid_set and str(actual) in valid_set else ""


def _bool_hits(rows: pd.DataFrame, column: str) -> int:
    return int(rows[column].astype(str).str.lower().eq("true").sum()) if not rows.empty and column in rows.columns else 0


def _summary_row(frame: pd.DataFrame, strategy: str) -> dict[str, object]:
    rows = frame[frame["strategy_name"].astype(str).eq(strategy)] if not frame.empty else pd.DataFrame()
    return rows.iloc[0].to_dict() if not rows.empty else {}


def _best(frame: pd.DataFrame, rate_col: str, count_col: str) -> dict[str, object]:
    if frame.empty:
        return {}
    ranked = frame.sort_values([rate_col, count_col, "strategy_name"], ascending=[False, False, True])
    return ranked.iloc[0].to_dict()


def _recommendation(delta: float, coverage: int, total: int) -> str:
    if delta <= 0.0:
        return "TEAM_STRENGTH_FILTER_NOT_HELPFUL"
    if delta >= 0.03 and coverage >= max(30, int(total * 0.25)):
        return "TEAM_STRENGTH_FILTER_PROMISING"
    if delta >= 0.03 and coverage > 0:
        return "TEAM_STRENGTH_FILTER_PROMISING_LOW_COVERAGE"
    return "KEEP_AS_DIAGNOSTIC_ONLY"


def _bucket_suffix(bucket: str) -> str:
    return {"GOALS_0_1": "goals_0_1", "GOALS_2_3": "goals_2_3", "GOALS_4_PLUS": "goals_4_plus"}[bucket]


def _markdown_table(frame: pd.DataFrame) -> str:
    cols = ["strategy_name", "goal_bucket_evaluable_count", "goal_bucket_hit_rate", "result_evaluable_count", "result_hit_rate", "goals_2_3_prediction_bias"]
    if frame.empty:
        return ""
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame[cols].iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)
