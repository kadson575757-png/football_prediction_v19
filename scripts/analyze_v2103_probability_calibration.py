# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


BUCKETS = [
    ("0.30-0.35", 0.30, 0.35),
    ("0.35-0.40", 0.35, 0.40),
    ("0.40-0.45", 0.40, 0.45),
    ("0.45-0.50", 0.45, 0.50),
    ("0.50-0.55", 0.50, 0.55),
    ("0.55-0.60", 0.55, 0.60),
    ("0.60-0.70", 0.60, 0.70),
    ("0.70-1.00", 0.70, 1.0000001),
]

ROW_COLUMNS = [
    "competition",
    "season",
    "home_team",
    "away_team",
    "match_date",
    "real_result",
    "home_win_probability",
    "draw_probability",
    "away_win_probability",
    "top_probability_outcome",
    "top_probability",
    "top_probability_hit",
    "multiclass_brier_row",
    "home_brier_row",
    "draw_brier_row",
    "away_brier_row",
    "calibration_bucket",
    "probability_edge",
    "probability_edge_band",
    "uncertainty_level",
    "data_quality_band",
]

SUMMARY_KEYS = [
    "v2103_probability_calibration_status",
    "rows_analyzed",
    "probability_rows_count",
    "result_known_count",
    "top_probability_hit_rate",
    "multiclass_brier_score",
    "home_brier_score",
    "draw_brier_score",
    "away_brier_score",
    "top_probability_average",
    "top_probability_empirical_hit_rate",
    "calibration_gap",
    "expected_calibration_error",
    "max_calibration_error",
    "worst_calibration_bucket",
    "recommendation",
    "automatic_betting_enabled",
    "staking_logic_enabled",
    "roi_logic_enabled",
]


def analyze_probability_calibration(
    rows: str | Path | pd.DataFrame,
    output_dir: str | Path = "outputs/v2103_probability_calibration",
) -> dict[str, object]:
    frame = pd.read_csv(rows, keep_default_na=False) if not isinstance(rows, pd.DataFrame) else rows.copy()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    calibration_rows = build_calibration_rows(frame)
    known = calibration_rows[calibration_rows["real_result"].isin(["HOME", "DRAW", "AWAY"])].copy()
    buckets = build_bucket_summary(known)
    summary = build_calibration_summary(calibration_rows, known, buckets)

    rows_path = out / "v2103_probability_calibration_rows.csv"
    json_path = out / "v2103_probability_calibration_summary.json"
    report_path = out / "v2103_probability_calibration_report.md"
    calibration_rows.to_csv(rows_path, index=False)
    json_path.write_text(json.dumps({**summary, "buckets": buckets.to_dict("records")}, indent=2), encoding="utf-8")
    report_path.write_text(render_markdown_report(summary, buckets), encoding="utf-8")

    return {
        **summary,
        "v2103_probability_calibration_rows_csv_path": str(rows_path.resolve()),
        "v2103_probability_calibration_summary_json_path": str(json_path.resolve()),
        "v2103_probability_calibration_report_md_path": str(report_path.resolve()),
    }


def build_calibration_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        home = _num(row.get("home_win_probability"))
        draw = _num(row.get("draw_probability"))
        away = _num(row.get("away_win_probability"))
        top_outcome = str(row.get("top_probability_outcome") or _top_outcome(home, draw, away)).upper()
        if top_outcome not in {"HOME", "DRAW", "AWAY"}:
            top_outcome = _top_outcome(home, draw, away)
        top_probability = {"HOME": home, "DRAW": draw, "AWAY": away}[top_outcome]
        real_result = _normalize_result(row)
        known = real_result in {"HOME", "DRAW", "AWAY"}
        actual = {
            "HOME": 1.0 if real_result == "HOME" else 0.0,
            "DRAW": 1.0 if real_result == "DRAW" else 0.0,
            "AWAY": 1.0 if real_result == "AWAY" else 0.0,
        }
        home_brier = (home - actual["HOME"]) ** 2 if known else 0.0
        draw_brier = (draw - actual["DRAW"]) ** 2 if known else 0.0
        away_brier = (away - actual["AWAY"]) ** 2 if known else 0.0
        rows.append(
            {
                "competition": row.get("competition", ""),
                "season": row.get("season", ""),
                "home_team": row.get("home_team", ""),
                "away_team": row.get("away_team", ""),
                "match_date": row.get("match_date", row.get("resolved_match_date", row.get("input_match_date", ""))),
                "real_result": real_result,
                "home_win_probability": home,
                "draw_probability": draw,
                "away_win_probability": away,
                "top_probability_outcome": top_outcome,
                "top_probability": top_probability,
                "top_probability_hit": int(known and top_outcome == real_result),
                "multiclass_brier_row": round((home_brier + draw_brier + away_brier) / 3, 4) if known else 0.0,
                "home_brier_row": round(home_brier, 4) if known else 0.0,
                "draw_brier_row": round(draw_brier, 4) if known else 0.0,
                "away_brier_row": round(away_brier, 4) if known else 0.0,
                "calibration_bucket": calibration_bucket(top_probability),
                "probability_edge": _num(row.get("probability_edge")),
                "probability_edge_band": row.get("probability_edge_band", ""),
                "uncertainty_level": row.get("uncertainty_level", ""),
                "data_quality_band": row.get("data_quality_band", ""),
            }
        )
    return pd.DataFrame(rows, columns=ROW_COLUMNS)


def build_bucket_summary(known: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for bucket_name, _, _ in BUCKETS:
        group = known[known["calibration_bucket"].eq(bucket_name)]
        rows_count = int(len(group))
        avg_top = round(float(group["top_probability"].mean()), 4) if rows_count else 0.0
        hit_rate = round(float(group["top_probability_hit"].mean()), 4) if rows_count else 0.0
        gap = round(hit_rate - avg_top, 4) if rows_count else 0.0
        rows.append(
            {
                "bucket_name": bucket_name,
                "rows_count": rows_count,
                "average_top_probability": avg_top,
                "empirical_hit_rate": hit_rate,
                "calibration_gap": gap,
                "home_count": int(group["top_probability_outcome"].eq("HOME").sum()) if rows_count else 0,
                "draw_count": int(group["top_probability_outcome"].eq("DRAW").sum()) if rows_count else 0,
                "away_count": int(group["top_probability_outcome"].eq("AWAY").sum()) if rows_count else 0,
            }
        )
    return pd.DataFrame(rows)


def build_calibration_summary(rows: pd.DataFrame, known: pd.DataFrame, buckets: pd.DataFrame) -> dict[str, object]:
    known_count = int(len(known))
    probability_rows_count = int((rows[["home_win_probability", "draw_probability", "away_win_probability"]].sum(axis=1) > 0).sum()) if not rows.empty else 0
    top_avg = round(float(known["top_probability"].mean()), 4) if known_count else 0.0
    hit_rate = round(float(known["top_probability_hit"].mean()), 4) if known_count else 0.0
    ece = _expected_calibration_error(buckets, known_count)
    max_error = round(float(buckets["calibration_gap"].abs().max()), 4) if not buckets.empty else 0.0
    worst_bucket = _worst_bucket(buckets)
    summary = {
        "v2103_probability_calibration_status": "READY",
        "rows_analyzed": int(len(rows)),
        "probability_rows_count": probability_rows_count,
        "result_known_count": known_count,
        "top_probability_hit_rate": hit_rate,
        "multiclass_brier_score": _mean(known, "multiclass_brier_row"),
        "home_brier_score": _mean(known, "home_brier_row"),
        "draw_brier_score": _mean(known, "draw_brier_row"),
        "away_brier_score": _mean(known, "away_brier_row"),
        "top_probability_average": top_avg,
        "top_probability_empirical_hit_rate": hit_rate,
        "calibration_gap": round(hit_rate - top_avg, 4),
        "expected_calibration_error": ece,
        "max_calibration_error": max_error,
        "worst_calibration_bucket": worst_bucket,
        "average_home_probability": _mean(known, "home_win_probability"),
        "average_draw_probability": _mean(known, "draw_probability"),
        "average_away_probability": _mean(known, "away_win_probability"),
        "actual_home_rate": _actual_rate(known, "HOME"),
        "actual_draw_rate": _actual_rate(known, "DRAW"),
        "actual_away_rate": _actual_rate(known, "AWAY"),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    summary["home_probability_gap"] = round(float(summary["actual_home_rate"]) - float(summary["average_home_probability"]), 4)
    summary["draw_probability_gap"] = round(float(summary["actual_draw_rate"]) - float(summary["average_draw_probability"]), 4)
    summary["away_probability_gap"] = round(float(summary["actual_away_rate"]) - float(summary["average_away_probability"]), 4)
    summary["recommendation"] = recommendation(known_count, ece)
    return summary


def calibration_bucket(probability: object) -> str:
    value = _num(probability)
    for name, lower, upper in BUCKETS:
        if lower <= value < upper:
            return name
    if value < 0.30:
        return "0.30-0.35"
    return "0.70-1.00"


def recommendation(result_known_count: int, expected_calibration_error: float) -> str:
    if result_known_count < 20:
        return "CALIBRATION_SAMPLE_TOO_SMALL"
    if expected_calibration_error <= 0.08:
        return "CALIBRATION_LOOKS_ACCEPTABLE"
    if expected_calibration_error <= 0.15:
        return "CALIBRATION_NEEDS_ATTENTION"
    return "CALIBRATION_POOR_REVIEW_REQUIRED"


def render_markdown_report(summary: dict[str, object], buckets: pd.DataFrame) -> str:
    outcome_rows = [
        ("Home", summary["average_home_probability"], summary["actual_home_rate"], summary["home_probability_gap"]),
        ("Draw", summary["average_draw_probability"], summary["actual_draw_rate"], summary["draw_probability_gap"]),
        ("Away", summary["average_away_probability"], summary["actual_away_rate"], summary["away_probability_gap"]),
    ]
    interpretation = _interpretation(float(summary["calibration_gap"]), float(summary["expected_calibration_error"]))
    return "\n".join(
        [
            "# v2.10.3 Probability Calibration Diagnostics",
            "",
            "## Safety",
            "- automatic_betting_enabled=false",
            "- staking_logic_enabled=false",
            "- roi_logic_enabled=false",
            "- No productive betting logic",
            "",
            "## Executive Summary",
            f"- rows_analyzed: {summary['rows_analyzed']}",
            f"- result_known_count: {summary['result_known_count']}",
            f"- top_probability_hit_rate: {summary['top_probability_hit_rate']}",
            f"- multiclass_brier_score: {summary['multiclass_brier_score']}",
            f"- expected_calibration_error: {summary['expected_calibration_error']}",
            f"- calibration_gap: {summary['calibration_gap']}",
            f"- recommendation: {summary['recommendation']}",
            "",
            "## Top Probability Calibration Buckets",
            _bucket_table(buckets),
            "",
            "## Outcome Distribution",
            "| Outcome | Average probability | Actual rate | Gap |",
            "|---|---:|---:|---:|",
            *[f"| {name} | {avg} | {actual} | {gap} |" for name, avg, actual, gap in outcome_rows],
            "",
            "## Worst Calibration Buckets",
            _worst_table(buckets),
            "",
            "## Interpretation",
            interpretation,
            "",
            "## Conclusion",
            "No probability changes were made. No productive activation was added. This is diagnostics only. Next step: review calibration gaps before any future model-policy work.",
            "",
        ]
    )


def _normalize_result(row: pd.Series) -> str:
    for field in ["real_result", "result", "outcome", "actual_result"]:
        value = str(row.get(field, "")).strip().upper()
        if value:
            break
    else:
        return "RESULT_UNKNOWN"
    mapping = {
        "H": "HOME",
        "HOME": "HOME",
        "HOME_WIN": "HOME",
        "D": "DRAW",
        "DRAW": "DRAW",
        "A": "AWAY",
        "AWAY": "AWAY",
        "AWAY_WIN": "AWAY",
    }
    return mapping.get(value, "RESULT_UNKNOWN")


def _top_outcome(home: float, draw: float, away: float) -> str:
    return sorted([("HOME", home), ("DRAW", draw), ("AWAY", away)], key=lambda item: item[1], reverse=True)[0][0]


def _expected_calibration_error(buckets: pd.DataFrame, known_count: int) -> float:
    if known_count <= 0 or buckets.empty:
        return 0.0
    weighted = (buckets["rows_count"].astype(float) * buckets["calibration_gap"].astype(float).abs()).sum()
    return round(float(weighted / known_count), 4)


def _worst_bucket(buckets: pd.DataFrame) -> str:
    candidates = buckets[buckets["rows_count"].astype(int) >= 3].copy()
    if candidates.empty:
        return ""
    candidates["abs_gap"] = candidates["calibration_gap"].astype(float).abs()
    return str(candidates.sort_values(["abs_gap", "rows_count"], ascending=[False, False]).iloc[0]["bucket_name"])


def _mean(frame: pd.DataFrame, column: str) -> float:
    return round(float(frame[column].mean()), 4) if not frame.empty and column in frame else 0.0


def _actual_rate(frame: pd.DataFrame, outcome: str) -> float:
    return round(float(frame["real_result"].eq(outcome).mean()), 4) if not frame.empty else 0.0


def _bucket_table(buckets: pd.DataFrame) -> str:
    lines = ["| Bucket | Rows | Average top probability | Empirical hit rate | Calibration gap |", "|---|---:|---:|---:|---:|"]
    for _, row in buckets.iterrows():
        lines.append(f"| {row['bucket_name']} | {row['rows_count']} | {row['average_top_probability']} | {row['empirical_hit_rate']} | {row['calibration_gap']} |")
    return "\n".join(lines)


def _worst_table(buckets: pd.DataFrame) -> str:
    work = buckets.copy()
    if work.empty:
        return "No buckets available."
    work["abs_gap"] = work["calibration_gap"].astype(float).abs()
    lines = ["| Bucket | Rows | Calibration gap |", "|---|---:|---:|"]
    for _, row in work.sort_values("abs_gap", ascending=False).head(5).iterrows():
        lines.append(f"| {row['bucket_name']} | {row['rows_count']} | {row['calibration_gap']} |")
    return "\n".join(lines)


def _interpretation(calibration_gap: float, ece: float) -> str:
    direction = "overconfident" if calibration_gap < 0 else ("underconfident" if calibration_gap > 0 else "balanced")
    level = "acceptable" if ece <= 0.08 else ("needs attention" if ece <= 0.15 else "poor")
    return f"Top probabilities look {direction}; calibration error is {level}. Review Home/Draw/Away distribution gaps before any future diagnostic follow-up."


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return round(float(value), 4)
    except (TypeError, ValueError):
        return 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="outputs/v27_prematch_evaluation/v27_prematch_evaluation_rows.csv")
    parser.add_argument("--output-dir", default="outputs/v2103_probability_calibration")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_probability_calibration(args.rows, args.output_dir)
    for key in SUMMARY_KEYS:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
