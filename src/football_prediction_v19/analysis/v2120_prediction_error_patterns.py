# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

OUTCOMES = ("HOME", "DRAW", "AWAY")
EDGE_BUCKETS = (
    "EDGE_0_03", "EDGE_0_05", "EDGE_0_08", "EDGE_0_10", "EDGE_0_15", "EDGE_GT_15",
)
TOP_PROBABILITY_BUCKETS = (
    "TOP_PROB_LT_035", "TOP_PROB_035_040", "TOP_PROB_040_045",
    "TOP_PROB_045_050", "TOP_PROB_GT_050",
)
FAVORITE_GAP_BUCKETS = (
    "BALANCED", "SMALL_FAVORITE_GAP", "MEDIUM_FAVORITE_GAP", "LARGE_FAVORITE_GAP",
)
ERROR_TYPES = (
    "HIT", "HOME_TOP_ACTUAL_DRAW", "HOME_TOP_ACTUAL_AWAY",
    "AWAY_TOP_ACTUAL_DRAW", "AWAY_TOP_ACTUAL_HOME",
    "DRAW_TOP_ACTUAL_HOME", "DRAW_TOP_ACTUAL_AWAY", "UNKNOWN",
)
SAFETY_FLAGS = {
    "automatic_betting_enabled": False,
    "staking_logic_enabled": False,
    "roi_logic_enabled": False,
}


def classify_error_type(top_outcome: object, actual_result: object) -> str:
    predicted = _outcome(top_outcome)
    actual = _outcome(actual_result)
    if predicted not in OUTCOMES or actual not in OUTCOMES:
        return "UNKNOWN"
    if predicted == actual:
        return "HIT"
    value = f"{predicted}_TOP_ACTUAL_{actual}"
    return value if value in ERROR_TYPES else "UNKNOWN"


def prediction_error_type(top_outcome: object, actual_result: object) -> str:
    """Compatibility alias for callers that prefer a descriptive function name."""
    return classify_error_type(top_outcome, actual_result)


def edge_bucket(value: object) -> str:
    edge = _number(value)
    if pd.isna(edge) or edge < 0:
        return "UNKNOWN"
    if edge <= 0.03:
        return "EDGE_0_03"
    if edge <= 0.05:
        return "EDGE_0_05"
    if edge <= 0.08:
        return "EDGE_0_08"
    if edge <= 0.10:
        return "EDGE_0_10"
    if edge <= 0.15:
        return "EDGE_0_15"
    return "EDGE_GT_15"


def probability_edge_bucket(value: object) -> str:
    return edge_bucket(value)


def top_probability_bucket(value: object) -> str:
    probability = _number(value)
    if pd.isna(probability):
        return "UNKNOWN"
    if probability < 0.35:
        return "TOP_PROB_LT_035"
    if probability < 0.40:
        return "TOP_PROB_035_040"
    if probability < 0.45:
        return "TOP_PROB_040_045"
    if probability <= 0.50:
        return "TOP_PROB_045_050"
    return "TOP_PROB_GT_050"


def favorite_side(home_probability: object, away_probability: object) -> str:
    home = _number(home_probability)
    away = _number(away_probability)
    if pd.isna(home) or pd.isna(away):
        return "UNKNOWN"
    if abs(home - away) <= 0.03 + 1e-12:
        return "BALANCED"
    return "HOME" if home > away else "AWAY"


def favorite_gap_bucket(home_probability: object, away_probability: object) -> str:
    home = _number(home_probability)
    away = _number(away_probability)
    if pd.isna(home) or pd.isna(away):
        return "UNKNOWN"
    gap = abs(home - away)
    if gap <= 0.03 + 1e-12:
        return "BALANCED"
    if gap <= 0.05 + 1e-12:
        return "SMALL_FAVORITE_GAP"
    if gap <= 0.10 + 1e-12:
        return "MEDIUM_FAVORITE_GAP"
    return "LARGE_FAVORITE_GAP"


def prepare_prediction_rows(rows: pd.DataFrame) -> pd.DataFrame:
    source = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    prepared = pd.DataFrame(index=source.index)
    aliases = {
        "match_date": ("match_date", "Date", "date"),
        "home_team": ("home_team", "HomeTeam", "home"),
        "away_team": ("away_team", "AwayTeam", "away"),
        "actual_result": ("actual_result", "actual_result_outcome", "FTR"),
        "top_probability_outcome": ("top_probability_outcome", "top_outcome"),
        "home_win_probability": ("home_win_probability", "home_probability"),
        "draw_probability": ("draw_probability",),
        "away_win_probability": ("away_win_probability", "away_probability"),
        "probability_edge": ("probability_edge",),
        "probability_edge_band": ("probability_edge_band",),
        "uncertainty_level": ("uncertainty_level",),
        "data_quality_band": ("data_quality_band", "source_quality_band"),
    }
    for target, candidates in aliases.items():
        selected = next((name for name in candidates if name in source.columns), None)
        prepared[target] = source[selected] if selected else ""
    numeric = ("home_win_probability", "draw_probability", "away_win_probability", "probability_edge")
    for column in numeric:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    for column in ("actual_result", "top_probability_outcome"):
        prepared[column] = prepared[column].map(_outcome)
    probability_columns = ["home_win_probability", "draw_probability", "away_win_probability"]
    prepared["top_probability"] = prepared[probability_columns].max(axis=1, skipna=True)
    prepared.loc[prepared[probability_columns].isna().all(axis=1), "top_probability"] = float("nan")
    prepared["evaluable"] = (
        prepared["actual_result"].isin(OUTCOMES)
        & prepared["top_probability_outcome"].isin(OUTCOMES)
    )
    prepared["prediction_hit"] = (
        prepared["evaluable"]
        & prepared["top_probability_outcome"].eq(prepared["actual_result"])
    )
    prepared["error_type"] = [
        classify_error_type(predicted, actual)
        for predicted, actual in zip(prepared["top_probability_outcome"], prepared["actual_result"])
    ]
    prepared["edge_bucket"] = prepared["probability_edge"].map(edge_bucket)
    prepared["top_probability_bucket"] = prepared["top_probability"].map(top_probability_bucket)
    prepared["favorite_side"] = [
        favorite_side(home, away)
        for home, away in zip(prepared["home_win_probability"], prepared["away_win_probability"])
    ]
    prepared["favorite_gap"] = (prepared["home_win_probability"] - prepared["away_win_probability"]).abs()
    prepared["favorite_gap_bucket"] = [
        favorite_gap_bucket(home, away)
        for home, away in zip(prepared["home_win_probability"], prepared["away_win_probability"])
    ]
    return prepared.reset_index(drop=True)


def compute_error_type_summary(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    total = len(rows)
    for name in ERROR_TYPES:
        count = int(rows["error_type"].eq(name).sum()) if not rows.empty else 0
        if count:
            records.append({"error_type": name, "count": count, "rate": _rate(count, total)})
    return pd.DataFrame(records, columns=["error_type", "count", "rate"])


def compute_edge_band_error_summary(rows: pd.DataFrame) -> pd.DataFrame:
    return _bucket_summary(rows, "edge_bucket", EDGE_BUCKETS)


def compute_top_probability_bucket_summary(rows: pd.DataFrame) -> pd.DataFrame:
    return _bucket_summary(rows, "top_probability_bucket", TOP_PROBABILITY_BUCKETS)


def compute_home_away_bias_summary(rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "top_probability_outcome", "count", "hit_rate", "actual_home_count",
        "actual_draw_count", "actual_away_count", "home_overprediction_count",
        "away_overprediction_count", "draw_underprediction_count",
    ]
    records = []
    draw_underprediction = int(
        (rows["actual_result"].eq("DRAW") & ~rows["top_probability_outcome"].eq("DRAW")).sum()
    ) if not rows.empty else 0
    for outcome in OUTCOMES:
        group = rows[rows["top_probability_outcome"].eq(outcome)]
        records.append({
            "top_probability_outcome": outcome,
            "count": int(len(group)),
            "hit_rate": _rate(int(group["prediction_hit"].sum()), len(group)),
            "actual_home_count": int(group["actual_result"].eq("HOME").sum()),
            "actual_draw_count": int(group["actual_result"].eq("DRAW").sum()),
            "actual_away_count": int(group["actual_result"].eq("AWAY").sum()),
            "home_overprediction_count": int((group["actual_result"] != "HOME").sum()) if outcome == "HOME" else 0,
            "away_overprediction_count": int((group["actual_result"] != "AWAY").sum()) if outcome == "AWAY" else 0,
            "draw_underprediction_count": draw_underprediction if outcome == "DRAW" else 0,
        })
    return pd.DataFrame(records, columns=columns)


def compute_team_error_summary(rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "team", "home_matches_count", "home_prediction_top_count", "home_prediction_hit_rate",
        "actual_home_win_rate", "model_home_top_rate", "home_overprediction_delta",
        "away_matches_count", "away_prediction_top_count", "away_prediction_hit_rate",
        "actual_away_win_rate", "model_away_top_rate", "away_overprediction_delta",
        "team_matches_count", "team_involved_hit_rate", "team_involved_miss_count",
        "most_common_error_type",
    ]
    teams = sorted(set(rows["home_team"].dropna().astype(str)) | set(rows["away_team"].dropna().astype(str)))
    teams = [team for team in teams if team.strip()]
    records = []
    for team in teams:
        home_rows = rows[rows["home_team"].astype(str).eq(team)]
        away_rows = rows[rows["away_team"].astype(str).eq(team)]
        involved = pd.concat([home_rows, away_rows], ignore_index=True)
        home_count, away_count = len(home_rows), len(away_rows)
        home_top = int(home_rows["top_probability_outcome"].eq("HOME").sum())
        away_top = int(away_rows["top_probability_outcome"].eq("AWAY").sum())
        home_actual = int(home_rows["actual_result"].eq("HOME").sum())
        away_actual = int(away_rows["actual_result"].eq("AWAY").sum())
        errors = involved.loc[~involved["prediction_hit"], "error_type"].tolist()
        records.append({
            "team": team,
            "home_matches_count": int(home_count),
            "home_prediction_top_count": home_top,
            "home_prediction_hit_rate": _rate(int(home_rows["prediction_hit"].sum()), home_count),
            "actual_home_win_rate": _rate(home_actual, home_count),
            "model_home_top_rate": _rate(home_top, home_count),
            "home_overprediction_delta": round(_rate(home_top, home_count) - _rate(home_actual, home_count), 4),
            "away_matches_count": int(away_count),
            "away_prediction_top_count": away_top,
            "away_prediction_hit_rate": _rate(int(away_rows["prediction_hit"].sum()), away_count),
            "actual_away_win_rate": _rate(away_actual, away_count),
            "model_away_top_rate": _rate(away_top, away_count),
            "away_overprediction_delta": round(_rate(away_top, away_count) - _rate(away_actual, away_count), 4),
            "team_matches_count": int(len(involved)),
            "team_involved_hit_rate": _rate(int(involved["prediction_hit"].sum()), len(involved)),
            "team_involved_miss_count": int((~involved["prediction_hit"]).sum()),
            "most_common_error_type": _most_common(errors, fallback="HIT"),
        })
    return pd.DataFrame(records, columns=columns)


def compute_favorite_underdog_summary(rows: pd.DataFrame) -> pd.DataFrame:
    columns = ["favorite_gap_bucket", "count", "hit_rate", "actual_draw_rate", "favorite_win_rate", "underdog_win_rate"]
    records = []
    for bucket in FAVORITE_GAP_BUCKETS:
        group = rows[rows["favorite_gap_bucket"].eq(bucket)]
        favorite_wins = 0
        underdog_wins = 0
        for _, row in group.iterrows():
            side = row["favorite_side"]
            if side in ("HOME", "AWAY"):
                favorite_wins += int(row["actual_result"] == side)
                underdog_wins += int(row["actual_result"] == ("AWAY" if side == "HOME" else "HOME"))
        records.append({
            "favorite_gap_bucket": bucket,
            "count": int(len(group)),
            "hit_rate": _rate(int(group["prediction_hit"].sum()), len(group)),
            "actual_draw_rate": _rate(int(group["actual_result"].eq("DRAW").sum()), len(group)),
            "favorite_win_rate": _rate(favorite_wins, len(group)),
            "underdog_win_rate": _rate(underdog_wins, len(group)),
        })
    return pd.DataFrame(records, columns=columns)


def analyze_prediction_error_patterns(
    rows: pd.DataFrame,
    *,
    output_dir: str | Path = "outputs/v2120_prediction_error_patterns",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prepared = prepare_prediction_rows(rows)
    evaluable = prepared[prepared["evaluable"]].copy().reset_index(drop=True)
    error_summary = compute_error_type_summary(prepared)
    edge_summary = compute_edge_band_error_summary(evaluable)
    top_summary = compute_top_probability_bucket_summary(evaluable)
    bias_summary = compute_home_away_bias_summary(evaluable)
    team_summary = compute_team_error_summary(evaluable)
    favorite_summary = compute_favorite_underdog_summary(evaluable)
    wrong_high = evaluable[
        ~evaluable["prediction_hit"]
        & (evaluable["top_probability"].ge(0.45) | evaluable["probability_edge"].ge(0.10))
    ].copy().sort_values("top_probability", ascending=False, na_position="last")
    correct_low = evaluable[
        evaluable["prediction_hit"] & evaluable["probability_edge"].le(0.05)
    ].copy()
    summary = _build_summary(
        prepared, evaluable, error_summary, edge_summary, top_summary,
        bias_summary, team_summary, wrong_high, correct_low, out,
    )
    artifacts = {
        "v2120_error_type_summary.csv": error_summary,
        "v2120_edge_band_error_summary.csv": edge_summary,
        "v2120_top_probability_bucket_summary.csv": top_summary,
        "v2120_home_away_bias_summary.csv": bias_summary,
        "v2120_team_error_summary.csv": team_summary,
        "v2120_favorite_underdog_summary.csv": favorite_summary,
        "v2120_wrong_high_confidence_rows.csv": _detail_rows(wrong_high),
        "v2120_correct_low_confidence_rows.csv": _detail_rows(correct_low),
    }
    for filename, frame in artifacts.items():
        frame.to_csv(out / filename, index=False)
    (out / "v2120_prediction_error_patterns_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    (out / "v2120_prediction_error_patterns_report.md").write_text(
        render_report(
            summary, error_summary, edge_summary, top_summary,
            bias_summary, team_summary, favorite_summary,
        ),
        encoding="utf-8",
    )
    return {
        "v2120_prediction_error_patterns_status": "READY",
        **summary,
        "summary_json_path": str((out / "v2120_prediction_error_patterns_summary.json").resolve()),
        "report_md_path": str((out / "v2120_prediction_error_patterns_report.md").resolve()),
    }


def render_report(
    summary: Mapping[str, object],
    error_summary: pd.DataFrame,
    edge_summary: pd.DataFrame,
    top_summary: pd.DataFrame,
    bias_summary: pd.DataFrame | None = None,
    team_summary: pd.DataFrame | None = None,
    favorite_summary: pd.DataFrame | None = None,
) -> str:
    bias_summary = pd.DataFrame() if bias_summary is None else bias_summary
    team_summary = pd.DataFrame() if team_summary is None else team_summary
    favorite_summary = pd.DataFrame() if favorite_summary is None else favorite_summary
    team_columns = [
        "team", "team_matches_count", "team_involved_hit_rate", "team_involved_miss_count",
        "home_overprediction_delta", "away_overprediction_delta", "most_common_error_type",
    ]
    team_report = team_summary.sort_values(
        ["team_involved_miss_count", "team"], ascending=[False, True], kind="stable",
    ).head(10).reindex(columns=team_columns)
    return "\n".join([
        "# v2.12.0 Prediction Error Pattern Diagnostics", "",
        "Diagnostic-only analysis of final model predictions. Probabilities and model decisions are not changed.", "",
        f"- rows_loaded: {summary['rows_loaded']}",
        f"- evaluable_count: {summary['evaluable_count']}",
        f"- baseline_hit_rate: {summary['baseline_hit_rate']}",
        f"- main_error_problem: {summary['main_error_problem']}",
        f"- recommendation: {summary['recommendation']}", "",
        "## Error types", "", _markdown_table(error_summary), "",
        "## Probability edge buckets", "", _markdown_table(edge_summary), "",
        "## Top probability buckets", "", _markdown_table(top_summary), "",
        "## Home / away bias", "", _markdown_table(bias_summary), "",
        "## Favorite / underdog gaps", "", _markdown_table(favorite_summary), "",
        "## Teams with the most involved misses", "", _markdown_table(team_report), "",
        f"Wrong high-confidence rows: {summary['wrong_high_confidence_count']}", "",
        f"Correct low-confidence rows: {summary['correct_low_confidence_count']}", "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _build_summary(
    prepared: pd.DataFrame,
    rows: pd.DataFrame,
    error_summary: pd.DataFrame,
    edge_summary: pd.DataFrame,
    top_summary: pd.DataFrame,
    bias_summary: pd.DataFrame,
    team_summary: pd.DataFrame,
    wrong_high: pd.DataFrame,
    correct_low: pd.DataFrame,
    output_dir: Path,
) -> dict[str, object]:
    evaluable_count = len(rows)
    hit_count = int(rows["prediction_hit"].sum()) if not rows.empty else 0
    outcome_metrics = {}
    for outcome in OUTCOMES:
        group = rows[rows["top_probability_outcome"].eq(outcome)]
        outcome_metrics[outcome] = (len(group), _rate(int(group["prediction_hit"].sum()), len(group)))
    misses = error_summary[~error_summary["error_type"].isin(["HIT", "UNKNOWN"])]
    biggest = _rank_row(misses, "count", ascending=False)
    nonempty_edges = edge_summary[edge_summary["count"].gt(0)]
    worst_edge = _rank_row(nonempty_edges, "hit_rate", ascending=True)
    best_edge = _rank_row(nonempty_edges, "hit_rate", ascending=False)
    nonempty_top = top_summary[top_summary["count"].gt(0)]
    worst_top = _rank_row(nonempty_top, "hit_rate", ascending=True)
    home_team = _rank_row(team_summary[team_summary["home_matches_count"].gt(0)], "home_overprediction_delta", ascending=False)
    away_team = _rank_row(team_summary[team_summary["away_matches_count"].gt(0)], "away_overprediction_delta", ascending=False)
    main_problem, recommendation = _diagnostic_recommendation(rows, bias_summary, team_summary, wrong_high, edge_summary)
    return {
        "rows_loaded": int(len(prepared)),
        "evaluable_count": int(evaluable_count),
        "hit_count": hit_count,
        "miss_count": int(evaluable_count - hit_count),
        "hit_rate": _rate(hit_count, evaluable_count),
        "baseline_hit_rate": _rate(hit_count, evaluable_count),
        "home_top_count": int(outcome_metrics["HOME"][0]),
        "draw_top_count": int(outcome_metrics["DRAW"][0]),
        "away_top_count": int(outcome_metrics["AWAY"][0]),
        "home_top_hit_rate": outcome_metrics["HOME"][1],
        "draw_top_hit_rate": outcome_metrics["DRAW"][1],
        "away_top_hit_rate": outcome_metrics["AWAY"][1],
        "actual_home_count": int(rows["actual_result"].eq("HOME").sum()),
        "actual_draw_count": int(rows["actual_result"].eq("DRAW").sum()),
        "actual_away_count": int(rows["actual_result"].eq("AWAY").sum()),
        "biggest_error_type": str(biggest.get("error_type", "")),
        "biggest_error_type_count": int(biggest.get("count", 0)),
        "worst_edge_bucket": str(worst_edge.get("edge_bucket", "")),
        "worst_edge_bucket_hit_rate": float(worst_edge.get("hit_rate", 0.0)),
        "best_edge_bucket": str(best_edge.get("edge_bucket", "")),
        "best_edge_bucket_hit_rate": float(best_edge.get("hit_rate", 0.0)),
        "worst_top_probability_bucket": str(worst_top.get("top_probability_bucket", "")),
        "worst_top_probability_bucket_hit_rate": float(worst_top.get("hit_rate", 0.0)),
        "most_overpredicted_team_home": str(home_team.get("team", "")),
        "most_overpredicted_team_away": str(away_team.get("team", "")),
        "wrong_high_confidence_count": int(len(wrong_high)),
        "correct_low_confidence_count": int(len(correct_low)),
        "main_error_problem": main_problem,
        "recommendation": recommendation,
        **SAFETY_FLAGS,
        "output_dir": str(output_dir).replace("\\", "/"),
    }


def _diagnostic_recommendation(rows, bias_summary, team_summary, wrong_high, edge_summary):
    if rows.empty:
        return "EDGE_CALIBRATION_WEAK", "KEEP_AS_DIAGNOSTIC_ONLY"
    home_over = int((rows["top_probability_outcome"].eq("HOME") & ~rows["actual_result"].eq("HOME")).sum())
    away_over = int((rows["top_probability_outcome"].eq("AWAY") & ~rows["actual_result"].eq("AWAY")).sum())
    draw_under = int((rows["actual_result"].eq("DRAW") & ~rows["top_probability_outcome"].eq("DRAW")).sum())
    high_conf = len(wrong_high)
    eligible_teams = team_summary[team_summary["team_matches_count"].ge(3)]
    max_team_delta = 0.0
    if not eligible_teams.empty:
        max_team_delta = float(max(
            eligible_teams["home_overprediction_delta"].abs().max(),
            eligible_teams["away_overprediction_delta"].abs().max(),
        ))
    edge_rows = edge_summary[edge_summary["count"].gt(0)]
    edge_spread = float(edge_rows["hit_rate"].max() - edge_rows["hit_rate"].min()) if len(edge_rows) > 1 else 0.0
    if max_team_delta >= 0.35:
        return "TEAM_SPECIFIC_BIAS", "INVESTIGATE_TEAM_SPECIFIC_BIAS"
    signals = [
        (draw_under, 3, "DRAW_UNDERPREDICTED", "INVESTIGATE_DRAW_UNDERPREDICTION"),
        (home_over, 2, "HOME_OVERPREDICTED", "INVESTIGATE_HOME_OVERPREDICTION"),
        (away_over, 1, "AWAY_OVERPREDICTED", "INVESTIGATE_AWAY_OVERPREDICTION"),
        (high_conf, 0, "HIGH_CONFIDENCE_ERRORS", "INVESTIGATE_EDGE_CALIBRATION"),
    ]
    score, _, problem, recommendation = max(signals, key=lambda item: (item[0], item[1]))
    if edge_spread >= 0.20 and high_conf >= score:
        return "EDGE_CALIBRATION_WEAK", "INVESTIGATE_EDGE_CALIBRATION"
    return problem, recommendation


def _bucket_summary(rows: pd.DataFrame, bucket_column: str, buckets: Iterable[str]) -> pd.DataFrame:
    columns = [
        bucket_column, "count", "hit_count", "miss_count", "hit_rate",
        "actual_home_rate", "actual_draw_rate", "actual_away_rate",
        "top_home_rate", "top_draw_rate", "top_away_rate",
    ]
    records = []
    for bucket in buckets:
        group = rows[rows[bucket_column].eq(bucket)]
        count = len(group)
        hit_count = int(group["prediction_hit"].sum())
        records.append({
            bucket_column: bucket, "count": int(count), "hit_count": hit_count,
            "miss_count": int(count - hit_count), "hit_rate": _rate(hit_count, count),
            "actual_home_rate": _rate(int(group["actual_result"].eq("HOME").sum()), count),
            "actual_draw_rate": _rate(int(group["actual_result"].eq("DRAW").sum()), count),
            "actual_away_rate": _rate(int(group["actual_result"].eq("AWAY").sum()), count),
            "top_home_rate": _rate(int(group["top_probability_outcome"].eq("HOME").sum()), count),
            "top_draw_rate": _rate(int(group["top_probability_outcome"].eq("DRAW").sum()), count),
            "top_away_rate": _rate(int(group["top_probability_outcome"].eq("AWAY").sum()), count),
        })
    return pd.DataFrame(records, columns=columns)


def _detail_rows(rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "match_date", "home_team", "away_team", "actual_result", "top_probability_outcome",
        "home_win_probability", "draw_probability", "away_win_probability", "top_probability",
        "probability_edge", "error_type", "uncertainty_level", "data_quality_band",
    ]
    return rows.reindex(columns=columns)


def _rank_row(frame: pd.DataFrame, column: str, *, ascending: bool) -> dict[str, object]:
    if frame.empty:
        return {}
    return frame.sort_values(column, ascending=ascending, kind="stable").iloc[0].to_dict()


def _most_common(values: Iterable[str], *, fallback: str = "") -> str:
    counts = Counter(values)
    return counts.most_common(1)[0][0] if counts else fallback


def _outcome(value: object) -> str:
    text = str(value).strip().upper()
    aliases = {"H": "HOME", "D": "DRAW", "A": "AWAY", "1": "HOME", "X": "DRAW", "2": "AWAY"}
    return aliases.get(text, text)


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _rate(count: int, total: int) -> float:
    return round(float(count / total), 4) if total else 0.0


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)
