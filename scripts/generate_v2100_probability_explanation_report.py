# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v27_evaluation_metrics import compute_v27_metrics  # noqa: E402


def generate_probability_explanation_report(rows: str | Path, output_dir: str | Path = "outputs/v2100_probability_explanation_report") -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(rows, keep_default_na=False)
    work = _prepare_frame(frame)
    metrics = compute_v27_metrics(work)
    summary = {
        "v2100_probability_explanation_report_status": "READY",
        "rows_analyzed": int(len(work)),
        "probability_rows_count": metrics["probability_rows_count"],
        "top_probability_home_count": metrics["top_probability_home_count"],
        "top_probability_draw_count": metrics["top_probability_draw_count"],
        "top_probability_away_count": metrics["top_probability_away_count"],
        "top_probability_hit_rate": metrics["top_probability_hit_rate"],
        "average_home_probability": round(float(work["home_win_probability"].mean()), 4) if len(work) else 0.0,
        "average_draw_probability": round(float(work["draw_probability"].mean()), 4) if len(work) else 0.0,
        "average_away_probability": round(float(work["away_win_probability"].mean()), 4) if len(work) else 0.0,
        "high_uncertainty_count": int(work["uncertainty_level"].astype(str).eq("HIGH").sum()),
        "medium_uncertainty_count": int(work["uncertainty_level"].astype(str).eq("MEDIUM").sum()),
        "low_uncertainty_count": int(work["uncertainty_level"].astype(str).eq("LOW").sum()),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    rows_path = out / "v2100_probability_explanation_rows.csv"
    json_path = out / "v2100_probability_explanation_summary.json"
    md_path = out / "v2100_probability_explanation_report.md"
    work.to_csv(rows_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(work, summary), encoding="utf-8")
    return {**summary, "rows_csv_path": str(rows_path.resolve()), "summary_json_path": str(json_path.resolve()), "report_md_path": str(md_path.resolve())}


def _prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    for column in ["home_win_probability", "draw_probability", "away_win_probability", "probability_edge"]:
        if column not in work.columns:
            work[column] = 0.0
        work[column] = pd.to_numeric(work[column], errors="coerce").fillna(0.0)
    for column, default in {
        "top_probability_outcome": "UNKNOWN",
        "uncertainty_level": "HIGH",
        "base_probability_explanation": "",
        "goal_difference_shadow_explanation": "",
        "goals_for_shadow_explanation": "",
        "goals_against_shadow_explanation": "",
        "signal_alignment_summary": "",
        "signal_conflict_summary": "",
    }.items():
        if column not in work.columns:
            work[column] = default
    return work


def _markdown(work: pd.DataFrame, summary: dict[str, object]) -> str:
    lines = [
        "# v2.10.0 Probability Explanation Report",
        "",
        "## Safety",
        "- automatic_betting_enabled=false",
        "- staking_logic_enabled=false",
        "- roi_logic_enabled=false",
        "- No productive betting logic",
        "",
        "## Executive Summary",
        f"- rows_analyzed: {summary['rows_analyzed']}",
        f"- probability_rows_count: {summary['probability_rows_count']}",
        f"- top_probability_home_count: {summary['top_probability_home_count']}",
        f"- top_probability_draw_count: {summary['top_probability_draw_count']}",
        f"- top_probability_away_count: {summary['top_probability_away_count']}",
        f"- top_probability_hit_rate: {summary['top_probability_hit_rate']}",
        f"- high_uncertainty_count: {summary['high_uncertainty_count']}",
        "",
        "## Probability Distribution",
        "| Match | Home | Draw | Away | Top Outcome | Edge | Uncertainty |",
        "| --- | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for _, row in work.iterrows():
        match = f"{row.get('home_team', '')} vs {row.get('away_team', '')}"
        lines.append(
            f"| {match} | {_fmt(row.get('home_win_probability'))} | {_fmt(row.get('draw_probability'))} | "
            f"{_fmt(row.get('away_win_probability'))} | {row.get('top_probability_outcome', '')} | "
            f"{_fmt(row.get('probability_edge'))} | {row.get('uncertainty_level', '')} |"
        )
    lines.extend(["", "## Signal Explanation"])
    for _, row in work.iterrows():
        match = f"{row.get('home_team', '')} vs {row.get('away_team', '')}"
        lines.extend(
            [
                f"### {match}",
                f"- Base: {row.get('base_probability_explanation', '')}",
                f"- GD: {row.get('goal_difference_shadow_explanation', '')}",
                f"- GF: {row.get('goals_for_shadow_explanation', '')}",
                f"- GA: {row.get('goals_against_shadow_explanation', '')}",
                f"- Alignment: {row.get('signal_alignment_summary', '')}",
                f"- Conflict: {row.get('signal_conflict_summary', '')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Conclusion",
            "No gate prevents probability output.",
            "This report contains probabilities and explanation only.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: object) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "0.0000"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="outputs/v27_prematch_evaluation/v27_prematch_evaluation_rows.csv")
    parser.add_argument("--output-dir", default="outputs/v2100_probability_explanation_report")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = generate_probability_explanation_report(args.rows, args.output_dir)
    for key in [
        "v2100_probability_explanation_report_status",
        "rows_analyzed",
        "probability_rows_count",
        "top_probability_home_count",
        "top_probability_draw_count",
        "top_probability_away_count",
        "top_probability_hit_rate",
        "average_home_probability",
        "average_draw_probability",
        "average_away_probability",
        "high_uncertainty_count",
        "medium_uncertainty_count",
        "low_uncertainty_count",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
