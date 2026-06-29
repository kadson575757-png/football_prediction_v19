# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def analyze_promising_indicator_mix(rows: str | Path, output_dir: str | Path = "outputs/v298_promising_indicator_mix") -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(rows, keep_default_na=False)
    work = prepare_promising_mix_frame(frame)
    mix_summaries: list[dict[str, object]] = []
    selected = None
    for gd_weight in [0.0, 0.25, 0.5, 0.75, 1.0]:
        for gf_weight in [0.0, 0.25, 0.5, 0.75, 1.0]:
            for ga_weight in [0.0, 0.25, 0.5, 0.75, 1.0]:
                name = f"grid_gd_{gd_weight}_gf_{gf_weight}_ga_{ga_weight}"
                mixed = apply_promising_indicator_mix(work, gd_weight=gd_weight, gf_weight=gf_weight, ga_weight=ga_weight, mix_name=name)
                mix_summaries.append(_mix_summary(mixed, name, gd_weight, gf_weight, ga_weight))
                if gd_weight == 0.5 and gf_weight == 0.5 and ga_weight == 0.5:
                    selected = mixed
    if selected is None:
        selected = apply_promising_indicator_mix(work, gd_weight=0.5, gf_weight=0.5, ga_weight=0.5, mix_name="grid_gd_0.5_gf_0.5_ga_0.5")
    best = max(mix_summaries, key=lambda item: (float(item["hit_rate"]), int(item["decision_count"]))) if mix_summaries else {}
    base_hit_rate = _shadow_hit_rate(work, "base_shadow_predicted_winner")
    gd_hit_rate = _shadow_hit_rate(work, "gd_shadow_predicted_winner")
    gf_hit_rate = _shadow_hit_rate(work, "gf_shadow_predicted_winner")
    ga_hit_rate = _shadow_hit_rate(work, "ga_shadow_predicted_winner")
    combined_decisions = selected["combined_shadow_result"].astype(str).isin(["HIT", "MISS"])
    summary = {
        "v298_promising_indicator_mix_status": "READY",
        "rows_analyzed": int(len(work)),
        "base_hit_rate": base_hit_rate,
        "gd_shadow_hit_rate": gd_hit_rate,
        "gf_shadow_hit_rate": gf_hit_rate,
        "ga_shadow_hit_rate": ga_hit_rate,
        "combined_shadow_hit_rate": _rate(int(selected["combined_shadow_result"].astype(str).eq("HIT").sum()), int(combined_decisions.sum())),
        "combined_shadow_decision_count": int(combined_decisions.sum()),
        "combined_shadow_hit_count": int(selected["combined_shadow_result"].astype(str).eq("HIT").sum()),
        "combined_shadow_miss_count": int(selected["combined_shadow_result"].astype(str).eq("MISS").sum()),
        "combined_shadow_no_clear_winner_count": int(selected["combined_shadow_result"].astype(str).eq("NO_CLEAR_WINNER").sum()),
        "best_mix_name": best.get("mix_name", ""),
        "best_mix_hit_rate": best.get("hit_rate", 0.0),
        "best_gd_weight": best.get("gd_weight", 0.0),
        "best_gf_weight": best.get("gf_weight", 0.0),
        "best_ga_weight": best.get("ga_weight", 0.0),
        "recommendation": _recommendation(best, base_hit_rate, gd_hit_rate, gf_hit_rate, ga_hit_rate),
        "mix_summaries": mix_summaries,
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    rows_path = out / "v298_promising_indicator_mix_rows.csv"
    json_path = out / "v298_promising_indicator_mix_summary.json"
    md_path = out / "v298_promising_indicator_mix_report.md"
    selected.to_csv(rows_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(summary), encoding="utf-8")
    return {**summary, "rows_csv_path": str(rows_path.resolve()), "summary_json_path": str(json_path.resolve()), "report_md_path": str(md_path.resolve())}


def prepare_promising_mix_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    defaults = {
        "base_home_win_probability": "home_win_probability",
        "base_draw_probability": "draw_probability",
        "base_away_probability": "away_win_probability",
        "gd_adjusted_home_win_probability": "base_home_win_probability",
        "gd_adjusted_draw_probability": "base_draw_probability",
        "gd_adjusted_away_probability": "base_away_probability",
        "gf_adjusted_home_win_probability": "base_home_win_probability",
        "gf_adjusted_draw_probability": "base_draw_probability",
        "gf_adjusted_away_probability": "base_away_probability",
        "ga_adjusted_home_win_probability": "base_home_win_probability",
        "ga_adjusted_draw_probability": "base_draw_probability",
        "ga_adjusted_away_probability": "base_away_probability",
    }
    for column, fallback in defaults.items():
        if column not in work.columns:
            work[column] = work.get(fallback, 0.0)
    for column in defaults:
        work[column] = pd.to_numeric(work[column], errors="coerce").fillna(0.0)
    work["gd_home_delta"] = work["gd_adjusted_home_win_probability"] - work["base_home_win_probability"]
    work["gd_away_delta"] = work["gd_adjusted_away_probability"] - work["base_away_probability"]
    work["gf_home_delta"] = work["gf_adjusted_home_win_probability"] - work["base_home_win_probability"]
    work["gf_away_delta"] = work["gf_adjusted_away_probability"] - work["base_away_probability"]
    work["ga_home_delta"] = work["ga_adjusted_home_win_probability"] - work["base_home_win_probability"]
    work["ga_away_delta"] = work["ga_adjusted_away_probability"] - work["base_away_probability"]
    work["base_shadow_predicted_winner"] = [combined_shadow_predicted_winner(home, away) for home, away in zip(work["base_home_win_probability"], work["base_away_probability"], strict=False)]
    work["gd_shadow_predicted_winner"] = [combined_shadow_predicted_winner(home, away) for home, away in zip(work["gd_adjusted_home_win_probability"], work["gd_adjusted_away_probability"], strict=False)]
    work["gf_shadow_predicted_winner"] = [combined_shadow_predicted_winner(home, away) for home, away in zip(work["gf_adjusted_home_win_probability"], work["gf_adjusted_away_probability"], strict=False)]
    work["ga_shadow_predicted_winner"] = [combined_shadow_predicted_winner(home, away) for home, away in zip(work["ga_adjusted_home_win_probability"], work["ga_adjusted_away_probability"], strict=False)]
    return work


def apply_promising_indicator_mix(frame: pd.DataFrame, *, gd_weight: float, gf_weight: float, ga_weight: float, mix_name: str = "custom") -> pd.DataFrame:
    work = frame.copy()
    home_delta = (work["gd_home_delta"] * gd_weight + work["gf_home_delta"] * gf_weight + work["ga_home_delta"] * ga_weight).clip(-0.08, 0.08)
    away_delta = (work["gd_away_delta"] * gd_weight + work["gf_away_delta"] * gf_weight + work["ga_away_delta"] * ga_weight).clip(-0.08, 0.08)
    home = (work["base_home_win_probability"] + home_delta).clip(lower=0.01)
    draw = work["base_draw_probability"].clip(lower=0.01)
    away = (work["base_away_probability"] + away_delta).clip(lower=0.01)
    total = home + draw + away
    work["combined_shadow_mix_name"] = mix_name
    work["combined_shadow_gd_weight"] = gd_weight
    work["combined_shadow_gf_weight"] = gf_weight
    work["combined_shadow_ga_weight"] = ga_weight
    work["combined_shadow_home_probability"] = (home / total).round(4)
    work["combined_shadow_draw_probability"] = (draw / total).round(4)
    work["combined_shadow_away_probability"] = (1.0 - work["combined_shadow_home_probability"] - work["combined_shadow_draw_probability"]).round(4)
    work["combined_shadow_predicted_winner"] = [combined_shadow_predicted_winner(home_prob, away_prob) for home_prob, away_prob in zip(work["combined_shadow_home_probability"], work["combined_shadow_away_probability"], strict=False)]
    work["combined_shadow_result"] = [_winner_result(predicted, real) for predicted, real in zip(work["combined_shadow_predicted_winner"], work.get("real_result", ""), strict=False)]
    return work


def combined_shadow_predicted_winner(home_probability: object, away_probability: object) -> str:
    home = _num(home_probability)
    away = _num(away_probability)
    diff = round(home - away, 4)
    if diff >= 0.04:
        return "HOME"
    if diff <= -0.04:
        return "AWAY"
    return "NO_CLEAR_WINNER"


def _mix_summary(frame: pd.DataFrame, mix_name: str, gd_weight: float, gf_weight: float, ga_weight: float) -> dict[str, object]:
    decisions = frame["combined_shadow_result"].astype(str).isin(["HIT", "MISS"])
    hits = frame["combined_shadow_result"].astype(str).eq("HIT")
    return {
        "mix_name": mix_name,
        "gd_weight": gd_weight,
        "gf_weight": gf_weight,
        "ga_weight": ga_weight,
        "decision_count": int(decisions.sum()),
        "hit_count": int(hits.sum()),
        "miss_count": int(frame["combined_shadow_result"].astype(str).eq("MISS").sum()),
        "hit_rate": _rate(int(hits.sum()), int(decisions.sum())),
    }


def _shadow_hit_rate(frame: pd.DataFrame, predicted_column: str) -> float:
    if predicted_column not in frame.columns:
        return 0.0
    results = [_winner_result(predicted, real) for predicted, real in zip(frame[predicted_column], frame.get("real_result", ""), strict=False)]
    decisions = [value for value in results if value in {"HIT", "MISS"}]
    hits = [value for value in decisions if value == "HIT"]
    return _rate(len(hits), len(decisions))


def _winner_result(predicted: object, real_result: object) -> str:
    predicted_text = str(predicted)
    real_text = str(real_result)
    if predicted_text == "NO_CLEAR_WINNER":
        return "NO_CLEAR_WINNER"
    if predicted_text == "HOME":
        return "HIT" if real_text == "HOME_WIN" else ("MISS" if real_text in {"AWAY_WIN", "DRAW"} else "RESULT_UNKNOWN")
    if predicted_text == "AWAY":
        return "HIT" if real_text == "AWAY_WIN" else ("MISS" if real_text in {"HOME_WIN", "DRAW"} else "RESULT_UNKNOWN")
    return "RESULT_UNKNOWN"


def _recommendation(best: dict[str, object], base_hit_rate: float, gd_hit_rate: float, gf_hit_rate: float, ga_hit_rate: float) -> str:
    if not best or int(best.get("decision_count", 0)) == 0:
        return "KEEP_SHADOW_ONLY"
    if float(best.get("hit_rate", 0.0)) > max(base_hit_rate, gd_hit_rate, gf_hit_rate, ga_hit_rate):
        return "PROMISING_MIX_PROMISING"
    return "PROMISING_MIX_NOT_HELPFUL"


def _rate(numerator: int, denominator: int) -> float:
    return round(float(numerator / denominator), 4) if denominator else 0.0


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _markdown(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# v2.9.8 Promising Indicator Mix Probe",
            "",
            f"- rows_analyzed: {summary['rows_analyzed']}",
            f"- base_hit_rate: {summary['base_hit_rate']}",
            f"- gd_shadow_hit_rate: {summary['gd_shadow_hit_rate']}",
            f"- gf_shadow_hit_rate: {summary['gf_shadow_hit_rate']}",
            f"- ga_shadow_hit_rate: {summary['ga_shadow_hit_rate']}",
            f"- combined_shadow_hit_rate: {summary['combined_shadow_hit_rate']}",
            f"- best_mix_name: {summary['best_mix_name']}",
            f"- best_mix_hit_rate: {summary['best_mix_hit_rate']}",
            f"- recommendation: {summary['recommendation']}",
            "",
            "Diagnostic-only probe. Final runner probabilities are not changed.",
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
    parser.add_argument("--output-dir", default="outputs/v298_promising_indicator_mix")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_promising_indicator_mix(args.rows, args.output_dir)
    for key in [
        "v298_promising_indicator_mix_status",
        "rows_analyzed",
        "base_hit_rate",
        "gd_shadow_hit_rate",
        "gf_shadow_hit_rate",
        "ga_shadow_hit_rate",
        "combined_shadow_hit_rate",
        "combined_shadow_decision_count",
        "combined_shadow_hit_count",
        "combined_shadow_miss_count",
        "combined_shadow_no_clear_winner_count",
        "best_mix_name",
        "best_mix_hit_rate",
        "best_gd_weight",
        "best_gf_weight",
        "best_ga_weight",
        "recommendation",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
