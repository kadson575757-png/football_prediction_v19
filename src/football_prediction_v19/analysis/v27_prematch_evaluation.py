# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from football_prediction_v19.analysis.v27_evaluation_metrics import compute_v27_metrics
from football_prediction_v19.analysis.v27_result_resolver import resolve_match_result
from scripts.run_match_winner_analysis import run_match_winner_analysis


OUTPUT_COLUMNS = [
    "competition", "season", "home_team", "away_team", "input_match_date", "resolved_match_date",
    "as_of_date", "fixture_resolver_status", "fixture_resolver_source", "asof_guard_status",
    "winner_analysis_status", "decision_class", "predicted_winner", "home_win_probability",
    "draw_probability", "away_win_probability", "confidence", "risk_level", "source_quality_band",
    "prediction_tier", "xg_available", "odds_available", "real_home_goals", "real_away_goals",
    "real_result", "result_status", "evaluation_result", "primary_reasons", "risk_notes",
    "base_home_win_probability", "base_draw_probability", "base_away_probability",
    "ppg_adjusted_home_win_probability", "ppg_adjusted_draw_probability", "ppg_adjusted_away_probability",
    "ppg_adjustment_applied", "ppg_adjustment_strength", "ppg_adjustment_reason",
    "home_home_ppg_before_match", "away_away_ppg_before_match", "home_away_ppg_diff",
    "ppg_indicator_quality",
    "last5_adjusted_home_win_probability", "last5_adjusted_draw_probability", "last5_adjusted_away_probability",
    "last5_adjustment_applied", "last5_adjustment_strength", "last5_adjustment_reason",
    "home_last5_points", "away_last5_points", "home_last5_points_per_match",
    "away_last5_points_per_match", "last5_points_diff", "last5_indicator_quality",
    "gd_adjusted_home_win_probability", "gd_adjusted_draw_probability", "gd_adjusted_away_probability",
    "gd_adjustment_applied", "gd_adjustment_strength", "gd_adjustment_reason",
    "home_matches_before_match", "away_matches_before_match",
    "home_goals_for_before_match", "home_goals_against_before_match",
    "away_goals_for_before_match", "away_goals_against_before_match",
    "home_goal_difference_before_match", "away_goal_difference_before_match",
    "goal_difference_diff", "goal_difference_indicator_quality",
    "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled",
]


def run_prematch_evaluation(
    input_csv: str | Path,
    source_profile: str = "config/v20_internet_sources.yaml",
    cache_only: bool = True,
    enable_network: bool = False,
    output_dir: str | Path = "outputs/v27_prematch_evaluation",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    input_frame = pd.read_csv(input_csv, keep_default_na=False)
    rows: list[dict[str, Any]] = []
    for idx, row in input_frame.iterrows():
        prediction = run_match_winner_analysis(
            competition=row.get("competition", ""),
            season=row.get("season", ""),
            home=row.get("home_team", ""),
            away=row.get("away_team", ""),
            match_date=row.get("match_date", ""),
            source_profile=source_profile,
            cache_only=cache_only,
            enable_network=enable_network,
            output_dir=out / f"match_{idx + 1}",
        )
        prediction_snapshot = dict(prediction)
        result = resolve_match_result(
            str(row.get("competition", "")),
            str(row.get("season", "")),
            str(row.get("home_team", "")),
            str(row.get("away_team", "")),
            str(prediction_snapshot.get("match_date") or prediction_snapshot.get("resolved_match_date") or row.get("match_date", "")),
            source_profile=source_profile,
            cache_only=cache_only,
            enable_network=enable_network,
        )
        rows.append(_evaluation_row(row, prediction_snapshot, result))
    rows_frame = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    metrics = compute_v27_metrics(rows_frame)
    status = _status(metrics)
    summary = {"v27_prematch_evaluation_status": status, **metrics}
    rows_path = out / "v27_prematch_evaluation_rows.csv"
    json_path = out / "v27_prematch_evaluation_summary.json"
    md_path = out / "v27_prematch_evaluation_report.md"
    rows_frame.to_csv(rows_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown_report(summary), encoding="utf-8")
    return {
        **summary,
        "v27_prematch_evaluation_rows_csv_path": str(rows_path.resolve()),
        "v27_prematch_evaluation_summary_json_path": str(json_path.resolve()),
        "v27_prematch_evaluation_report_md_path": str(md_path.resolve()),
    }


def _evaluation_row(input_row: pd.Series, prediction: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    real_result = str(result.get("result", "RESULT_UNKNOWN"))
    decision_class = str(prediction.get("decision_class", ""))
    predicted_winner = str(prediction.get("predicted_winner", ""))
    return {
        "competition": input_row.get("competition", ""),
        "season": input_row.get("season", ""),
        "home_team": input_row.get("home_team", ""),
        "away_team": input_row.get("away_team", ""),
        "input_match_date": input_row.get("match_date", ""),
        "resolved_match_date": prediction.get("resolved_match_date") or prediction.get("match_date", ""),
        "as_of_date": prediction.get("as_of_date", ""),
        "fixture_resolver_status": prediction.get("fixture_resolver_status", ""),
        "fixture_resolver_source": prediction.get("fixture_resolver_source", ""),
        "asof_guard_status": prediction.get("asof_guard_status", ""),
        "winner_analysis_status": prediction.get("winner_analysis_status", ""),
        "decision_class": decision_class,
        "predicted_winner": predicted_winner,
        "home_win_probability": prediction.get("home_win_probability", 0.0),
        "draw_probability": prediction.get("draw_probability", 0.0),
        "away_win_probability": prediction.get("away_win_probability", 0.0),
        "confidence": prediction.get("confidence", 0.0),
        "risk_level": prediction.get("risk_level", ""),
        "source_quality_band": prediction.get("source_quality_band", ""),
        "prediction_tier": prediction.get("prediction_tier", ""),
        "xg_available": prediction.get("xg_available", False),
        "odds_available": prediction.get("odds_available", False),
        "real_home_goals": result.get("home_goals", ""),
        "real_away_goals": result.get("away_goals", ""),
        "real_result": real_result,
        "result_status": result.get("result_status", ""),
        "evaluation_result": _evaluation_result(prediction, real_result, str(result.get("result_status", ""))),
        "primary_reasons": prediction.get("primary_reasons", []),
        "risk_notes": prediction.get("risk_notes", []),
        "base_home_win_probability": prediction.get("base_home_win_probability", prediction.get("home_win_probability", 0.0)),
        "base_draw_probability": prediction.get("base_draw_probability", prediction.get("draw_probability", 0.0)),
        "base_away_probability": prediction.get("base_away_probability", prediction.get("base_away_win_probability", prediction.get("away_win_probability", 0.0))),
        "ppg_adjusted_home_win_probability": prediction.get("ppg_adjusted_home_win_probability", prediction.get("adjusted_home_win_probability", prediction.get("home_win_probability", 0.0))),
        "ppg_adjusted_draw_probability": prediction.get("ppg_adjusted_draw_probability", prediction.get("adjusted_draw_probability", prediction.get("draw_probability", 0.0))),
        "ppg_adjusted_away_probability": prediction.get("ppg_adjusted_away_probability", prediction.get("adjusted_away_win_probability", prediction.get("away_win_probability", 0.0))),
        "ppg_adjustment_applied": prediction.get("ppg_adjustment_applied", False),
        "ppg_adjustment_strength": prediction.get("ppg_adjustment_strength", 0.0),
        "ppg_adjustment_reason": prediction.get("ppg_adjustment_reason", ""),
        "home_home_ppg_before_match": prediction.get("home_home_ppg_before_match", 0.0),
        "away_away_ppg_before_match": prediction.get("away_away_ppg_before_match", 0.0),
        "home_away_ppg_diff": prediction.get("home_away_ppg_diff", 0.0),
        "ppg_indicator_quality": prediction.get("ppg_indicator_quality", ""),
        "last5_adjusted_home_win_probability": prediction.get("last5_adjusted_home_win_probability", prediction.get("home_win_probability", 0.0)),
        "last5_adjusted_draw_probability": prediction.get("last5_adjusted_draw_probability", prediction.get("draw_probability", 0.0)),
        "last5_adjusted_away_probability": prediction.get("last5_adjusted_away_probability", prediction.get("away_win_probability", 0.0)),
        "last5_adjustment_applied": prediction.get("last5_adjustment_applied", False),
        "last5_adjustment_strength": prediction.get("last5_adjustment_strength", 0.0),
        "last5_adjustment_reason": prediction.get("last5_adjustment_reason", ""),
        "home_last5_points": prediction.get("home_last5_points", 0),
        "away_last5_points": prediction.get("away_last5_points", 0),
        "home_last5_points_per_match": prediction.get("home_last5_points_per_match", 0.0),
        "away_last5_points_per_match": prediction.get("away_last5_points_per_match", 0.0),
        "last5_points_diff": prediction.get("last5_points_diff", 0),
        "last5_indicator_quality": prediction.get("last5_indicator_quality", ""),
        "gd_adjusted_home_win_probability": prediction.get("gd_adjusted_home_win_probability", prediction.get("home_win_probability", 0.0)),
        "gd_adjusted_draw_probability": prediction.get("gd_adjusted_draw_probability", prediction.get("draw_probability", 0.0)),
        "gd_adjusted_away_probability": prediction.get("gd_adjusted_away_probability", prediction.get("away_win_probability", 0.0)),
        "gd_adjustment_applied": prediction.get("gd_adjustment_applied", False),
        "gd_adjustment_strength": prediction.get("gd_adjustment_strength", 0.0),
        "gd_adjustment_reason": prediction.get("gd_adjustment_reason", ""),
        "home_matches_before_match": prediction.get("home_matches_before_match", 0),
        "away_matches_before_match": prediction.get("away_matches_before_match", 0),
        "home_goals_for_before_match": prediction.get("home_goals_for_before_match", 0),
        "home_goals_against_before_match": prediction.get("home_goals_against_before_match", 0),
        "away_goals_for_before_match": prediction.get("away_goals_for_before_match", 0),
        "away_goals_against_before_match": prediction.get("away_goals_against_before_match", 0),
        "home_goal_difference_before_match": prediction.get("home_goal_difference_before_match", 0),
        "away_goal_difference_before_match": prediction.get("away_goal_difference_before_match", 0),
        "goal_difference_diff": prediction.get("goal_difference_diff", 0),
        "goal_difference_indicator_quality": prediction.get("goal_difference_indicator_quality", ""),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def _evaluation_result(prediction: dict[str, Any], real_result: str, result_status: str) -> str:
    if str(prediction.get("winner_analysis_status")) == "DATA_BLOCKED" or str(prediction.get("decision_class")) == "DATA_BLOCKED":
        return "DATA_BLOCKED"
    if result_status != "RESOLVED" or real_result == "RESULT_UNKNOWN":
        return "RESULT_UNKNOWN"
    decision_class = str(prediction.get("decision_class", ""))
    predicted = str(prediction.get("predicted_winner", ""))
    if decision_class not in {"WINNER_LEAN", "WINNER_PICK"} or predicted not in {"HOME", "AWAY"}:
        return "NO_DECISION"
    expected = "HOME_WIN" if predicted == "HOME" else "AWAY_WIN"
    return "HIT" if real_result == expected else "MISS"


def _status(metrics: dict[str, object]) -> str:
    if int(metrics.get("hit_count", 0)) + int(metrics.get("miss_count", 0)) > 0:
        if int(metrics.get("data_blocked_count", 0)) or int(metrics.get("result_unknown_count", 0)):
            return "PARTIAL"
        return "READY"
    return "DATA_BLOCKED"


def _markdown_report(summary: dict[str, object]) -> str:
    sections = [
        "# v2.7 Real Pre-Match Evaluation",
        "",
        "## Status",
        f"- v27_prematch_evaluation_status: {summary['v27_prematch_evaluation_status']}",
        f"- matches_requested: {summary['matches_requested']}",
        "",
        "## Decision Coverage",
        f"- decision_count: {summary['decision_count']}",
        f"- winner_pick_count: {summary['winner_pick_count']}",
        f"- winner_lean_count: {summary['winner_lean_count']}",
        "",
        "## Hit/Miss Summary",
        f"- hit_count: {summary['hit_count']}",
        f"- miss_count: {summary['miss_count']}",
        f"- hit_rate: {summary['hit_rate']}",
        "",
        "## No-Decision Summary",
        f"- no_decision_count: {summary['no_decision_count']}",
        f"- no_decision_rate: {summary['no_decision_rate']}",
        "",
        "## Data-Blocked Summary",
        f"- data_blocked_count: {summary['data_blocked_count']}",
        f"- data_blocked_rate: {summary['data_blocked_rate']}",
        "",
        "## Result-Unknown Summary",
        f"- result_unknown_count: {summary['result_unknown_count']}",
        f"- result_unknown_rate: {summary['result_unknown_rate']}",
        "",
        "## Results By Competition",
        json.dumps(summary.get("hit_rate_by_competition", {}), indent=2),
        "",
        "## Top Risk Notes",
        json.dumps(summary.get("top_risk_notes", {}), indent=2),
        "",
        "## Top Block Reasons",
        json.dumps(summary.get("top_block_reasons", {}), indent=2),
        "",
        "## Safety",
        "- automatic_betting_enabled: false",
        "- staking_logic_enabled: false",
        "- roi_logic_enabled: false",
        "- productive_betting_enabled: false",
        "",
        "No automatic bet, no stake, no ROI, no profit, no yield, no bankroll logic.",
        "",
    ]
    return "\n".join(sections)
