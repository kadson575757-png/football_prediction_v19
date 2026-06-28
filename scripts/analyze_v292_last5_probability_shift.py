# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def analyze_last5_probability_shift(rows: str | Path, output_dir: str | Path = "outputs/v292_last5_probability_shift") -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    work = pd.read_csv(rows, keep_default_na=False)
    shadow_map = {
        "last5_adjusted_home_win_probability": "home_win_probability",
        "last5_adjusted_draw_probability": "draw_probability",
        "last5_adjusted_away_probability": "away_win_probability",
    }
    for target, fallback in shadow_map.items():
        if target not in work.columns:
            work[target] = work.get(fallback, 0)
    for column in ["base_home_win_probability", "base_draw_probability", "base_away_probability", "last5_adjusted_home_win_probability", "last5_adjusted_draw_probability", "last5_adjusted_away_probability"]:
        work[column] = pd.to_numeric(work.get(column, 0), errors="coerce").fillna(0.0)
    work["home_shift"] = work["last5_adjusted_home_win_probability"] - work["base_home_win_probability"]
    work["draw_shift"] = work["last5_adjusted_draw_probability"] - work["base_draw_probability"]
    work["away_shift"] = work["last5_adjusted_away_probability"] - work["base_away_probability"]
    applied = work.get("last5_adjustment_applied", pd.Series([False] * len(work))).astype(str).str.lower().isin(["true", "1", "yes"])
    decisions = work["evaluation_result"].astype(str).isin(["HIT", "MISS"]) if "evaluation_result" in work else pd.Series([False] * len(work))
    hits = work["evaluation_result"].astype(str).eq("HIT") if "evaluation_result" in work else pd.Series([False] * len(work))
    summary = {
        "v292_last5_probability_shift_status": "READY",
        "rows_analyzed": int(len(work)),
        "last5_adjustment_applied_count": int(applied.sum()),
        "average_home_shift": round(float(work["home_shift"].mean()), 4) if not work.empty else 0.0,
        "average_away_shift": round(float(work["away_shift"].mean()), 4) if not work.empty else 0.0,
        "average_draw_shift": round(float(work["draw_shift"].mean()), 4) if not work.empty else 0.0,
        "biggest_home_last5_upgrades": _top_rows(work, "home_shift"),
        "biggest_away_last5_upgrades": _top_rows(work, "away_shift"),
        "unchanged_count": int((~applied).sum()),
        "hit_count": int(hits.sum()),
        "miss_count": int(work["evaluation_result"].astype(str).eq("MISS").sum()) if "evaluation_result" in work else 0,
        "hit_rate": _rate(int(hits.sum()), int(decisions.sum())),
        "hit_rate_last5_adjusted_rows": _rate(int((hits & applied).sum()), int((decisions & applied).sum())),
        "hit_rate_last5_unchanged_rows": _rate(int((hits & ~applied).sum()), int((decisions & ~applied).sum())),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    rows_path = out / "v292_last5_probability_shift_rows.csv"
    json_path = out / "v292_last5_probability_shift_summary.json"
    md_path = out / "v292_last5_probability_shift_report.md"
    work.to_csv(rows_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(summary), encoding="utf-8")
    return {**summary, "rows_csv_path": str(rows_path.resolve()), "summary_json_path": str(json_path.resolve()), "report_md_path": str(md_path.resolve())}


def _top_rows(frame: pd.DataFrame, column: str) -> list[dict[str, object]]:
    cols = ["competition", "home_team", "away_team", "match_date", column, "last5_points_diff"]
    available = [col for col in cols if col in frame.columns]
    return frame.sort_values(column, ascending=False).head(5)[available].to_dict(orient="records") if not frame.empty else []


def _rate(numerator: int, denominator: int) -> float:
    return round(float(numerator / denominator), 4) if denominator else 0.0


def _markdown(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# v2.9.2 Last-5 Form Probability Shift",
            "",
            f"- rows_analyzed: {summary['rows_analyzed']}",
            f"- last5_adjustment_applied_count: {summary['last5_adjustment_applied_count']}",
            f"- average_home_shift: {summary['average_home_shift']}",
            f"- average_away_shift: {summary['average_away_shift']}",
            f"- average_draw_shift: {summary['average_draw_shift']}",
            f"- hit_rate: {summary['hit_rate']}",
            "",
            "## Safety",
            "- automatic_betting_enabled: false",
            "- staking_logic_enabled: false",
            "- roi_logic_enabled: false",
            "",
            "No betting metrics, no stake, no ROI, no profit, no yield, no bankroll logic.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="outputs/v27_prematch_evaluation/v27_prematch_evaluation_rows.csv")
    parser.add_argument("--output-dir", default="outputs/v292_last5_probability_shift")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_last5_probability_shift(args.rows, args.output_dir)
    for key in [
        "v292_last5_probability_shift_status",
        "rows_analyzed",
        "last5_adjustment_applied_count",
        "average_home_shift",
        "average_away_shift",
        "average_draw_shift",
        "hit_rate",
        "hit_rate_last5_adjusted_rows",
        "hit_rate_last5_unchanged_rows",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
