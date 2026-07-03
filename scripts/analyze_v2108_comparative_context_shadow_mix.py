# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


INDICATORS = {
    "cop": "COMMON_OPPONENT_PERFORMANCE_PROFILE",
    "sbp": "STRENGTH_BAND_PERFORMANCE_PROFILE",
    "rar": "RESPONSE_AFTER_RESULT_PROFILE",
    "hre": "HEAVY_RESULT_EXPOSURE_PROFILE",
}


def analyze_comparative_context_shadow_mix(rows: str | Path, output_dir: str | Path = "outputs/v2108_comparative_context_shadow_mix") -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(rows, keep_default_na=False)
    work = _prepare(frame)
    summary = _summary(work)
    rows_path = out / "v2108_comparative_context_shadow_mix_rows.csv"
    json_path = out / "v2108_comparative_context_shadow_mix_summary.json"
    md_path = out / "v2108_comparative_context_shadow_mix_report.md"
    work.to_csv(rows_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(summary), encoding="utf-8")
    return {**summary, "rows_csv_path": str(rows_path.resolve()), "summary_json_path": str(json_path.resolve()), "report_md_path": str(md_path.resolve())}


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    for column in ["home_win_probability", "draw_probability", "away_win_probability"]:
        if column not in work.columns:
            work[column] = 0.0
        work[column] = pd.to_numeric(work[column], errors="coerce").fillna(0.0)
    work["base_shadow_top_outcome"] = [_top(h, d, a) for h, d, a in zip(work["home_win_probability"], work["draw_probability"], work["away_win_probability"], strict=False)]
    work["base_shadow_result"] = [_hit(top, real) for top, real in zip(work["base_shadow_top_outcome"], work.get("real_result", ""), strict=False)]
    for prefix in list(INDICATORS) + ["v2108_mix", "v2108_combined_mix"]:
        for suffix, base_column in [("home_win_probability", "home_win_probability"), ("draw_probability", "draw_probability"), ("away_probability", "away_win_probability")]:
            column = f"{prefix}_adjusted_{suffix}"
            legacy_column = f"{prefix}_adjusted_away_win_probability" if suffix == "away_probability" else column
            if column not in work.columns:
                work[column] = work[legacy_column] if legacy_column in work.columns else work[base_column]
            work[column] = pd.to_numeric(work[column], errors="coerce").fillna(work[base_column])
        work[f"{prefix}_shadow_top_outcome"] = [_top(h, d, a) for h, d, a in zip(work[f"{prefix}_adjusted_home_win_probability"], work[f"{prefix}_adjusted_draw_probability"], work[f"{prefix}_adjusted_away_probability"], strict=False)]
        work[f"{prefix}_shadow_result"] = [_hit(top, real) for top, real in zip(work[f"{prefix}_shadow_top_outcome"], work.get("real_result", ""), strict=False)]
    return work


def _summary(work: pd.DataFrame) -> dict[str, object]:
    base_rate = _hit_rate(work["base_shadow_result"])
    indicator_summaries = {prefix: _indicator_summary(work, prefix) for prefix in INDICATORS}
    best_prefix = max(indicator_summaries, key=lambda key: indicator_summaries[key]["shadow_top_hit_rate"]) if indicator_summaries else ""
    best_rate = indicator_summaries[best_prefix]["shadow_top_hit_rate"] if best_prefix else 0.0
    v2108_rate = _hit_rate(work["v2108_mix_shadow_result"])
    combined_rate = _hit_rate(work["v2108_combined_mix_shadow_result"])
    overall = {"v2108_mix": v2108_rate, "v2108_combined_mix": combined_rate, **{INDICATORS[k]: v["shadow_top_hit_rate"] for k, v in indicator_summaries.items()}}
    best_overall_name = max(overall, key=overall.get) if overall else ""
    summary = {
        "v2108_comparative_context_shadow_mix_status": "READY",
        "rows_analyzed": int(len(work)),
        "base_top_probability_hit_rate": base_rate,
        "v2108_mix_top_hit_rate": v2108_rate,
        "v2108_mix_top_home_count": int(work["v2108_mix_shadow_top_outcome"].eq("HOME").sum()),
        "v2108_mix_top_draw_count": int(work["v2108_mix_shadow_top_outcome"].eq("DRAW").sum()),
        "v2108_mix_top_away_count": int(work["v2108_mix_shadow_top_outcome"].eq("AWAY").sum()),
        "v2108_mix_changed_top_outcome_count": int((work["v2108_mix_shadow_top_outcome"] != work["base_shadow_top_outcome"]).sum()),
        "v2108_combined_mix_top_hit_rate": combined_rate,
        "v2108_combined_mix_top_home_count": int(work["v2108_combined_mix_shadow_top_outcome"].eq("HOME").sum()),
        "v2108_combined_mix_top_draw_count": int(work["v2108_combined_mix_shadow_top_outcome"].eq("DRAW").sum()),
        "v2108_combined_mix_top_away_count": int(work["v2108_combined_mix_shadow_top_outcome"].eq("AWAY").sum()),
        "v2108_combined_mix_changed_top_outcome_count": int((work["v2108_combined_mix_shadow_top_outcome"] != work["base_shadow_top_outcome"]).sum()),
        "best_single_indicator_name": INDICATORS.get(best_prefix, ""),
        "best_single_indicator_hit_rate": best_rate,
        "best_overall_shadow_name": best_overall_name,
        "best_overall_shadow_hit_rate": overall.get(best_overall_name, 0.0),
        "v2108_mix_vs_base_delta": round(v2108_rate - base_rate, 4),
        "v2108_combined_mix_vs_base_delta": round(combined_rate - base_rate, 4),
        "recommendation": _recommendation(base_rate, best_rate, v2108_rate, combined_rate),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    for prefix, values in indicator_summaries.items():
        summary[f"{prefix}_shadow_top_hit_rate"] = values["shadow_top_hit_rate"]
        summary[f"{prefix}_summary"] = values
    return summary


def _indicator_summary(work: pd.DataFrame, prefix: str) -> dict[str, object]:
    applied = work.get(f"{prefix}_adjustment_applied", pd.Series([False] * len(work))).astype(str).str.lower().isin(["true", "1", "yes"])
    return {"adjustment_applied_count": int(applied.sum()), "shadow_top_hit_rate": _hit_rate(work[f"{prefix}_shadow_result"]), "hit_rate_adjusted_rows": _hit_rate(work.loc[applied, f"{prefix}_shadow_result"]), "hit_rate_unchanged_rows": _hit_rate(work.loc[~applied, f"{prefix}_shadow_result"]), "average_home_shift": _avg_shift(work, prefix, "home_win_probability"), "average_draw_shift": _avg_shift(work, prefix, "draw_probability"), "average_away_shift": _avg_shift(work, prefix, "away_win_probability"), "top_home_after_count": int(work[f"{prefix}_shadow_top_outcome"].eq("HOME").sum()), "top_draw_after_count": int(work[f"{prefix}_shadow_top_outcome"].eq("DRAW").sum()), "top_away_after_count": int(work[f"{prefix}_shadow_top_outcome"].eq("AWAY").sum())}


def _recommendation(base: float, best: float, v2108: float, combined: float) -> str:
    if combined > base and combined >= max(best, v2108):
        return "V2108_COMBINED_MIX_PROMISING"
    if v2108 > base and v2108 >= best:
        return "COMPARATIVE_CONTEXT_INDICATORS_PROMISING"
    if best > base and best > max(v2108, combined):
        return "SINGLE_INDICATOR_STRONGER_THAN_MIX"
    if max(best, v2108, combined) <= base:
        return "SHADOW_INDICATORS_NOT_HELPFUL"
    return "KEEP_SHADOW_ONLY_MORE_DATA_NEEDED"


def _avg_shift(work: pd.DataFrame, prefix: str, base_col: str) -> float:
    adjusted_col = f"{prefix}_adjusted_{base_col}"
    if adjusted_col not in work.columns and base_col == "away_win_probability":
        adjusted_col = f"{prefix}_adjusted_away_probability"
    return round(float((work[adjusted_col] - work[base_col]).mean()), 4) if len(work) and adjusted_col in work.columns else 0.0


def _hit_rate(values: pd.Series) -> float:
    known = values.astype(str).isin(["HIT", "MISS"])
    return round(float(values.astype(str).eq("HIT").sum() / known.sum()), 4) if int(known.sum()) else 0.0


def _hit(top: object, real: object) -> str:
    expected = {"HOME": "HOME_WIN", "DRAW": "DRAW", "AWAY": "AWAY_WIN"}.get(str(top))
    if not expected or str(real).strip() in {"", "RESULT_UNKNOWN"}:
        return "RESULT_UNKNOWN"
    return "HIT" if str(real) == expected else "MISS"


def _top(home: object, draw: object, away: object) -> str:
    return max({"HOME": _num(home), "DRAW": _num(draw), "AWAY": _num(away)}.items(), key=lambda item: item[1])[0]


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _markdown(summary: dict[str, object]) -> str:
    return "\n".join(["# v2.10.8 Comparative Context Shadow Mix", "", f"- rows_analyzed: {summary['rows_analyzed']}", f"- base_top_probability_hit_rate: {summary['base_top_probability_hit_rate']}", f"- v2108_mix_top_hit_rate: {summary['v2108_mix_top_hit_rate']}", f"- v2108_combined_mix_top_hit_rate: {summary['v2108_combined_mix_top_hit_rate']}", f"- recommendation: {summary['recommendation']}", "", "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false."])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="outputs/v27_prematch_evaluation/v27_prematch_evaluation_rows.csv")
    parser.add_argument("--output-dir", default="outputs/v2108_comparative_context_shadow_mix")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_comparative_context_shadow_mix(args.rows, args.output_dir)
    for key in ["v2108_comparative_context_shadow_mix_status", "rows_analyzed", "base_top_probability_hit_rate", "cop_shadow_top_hit_rate", "sbp_shadow_top_hit_rate", "rar_shadow_top_hit_rate", "hre_shadow_top_hit_rate", "v2108_mix_top_hit_rate", "v2108_combined_mix_top_hit_rate", "best_single_indicator_name", "best_single_indicator_hit_rate", "best_overall_shadow_name", "best_overall_shadow_hit_rate", "v2108_mix_vs_base_delta", "v2108_combined_mix_vs_base_delta", "recommendation", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
