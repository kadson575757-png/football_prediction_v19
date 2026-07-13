# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import (
    SAFETY_FLAGS,
    prepare_prediction_rows,
)

DETAIL_COLUMNS = [
    "match_date", "home_team", "away_team", "actual_result", "top_probability_outcome",
    "prediction_hit", "error_type", "home_win_probability", "draw_probability",
    "away_win_probability", "top_probability", "probability_edge",
]


def add_wrong_high_confidence(rows: pd.DataFrame) -> pd.DataFrame:
    frame = rows.copy()
    frame["wrong_high_confidence"] = (
        ~frame["prediction_hit"].astype(bool)
        & (frame["top_probability"].ge(0.45) | frame["probability_edge"].ge(0.10))
    )
    return frame


def compute_home_team_bias_summary(rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "team", "home_matches_count", "model_home_top_count", "actual_home_win_count",
        "actual_home_draw_count", "actual_home_loss_count", "model_home_top_rate",
        "actual_home_win_rate", "home_overprediction_delta", "home_top_hit_count",
        "home_top_miss_count", "home_top_hit_rate", "home_top_actual_draw_count",
        "home_top_actual_away_count", "average_home_win_probability",
        "wrong_high_confidence_home_count",
    ]
    records = []
    teams = _teams(rows, "home_team")
    for team in teams:
        group = rows[rows["home_team"].astype(str).eq(team)]
        home_top = group[group["top_probability_outcome"].eq("HOME")]
        count = len(group)
        model_top_count = len(home_top)
        actual_win_count = int(group["actual_result"].eq("HOME").sum())
        top_hit_count = int(home_top["actual_result"].eq("HOME").sum())
        model_rate = _rate(model_top_count, count)
        actual_rate = _rate(actual_win_count, count)
        records.append({
            "team": team,
            "home_matches_count": int(count),
            "model_home_top_count": int(model_top_count),
            "actual_home_win_count": actual_win_count,
            "actual_home_draw_count": int(group["actual_result"].eq("DRAW").sum()),
            "actual_home_loss_count": int(group["actual_result"].eq("AWAY").sum()),
            "model_home_top_rate": model_rate,
            "actual_home_win_rate": actual_rate,
            "home_overprediction_delta": round(model_rate - actual_rate, 4),
            "home_top_hit_count": top_hit_count,
            "home_top_miss_count": int(model_top_count - top_hit_count),
            "home_top_hit_rate": _rate(top_hit_count, model_top_count),
            "home_top_actual_draw_count": int(home_top["actual_result"].eq("DRAW").sum()),
            "home_top_actual_away_count": int(home_top["actual_result"].eq("AWAY").sum()),
            "average_home_win_probability": _mean(group["home_win_probability"]),
            "wrong_high_confidence_home_count": int(group["wrong_high_confidence"].sum()),
        })
    return pd.DataFrame(records, columns=columns)


def compute_away_team_bias_summary(rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "team", "away_matches_count", "model_away_top_count", "actual_away_win_count",
        "actual_away_draw_count", "actual_away_loss_count", "model_away_top_rate",
        "actual_away_win_rate", "away_overprediction_delta", "away_top_hit_count",
        "away_top_miss_count", "away_top_hit_rate", "away_top_actual_draw_count",
        "away_top_actual_home_count", "average_away_win_probability",
        "wrong_high_confidence_away_count",
    ]
    records = []
    teams = _teams(rows, "away_team")
    for team in teams:
        group = rows[rows["away_team"].astype(str).eq(team)]
        away_top = group[group["top_probability_outcome"].eq("AWAY")]
        count = len(group)
        model_top_count = len(away_top)
        actual_win_count = int(group["actual_result"].eq("AWAY").sum())
        top_hit_count = int(away_top["actual_result"].eq("AWAY").sum())
        model_rate = _rate(model_top_count, count)
        actual_rate = _rate(actual_win_count, count)
        records.append({
            "team": team,
            "away_matches_count": int(count),
            "model_away_top_count": int(model_top_count),
            "actual_away_win_count": actual_win_count,
            "actual_away_draw_count": int(group["actual_result"].eq("DRAW").sum()),
            "actual_away_loss_count": int(group["actual_result"].eq("HOME").sum()),
            "model_away_top_rate": model_rate,
            "actual_away_win_rate": actual_rate,
            "away_overprediction_delta": round(model_rate - actual_rate, 4),
            "away_top_hit_count": top_hit_count,
            "away_top_miss_count": int(model_top_count - top_hit_count),
            "away_top_hit_rate": _rate(top_hit_count, model_top_count),
            "away_top_actual_draw_count": int(away_top["actual_result"].eq("DRAW").sum()),
            "away_top_actual_home_count": int(away_top["actual_result"].eq("HOME").sum()),
            "average_away_win_probability": _mean(group["away_win_probability"]),
            "wrong_high_confidence_away_count": int(group["wrong_high_confidence"].sum()),
        })
    return pd.DataFrame(records, columns=columns)


def compute_team_involved_error_summary(rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "team", "involved_matches_count", "involved_hit_count", "involved_miss_count",
        "involved_hit_rate", "most_common_error_type", "most_common_error_type_count",
        "home_top_actual_draw_involved_count", "away_top_actual_draw_involved_count",
        "wrong_high_confidence_involved_count",
    ]
    teams = sorted(set(_teams(rows, "home_team")) | set(_teams(rows, "away_team")))
    records = []
    for team in teams:
        involved = rows[
            rows["home_team"].astype(str).eq(team) | rows["away_team"].astype(str).eq(team)
        ]
        errors = involved[~involved["prediction_hit"]]
        common_name, common_count = _most_common(errors["error_type"].tolist())
        hit_count = int(involved["prediction_hit"].sum())
        records.append({
            "team": team,
            "involved_matches_count": int(len(involved)),
            "involved_hit_count": hit_count,
            "involved_miss_count": int(len(involved) - hit_count),
            "involved_hit_rate": _rate(hit_count, len(involved)),
            "most_common_error_type": common_name,
            "most_common_error_type_count": common_count,
            "home_top_actual_draw_involved_count": int(involved["error_type"].eq("HOME_TOP_ACTUAL_DRAW").sum()),
            "away_top_actual_draw_involved_count": int(involved["error_type"].eq("AWAY_TOP_ACTUAL_DRAW").sum()),
            "wrong_high_confidence_involved_count": int(involved["wrong_high_confidence"].sum()),
        })
    return pd.DataFrame(records, columns=columns)


def compute_bias_severity_summary(
    home_summary: pd.DataFrame,
    away_summary: pd.DataFrame,
    involved_summary: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "team", "home_bias_severity_score", "away_bias_severity_score",
        "involved_bias_severity_score", "total_bias_severity_score", "primary_bias_area",
    ]
    teams = sorted(
        set(home_summary.get("team", pd.Series(dtype=str)).astype(str))
        | set(away_summary.get("team", pd.Series(dtype=str)).astype(str))
        | set(involved_summary.get("team", pd.Series(dtype=str)).astype(str))
    )
    home_by_team = home_summary.set_index("team") if not home_summary.empty else pd.DataFrame()
    away_by_team = away_summary.set_index("team") if not away_summary.empty else pd.DataFrame()
    involved_by_team = involved_summary.set_index("team") if not involved_summary.empty else pd.DataFrame()
    records = []
    for team in teams:
        home = _indexed_record(home_by_team, team)
        away = _indexed_record(away_by_team, team)
        involved = _indexed_record(involved_by_team, team)
        home_score = round(
            abs(float(home.get("home_overprediction_delta", 0.0))) * 100
            + int(home.get("home_top_miss_count", 0)) * 2
            + int(home.get("wrong_high_confidence_home_count", 0)) * 3,
            4,
        )
        away_score = round(
            abs(float(away.get("away_overprediction_delta", 0.0))) * 100
            + int(away.get("away_top_miss_count", 0)) * 2
            + int(away.get("wrong_high_confidence_away_count", 0)) * 3,
            4,
        )
        involved_score = round(
            int(involved.get("involved_miss_count", 0)) * 2
            + int(involved.get("wrong_high_confidence_involved_count", 0)) * 3,
            4,
        )
        scores = {"HOME": home_score, "AWAY": away_score, "INVOLVED": involved_score}
        maximum = max(scores.values(), default=0.0)
        leaders = [name for name, score in scores.items() if score == maximum]
        records.append({
            "team": team,
            "home_bias_severity_score": home_score,
            "away_bias_severity_score": away_score,
            "involved_bias_severity_score": involved_score,
            "total_bias_severity_score": round(home_score + away_score + involved_score, 4),
            "primary_bias_area": leaders[0] if len(leaders) == 1 else "MIXED",
        })
    return pd.DataFrame(records, columns=columns)


def analyze_team_specific_bias_drilldown(
    rows: pd.DataFrame,
    *,
    output_dir: str | Path = "outputs/v2121_team_specific_bias_drilldown",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prepared = prepare_prediction_rows(rows)
    evaluable = add_wrong_high_confidence(
        prepared[prepared["evaluable"]].copy().reset_index(drop=True)
    )
    home_summary = compute_home_team_bias_summary(evaluable)
    away_summary = compute_away_team_bias_summary(evaluable)
    involved_summary = compute_team_involved_error_summary(evaluable)
    severity_summary = compute_bias_severity_summary(home_summary, away_summary, involved_summary)
    error_rows = evaluable[~evaluable["prediction_hit"]].copy()
    bournemouth = evaluable[evaluable["home_team"].astype(str).str.casefold().eq("bournemouth")]
    liverpool = evaluable[evaluable["away_team"].astype(str).str.casefold().eq("liverpool")]
    summary = _build_summary(
        prepared, evaluable, home_summary, away_summary, involved_summary, severity_summary, out,
    )
    artifacts = {
        "v2121_home_team_bias_summary.csv": home_summary,
        "v2121_away_team_bias_summary.csv": away_summary,
        "v2121_team_involved_error_summary.csv": involved_summary,
        "v2121_team_error_rows.csv": _detail_rows(error_rows),
        "v2121_bournemouth_home_drilldown.csv": _detail_rows(bournemouth),
        "v2121_liverpool_away_drilldown.csv": _detail_rows(liverpool),
        "v2121_team_bias_severity_summary.csv": severity_summary,
    }
    for filename, frame in artifacts.items():
        frame.to_csv(out / filename, index=False)
    (out / "v2121_team_specific_bias_drilldown_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    (out / "v2121_team_specific_bias_drilldown_report.md").write_text(
        render_report(summary, home_summary, away_summary, involved_summary, severity_summary),
        encoding="utf-8",
    )
    return {
        "v2121_team_specific_bias_drilldown_status": "READY",
        **summary,
        "summary_json_path": str((out / "v2121_team_specific_bias_drilldown_summary.json").resolve()),
        "report_md_path": str((out / "v2121_team_specific_bias_drilldown_report.md").resolve()),
    }


def render_report(
    summary: Mapping[str, object],
    home_summary: pd.DataFrame,
    away_summary: pd.DataFrame,
    involved_summary: pd.DataFrame,
    severity_summary: pd.DataFrame,
) -> str:
    home_ranked = home_summary.sort_values(
        ["home_overprediction_delta", "home_top_miss_count"], ascending=[False, False], kind="stable",
    ).head(10)
    away_ranked = away_summary.sort_values(
        ["away_overprediction_delta", "away_top_miss_count"], ascending=[False, False], kind="stable",
    ).head(10)
    involved_ranked = involved_summary.sort_values(
        ["involved_miss_count", "wrong_high_confidence_involved_count"], ascending=[False, False], kind="stable",
    ).head(10)
    severity_ranked = severity_summary.sort_values(
        "total_bias_severity_score", ascending=False, kind="stable",
    ).head(10)
    return "\n".join([
        "# v2.12.1 Team-Specific Bias Drilldown", "",
        "Diagnostic-only team bias analysis. Final probabilities and production decisions are unchanged.", "",
        f"- rows_loaded: {summary['rows_loaded']}",
        f"- evaluable_count: {summary['evaluable_count']}",
        f"- baseline_hit_rate: {summary['baseline_hit_rate']}",
        f"- main_team_bias_problem: {summary['main_team_bias_problem']}",
        f"- recommendation: {summary['recommendation']}", "",
        "## Highest home overprediction", "", _markdown_table(home_ranked), "",
        "## Highest away overprediction", "", _markdown_table(away_ranked), "",
        "## Highest involved error counts", "", _markdown_table(involved_ranked), "",
        "## Highest total bias severity", "", _markdown_table(severity_ranked), "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _build_summary(prepared, rows, home, away, involved, severity, output_dir):
    hit_count = int(rows["prediction_hit"].sum()) if not rows.empty else 0
    worst_home = _rank(home, ["home_overprediction_delta", "home_top_miss_count"], [False, False])
    worst_away = _rank(away, ["away_overprediction_delta", "away_top_miss_count"], [False, False])
    worst_involved = _rank(involved, ["involved_miss_count", "wrong_high_confidence_involved_count"], [False, False])
    highest_severity = _rank(severity, ["total_bias_severity_score"], [False])
    bournemouth = _casefold_record(home, "Bournemouth")
    liverpool = _casefold_record(away, "Liverpool")
    problem, recommendation = _recommendation(highest_severity, worst_home, worst_away)
    return {
        "rows_loaded": int(len(prepared)),
        "evaluable_count": int(len(rows)),
        "baseline_hit_rate": _rate(hit_count, len(rows)),
        "worst_home_overpredicted_team": str(worst_home.get("team", "")),
        "worst_home_overprediction_delta": float(worst_home.get("home_overprediction_delta", 0.0)),
        "worst_away_overpredicted_team": str(worst_away.get("team", "")),
        "worst_away_overprediction_delta": float(worst_away.get("away_overprediction_delta", 0.0)),
        "worst_involved_team": str(worst_involved.get("team", "")),
        "worst_involved_miss_count": int(worst_involved.get("involved_miss_count", 0)),
        "highest_bias_severity_team": str(highest_severity.get("team", "")),
        "highest_bias_severity_score": float(highest_severity.get("total_bias_severity_score", 0.0)),
        "bournemouth_home_matches_count": int(bournemouth.get("home_matches_count", 0)),
        "bournemouth_home_hit_rate": float(bournemouth.get("home_top_hit_rate", 0.0)),
        "bournemouth_home_top_actual_draw_count": int(bournemouth.get("home_top_actual_draw_count", 0)),
        "liverpool_away_matches_count": int(liverpool.get("away_matches_count", 0)),
        "liverpool_away_hit_rate": float(liverpool.get("away_top_hit_rate", 0.0)),
        "liverpool_away_top_actual_draw_count": int(liverpool.get("away_top_actual_draw_count", 0)),
        "main_team_bias_problem": problem,
        "recommendation": recommendation,
        "output_dir": str(output_dir).replace("\\", "/"),
        **SAFETY_FLAGS,
    }


def _recommendation(highest, worst_home, worst_away):
    if not highest:
        return "MIXED_TEAM_BIAS", "KEEP_AS_DIAGNOSTIC_ONLY"
    primary = str(highest.get("primary_bias_area", "MIXED"))
    home_delta = float(worst_home.get("home_overprediction_delta", 0.0))
    away_delta = float(worst_away.get("away_overprediction_delta", 0.0))
    if primary == "HOME" and home_delta > 0:
        return "HOME_TEAM_OVERPREDICTION", "INVESTIGATE_HOME_TEAM_CORRECTION"
    if primary == "AWAY" and away_delta > 0:
        return "AWAY_TEAM_OVERPREDICTION", "INVESTIGATE_AWAY_TEAM_CORRECTION"
    if primary == "INVOLVED":
        return "TEAM_INVOLVED_ERROR_CLUSTER", "INVESTIGATE_TEAM_SPECIFIC_CORRECTION_LAYER"
    return "MIXED_TEAM_BIAS", "INVESTIGATE_TEAM_SPECIFIC_CORRECTION_LAYER"


def _detail_rows(rows: pd.DataFrame) -> pd.DataFrame:
    return rows.reindex(columns=DETAIL_COLUMNS)


def _rank(frame: pd.DataFrame, columns: list[str], ascending: list[bool]) -> dict[str, object]:
    if frame.empty:
        return {}
    ranked = frame.sort_values(columns + ["team"], ascending=ascending + [True], kind="stable")
    return ranked.iloc[0].to_dict()


def _casefold_record(frame: pd.DataFrame, team: str) -> dict[str, object]:
    if frame.empty:
        return {}
    matched = frame[frame["team"].astype(str).str.casefold().eq(team.casefold())]
    return matched.iloc[0].to_dict() if not matched.empty else {}


def _indexed_record(frame: pd.DataFrame, team: str) -> dict[str, object]:
    if frame.empty or team not in frame.index:
        return {}
    row = frame.loc[team]
    return row.iloc[0].to_dict() if isinstance(row, pd.DataFrame) else row.to_dict()


def _teams(rows: pd.DataFrame, column: str) -> list[str]:
    if rows.empty or column not in rows:
        return []
    return sorted({str(value) for value in rows[column].dropna() if str(value).strip()})


def _most_common(values: Iterable[str]) -> tuple[str, int]:
    counts = Counter(values)
    return counts.most_common(1)[0] if counts else ("HIT", 0)


def _mean(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return round(float(numeric.mean()), 4) if not numeric.empty else 0.0


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
