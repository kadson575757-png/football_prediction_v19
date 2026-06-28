# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

MIXES: dict[str, tuple[float, float]] = {
    "base_only": (0.0, 0.0),
    "balanced_half_ppg_half_last5": (0.5, 0.5),
    "full_ppg_full_last5": (1.0, 1.0),
    "light_ppg_heavy_last5": (0.25, 0.75),
    "heavy_ppg_light_last5": (0.75, 0.25),
}


def analyze_combined_shadow_mix(rows: str | Path, output_dir: str | Path = "outputs/v293_combined_shadow_mix") -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(rows, keep_default_na=False)
    work = prepare_shadow_mix_frame(frame)
    mix_summaries: list[dict[str, object]] = []
    selected = None
    for name, (ppg_weight, last5_weight) in _mix_grid().items():
        mixed = apply_combined_shadow_mix(work, ppg_weight=ppg_weight, last5_weight=last5_weight, mix_name=name)
        mix_summaries.append(_mix_summary(mixed, name, ppg_weight, last5_weight))
        if name == "balanced_half_ppg_half_last5":
            selected = mixed
    if selected is None:
        selected = apply_combined_shadow_mix(work, ppg_weight=0.5, last5_weight=0.5, mix_name="balanced_half_ppg_half_last5")
    best = max(mix_summaries, key=lambda item: (float(item["hit_rate"]), int(item["decision_count"]))) if mix_summaries else {}
    base_hit_rate = _shadow_hit_rate(work, "base_shadow_predicted_winner")
    ppg_hit_rate = _shadow_hit_rate(work, "ppg_shadow_predicted_winner")
    last5_hit_rate = _shadow_hit_rate(work, "last5_shadow_predicted_winner")
    combined_decisions = selected["combined_shadow_result"].astype(str).isin(["HIT", "MISS"])
    summary = {
        "v293_combined_shadow_mix_status": "READY",
        "rows_analyzed": int(len(work)),
        "base_hit_rate": base_hit_rate,
        "ppg_shadow_hit_rate": ppg_hit_rate,
        "last5_shadow_hit_rate": last5_hit_rate,
        "combined_shadow_hit_rate": _rate(int(selected["combined_shadow_result"].astype(str).eq("HIT").sum()), int(combined_decisions.sum())),
        "combined_shadow_decision_count": int(combined_decisions.sum()),
        "combined_shadow_hit_count": int(selected["combined_shadow_result"].astype(str).eq("HIT").sum()),
        "combined_shadow_miss_count": int(selected["combined_shadow_result"].astype(str).eq("MISS").sum()),
        "combined_shadow_no_clear_winner_count": int(selected["combined_shadow_result"].astype(str).eq("NO_CLEAR_WINNER").sum()),
        "best_mix_name": best.get("mix_name", ""),
        "best_mix_hit_rate": best.get("hit_rate", 0.0),
        "best_ppg_weight": best.get("ppg_weight", 0.0),
        "best_last5_weight": best.get("last5_weight", 0.0),
        "recommendation": _recommendation(best, base_hit_rate, ppg_hit_rate, last5_hit_rate),
        "mix_summaries": mix_summaries,
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    rows_path = out / "v293_combined_shadow_mix_rows.csv"
    json_path = out / "v293_combined_shadow_mix_summary.json"
    md_path = out / "v293_combined_shadow_mix_report.md"
    selected.to_csv(rows_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(summary), encoding="utf-8")
    return {**summary, "rows_csv_path": str(rows_path.resolve()), "summary_json_path": str(json_path.resolve()), "report_md_path": str(md_path.resolve())}


def prepare_shadow_mix_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    defaults = {
        "base_home_win_probability": "home_win_probability",
        "base_draw_probability": "draw_probability",
        "base_away_probability": "away_win_probability",
        "ppg_adjusted_home_win_probability": "base_home_win_probability",
        "ppg_adjusted_draw_probability": "base_draw_probability",
        "ppg_adjusted_away_probability": "base_away_probability",
        "last5_adjusted_home_win_probability": "base_home_win_probability",
        "last5_adjusted_draw_probability": "base_draw_probability",
        "last5_adjusted_away_probability": "base_away_probability",
    }
    for column, fallback in defaults.items():
        if column not in work.columns:
            work[column] = work.get(fallback, 0.0)
    for column in defaults:
        work[column] = pd.to_numeric(work[column], errors="coerce").fillna(0.0)
    work["ppg_home_delta"] = work["ppg_adjusted_home_win_probability"] - work["base_home_win_probability"]
    work["ppg_away_delta"] = work["ppg_adjusted_away_probability"] - work["base_away_probability"]
    work["last5_home_delta"] = work["last5_adjusted_home_win_probability"] - work["base_home_win_probability"]
    work["last5_away_delta"] = work["last5_adjusted_away_probability"] - work["base_away_probability"]
    work["base_shadow_predicted_winner"] = [
        combined_shadow_predicted_winner(home, away)
        for home, away in zip(work["base_home_win_probability"], work["base_away_probability"], strict=False)
    ]
    work["ppg_shadow_predicted_winner"] = [
        combined_shadow_predicted_winner(home, away)
        for home, away in zip(work["ppg_adjusted_home_win_probability"], work["ppg_adjusted_away_probability"], strict=False)
    ]
    work["last5_shadow_predicted_winner"] = [
        combined_shadow_predicted_winner(home, away)
        for home, away in zip(work["last5_adjusted_home_win_probability"], work["last5_adjusted_away_probability"], strict=False)
    ]
    return work


def apply_combined_shadow_mix(frame: pd.DataFrame, *, ppg_weight: float, last5_weight: float, mix_name: str = "custom") -> pd.DataFrame:
    work = frame.copy()
    home_delta = (work["ppg_home_delta"] * ppg_weight + work["last5_home_delta"] * last5_weight).clip(-0.06, 0.06)
    away_delta = (work["ppg_away_delta"] * ppg_weight + work["last5_away_delta"] * last5_weight).clip(-0.06, 0.06)
    home = (work["base_home_win_probability"] + home_delta).clip(lower=0.01)
    draw = work["base_draw_probability"].clip(lower=0.01)
    away = (work["base_away_probability"] + away_delta).clip(lower=0.01)
    total = home + draw + away
    work["combined_shadow_mix_name"] = mix_name
    work["combined_shadow_ppg_weight"] = ppg_weight
    work["combined_shadow_last5_weight"] = last5_weight
    work["combined_shadow_home_probability"] = (home / total).round(4)
    work["combined_shadow_draw_probability"] = (draw / total).round(4)
    work["combined_shadow_away_probability"] = (1.0 - work["combined_shadow_home_probability"] - work["combined_shadow_draw_probability"]).round(4)
    work["combined_shadow_predicted_winner"] = [
        combined_shadow_predicted_winner(home_prob, away_prob)
        for home_prob, away_prob in zip(work["combined_shadow_home_probability"], work["combined_shadow_away_probability"], strict=False)
    ]
    work["combined_shadow_result"] = [
        _winner_result(predicted, real)
        for predicted, real in zip(work["combined_shadow_predicted_winner"], work.get("real_result", ""), strict=False)
    ]
    return work


def combined_shadow_predicted_winner(home_probability: object, away_probability: object) -> str:
    home = _num(home_probability)
    away = _num(away_probability)
    if abs(home - away) < 0.04:
        return "NO_CLEAR_WINNER"
    return "HOME" if home > away else "AWAY"


def _mix_grid() -> dict[str, tuple[float, float]]:
    mixes = dict(MIXES)
    for ppg_weight in [0.0, 0.25, 0.5, 0.75, 1.0]:
        for last5_weight in [0.0, 0.25, 0.5, 0.75, 1.0]:
            mixes.setdefault(f"grid_ppg_{ppg_weight}_last5_{last5_weight}", (ppg_weight, last5_weight))
    return mixes


def _mix_summary(frame: pd.DataFrame, mix_name: str, ppg_weight: float, last5_weight: float) -> dict[str, object]:
    decisions = frame["combined_shadow_result"].astype(str).isin(["HIT", "MISS"])
    hits = frame["combined_shadow_result"].astype(str).eq("HIT")
    return {
        "mix_name": mix_name,
        "ppg_weight": ppg_weight,
        "last5_weight": last5_weight,
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


def _recommendation(best: dict[str, object], base_hit_rate: float, ppg_hit_rate: float, last5_hit_rate: float) -> str:
    if not best or int(best.get("decision_count", 0)) == 0:
        return "KEEP_SHADOW_ONLY"
    benchmark = max(base_hit_rate, ppg_hit_rate, last5_hit_rate)
    if float(best.get("hit_rate", 0.0)) > benchmark:
        return "COMBINED_MIX_PROMISING"
    return "COMBINED_MIX_NOT_HELPFUL"


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
            "# v2.9.3 Combined Shadow Mix Probe",
            "",
            f"- rows_analyzed: {summary['rows_analyzed']}",
            f"- base_hit_rate: {summary['base_hit_rate']}",
            f"- ppg_shadow_hit_rate: {summary['ppg_shadow_hit_rate']}",
            f"- last5_shadow_hit_rate: {summary['last5_shadow_hit_rate']}",
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
            "No betting metrics, no stake, no ROI, no yield, no bankroll logic.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="outputs/v27_prematch_evaluation/v27_prematch_evaluation_rows.csv")
    parser.add_argument("--output-dir", default="outputs/v293_combined_shadow_mix")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_combined_shadow_mix(args.rows, args.output_dir)
    for key in [
        "v293_combined_shadow_mix_status",
        "rows_analyzed",
        "base_hit_rate",
        "ppg_shadow_hit_rate",
        "last5_shadow_hit_rate",
        "combined_shadow_hit_rate",
        "best_mix_name",
        "best_mix_hit_rate",
        "best_ppg_weight",
        "best_last5_weight",
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
